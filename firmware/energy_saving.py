import time

import alarm

from config import Config
from enums import BatterySaverMode, LdProduct
from logger import logger
from wifi_client import WifiUtil

# Stay awake after boot / button wake / BLE disconnect so the app can connect.
GRACE_WINDOW_S = 120

# Normal mode: BLE advertising window after each measurement before sleeping.
POST_MEASUREMENT_WINDOW_S = 60

# Estimated boot + sensor init time subtracted from sleep duration.
BOOT_COMPENSATION_S = 10

# Do not deep-sleep for shorter stretches (overhead not worth it).
MIN_SLEEP_S = 15

# Short status blinks instead of always-on LED while energy saving is active.
SHORT_BLINK_ON_S = 0.08
SHORT_BLINK_OFF_S = 0.05
STATUS_BLINK_COOLDOWN_S = 30

_SUPPORTED_MODELS = (
    LdProduct.AIR_STATION,
    LdProduct.AIR_AROUND,
    LdProduct.AIR_BIKE,
)


def is_energy_saving_enabled() -> bool:
    mode = Config.settings.get("battery_save_mode", BatterySaverMode.off)
    if mode not in (BatterySaverMode.normal, BatterySaverMode.ultra):
        return False
    return Config.settings.get("MODEL") in _SUPPORTED_MODELS


def should_skip_ota_on_wake() -> bool:
    """Skip blocking OTA in code.py after a timed deep-sleep wake."""
    if not is_energy_saving_enabled():
        return False
    wake = alarm.wake_alarm
    if wake is None:
        return False
    return isinstance(wake, alarm.TimeAlarm)


def _primary_led_color(pattern: dict):
    from led_controller import RepeatMode

    if pattern.get("repeat_mode") == RepeatMode.PERMANENT:
        return pattern.get("color")
    elements = pattern.get("elements")
    if elements:
        return elements[0].get("color")
    return pattern.get("color")


def _pattern_status_key(pattern: dict):
    from led_controller import RepeatMode

    return (pattern.get("repeat_mode"), _primary_led_color(pattern))


def short_blink_pattern(color) -> dict:
    from enums import Color
    from led_controller import RepeatMode

    return {
        "repeat_mode": RepeatMode.TIMES,
        "repeat_times": 1,
        "elements": [
            {"color": color, "duration": SHORT_BLINK_ON_S},
            {"color": Color.OFF, "duration": SHORT_BLINK_OFF_S},
        ],
    }


def adapt_led_pattern(pattern: dict) -> dict:
    """Map always-on / looping status patterns to a single short blink."""
    if not is_energy_saving_enabled():
        return pattern

    from led_controller import RepeatMode

    mode = pattern.get("repeat_mode")
    if mode == RepeatMode.TIMES:
        return pattern

    color = _primary_led_color(pattern)
    if color is None:
        return pattern

    return short_blink_pattern(color)


def show_battery_startup_blink(status_led, percent: int) -> None:
    """One brief battery hint at boot instead of the long pulse sequence."""
    from enums import Color

    color = Color.RED if percent < 10 else Color.GREEN
    status_led.show_led(short_blink_pattern(color))
    time.sleep(SHORT_BLINK_ON_S + SHORT_BLINK_OFF_S)


class EnergySaving:
    def __init__(self, device, button_pin, button):
        self._device = device
        self._button_pin = button_pin
        self._button = button
        self._ble_was_connected = False
        self._grace_until = time.monotonic() + GRACE_WINDOW_S

    def maybe_sleep(self, ble_connected: bool) -> None:
        if not is_energy_saving_enabled():
            return

        if ble_connected:
            self._ble_was_connected = True
            return

        if self._ble_was_connected:
            self._ble_was_connected = False
            self._grace_until = time.monotonic() + GRACE_WINDOW_S
            logger.debug("Energy saving: BLE disconnected, grace window restarted")

        if time.monotonic() < self._grace_until:
            return

        last_measurement = getattr(self._device, "last_measurement", None)
        if last_measurement is None:
            return

        mode = Config.settings.get("battery_save_mode", BatterySaverMode.off)
        if mode == BatterySaverMode.normal:
            if time.monotonic() - last_measurement < POST_MEASUREMENT_WINDOW_S:
                return

        interval = Config.settings.get("measurement_interval", 30)
        remaining = (last_measurement + interval) - time.monotonic() - BOOT_COMPENSATION_S
        if remaining < MIN_SLEEP_S:
            return

        self._flush_before_sleep()
        self._enter_deep_sleep(remaining)

    def _flush_before_sleep(self) -> None:
        if not WifiUtil.radio.connected:
            return
        try:
            self._device.send_to_api()
        except Exception as e:
            logger.warning(f"Energy saving: flush before sleep failed ({type(e).__name__}: {e})")

    def _enter_deep_sleep(self, sleep_seconds: float) -> None:
        logger.info(
            f"Energy saving: deep sleep for {sleep_seconds:.0f}s "
            f"(mode={Config.settings.get('battery_save_mode')}, "
            f"interval={Config.settings.get('measurement_interval')}s)"
        )

        try:
            self._device.status_led.status_led.deinit()
        except Exception as e:
            logger.warning(f"Energy saving: LED deinit failed ({type(e).__name__}: {e})")

        try:
            self._button.deinit()
        except Exception as e:
            logger.warning(f"Energy saving: button deinit failed ({type(e).__name__}: {e})")

        wake_at = time.time() + sleep_seconds
        time_alarm = alarm.TimeAlarm(epoch_time=wake_at)
        pin_alarm = alarm.PinAlarm(self._button_pin, value=True)
        alarm.exit_and_deep_sleep_until_alarms(time_alarm, pin_alarm)
