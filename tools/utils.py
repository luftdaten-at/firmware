"""Deploy helpers for CircuitPython ESP32-S3 — used by deploy.ipynb. See readme.md."""

from __future__ import annotations

import ast
import copy
import errno
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

DEPLOY_DIR = Path(__file__).resolve().parent
# Per-device folders: ``settings_backups/<device_id>/`` (``device_id`` from TOML).
SETTINGS_BACKUPS_DIR = DEPLOY_DIR / "settings_backups"
UNKNOWN_DEVICE_BACKUP = "unknown"
BIN_DIR = DEPLOY_DIR / "bin"

# Used when directory index cannot be parsed (CDN errors, HTML changes).
DEFAULT_CIRCUITPYTHON_FALLBACK_URL = (
    "https://downloads.circuitpython.org/bin/espressif_esp32s3_devkitc_1_n8r8/en_GB/adafruit-circuitpython-espressif_esp32s3_devkitc_1_n8r8-en_GB-10.1.4.bin"
)

_BIN_VERSION_SUFFIX = re.compile(r"-(\d+)\.(\d+)\.(\d+)\.bin$", re.IGNORECASE)
_HREF_BIN = re.compile(r'href="([^"]+\.bin)"', re.IGNORECASE)

DEFAULT_IGNORE_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".DS_Store",
        "__pycache__",
        ".gitignore",
        ".idea",
        ".vscode",
    }
)
DEFAULT_IGNORE_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo")


def find_repo_root(start: Path | None = None) -> Path:
    """Walk parents until `firmware/code.py` exists (repository root)."""
    candidates: list[Path] = []
    if start is not None:
        p = start.resolve()
        candidates.extend([p, *p.parents])
    p = Path.cwd().resolve()
    candidates.extend([p, *p.parents])
    candidates.append(DEPLOY_DIR)
    candidates.extend(DEPLOY_DIR.parents)
    seen: set[Path] = set()
    for d in candidates:
        if d in seen:
            continue
        seen.add(d)
        if (d / "firmware" / "code.py").is_file():
            return d
    raise FileNotFoundError(
        "Could not find repo root (firmware/code.py). "
        "cd to the repository root or open Jupyter with cwd set to deploy/."
    )


def firmware_src() -> Path:
    return find_repo_root() / "firmware"


def _default_circuitpython_bin() -> Path:
    """Initial path hint; `ensure_circuitpython_bin` resolves a real file under `BIN_DIR`."""
    return BIN_DIR / "adafruit-circuitpython-espressif_esp32s3_devkitc_1_n8r8-de_DE.bin"


def _version_tuple_from_bin_filename(name: str) -> tuple[int, int, int] | None:
    m = _BIN_VERSION_SUFFIX.search(name)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _fetch_url_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "firmware-deploy/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _list_bins_from_index(board_id: str, locale: str) -> list[tuple[tuple[int, int, int], str, str]]:
    """Return (version_tuple, filename, absolute_url) from the official directory index."""
    base = f"https://downloads.circuitpython.org/bin/{board_id}/{locale}/"
    html = _fetch_url_bytes(base).decode("utf-8", errors="replace")
    out: list[tuple[tuple[int, int, int], str, str]] = []
    prefix = f"adafruit-circuitpython-{board_id}"
    for m in _HREF_BIN.finditer(html):
        href = m.group(1)
        name = href.split("/")[-1]
        if not name.lower().endswith(".bin"):
            continue
        if not name.startswith(prefix):
            continue
        ver = _version_tuple_from_bin_filename(name)
        if ver is None:
            continue
        abs_url = urljoin(base, href)
        out.append((ver, name, abs_url))
    return out


def _download_to(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = _fetch_url_bytes(url)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    tmp.write_bytes(data)
    tmp.replace(dest)
    print(f"Downloaded {url} -> {dest}", flush=True)


def _pick_newest_bin_in_dir(board_id: str, directory: Path) -> Path | None:
    prefix = f"adafruit-circuitpython-{board_id}"
    best: tuple[tuple[int, int, int], Path] | None = None
    for p in directory.glob("*.bin"):
        if not p.name.startswith(prefix):
            continue
        ver = _version_tuple_from_bin_filename(p.name)
        if ver is None:
            continue
        if best is None or ver > best[0]:
            best = (ver, p)
    return best[1] if best else None


def ensure_circuitpython_bin(cfg: DeployConfig) -> Path:
    """Use existing `cfg.circuitpython_bin`, newest matching file in `BIN_DIR`, or download from index / fallback."""
    if cfg.circuitpython_bin.is_file():
        return cfg.circuitpython_bin.resolve()

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    existing = _pick_newest_bin_in_dir(cfg.circuitpython_board_id, BIN_DIR)
    if existing is not None:
        cfg.circuitpython_bin = existing
        print(f"Using existing firmware: {existing}", flush=True)
        return existing.resolve()

    candidates: list[tuple[tuple[int, int, int], str, str]] = []
    try:
        candidates = _list_bins_from_index(
            cfg.circuitpython_board_id, cfg.circuitpython_locale
        )
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"Could not list download index ({e}); trying fallback URL.", flush=True)

    if candidates:
        candidates.sort(key=lambda x: x[0])
        _ver, name, url = candidates[-1]
        dest = BIN_DIR / name
        print(f"Downloading newest from index: {name}", flush=True)
        _download_to(url, dest)
        cfg.circuitpython_bin = dest
        return dest.resolve()

    fallback = cfg.circuitpython_download_fallback_url
    if not fallback:
        raise FileNotFoundError(
            f"No .bin in {BIN_DIR}, index listing failed or empty, and "
            "circuitpython_download_fallback_url is not set."
        )
    path_last = urlparse(fallback).path.rstrip("/").split("/")[-1]
    name = path_last if path_last.lower().endswith(".bin") else (
        f"adafruit-circuitpython-{cfg.circuitpython_board_id}-fallback.bin"
    )
    dest = BIN_DIR / name
    print(f"Downloading fallback firmware: {fallback}", flush=True)
    _download_to(fallback, dest)
    cfg.circuitpython_bin = dest
    return dest.resolve()


@dataclass
class DeployConfig:
    serial_port: str = "/dev/tty.usbmodem101"
    circuitpy_root: Path = field(default_factory=lambda: Path("/Volumes/CIRCUITPY"))
    circuitpython_bin: Path = field(default_factory=_default_circuitpython_bin)
    circuitpython_board_id: str = "espressif_esp32s3_devkitc_1_n8r8"
    circuitpython_locale: str = "de_DE"
    circuitpython_download_fallback_url: str | None = DEFAULT_CIRCUITPYTHON_FALLBACK_URL
    do_erase_flash: bool = True
    do_write_firmware: bool = True
    wait_for_circuitpy_mount: bool = True
    wait_timeout_s: float = 120.0
    poll_interval_s: float = 1.0
    do_copy_firmware_tree: bool = True
    full_flash_settings: Path = field(default_factory=lambda: DEPLOY_DIR / "settings.toml")


def run_esptool(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "esptool"] + args
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, text=True)


def wait_for_path(path: Path, *, timeout_s: float, interval_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    path = path.resolve()
    while time.monotonic() < deadline:
        if path.exists():
            print(f"Found: {path}", flush=True)
            return
        print(f"Waiting for {path} …", flush=True)
        time.sleep(interval_s)
    raise TimeoutError(f"Path did not appear within {timeout_s}s: {path}")


def _should_skip_name(name: str, *, ignore_names: Iterable[str]) -> bool:
    if name in ignore_names:
        return True
    if name.lower() == "readme.md":
        return True
    if name.endswith(DEFAULT_IGNORE_SUFFIXES):
        return True
    return False


def _collect_firmware_copy_jobs(
    src: Path, dst: Path, ign: frozenset[str]
) -> list[tuple[Path, Path]]:
    """List (source_file, dest_file) pairs for files under ``src`` (top-level walk like ``cp -r src/*``)."""
    jobs: list[tuple[Path, Path]] = []

    def walk(sub: Path, sub_dst: Path) -> None:
        if _should_skip_name(sub.name, ignore_names=ign):
            return
        if sub.is_dir():
            for child in sorted(sub.iterdir(), key=lambda p: p.name.lower()):
                walk(child, sub_dst / child.name)
        else:
            jobs.append((sub, sub_dst))

    for entry in sorted(src.iterdir(), key=lambda p: p.name.lower()):
        if _should_skip_name(entry.name, ignore_names=ign):
            continue
        walk(entry, dst / entry.name)
    return jobs


def _format_copy_progress_line(
    index: int, total: int, src_file: Path, src_root: Path, *, width: int = 100
) -> str:
    try:
        rel = str(src_file.relative_to(src_root))
    except ValueError:
        rel = src_file.name
    if len(rel) > 52:
        rel = rel[:24] + "…" + rel[-25:]
    pct = (100 * index) // total if total else 100
    line = f"Firmware copy [{index:>4}/{total}] {pct:>3}%  {rel}"
    if len(line) > width:
        line = line[: width - 1] + "…"
    return line


def copy_firmware_tree(
    src: Path,
    dst: Path,
    *,
    ignore_names: Iterable[str] | None = None,
    show_progress: bool = True,
    use_progress_bar: bool = True,
) -> None:
    """Mirror `cp -r src/* dst` with ignores at every directory level.

    When ``tqdm`` is installed (``uv sync``) and ``use_progress_bar`` is true, shows
    a notebook-friendly progress bar over files; otherwise falls back to a
    throttled one-line text progress indicator.
    """
    ign = frozenset(ignore_names or DEFAULT_IGNORE_NAMES)
    if not src.is_dir():
        raise NotADirectoryError(src)
    dst.mkdir(parents=True, exist_ok=True)

    src = src.resolve()
    jobs = _collect_firmware_copy_jobs(src, dst, ign)
    total = len(jobs)
    if total == 0:
        print(f"No files to copy under {src}", flush=True)
        return

    tqdm_cls = None
    if show_progress and use_progress_bar:
        try:
            from tqdm.auto import tqdm as tqdm_cls
        except ImportError:
            tqdm_cls = None

    if show_progress:
        print(f"Firmware copy: {total} files -> {dst}", flush=True)

    if tqdm_cls is not None:
        with tqdm_cls(jobs, desc="Firmware copy", unit="file", leave=True) as pbar:
            for sub, sub_dst in pbar:
                sub_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sub, sub_dst)
                try:
                    rel = str(sub.relative_to(src))
                except ValueError:
                    rel = sub.name
                if len(rel) > 52:
                    rel = rel[:24] + "…" + rel[-25:]
                pbar.set_postfix_str(rel, refresh=False)
    else:
        report_every = 1
        if total > 120:
            report_every = max(1, total // 60)

        for i, (sub, sub_dst) in enumerate(jobs, start=1):
            sub_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sub, sub_dst)
            if show_progress and (i == 1 or i == total or i % report_every == 0):
                line = _format_copy_progress_line(i, total, sub, src)
                end = "\n" if i == total else "\r"
                print(line + " " * max(0, 100 - len(line)), flush=True, end=end)

    if hasattr(os, "sync"):
        os.sync()
    print(f"Copied firmware tree {src} -> {dst} ({total} files)", flush=True)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Copied {src} -> {dst}", flush=True)


def sanitize_settings_backup_folder_name(device_id: str) -> str:
    """Safe single path segment for ``settings_backups/<here>/``."""
    s = "".join(
        c if (c.isalnum() or c in "-._") else "_"
        for c in (device_id or "").strip()
    ).strip("_")
    if not s:
        return UNKNOWN_DEVICE_BACKUP
    return s[:128]


def read_device_id_from_settings_toml(path: Path) -> str | None:
    """Return ``device_id`` from a ``settings.toml`` file, or ``None`` if missing / unreadable."""
    if not path.is_file():
        return None
    try:
        import tomli

        data = tomli.loads(path.read_text(encoding="utf-8"))
        val = data.get("device_id")
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None
    except Exception:
        pass
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r'^\s*device_id\s*=\s*"([^"]*)"', text, re.MULTILINE)
    if m:
        s = m.group(1).strip()
        return s if s else None
    m = re.search(r"^\s*device_id\s*=\s*'([^']*)'", text, re.MULTILINE)
    if m:
        s = m.group(1).strip()
        return s if s else None
    return None


def settings_backup_dir_for_device_id(device_id: str) -> Path:
    return SETTINGS_BACKUPS_DIR / sanitize_settings_backup_folder_name(device_id)


def backup_settings_from_device(cfg: DeployConfig) -> Path | None:
    """
    Copy ``settings.toml`` (and ``startup.toml`` if present) from CIRCUITPY into
    ``settings_backups/<device_id>/``. Returns the backup directory, or ``None`` if
    there is no ``settings.toml`` on the device.
    """
    src = cfg.circuitpy_root / "settings.toml"
    if not src.is_file():
        return None
    raw_id = read_device_id_from_settings_toml(src)
    folder_key = raw_id if raw_id else UNKNOWN_DEVICE_BACKUP
    if not raw_id:
        print(
            f"Warning: no device_id in {src}; using backup folder {UNKNOWN_DEVICE_BACKUP!r}.",
            flush=True,
        )
    dest_dir = settings_backup_dir_for_device_id(folder_key)
    dest_dir.mkdir(parents=True, exist_ok=True)
    copy_file(src, dest_dir / "settings.toml")
    startup_src = cfg.circuitpy_root / "startup.toml"
    if startup_src.is_file():
        copy_file(startup_src, dest_dir / "startup.toml")
    return dest_dir


def restore_settings_backup(cfg: DeployConfig, backup_dir: Path) -> None:
    src = backup_dir / "settings.toml"
    if not src.is_file():
        raise FileNotFoundError(src)
    copy_file(src, cfg.circuitpy_root / "settings.toml")
    startup_backup = backup_dir / "startup.toml"
    if startup_backup.is_file():
        copy_file(startup_backup, cfg.circuitpy_root / "startup.toml")


def _merge_toml_add_missing_keys(old: dict, new: dict) -> dict:
    """Deep copy of ``old``; add any key from ``new`` that is missing in ``old`` (recursive for dict values)."""
    merged = copy.deepcopy(old)
    for key, new_val in new.items():
        if key not in merged:
            merged[key] = copy.deepcopy(new_val)
        elif isinstance(merged[key], dict) and isinstance(new_val, dict):
            merged[key] = _merge_toml_add_missing_keys(merged[key], new_val)
    return merged


def _list_toml_keys_added_by_merge(old: dict, new: dict, prefix: str = "") -> list[str]:
    """Human-readable paths for keys present in ``new`` but not in ``old`` (recursive)."""
    added: list[str] = []
    for key, new_val in new.items():
        label = f"{prefix}.{key}" if prefix else str(key)
        if key not in old:
            added.append(label)
        elif isinstance(old.get(key), dict) and isinstance(new_val, dict):
            added.extend(_list_toml_keys_added_by_merge(old[key], new_val, label))
    return added


def _merge_toml_template_into_backup(
    backup_path: Path,
    template_path: Path,
    log_label: str,
) -> None:
    """Merge repo template on CIRCUITPY into slot backup: keep backup values, add missing keys from template."""
    if not backup_path.is_file():
        print(f"{log_label} merge: no backup at {backup_path}; skipping.", flush=True)
        return
    if not template_path.is_file():
        print(
            f"No {template_path.name} on device after copy; skipping {log_label} merge.",
            flush=True,
        )
        return
    try:
        import tomli
        import tomli_w
    except ImportError:
        print(f"tomli/tomli-w missing (run ``uv sync``); skipping {log_label} merge.", flush=True)
        return

    try:
        old_data = tomli.loads(backup_path.read_text(encoding="utf-8"))
    except Exception as ex:
        raise ValueError(f"Could not parse backup {backup_path}: {ex}") from ex

    try:
        new_data = tomli.loads(template_path.read_text(encoding="utf-8"))
    except Exception as ex:
        print(
            f"Warning: could not parse template {template_path}: {ex}; "
            f"keeping {log_label} backup unchanged.",
            flush=True,
        )
        return

    added = _list_toml_keys_added_by_merge(old_data, new_data)
    if not added:
        print(f"{log_label} merge: no new keys in repo template (backup unchanged).", flush=True)
        return

    merged = _merge_toml_add_missing_keys(old_data, new_data)
    tmp = backup_path.with_suffix(".toml.merged.tmp")
    try:
        tmp.write_text(tomli_w.dumps(merged), encoding="utf-8")
        tmp.replace(backup_path)
    except Exception:
        if tmp.is_file():
            tmp.unlink(missing_ok=True)
        raise

    preview = ", ".join(added[:24])
    if len(added) > 24:
        preview += ", …"
    print(
        f"{log_label} merge: added {len(added)} key(s) from repo template into backup: {preview}",
        flush=True,
    )


def merge_repo_settings_into_backup(cfg: DeployConfig, backup_dir: Path) -> None:
    """After ``copy_firmware_tree``, merge repo ``settings.toml`` on CIRCUITPY into the device backup."""
    _merge_toml_template_into_backup(
        backup_dir / "settings.toml",
        cfg.circuitpy_root / "settings.toml",
        "Settings",
    )


def merge_repo_startup_into_backup(cfg: DeployConfig, backup_dir: Path) -> None:
    """Merge repo ``startup.toml`` on CIRCUITPY into the device backup (same rules as settings)."""
    _merge_toml_template_into_backup(
        backup_dir / "startup.toml",
        cfg.circuitpy_root / "startup.toml",
        "Startup",
    )


def deploy_full_flash_settings(cfg: DeployConfig) -> None:
    if not cfg.full_flash_settings.is_file():
        raise FileNotFoundError(cfg.full_flash_settings)
    copy_file(cfg.full_flash_settings, cfg.circuitpy_root / "settings.toml")


def flash_with_esptool(cfg: DeployConfig) -> None:
    """Erase (optional) and write the CircuitPython `.bin` over serial; does not touch `CIRCUITPY`."""
    if cfg.do_erase_flash:
        run_esptool(["--port", cfg.serial_port, "erase_flash"])
    if cfg.do_write_firmware:
        bin_path = ensure_circuitpython_bin(cfg)
        run_esptool(
            ["--port", cfg.serial_port, "write_flash", "-z", "0x0", str(bin_path)]
        )
    print(
        "Reset the board if needed; after this, CIRCUITPY should mount for the copy step.",
        flush=True,
    )


def copy_firmware_to_circuitpy(cfg: DeployConfig) -> None:
    """Wait for the USB drive, copy repo ``firmware/`` onto it, then restore device settings.

    If ``CIRCUITPY/settings.toml`` exists before the copy, it is copied first to
    ``deploy/settings_backups/<device_id>/`` (subfolder from ``device_id`` in that file),
    the firmware tree is copied, then the backed-up ``settings.toml`` / ``startup.toml``
    are copied back onto CIRCUITPY (backup files remain under ``settings_backups/``).

    If there is no ``settings.toml`` on the device yet, ``deploy/settings.toml`` is
    installed (same as a blank new board).
    """
    if cfg.wait_for_circuitpy_mount:
        wait_for_path(
            cfg.circuitpy_root,
            timeout_s=cfg.wait_timeout_s,
            interval_s=cfg.poll_interval_s,
        )
    backup_dir = backup_settings_from_device(cfg)

    if cfg.do_copy_firmware_tree:
        copy_firmware_tree(firmware_src(), cfg.circuitpy_root)
        if backup_dir is not None:
            restore_settings_backup(cfg, backup_dir)
            print(
                f"Restored device settings from {backup_dir} (copy also kept there).",
                flush=True,
            )
        else:
            deploy_full_flash_settings(cfg)


def run_full_flash(cfg: DeployConfig) -> None:
    flash_with_esptool(cfg)
    copy_firmware_to_circuitpy(cfg)
    print("Full flash finished.", flush=True)


def run_update_only(cfg: DeployConfig) -> None:
    if not cfg.circuitpy_root.is_dir():
        raise FileNotFoundError(
            f"CIRCUITPY not mounted: {cfg.circuitpy_root} — adjust circuitpy_root or connect USB."
        )
    backup_dir = backup_settings_from_device(cfg)
    if backup_dir is None:
        raise FileNotFoundError(
            f"No {cfg.circuitpy_root / 'settings.toml'} — use copy_firmware_to_circuitpy / "
            "full flash for a new board, or create settings.toml on the device first."
        )
    copy_firmware_tree(firmware_src(), cfg.circuitpy_root)
    merge_repo_settings_into_backup(cfg, backup_dir)
    merge_repo_startup_into_backup(cfg, backup_dir)
    restore_settings_backup(cfg, backup_dir)
    print("Update finished.", flush=True)


def list_serial_ports() -> None:
    try:
        from serial.tools import list_ports
    except ImportError:
        print("Install pyserial: pip install pyserial", flush=True)
        return
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.", flush=True)
        return
    for p in ports:
        print(f"{p.device}: {p.description!r} hwid={p.hwid!r}", flush=True)


def pick_serial_port_interactive(cfg: DeployConfig) -> None:
    """List serial ports and optionally set ``cfg.serial_port`` via ``input()`` (numbered choice).

    In Jupyter, answer the prompt in the box that appears below the cell. Press Enter
    alone to keep the current ``CFG.serial_port``.
    """
    try:
        from serial.tools import list_ports
    except ImportError:
        print("Install pyserial (e.g. ``uv sync`` at repo root); keeping serial_port:", cfg.serial_port, flush=True)
        return
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found; keeping serial_port:", cfg.serial_port, flush=True)
        return
    print("Available serial ports:", flush=True)
    current = cfg.serial_port
    for i, p in enumerate(ports, 1):
        mark = "  <- current CFG.serial_port" if p.device == current else ""
        print(f"  {i}) {p.device} — {p.description!r}{mark}", flush=True)
    raw = input(
        f"Enter port number 1-{len(ports)}, or press Enter to keep {current!r}: "
    ).strip()
    if not raw:
        print("Unchanged:", cfg.serial_port, flush=True)
        return
    try:
        n = int(raw)
    except ValueError:
        print(f"Not a number: {raw!r}; keeping {cfg.serial_port!r}", flush=True)
        return
    if not 1 <= n <= len(ports):
        print(f"Out of range; keeping {cfg.serial_port!r}", flush=True)
        return
    cfg.serial_port = ports[n - 1].device
    print("Using serial_port:", cfg.serial_port, flush=True)


# Multiline code: use raw REPL (like mpremote/ampy), not “paste” (Ctrl-E) — on some
# boards paste collapses to one line, producing ``import osD``-style errors.
_REPL_BREAK = b"\x03\x03"
_RAW_REPL_START = b"\x01"  # Ctrl-A
_RAW_REPL_EXIT = b"\x02"  # Ctrl-B: leave raw, back to normal REPL
_REPL_EXEC = b"\x04"  # Ctrl-D: run script in raw REPL

# On-device and host use the same bytes. Markers are built in scripts as '__'+'CPS'+'0__' etc.
# so a Traceback/echo does not contain the same contiguous literal as in ``print('__…')``.
_CP_SEND_START_HEX = b"__" + b"CPS" + b"0__"
_CP_SEND_END = b"__" + b"CPE" + b"0__"
_CP_FILE_ERR = b"__" + b"CPF" + b"1__"
_CP_LIST_START = b"__" + b"CPL" + b"0__"


def _macos_serial_sibling_path(port: str) -> str | None:
    """``/dev/cu.usb...`` <-> ``/dev/tty.usb...`` (same device, different callout/locking rules)."""
    if sys.platform != "darwin" or not port.startswith("/dev/"):
        return None
    name = Path(port).name
    if name.startswith("cu."):
        sib = "/dev/tty." + name[3:]
    elif name.startswith("tty."):
        sib = "/dev/cu." + name[4:]
    else:
        return None
    return sib if Path(sib).exists() else None


def _serial_open_errno(exc: BaseException) -> int | None:
    if isinstance(exc, OSError) and exc.errno is not None:
        return exc.errno
    if exc.args and isinstance(exc.args[0], int):
        return exc.args[0]
    e = getattr(exc, "errno", None)
    return int(e) if e is not None else None


def _is_serial_port_busy_error(exc: BaseException) -> bool:
    if _serial_open_errno(exc) == errno.EBUSY:
        return True
    s = str(exc).lower()
    return "resource busy" in s or "device or resource busy" in s


def _lsof_for_port(path: str) -> str:
    try:
        r = subprocess.run(
            ["lsof", path],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if r.returncode != 0 or not r.stdout.strip():
        return ""
    return f"\nWho has this open (lsof {path!r}):\n{r.stdout.rstrip()}\n"


def _open_serial_for_repl(
    port: str,
    *,
    baudrate: int,
    timeout: float,
) -> Any:
    """Open a serial port, retry a few times on EBUSY, and try the macOS cu/tty sibling path."""
    import serial as serial_mod

    candidates: list[str] = [port]
    sib = _macos_serial_sibling_path(port)
    if sib and sib not in candidates:
        candidates.append(sib)
    n_retries, delay_s = 4, 0.4
    last: BaseException | None = None
    for attempt in range(n_retries):
        for p in candidates:
            try:
                return serial_mod.Serial(
                    p,
                    baudrate=baudrate,
                    timeout=timeout,
                )
            except (serial_mod.SerialException, OSError) as e:  # type: ignore[misc]
                last = e
                if not _is_serial_port_busy_error(e):
                    raise
        if attempt + 1 < n_retries:
            time.sleep(delay_s)
    if last is None:  # pragma: no cover
        raise OSError("Could not open serial port (no exception recorded)")
    tried = " and ".join(repr(p) for p in candidates) if len(candidates) > 1 else repr(port)
    details = _lsof_for_port(port) + (_lsof_for_port(sib) if sib and sib != port else "")
    msg = (
        f"Serial port is busy (errno 16) — {tried} — another program has it open.\n"
        "Close: serial monitor/terminal, Thonny, minicom, screen, esptool, or another\n"
        "Jupyter/IDE session using this port, then run again. On macOS, ejecting CIRCUITPY\n"
        "or unplugging the board briefly can help if a driver left the port stuck.\n"
    )
    raise OSError(msg + details) from last


def _cp_repl_script_to_bytes(script: str) -> bytes:
    """UTF-8 with Unix newlines, trailing newline. Raw REPL uses \\n, not ``\\r\\n``."""
    s = "\n".join(script.splitlines())
    if not s.endswith("\n"):
        s += "\n"
    return s.encode("utf-8")


def _drain_raw_repl_banner(ser: Any) -> bytearray:
    """After Ctrl-A, read until raw-REPL prompt (or a short cap)."""
    out = bytearray()
    t_end = time.monotonic() + 0.4
    while time.monotonic() < t_end:
        n = ser.in_waiting
        if n:
            out.extend(ser.read(n))
            if b"raw REPL" in out or (out.endswith(b">") and b">" in out):
                time.sleep(0.02)
                out.extend(ser.read(ser.in_waiting or 0))
                return out
        time.sleep(0.02)
    return out


def _circuitpy_repl_run_script(
    port: str,
    script: str,
    read_timeout_s: float,
    start_marker: bytes,
    end_marker: bytes,
    *,
    baudrate: int = 115200,
) -> bytearray:
    """Run a one-shot script in raw REPL; return all serial bytes up to the end marker."""
    ser = _open_serial_for_repl(
        port,
        baudrate=baudrate,
        timeout=0.1,
    )
    try:
        ser.reset_input_buffer()
        ser.write(_REPL_BREAK)
        time.sleep(0.2)
        ser.read(ser.in_waiting or 0)  # discard any interrupt text
        ser.write(_RAW_REPL_START)
        time.sleep(0.05)
        _drain_raw_repl_banner(ser)
        ser.write(_cp_repl_script_to_bytes(script))
        ser.write(_REPL_EXEC)
        out = bytearray()
        t_end = time.monotonic() + read_timeout_s
        while time.monotonic() < t_end:
            n = ser.in_waiting
            if n:
                out.extend(ser.read(n))
            if end_marker in out and start_marker in out:
                break
            time.sleep(0.02)
        if end_marker not in out or start_marker not in out:
            raise OSError(
                f"REPL read timed out after {read_timeout_s}s; last bytes: {out[-500:]!r}"
            )
        return out
    finally:
        try:
            ser.write(_RAW_REPL_EXIT)
            time.sleep(0.05)
        except OSError:
            pass
        ser.close()


def _extract_file_err_line(out: bytes) -> str | None:
    """If the device signalled a file OSError, return the repr of the error."""
    i = out.find(_CP_FILE_ERR)
    if i < 0:
        return None
    line = out[i:].split(b"\r\n", 1)[0]
    line = line.split(b"\n", 1)[0]
    if not line.startswith(_CP_FILE_ERR):
        return None
    return line[len(_CP_FILE_ERR) :].decode("utf-8", errors="replace")


def list_circuitpy_sd_repl(
    port: str,
    *,
    root: str = "/sd",
    baudrate: int = 115200,
    read_timeout_s: float = 60.0,
) -> list[str]:
    """List entry names in ``root`` (``os.listdir`` only — no isfile, for VFS compatibility)."""
    root_n = root if root == "/" else root.rstrip("/")
    d_repr = repr(root_n)
    # Build with explicit newlines: paste mode (when used) can collapse f-strings; raw
    # REPL (see _circuitpy_repl_run_script) expects real \\n line breaks.
    script = "\n".join(
        [
            "import os",
            f"D = {d_repr}",
            "S0='__'+'CPL'+'0__'",
            "E0='__'+'CPE'+'0__'",
            "F1='__'+'CPF'+'1__'",
            "print(S0)",
            "try:",
            "    r = sorted(os.listdir(D))",
            "    print(repr(r))",
            "except Exception as e:",
            "    print(F1+repr(e))",
            "print(E0)",
        ]
    )
    out = _circuitpy_repl_run_script(
        port,
        script,
        read_timeout_s,
        _CP_LIST_START,
        _CP_SEND_END,
        baudrate=baudrate,
    )
    err = _extract_file_err_line(out)
    if err is not None:
        raise OSError(f"Could not list {root!r}: {err}")
    i0 = out.find(_CP_LIST_START) + len(_CP_LIST_START)
    epos = out.find(_CP_SEND_END, i0)
    if epos < 0:
        raise OSError(f"REPL list output missing end marker: {out[-400:]!r}")
    block = out[i0:epos]
    for line in block.splitlines():
        s = line.strip()
        if not s or s.startswith(b"__"):
            continue
        st = s.decode("utf-8", errors="replace").strip()
        if st.startswith("["):
            v = ast.literal_eval(st)
            if isinstance(v, list) and all(isinstance(x, str) for x in v):
                return v
    raise OSError(f"REPL list output had no list repr: {block!r}")


def download_circuitpy_sd_with_fallback(
    port: str,
    out_dir: Path,
    *,
    primary: str = "measurements.jsonl",
    root: str = "/sd",
    baudrate: int = 115200,
    read_timeout_s: float = 300.0,
) -> list[Path]:
    """List ``root`` on the device, try to save ``primary``, then the rest if that fails.

    If ``primary`` is downloaded successfully, returns a list with that path only. If
    the primary is missing on the device or the download fails, every other regular
    file in ``root`` is downloaded into ``out_dir`` (by basename).
    """
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    names = list_circuitpy_sd_repl(
        port, root=root, baudrate=baudrate, read_timeout_s=60.0
    )
    print(f"Files in {root!r} (from listdir): {names!r}", flush=True)
    primary_path = f"{root.rstrip('/')}/{primary}"
    dest_primary = out_dir / primary
    if primary in names:
        try:
            download_circuitpy_repl_file(
                port,
                primary_path,
                dest_primary,
                baudrate=baudrate,
                read_timeout_s=read_timeout_s,
            )
            return [dest_primary]
        except OSError as e:
            print(f"Could not download {primary!r} ({primary_path!r}): {e}", flush=True)
    else:
        print(
            f"{primary!r} is not in the device listing, downloading other files instead.",
            flush=True,
        )
    out_paths: list[Path] = []
    for n in names:
        if n == primary:
            continue
        p = f"{root.rstrip('/')}/{n}"
        local = out_dir / n
        try:
            download_circuitpy_repl_file(
                port,
                p,
                local,
                baudrate=baudrate,
                read_timeout_s=read_timeout_s,
            )
            out_paths.append(local)
        except OSError as e:
            print(f"Skipped {n!r}: {e}", flush=True)
    return out_paths


def download_circuitpy_repl_file(
    port: str,
    device_path: str,
    dest: Path,
    *,
    baudrate: int = 115200,
    read_timeout_s: float = 300.0,
    chunk_bytes: int = 256,
) -> Path:
    """Read a file on the device over the CircuitPython serial REPL and save it locally.

    Uses paste mode: runs a small on-device script that prints the file as hex lines
    (safe for the REPL and large files) between sentinel markers. Interrupts a running
    ``code.py`` with Ctrl-C first.

    **Device path** must be a string the board understands (e.g. ``/sd/measurements.jsonl``).
    On macOS, use either ``/dev/cu...`` or ``/dev/tty...``; both work with ``pyserial``.
    """
    if chunk_bytes < 32:
        raise ValueError("chunk_bytes should be at least 32")
    p_repr = repr(device_path)
    h = int(chunk_bytes)
    script = "\n".join(
        [
            "import binascii",
            f"P = {p_repr}",
            f"H = {h}",
            "S0='__'+'CPS'+'0__'",
            "E0='__'+'CPE'+'0__'",
            "F1='__'+'CPF'+'1__'",
            "print(S0)",
            "try:",
            "    with open(P, 'rb') as f:",
            "        while True:",
            "            c = f.read(H)",
            "            if not c:",
            "                break",
            "            print(binascii.hexlify(c).decode('ascii'))",
            "except Exception as e:",
            "    print(F1+repr(e))",
            "print(E0)",
        ]
    )

    dest = dest.expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    out = _circuitpy_repl_run_script(
        port,
        script,
        read_timeout_s,
        _CP_SEND_START_HEX,
        _CP_SEND_END,
        baudrate=baudrate,
    )
    err = _extract_file_err_line(out)
    if err is not None:
        raise OSError(
            f"On-device file error (path {device_path!r}): {err}"
        )
    h_start = out.find(_CP_SEND_START_HEX)
    h_end = out.rfind(_CP_SEND_END)
    if h_start < 0 or h_end < 0 or h_end <= h_start:
        raise OSError(
            f"Could not find REPL send markers: tail {out[-500:]!r}"
        )
    block = out[h_start + len(_CP_SEND_START_HEX) : h_end]
    raw = b""
    for line in block.splitlines():
        s = line.strip()
        if not s or s.startswith(b"__"):
            continue
        s = s.replace(b" ", b"")
        if not s or len(s) % 2 == 1:
            continue
        try:
            raw += bytes.fromhex(s.decode("ascii"))
        except ValueError:
            continue
    tmp = dest.with_suffix(dest.suffix + ".partial")
    tmp.write_bytes(raw)
    tmp.replace(dest)
    n = dest.stat().st_size
    print(f"Saved {n} bytes -> {dest}", flush=True)
    return dest
