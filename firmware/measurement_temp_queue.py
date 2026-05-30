"""Compact offline measurement queue on CIRCUITPY (Air Station / Air Cube, non-wifiless).

Stores compact JSONL under ``/json_queue`` (max 512 KiB). Replayed via
``WifiUtil.send_json_to_api`` when Wi-Fi is available again.
"""

import gc
import json
import os

from config import Config
from enums import LdProduct
from logger import logger

QUEUE_DIR = "/json_queue"
QUEUE_FILE = "/json_queue/measurements.ndjson"
MAX_QUEUE_BYTES = 512 * 1024


def _queue_applies():
    if Config.is_wifiless():
        return False
    return Config.settings.get("MODEL") in (LdProduct.AIR_STATION, LdProduct.AIR_CUBE)


def _stat_size(path):
    try:
        st = os.stat(path)
        sz = getattr(st, "st_size", None)
        if isinstance(sz, int):
            return sz
        if isinstance(st, tuple) and len(st) > 6:
            return int(st[6])
        return 0
    except OSError:
        return 0


def _ensure_queue_dir():
    try:
        os.mkdir(QUEUE_DIR)
    except OSError:
        pass


def _encode_line(payload):
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


def _read_lines():
    try:
        with open(QUEUE_FILE, "r") as f:
            return f.readlines()
    except OSError as e:
        eno = getattr(e, "errno", None)
        if eno == 2 or "No such file" in str(e):
            return []
        raise


def _write_lines(lines):
    with open(QUEUE_FILE, "w") as f:
        for ln in lines:
            f.write(ln if ln.endswith("\n") else ln + "\n")
    if hasattr(os, "sync"):
        os.sync()


def _lines_byte_size(lines):
    total = 0
    for ln in lines:
        if not ln:
            continue
        total += len(ln.encode("utf-8") if isinstance(ln, str) else ln)
    return total


def append_offline_measurement(payload):
    """Append one measurement JSON object; drop oldest lines over 512 KiB."""
    if not _queue_applies():
        return False
    _ensure_queue_dir()
    try:
        line = _encode_line(payload).decode("utf-8")
        lines = _read_lines()
        lines.append(line)
        while lines and _lines_byte_size(lines) > MAX_QUEUE_BYTES:
            lines.pop(0)
        _write_lines(lines)
        return True
    except Exception as e:
        logger.error(
            "Offline measurement queue write failed (%s: %s)"
            % (type(e).__name__, e)
        )
        return False


def replay_pending_to_api():
    """POST queued measurements; remove lines accepted with HTTP 200/422."""
    from wifi_client import WifiUtil

    if not _queue_applies() or not WifiUtil.radio.connected:
        return False

    _ensure_queue_dir()
    try:
        pending = _read_lines()
    except Exception as e:
        logger.error(
            "Offline measurement queue read failed (%s: %s)"
            % (type(e).__name__, e)
        )
        return False

    if not any(ln.strip() for ln in pending):
        return True

    idx = 0
    sent = 0
    while idx < len(pending):
        stripped = pending[idx].strip()
        if not stripped:
            idx += 1
            continue
        line_no = idx + 1
        try:
            payload = json.loads(stripped)
        except ValueError as e:
            logger.error(
                "Offline queue line %s: invalid JSON (%s); keeping from this line onward"
                % (line_no, e)
            )
            break
        gc.collect()
        try:
            resp = WifiUtil.send_json_to_api(payload)
        except Exception as e:
            logger.warning(
                "Offline queue line %s: upload failed (%s: %s); keeping from this line onward"
                % (line_no, type(e).__name__, e)
            )
            break
        if resp.status_code not in (200, 422):
            logger.warning(
                "Offline queue line %s: HTTP %s; keeping from this line onward"
                % (line_no, resp.status_code)
            )
            break
        idx += 1
        sent += 1

    unsent = pending[idx:]
    try:
        _write_lines(unsent)
    except Exception as e:
        logger.error(
            "Offline measurement queue rewrite failed (%s: %s)"
            % (type(e).__name__, e)
        )
        return False

    if sent:
        logger.info("Offline measurement queue: uploaded %s measurement(s)" % sent)
    return not any(ln.strip() for ln in unsent)


def pending_byte_size():
    """Current queue file size in bytes (0 if missing)."""
    if not _queue_applies():
        return 0
    return _stat_size(QUEUE_FILE)
