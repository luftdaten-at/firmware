"""Deploy helpers for CircuitPython ESP32-S3 — used by deploy.ipynb. See readme.md."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

DEPLOY_DIR = Path(__file__).resolve().parent
SETTINGS_BACKUPS_DIR = DEPLOY_DIR / "settings_backups"
BOARD_FIRMWARE_DIR = DEPLOY_DIR / "board_firmware"

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
    return (
        BOARD_FIRMWARE_DIR
        / "adafruit-circuitpython-espressif_esp32s3_devkitc_1_n8r8-en_US-9.2.4.bin"
    )


@dataclass
class DeployConfig:
    serial_port: str = "/dev/ttyACM0"
    circuitpy_root: Path = field(default_factory=lambda: Path("/media/nik/CIRCUITPY"))
    circuitpython_bin: Path = field(default_factory=_default_circuitpython_bin)
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


def copy_firmware_tree(
    src: Path,
    dst: Path,
    *,
    ignore_names: Iterable[str] | None = None,
) -> None:
    """Mirror `cp -r src/* dst` with ignores at every directory level."""
    ign = frozenset(ignore_names or DEFAULT_IGNORE_NAMES)
    if not src.is_dir():
        raise NotADirectoryError(src)
    dst.mkdir(parents=True, exist_ok=True)

    def copy_recursive(sub: Path, sub_dst: Path) -> None:
        if _should_skip_name(sub.name, ignore_names=ign):
            return
        if sub.is_dir():
            sub_dst.mkdir(parents=True, exist_ok=True)
            for child in sub.iterdir():
                copy_recursive(child, sub_dst / child.name)
        else:
            sub_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sub, sub_dst)

    for entry in src.iterdir():
        if _should_skip_name(entry.name, ignore_names=ign):
            continue
        copy_recursive(entry, dst / entry.name)
    if hasattr(os, "sync"):
        os.sync()
    print(f"Copied firmware tree {src} -> {dst}", flush=True)


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


def deploy_full_flash_settings(cfg: DeployConfig) -> None:
    if not cfg.full_flash_settings.is_file():
        raise FileNotFoundError(cfg.full_flash_settings)
    copy_file(cfg.full_flash_settings, cfg.circuitpy_root / "settings.toml")


def flash_with_esptool(cfg: DeployConfig) -> None:
    """Erase (optional) and write the CircuitPython `.bin` over serial; does not touch `CIRCUITPY`."""
    if cfg.do_erase_flash:
        run_esptool(["--port", cfg.serial_port, "erase_flash"])
    if cfg.do_write_firmware:
        if not cfg.circuitpython_bin.is_file():
            raise FileNotFoundError(cfg.circuitpython_bin)
        run_esptool(
            ["--port", cfg.serial_port, "write_flash", "-z", "0x0", str(cfg.circuitpython_bin)]
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
