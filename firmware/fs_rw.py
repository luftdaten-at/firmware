"""CircuitPython filesystem helpers (remount with USB MSC connected)."""

import storage
from storage import remount

from lib.cptoml import fetch, put_many
from logger import logger

_SECRET_SETTING_KEYS = frozenset(
    ("PASSWORD", "MQTT_PASSWORD", "api_key")
)


def format_setting_for_log(key, value) -> str:
    if key in _SECRET_SETTING_KEYS:
        n = len(value) if value is not None else 0
        return "%s=<redacted len=%d>" % (key, n)
    return "%s=%r" % (key, value)


def _usb_connected() -> bool:
    try:
        import supervisor

        return bool(supervisor.runtime.usb_connected)
    except Exception:
        return False


def _remount_readwrite() -> bool:
    """
    Remount CIRCUITPY read-write for settings persistence.

    While USB is connected, only ``storage.remount(..., disable_concurrent_write_protection=True)``
    is attempted — never bare ``remount("/", False)`` (raises RuntimeError on MSC).
    """
    usb = _usb_connected()
    logger.debug("fs_rw: remount RW (usb_connected=%s)" % usb)
    try:
        if usb:
            storage.remount(
                "/",
                readonly=False,
                disable_concurrent_write_protection=True,
            )
        else:
            try:
                storage.remount(
                    "/",
                    readonly=False,
                    disable_concurrent_write_protection=True,
                )
            except TypeError:
                remount("/", False)
        logger.debug("fs_rw: remount RW ok")
        return True
    except (OSError, RuntimeError, TypeError) as e:
        logger.warning(
            "fs_rw: remount RW failed (%s: %s); will try write without remount"
            % (type(e).__name__, e)
        )
        return False


def _remount_readonly(did_rw_remount: bool) -> None:
    if not did_rw_remount:
        return
    if _usb_connected():
        logger.debug("fs_rw: skip remount RO (USB connected; avoid host cache clobber)")
        return
    logger.debug("fs_rw: remount RO")
    try:
        try:
            storage.remount("/", True)
        except TypeError:
            remount("/", True)
    except (OSError, RuntimeError, TypeError) as e:
        logger.warning("fs_rw: remount RO failed: %s: %s" % (type(e).__name__, e))


def _verify_readback(path: str, items: dict) -> bool:
    mismatches = []
    for key, value in items.items():
        try:
            got = fetch(key, toml=path)
        except Exception as e:
            logger.warning("fs_rw: readback fetch %s failed: %s" % (key, e))
            mismatches.append(key)
            continue
        match = got == value or str(got) == str(value)
        logger.debug(
            "fs_rw: readback %s wrote=%s file=%s ok=%s"
            % (
                key,
                format_setting_for_log(key, value).split("=", 1)[-1],
                format_setting_for_log(key, got).split("=", 1)[-1],
                match,
            )
        )
        if not match:
            mismatches.append(key)
    if mismatches:
        logger.warning("fs_rw: readback mismatch after write: %s" % ", ".join(mismatches))
        return False
    return True


def persist_toml_values(items, toml_path: str) -> bool:
    """
    Write several keys to a TOML file in one read-modify-write.

    Never raises into the caller: RAM settings remain even if the file write fails.
    """
    if not items:
        logger.debug("fs_rw: persist skip (no keys) path=%s" % toml_path)
        return True
    path = toml_path if toml_path.startswith("/") else "/" + toml_path
    logger.debug(
        "fs_rw: persist %d key(s) to %s: %s"
        % (len(items), path, ", ".join(format_setting_for_log(k, v) for k, v in items.items()))
    )

    rw_remounted = _remount_readwrite()
    try:
        put_many(items, toml=path)
        if not _verify_readback(path, items):
            return False
        logger.info("fs_rw: persisted %s to %s" % (", ".join(items.keys()), path))
        return True
    except OSError as e:
        logger.warning(
            "fs_rw: could not persist %s to %s: %s (remount_ok=%s)"
            % (list(items.keys()), path, e, rw_remounted)
        )
        return False
    except Exception as e:
        logger.warning(
            "fs_rw: could not persist %s to %s: %s: %s (remount_ok=%s)"
            % (list(items.keys()), path, type(e).__name__, e, rw_remounted)
        )
        return False
    finally:
        _remount_readonly(rw_remounted)


def persist_toml_value(key, value, toml_path: str) -> bool:
    return persist_toml_values({key: value}, toml_path)
