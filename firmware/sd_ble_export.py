"""BLE chunk export for wifiless JSONL log on Air Station / Air Cube (see docs/ble-characteristics.md)."""

import os
import struct

from config import Config
from logger import logger

# Frame: status u8 + flags u8 + payload_len u16 BE + payload (max 508 bytes → total 512)
MAX_PAYLOAD = 508

STATUS_IDLE = 0
STATUS_PARTIAL = 1

STATUS_EOL = 2
STATUS_EOF = 3
STATUS_ERR = 4

SUB_NOT_WIFILESS = 1
SUB_MOUNT_FAIL = 2
SUB_OPEN_FAIL = 3
SUB_READ_FAIL = 4
SUB_NO_SESSION = 5

FLAG_IDLE_SD_LOG_NONEMPTY = 0x01


def _stat_size(path):
    """Return file size or -1 on failure."""
    try:
        st = os.stat(path)
        sz = getattr(st, "st_size", None)
        if isinstance(sz, int):
            return sz
        if isinstance(st, tuple) and len(st) > 6:
            return int(st[6])
        return -1
    except OSError:
        return -1


def _sd_log_file_nonempty():
    """True if mounted SD has the JSONL path with size > 0."""
    if not Config.is_wifiless():
        return False
    from sd_logger import ensure_sd_mounted

    if not ensure_sd_mounted():
        return False
    path = Config.settings.get("SD_LOG_PATH") or "/sd/measurements.jsonl"
    return _stat_size(path) > 0


def _idle_flags_byte():
    return FLAG_IDLE_SD_LOG_NONEMPTY if _sd_log_file_nonempty() else 0


_STATE_OPEN = "open"
_STATE_AFTER_EOF = "after_eof"

_last_frame = struct.pack(">BBH", STATUS_IDLE, 0, 0)
_fh = None
_pending = ""  # remainder of current JSONL line (UTF-8–safe chunked as str)
_state = ""  # "", _STATE_OPEN, or _STATE_AFTER_EOF


def export_read_value():
    """Last frame for ``sd_log_export`` characteristic. Refreshes idle ``flags`` (non-empty bit)."""
    global _last_frame
    if len(_last_frame) >= 1 and _last_frame[0] == STATUS_IDLE:
        _last_frame = struct.pack(">BBH", STATUS_IDLE, _idle_flags_byte(), 0)
    return _last_frame


def _set_frame(status, flags, payload_bytes):
    global _last_frame
    p = payload_bytes[:MAX_PAYLOAD]
    ln = len(p)
    _last_frame = struct.pack(">BBH", status, flags & 0xFF, ln) + p


def _set_idle_frame():
    global _last_frame
    _last_frame = struct.pack(">BBH", STATUS_IDLE, _idle_flags_byte(), 0)


def _close_file():
    global _fh
    if _fh is not None:
        try:
            _fh.close()
        except Exception:
            pass
        _fh = None


def handle_export_command(action, wifiless_ok):
    """BLE helper: ``action`` 0 = START, 1 = NEXT."""
    global _pending, _state

    action = int(action) & 0xFF if action is not None else 255

    if not wifiless_ok:
        _close_file()
        _pending = ""
        _state = ""
        _set_frame(STATUS_ERR, SUB_NOT_WIFILESS, bytes())
        return

    if action == 0:
        _export_start()

    elif action == 1:
        _export_next()

    else:
        _close_file()
        _pending = ""
        _state = ""
        _set_idle_frame()


def _export_start():
    global _fh, _pending, _state

    _close_file()
    _pending = ""
    _state = ""

    from sd_logger import ensure_sd_mounted

    if not ensure_sd_mounted():
        _set_frame(STATUS_ERR, SUB_MOUNT_FAIL, bytes())
        return

    path = Config.settings.get("SD_LOG_PATH") or "/sd/measurements.jsonl"
    try:
        _fh = open(path, "r")  # noqa SIM115 circuitpython global fh
        _state = _STATE_OPEN
        _set_idle_frame()
    except OSError as e:
        logger.warning(f"SD BLE export open failed ({type(e).__name__}: {e})")
        _fh = None
        _state = ""
        _set_frame(STATUS_ERR, SUB_OPEN_FAIL, bytes())


def _export_next():
    global _fh, _pending, _state

    if _state == _STATE_AFTER_EOF:
        _set_idle_frame()
        return

    if _fh is None:
        _set_frame(STATUS_ERR, SUB_NO_SESSION, bytes())
        return

    try:
        if _pending == "":
            ln = _fh.readline()
            if ln == "":
                _close_file()
                _pending = ""
                _state = _STATE_AFTER_EOF
                _set_frame(STATUS_EOF, 0, bytes())
                return
            if not isinstance(ln, str):
                ln = str(ln, "utf-8")
            _pending = ln

        frag, remainder = _utf8_safe_prefix_str(_pending, MAX_PAYLOAD)
        _pending = remainder

        blob = frag.encode("utf-8")

        stat = STATUS_PARTIAL if _pending else STATUS_EOL
        _set_frame(stat, 0, blob)

    except Exception as e:
        logger.warning(f"SD BLE export read failed ({type(e).__name__}: {e})")
        _close_file()
        _pending = ""
        _state = ""
        _set_frame(STATUS_ERR, SUB_READ_FAIL, bytes())


def _utf8_safe_prefix_str(s, max_bytes):
    """Split ``s`` so the UTF-8 encoding of returned prefix fits in ``max_bytes``."""
    if max_bytes <= 0 or not s:
        return "", s
    out = []
    nbytes = 0
    i = 0
    sz = len(s)
    while i < sz:
        ch = s[i]
        b = ch.encode("utf-8")
        lb = len(b)
        if nbytes + lb > max_bytes:
            break
        out.append(ch)
        nbytes += lb
        i += 1
    prefix = "".join(out)
    return prefix, s[len(prefix) :]
