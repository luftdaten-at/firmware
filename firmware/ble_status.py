"""Compute ``device_status_characteristic`` bytes for the Companion app."""

from config import Config
from enums import BleOperationalStatusFlags, BleWifiDetailCode, SensorModel
from wifi_client import WifiUtil


def _ssid_configured() -> bool:
    ssid = Config.settings.get("SSID")
    return bool(str(ssid or "").strip())


def _physical_sensor_count(device) -> int:
    count = getattr(device, "physical_sensor_count", None)
    if count is not None:
        return int(count)
    return sum(
        1 for s in device.sensors if s.model_id != SensorModel.VIRTUAL_SENSOR
    )


def compute_device_status_bytes(device) -> bytes:
    """Five-byte GATT payload: battery (0–2), Wi‑Fi detail (3), flags (4)."""
    flags = 0

    if device.ble_configuration_incomplete():
        flags |= BleOperationalStatusFlags.CONFIG_INCOMPLETE

    if _physical_sensor_count(device) == 0:
        flags |= BleOperationalStatusFlags.NO_SENSOR

    if _ssid_configured():
        flags |= BleOperationalStatusFlags.SSID_CONFIGURED

    wifi_detail = BleWifiDetailCode.NONE
    expect_wifi = (not Config.is_wifiless()) or _ssid_configured()
    if expect_wifi and not WifiUtil.radio.connected:
        flags |= BleOperationalStatusFlags.WIFI_FAILURE
        wifi_detail = WifiUtil.last_wifi_detail or BleWifiDetailCode.CONNECT_FAILED

    if device.battery_monitor is not None:
        has_battery = 1
        soc = round(device.battery_monitor.cell_soc())
        voltage = round(device.battery_monitor.cell_voltage() * 10)
    else:
        has_battery = 0
        soc = 0
        voltage = 0

    return bytes([has_battery, soc, voltage, wifi_detail, flags])
