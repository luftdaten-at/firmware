"""Deploy helpers for CircuitPython ESP32-S3 — used by deploy.ipynb. See readme.md."""

from __future__ import annotations

import copy
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
from typing import Iterable
from urllib.parse import urljoin, urlparse

DEPLOY_DIR = Path(__file__).resolve().parent
SETTINGS_BACKUPS_DIR = DEPLOY_DIR / "settings_backups"
BIN_DIR = DEPLOY_DIR / "bin"

# Used when directory index cannot be parsed (CDN errors, HTML changes).
DEFAULT_CIRCUITPYTHON_FALLBACK_URL = (
    "https://downloads.circuitpython.org/bin/espressif_esp32s3_devkitc_1_n8r8/de_DE/"
    "adafruit-circuitpython-espressif_esp32s3_devkitc_1_n8r8-de_DE-10.1.4.bin"
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
    settings_slot: int = 0
    do_erase_flash: bool = True
    do_write_firmware: bool = True
    wait_for_circuitpy_mount: bool = True
    wait_timeout_s: float = 120.0
    poll_interval_s: float = 1.0
    do_copy_firmware_tree: bool = True
    full_flash_settings: Path = field(default_factory=lambda: DEPLOY_DIR / "settings.toml")

    def __post_init__(self) -> None:
        if self.settings_slot not in (0, 1, 2):
            raise ValueError("settings_slot must be 0, 1, or 2")


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


def settings_backup_dir(cfg: DeployConfig) -> Path:
    return SETTINGS_BACKUPS_DIR / f"slot_{cfg.settings_slot}"


def backup_settings_from_device(cfg: DeployConfig) -> None:
    src = cfg.circuitpy_root / "settings.toml"
    dest_dir = settings_backup_dir(cfg)
    dest_dir.mkdir(parents=True, exist_ok=True)
    copy_file(src, dest_dir / "settings.toml")


def restore_settings_backup(cfg: DeployConfig) -> None:
    src = settings_backup_dir(cfg) / "settings.toml"
    if not src.is_file():
        raise FileNotFoundError(src)
    copy_file(src, cfg.circuitpy_root / "settings.toml")


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


def merge_repo_settings_into_backup(cfg: DeployConfig) -> None:
    """After ``copy_firmware_tree``, merge the repo ``settings.toml`` on CIRCUITPY into the slot backup.

    Preserves every value from the backed-up device file. Any key (including nested
    tables) that exists only in the template on the drive is added, then
    :func:`restore_settings_backup` writes the result back to the device.
    """
    backup_path = settings_backup_dir(cfg) / "settings.toml"
    template_path = cfg.circuitpy_root / "settings.toml"
    if not template_path.is_file():
        print(
            f"No {template_path.name} on device after copy; skipping template merge.",
            flush=True,
        )
        return
    try:
        import tomli
        import tomli_w
    except ImportError:
        print("tomli/tomli-w missing (run ``uv sync``); skipping settings merge.", flush=True)
        return

    try:
        old_data = tomli.loads(backup_path.read_text(encoding="utf-8"))
    except Exception as ex:
        raise ValueError(f"Could not parse backup settings {backup_path}: {ex}") from ex

    try:
        new_data = tomli.loads(template_path.read_text(encoding="utf-8"))
    except Exception as ex:
        print(
            f"Warning: could not parse template {template_path}: {ex}; "
            "keeping backup unchanged.",
            flush=True,
        )
        return

    added = _list_toml_keys_added_by_merge(old_data, new_data)
    if not added:
        print("Settings merge: no new keys in repo template (backup unchanged).", flush=True)
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
        f"Settings merge: added {len(added)} key(s) from repo template into backup: {preview}",
        flush=True,
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
    """Wait for the USB drive, copy repo `firmware/` onto it, apply full-flash `settings.toml`."""
    if cfg.wait_for_circuitpy_mount:
        wait_for_path(
            cfg.circuitpy_root,
            timeout_s=cfg.wait_timeout_s,
            interval_s=cfg.poll_interval_s,
        )
    if cfg.do_copy_firmware_tree:
        copy_firmware_tree(firmware_src(), cfg.circuitpy_root)
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
    backup_settings_from_device(cfg)
    copy_firmware_tree(firmware_src(), cfg.circuitpy_root)
    merge_repo_settings_into_backup(cfg)
    restore_settings_backup(cfg)
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
