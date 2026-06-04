#!/usr/bin/env python3
"""
Reference encoder for Air Station BLE config (command 0x06 + TLV).

Run: python3 tools/ble_tlv_reference.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "firmware"))

from enums import AirstationConfigFlags

from ble_tlv_codec import (
    format_tlv_payload_for_log,
    iter_tlv_records,
    pack_air_station_command,
    pack_tlv_record,
)


def example_geo_wifi():
    records = [
        pack_tlv_record(AirstationConfigFlags.LATITUDE, "48.2082"),
        pack_tlv_record(AirstationConfigFlags.LONGITUDE, "16.3738"),
        pack_tlv_record(AirstationConfigFlags.HEIGHT, "170"),
        pack_tlv_record(AirstationConfigFlags.SSID, "MyNetwork"),
        pack_tlv_record(AirstationConfigFlags.PASSWORD, "secret"),
    ]
    return pack_air_station_command(*records)


def example_latitude_only():
    return pack_air_station_command(
        pack_tlv_record(AirstationConfigFlags.LATITUDE, "47.0")
    )


def main():
    samples = [
        ("latitude_only", example_latitude_only()),
        ("geo_wifi", example_geo_wifi()),
    ]
    print("Air Station SET_AIR_STATION_CONFIGURATION (0x06) reference packets\n")
    for name, packet in samples:
        tlv = packet[1:]
        print("=== %s ===" % name)
        print("full hex:", packet.hex())
        print("command: 0x%02x" % packet[0])
        print("TLV parse:", format_tlv_payload_for_log(tlv))
        print("records:", sum(1 for _ in iter_tlv_records(tlv)))
        print()

    print("Companion encoder checklist:")
    print("  - First byte MUST be 0x06 (not repeated inside TLV).")
    print("  - Per field: flag (u8), length (u8), value (length bytes).")
    print("  - Geo: UTF-8 string; length = byte length.")
    print("  - Do NOT use one bitmask byte for multiple fields.")
    print("  - Max ~512 bytes per GATT write.")
    print("  - Success: READ air_station_configuration (geo) + USB settings.toml (SSID).")


if __name__ == "__main__":
    main()
