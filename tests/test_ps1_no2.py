"""
Host-side debug tests for PS1-NO2 UART frame helpers (no CircuitPython / hardware).

Run from repo root:
  uv run python -m unittest tests.test_ps1_no2
"""
import importlib
import os
import sys
import types
import unittest
from unittest import mock

# Firmware package lives under ./firmware; avoid importing other sensors that need hardware.
FIRMWARE = os.path.join(os.path.dirname(__file__), "..", "firmware")
FIRMWARE = os.path.abspath(FIRMWARE)
if FIRMWARE not in sys.path:
    sys.path.insert(0, FIRMWARE)

_board = types.ModuleType("board")
_board.IO17 = "IO17"
_board.IO18 = "IO18"
sys.modules["board"] = _board

_sys_busio = types.ModuleType("busio")
_sys_busio.UART = object
sys.modules["busio"] = _sys_busio

# Minimal logger so importing sensors.sensor and sensor_ps1_no2 does not depend on device storage
_sys_logger = types.ModuleType("logger")
_sys_logger.logger = types.SimpleNamespace(
    debug=lambda *a, **k: None,
    info=lambda *a, **k: None,
    error=lambda *a, **k: None,
)
sys.modules["logger"] = _sys_logger

# Import the module we test (re-import clean if re-run in same process)
m = importlib.import_module("sensors.sensor_ps1_no2")


def _load_sensor_ps1_fresh():
    for name in list(sys.modules):
        if name == "sensors.sensor_ps1_no2" or name.startswith("sensors.sensor_ps1_no2."):
            del sys.modules[name]
    return importlib.import_module("sensors.sensor_ps1_no2")


def _ps1_frame_with_ppb16(ppb):
    """9-byte 0x86 gas response: NO2 big-endian in bytes 4–5 (see ps1_no2_decode_ppb)."""
    hi = (int(ppb) >> 8) & 0xFF
    lo = int(ppb) & 0xFF
    b = bytearray([0xFF, 0x86, 0x00, 0x00, hi, lo, 0x00, 0x00, 0x00])
    b[8] = m.ps1_no2_checksum(bytes(b))
    return bytes(b)


class TestPs1ChecksumAndDecode(unittest.TestCase):
    def test_datasheet_line_checksum_still_parses(self):
        # Example 9-byte line from the doc: last byte 0x30 matches the checksum rule.
        frame = bytes([0xFF, 0x86, 0x00, 0x2A, 0x00, 0x00, 0x00, 0x20, 0x30])
        self.assertEqual(m.ps1_no2_checksum(frame), 0x30)
        self.assertTrue(m.ps1_no2_frame_valid(frame))
        # In this line, bytes 4–5 are 0,00 so decoded ppb is 0; 0x2A appears at byte 3 only
        self.assertEqual(m.ps1_no2_decode_ppb(frame), 0)

    def test_decode_42_and_1000_ppb(self):
        for want, b4, b5 in ((42, 0x00, 0x2A), (1000, 0x03, 0xE8)):
            frame = _ps1_frame_with_ppb16(want)
            self.assertEqual(frame[4], b4)
            self.assertEqual(frame[5], b5)
            self.assertTrue(m.ps1_no2_frame_valid(frame))
            self.assertEqual(m.ps1_no2_decode_ppb(frame), want)

    def test_read_gas_command_is_datasheet_no2_query(self):
        # Datasheet passive query; last byte is 0x79, not ps1_no2_checksum (response rule).
        self.assertEqual(
            m.PS1_NO2_READ_GAS,
            bytes([0xFF, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79]),
        )
        self.assertNotEqual(
            m.ps1_no2_checksum(m.PS1_NO2_READ_GAS), m.PS1_NO2_READ_GAS[-1]
        )

    def test_frame_valid_rejects(self):
        self.assertFalse(m.ps1_no2_frame_valid(None))
        self.assertFalse(m.ps1_no2_frame_valid(b""))
        self.assertFalse(m.ps1_no2_frame_valid(b"\x00" * 9))
        good = bytes([0xFF, 0x86, 0x00, 0x2A, 0x00, 0x00, 0x00, 0x20, 0x30])
        self.assertTrue(m.ps1_no2_frame_valid(good))
        bad_checksum = bytearray(good)
        bad_checksum[-1] = (bad_checksum[-1] + 1) & 0xFF
        self.assertFalse(m.ps1_no2_frame_valid(bytes(bad_checksum)))


class TestFindGasFrame(unittest.TestCase):
    def setUp(self):
        self.s = m.Ps1No2Sensor()

    def test_finds_frame_after_preamble(self):
        good = bytes([0xFF, 0x86, 0x00, 0x2A, 0x00, 0x00, 0x00, 0x20, 0x30])
        buf = bytearray(b"\xaa\xbb" + good)
        self.assertEqual(self.s._find_gas_frame(buf), good)

    def test_skips_invalid_checksum(self):
        good = bytes([0xFF, 0x86, 0x00, 0x2A, 0x00, 0x00, 0x00, 0x20, 0x30])
        bad = bytearray(good)
        bad[-1] = 0x00
        buf = bytearray(bad) + good
        self.assertEqual(self.s._find_gas_frame(buf), good)

    def test_returns_first_valid(self):
        a = bytes([0xFF, 0x86, 0x00, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x00])
        a = a[:-1] + bytes([m.ps1_no2_checksum(a[:8] + b"\x00")])
        b = bytes([0xFF, 0x86, 0x00, 0x00, 0x14, 0x00, 0x00, 0x00, 0x00])
        b = b[:-1] + bytes([m.ps1_no2_checksum(b[:8] + b"\x00")])
        buf = bytearray(a + b)
        self.assertEqual(self.s._find_gas_frame(buf), a)


class TestReadGasFrameWithFakeUart(unittest.TestCase):
    def test_read_returns_first_valid_9byte_frame(self):
        good = bytes([0xFF, 0x86, 0x00, 0x2A, 0x00, 0x00, 0x00, 0x20, 0x30])

        class FakeUart:
            def __init__(self, payload):
                self._q = bytearray(payload)
                self.deinited = False

            @property
            def in_waiting(self):
                return len(self._q)

            def read(self, n):
                n = min(n, len(self._q))
                out = bytes(self._q[:n])
                del self._q[:n]
                return out

            def deinit(self):
                self.deinited = True

        mod = _load_sensor_ps1_fresh()
        s = mod.Ps1No2Sensor()
        s.uart = FakeUart(good)
        with mock.patch.object(mod.time, "sleep", lambda _s=0.02: None):
            frame = s._read_gas_frame(timeout_s=0.2)
        self.assertEqual(frame, good)


class TestUartConnectionTest(unittest.TestCase):
    def setUp(self):
        self._good = bytes(
            [0xFF, 0x86, 0x00, 0x2A, 0x00, 0x00, 0x00, 0x20, 0x30]
        )

    def test_uart_test_stops_on_first_valid_frame(self):
        s = m.Ps1No2Sensor()
        calls = []

        def q():
            calls.append(1)
            return self._good

        s._query_gas_frame = q
        with mock.patch.object(m.time, "sleep"):
            out = s._uart_test_gas_frame()
        self.assertEqual(out, self._good)
        self.assertEqual(len(calls), 1)

    def test_uart_test_retries_until_valid(self):
        s = m.Ps1No2Sensor()
        n = 0

        def q():
            nonlocal n
            n += 1
            if n < 3:
                return None
            return self._good

        s._query_gas_frame = q
        with mock.patch.object(m.time, "sleep"):
            out = s._uart_test_gas_frame()
        self.assertEqual(out, self._good)
        self.assertEqual(n, 3)

    def test_uart_test_returns_last_frame_after_exhausting_attempts(self):
        s = m.Ps1No2Sensor()
        last = b"\xFF\x86" + b"\x00" * 7  # 9 B, never ps1_frame_valid
        s._query_gas_frame = lambda: last
        with mock.patch.object(m.time, "sleep"):
            out = s._uart_test_gas_frame()
        self.assertIs(out, last)


if __name__ == "__main__":
    unittest.main()
