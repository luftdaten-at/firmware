# CIRCUITPY Web Deploy

Browser-based tool to copy the repo **`firmware/`** tree onto a mounted **`CIRCUITPY`** USB volume. It mirrors the copy step of [`deploy.ipynb`](../deploy.ipynb) / [`utils.py`](../utils.py) (Step 2), without serial flashing.

## Quick start

From the repository root (or from this folder):

```bash
cd tools/web-deploy
python3 -m http.server 8765
```

Open **http://localhost:8765/** in a supported browser (see below). Do **not** open `index.html` via `file://` — Chromium often blocks the File System Access API on non-secure origins.

1. **Choose source folder** — select your repo’s `firmware/` directory (must contain `code.py`).
2. **Choose CIRCUITPY folder** — select the mounted volume root (e.g. `/Volumes/CIRCUITPY` on macOS).
3. Enable **Preserve settings** for updates (default on).
4. Click **Copy firmware to device**.

After a successful copy, **eject** the volume before unplugging USB.

## What it does

| Behavior | Python equivalent |
|----------|-------------------|
| Recursive copy of `firmware/*` with ignore rules | `copy_firmware_tree` |
| Skip `.git`, `__pycache__`, `.DS_Store`, `readme.md`, `*.pyc`, etc. | `DEFAULT_IGNORE_NAMES` in `utils.py` |
| Backup + restore `settings.toml` / `startup.toml` | Simplified `copy_firmware_update` (byte-exact restore, no TOML key merge in v1) |
| Detect `boot.toml` / `code.py` on device | Notebook Step 2 messaging |
| Optional install `tools/settings.toml` | `deploy_full_flash_settings` (fetch from `../settings.toml` when served from repo) |

**Not included in v1:** esptool flash, `settings_backups/` slot folders, or deep TOML merge of new template keys. Use the Jupyter notebook for those.

## Browser support evaluation

The tool needs **read/write access to a user-selected folder on disk**. That requires the [File System Access API](https://developer.chrome.com/docs/capabilities/web-apis/file-system-access) picker methods (`showDirectoryPicker` with `createWritable`), not only the origin-private file system (OPFS).

### Recommended (full deploy)

| Browser | Desktop | Write to CIRCUITPY | Notes |
|---------|---------|-------------------|--------|
| **Google Chrome** | 86+ (105+ fully) | Yes | Primary target |
| **Microsoft Edge** | 86+ (105+ fully) | Yes | Same Chromium APIs |
| **Opera** | 72+ | Yes | Chromium-based |
| **Brave** | Varies | Often behind flag | Enable native file system / File System Access in `brave://flags` if picker is missing |

### Limited / fallback only

| Browser | Folder write | Fallback in this tool |
|---------|--------------|------------------------|
| **Firefox** | No `showDirectoryPicker` for local disk (Mozilla standards position) | Source via **folder upload**; **Download firmware ZIP** for manual unzip onto `CIRCUITPY`. Firefox 151+ has [Web Serial](https://hacks.mozilla.org/2026/05/web-serial-support-in-firefox/) but that does **not** replace mass-storage copy. |
| **Safari** (macOS / iOS) | No local-disk pickers | Same ZIP / manual copy; use Chrome or Edge on macOS for one-click deploy |
| **Chrome / Edge Android** | No desktop folder pickers | Use desktop OS or `deploy.ipynb` |

### Runtime detection

The page runs `detectCompatibility()` on load and shows a green / yellow / red panel:

- **Green** — Chromium desktop with `showDirectoryPicker`; deploy button enabled.
- **Yellow** — folder upload + ZIP only (Firefox, Safari).
- **Red** — no usable APIs; use `deploy.ipynb`.

### Why not Web Serial?

Web Serial talks to the USB **serial** interface (REPL, esptool). **`CIRCUITPY`** is a separate **USB mass-storage** volume. Copying hundreds of files is done via the filesystem, not the serial port. Adafruit’s browser esptool targets flashing `.bin`, not syncing the whole `firmware/` tree.

## Manual fallback (any browser with folder upload)

1. Use **Choose source (folder upload)** and select `firmware/`.
2. Click **Download firmware ZIP**.
3. Unzip the archive onto the root of the `CIRCUITPY` drive (merge/replace files).
4. Preserve or edit `settings.toml` / `startup.toml` manually as needed.

## Security notes

- The site only accesses folders you explicitly pick; permissions are per-origin and per-folder.
- Serve locally or from a trusted host; do not host this on a public URL without understanding that users grant folder access to that origin.
- Close Thonny, serial monitors, and other apps using the device before copying.

## Related

- Full flash + copy + settings backup merge: [`../readme.md`](../readme.md), [`../deploy.ipynb`](../deploy.ipynb)
- End-user release ZIP: [GitHub Releases](https://github.com/luftdaten-at/firmware/releases)
