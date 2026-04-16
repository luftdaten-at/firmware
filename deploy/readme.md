# Deploy CircuitPython (ESP32-S3)

Flash the CircuitPython **`.bin`** with **esptool**, then copy the project tree onto the **`CIRCUITPY`** USB volume. The workflow is driven by [`deploy.ipynb`](deploy.ipynb) and [`utils.py`](utils.py).

## Quick start

### Environment with uv (recommended)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (standalone installer or `pip install uv`). Python 3.10+ is required.

From the **repository root** (parent of `deploy/`):

```bash
uv sync
```

That creates a **`.venv/`** at the **repo root** (gitignored) and installs **`esptool`**, **`jupyter`**, and **`pyserial`** from the root [`pyproject.toml`](../pyproject.toml).

Start Jupyter from the repo root; the notebook’s first code cell **`chdir`s into `deploy/`** so imports work:

```bash
uv run jupyter notebook deploy/deploy.ipynb
```

Or activate the venv and run Jupyter yourself:

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
jupyter notebook deploy/deploy.ipynb
```

In the notebook or IDE, pick the **Python interpreter** from **`<repo>/.venv`** if it is not selected automatically.

### Without uv

From the **repository root**:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install esptool jupyter pyserial
jupyter notebook deploy/deploy.ipynb
```

### Workflow

The notebook is organized as **three steps**: (1) **flash the board** (`flash_with_esptool`), (2) **copy firmware to a new board** (`copy_firmware_to_circuitpy` after `CIRCUITPY` mounts), (3) **update firmware on an existing board** (`run_update_only`). For a brand-new install you typically run 1 then 2; for an already-configured device run 3 only. **`run_full_flash`** is a shortcut for 1+2.

1. Edit **`CFG`** in [`deploy.ipynb`](deploy.ipynb) if needed, then run the **Step 1–3** cells that match your task (they are ready to run; avoid **Run all** unless you intend the full sequence).

2. **CircuitPython `.bin`**: put a build under **`deploy/bin/`** (only `*.bin` is gitignored; the folder is tracked), or let **`flash_with_esptool` / `run_full_flash`** download automatically: it picks the newest **`adafruit-circuitpython-<board_id>*.bin`** in `bin/`, else parses the [downloads index](https://downloads.circuitpython.org/bin/espressif_esp32s3_devkitc_1_n8r8/de_DE/) for your **`circuitpython_locale`**, else uses **`circuitpython_download_fallback_url`** (default is a pinned `de_DE` build). Override **`circuitpython_board_id`**, **`circuitpython_locale`**, or **`circuitpython_bin`** on **`DeployConfig`** as needed.

   If you still have images under the old **`deploy/board_firmware/`** path, move them into **`deploy/bin/`** once.

3. **ESP32-S3**: if the board does not enumerate for flashing, hold **BOOT** (or **B0**), tap **RESET**, release **RESET**, then release **BOOT**.

4. Serial port: the notebook **Configuration** section runs **`pick_serial_port_interactive(CFG)`** to list ports and choose one (default **`/dev/tty.usbmodem101`**). Examples: macOS `/dev/tty.usbmodem*`, Linux `/dev/ttyACM*` or `/dev/ttyUSB*`, Windows `COM*`. You can also call **`list_serial_ports()`** from `utils` without changing **`CFG`**.

## Layout

| Path | Purpose |
|------|---------|
| [`../pyproject.toml`](../pyproject.toml) (repo root) | Declares dependencies for **`uv sync`**; venv lives at **`<repo>/.venv`** |
| `deploy.ipynb` | Notebook — config, Step 1 flash / Step 2 new board / Step 3 update |
| `notebook_env.py` | Shared **`activate()`** so setup and serial cells find **`deploy/`** after a kernel restart |
| `utils.py` | Esptool wrapper, mount wait, tree copy, full flash / update |
| `settings.toml` | Copied to the device on **full flash** |
| `settings_backups/slot_0/` … `slot_2/` | Each holds a `settings.toml` stash for **update only** (one logical device per slot) |
| `bin/*.bin` | Board CircuitPython image for esptool (auto-downloaded or manual; `*.bin` gitignored, folder kept with `.gitkeep`) |

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

- **Step 1 — Flash the board**: `flash_with_esptool` — esptool only; **`ensure_circuitpython_bin`** resolves a `.bin` (file at `circuitpython_bin`, newest in `deploy/bin/`, index, or **`circuitpython_download_fallback_url`**).
- **Step 2 — Copy firmware to a new board**: `copy_firmware_to_circuitpy` — wait for `CIRCUITPY`, copy repo `firmware/` + `deploy/settings.toml`.
- **Step 3 — Update firmware (existing board)**: `run_update_only` — backup device `settings.toml` to `settings_backups/slot_N/`, copy `firmware/`, restore that slot file; **`settings_slot`** must be `0`, `1`, or `2`.
- **Shortcut**: `run_full_flash` = Step 1 + Step 2 (not Step 3).
