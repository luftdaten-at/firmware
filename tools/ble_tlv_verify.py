#!/usr/bin/env python3
"""
Parse hex BLE 0x06 payload (host verification).

  python3 tools/ble_tlv_verify.py 064b1234...
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "firmware"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from enums import BleCommands  # noqa: E402

from ble_tlv_codec import format_tlv_payload_for_log, iter_tlv_records  # noqa: E402


def parse_hex(s):
    s = s.replace(" ", "").replace(":", "").strip()
    return bytes.fromhex(s)


def main():
    ap = argparse.ArgumentParser(description="Verify BLE 0x06 TLV hex capture")
    ap.add_argument("hex", nargs="?", help="Hex string (optional if --file)")
    ap.add_argument("--file", type=Path, help="File containing hex")
    args = ap.parse_args()

    if args.file:
        raw = parse_hex(args.file.read_text())
    elif args.hex:
        raw = parse_hex(args.hex)
    else:
        ap.print_help()
        sys.exit(1)

    if raw[0] != BleCommands.SET_AIR_STATION_CONFIGURATION:
        print("WARNING: first byte 0x%02x (expected 0x06)" % raw[0])
        tlv = raw
    else:
        print("command: 0x06 OK")
        tlv = raw[1:]

    print("TLV (%d bytes): %s" % (len(tlv), format_tlv_payload_for_log(tlv)))
    n = sum(1 for _ in iter_tlv_records(tlv))
    print("total records:", n)
    print("On device: compare settings.toml on CIRCUITPY after write.")


if __name__ == "__main__":
    main()
