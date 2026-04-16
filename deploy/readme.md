# Deploy CircuitPython (ESP32-S3)

Flash the CircuitPython **`.bin`** with **esptool**, then copy the project tree onto the **`CIRCUITPY`** USB volume. The workflow is driven by [`deploy.ipynb`](deploy.ipynb) and [`utils.py`](utils.py).

## Quick start

### Environment with uv (recommended)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (standalone installer or `pip install uv`). Python 3.10+ is required.

From the **`deploy/`** directory:

```bash
cd deploy
uv sync
```

That creates a **`.venv/`** in `deploy/` (gitignored) and installs **`esptool`**, **`jupyter`**, and **`pyserial`** from [`pyproject.toml`](pyproject.toml).

Start Jupyter using that environment (kernel cwd must stay **`deploy/`** so `utils.py` imports work):

```bash
uv run jupyter notebook deploy.ipynb
```

Or activate the venv and run Jupyter yourself:

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
jupyter notebook deploy.ipynb
```

In the notebook, pick the **Python interpreter** from `deploy/.venv` if your editor does not pick it up automatically.

### Without uv

```bash
cd deploy
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install esptool jupyter pyserial
jupyter notebook deploy.ipynb
```

### Workflow

1. Edit **`CFG`** in [`deploy.ipynb`](deploy.ipynb), then uncomment the steps you need (`flash_with_esptool`, `copy_firmware_to_circuitpy`, `run_update_only`, or `run_full_flash`).

2. Download the **`.bin`** for your board from [circuitpython.org — ESP32-S3-DevKitC-1 N8R8](https://circuitpython.org/board/espressif_esp32s3_devkitc_1_n8r8/) and place it under `deploy/board_firmware/` (that directory is gitignored).

3. **ESP32-S3**: if the board does not enumerate for flashing, hold **BOOT** (or **B0**), tap **RESET**, release **RESET**, then release **BOOT**.

4. Serial port examples: macOS `/dev/tty.usbmodem*`, Linux `/dev/ttyACM*` or `/dev/ttyUSB*`, Windows `COM*` (Device Manager). Optional: run `list_serial_ports()` from `utils` in a notebook cell.

## Layout

| Path | Purpose |
|------|---------|
| `pyproject.toml` | Declares dependencies for **`uv sync`** |
| `deploy.ipynb` | Minimal notebook — config + run |
| `utils.py` | Esptool wrapper, mount wait, tree copy, full flash / update |
| `settings.toml` | Copied to the device on **full flash** |
| `settings_backups/slot_0/` … `slot_2/` | Each holds a `settings.toml` stash for **update only** (one logical device per slot) |
| `board_firmware/*.bin` | Board CircuitPython image for esptool (gitignored) |

## Deployment notes

### UF2 boards (SAMD, RP2040, many others)

Install by copying a **`.uf2`** to a **BOOT** USB volume (often **double-tap reset**). Wait for **`CIRCUITPY`**. See [circuitpython.org](https://circuitpython.org) and board docs. This repo’s **ESP32-S3** path uses **`.bin` + esptool**, not UF2 for the core image.

### ESP32 + esptool

Per [Adafruit — CircuitPython on ESP32 Quick Start (esptool)](https://learn.adafruit.com/circuitpython-with-esp32-quick-start/command-line-esptool):

- Use the correct **serial port**.
- **`erase_flash`** before a full install checks the link and clears stale flash layout.
- Flash with **`write_flash -z 0x0 firmware.bin`** for the combined CircuitPython image at **`0x0`** (other firmware may use different offsets).
- **Reset or power-cycle** after flashing.

### Copying to `CIRCUITPY`

- Wait until the volume is mounted (the notebook can **poll** via `wait_for_path`).
- After copying, **sync / eject** before unplugging to protect the FAT filesystem.
- Avoid heavy host writes while `code.py` is running if you see corruption; prefer a clean boot or REPL when needed.

### Libraries

This flow copies the whole [`../firmware/`](../firmware/) tree. For day-to-day libraries, consider **`circup`** (see [`../firmware/readme.md`](../firmware/readme.md)).

## Pipelines

- **Full flash**: `run_full_flash` in [`utils.py`](utils.py) runs esptool then USB copy, or run the same steps separately: `flash_with_esptool` then `copy_firmware_to_circuitpy`.
- **Update only**: copy device `settings.toml` → `deploy/settings_backups/slot_N/settings.toml`, refresh firmware tree from the repo, restore that file to the device. **`settings_slot`** (`N`) must be `0`, `1`, or `2`.
