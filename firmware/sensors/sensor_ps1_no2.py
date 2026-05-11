import time

import board  # type: ignore
import busio  # type: ignore

from enums import Dimension, Quality, SensorModel
from logger import logger
from sensors.sensor import Sensor


# Last byte 0x79 per SGX PS1 datasheet (Q&A / passive mode); not the same as
# ps1_no2_checksum() used for 9-byte *responses* — wrong byte → no module reply.
PS1_NO2_READ_GAS = bytes([0xFF, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])
PS1_NO2_RESPONSE_LEN = 9
PS1_NO2_WARMUP_S = 120.0
# Passive gas query retries during attempt_connection (cold sensor / line settling).
PS1_NO2_TEST_ATTEMPTS = 3
PS1_NO2_TEST_RETRY_DELAY_S = 0.2


def _ps1_uart_hex(data, max_bytes=0):
    """Space-separated uppercase hex for UART debug logs. Optionally truncate long buffers."""
    if data is None:
        return "None"
    b = data if isinstance(data, (bytes, bytearray, memoryview)) else bytes(data)
    if not b:
        return "(0 B)"
    if max_bytes and len(b) > max_bytes:
        b = b[:max_bytes]
        return (
            " ".join(f"{x:02X}" for x in b)
            + f" … (+{len(data) - max_bytes} B)"
        )
    return " ".join(f"{x:02X}" for x in b)


def ps1_no2_checksum(data):
    """Checksum used by PS1 UART frames: two's complement of bytes 1..n-2."""
    return (-sum(data[1:-1])) & 0xFF


def ps1_no2_frame_valid(frame):
    return (
        frame is not None
        and len(frame) == PS1_NO2_RESPONSE_LEN
        and frame[0] == 0xFF
        and frame[1] == 0x86
        and ps1_no2_checksum(frame) == frame[-1]
    )


def ps1_no2_decode_ppb(frame):
    """Decode the NO2 ppb value from a valid 0x86 gas response."""
    return (frame[4] << 8) | frame[5]


class Ps1No2Sensor(Sensor):
    """SGX Sensortech PS1-NO2-50-MOD over 3.3 V UART."""

    def __init__(self, tx=board.IO17, rx=board.IO18, baudrate=9600):
        super().__init__()
        self.model_id = SensorModel.PS1_NO2_50_MOD
        self.measures_values = [Dimension.NO2]
        self.current_values = {Dimension.NO2: None}
        self.value_quality = {Dimension.NO2: Quality.HIGH}
        self.tx = tx
        self.rx = rx
        self.baudrate = baudrate
        self.uart = None
        self.warmup_until = None
        self._warmup_logged = False

    def attempt_connection(self):
        try:
            self.uart = busio.UART(
                tx=self.tx,
                rx=self.rx,
                baudrate=self.baudrate,
                bits=8,
                parity=None,
                stop=1,
                timeout=0.1,
            )
            logger.debug(
                f"PS1-NO2 UART: open {self.baudrate} 8N1, "
                f"host tx={self.tx!s} host rx={self.rx!s}"
            )
            frame = self._uart_test_gas_frame()
        except Exception as e:
            logger.debug(f"PS1-NO2-50-MOD sensor not detected: {e}")
            self.deinit()
            return False

        if not ps1_no2_frame_valid(frame):
            logger.debug(
                "PS1-NO2-50-MOD not detected: "
                + (
                    f"invalid/corrupt frame {_ps1_uart_hex(frame)}"
                    if frame
                    else "no 9-byte valid response (see PS1-NO2 UART debug lines above)"
                )
            )
            self.deinit()
            return False

        self.warmup_until = time.monotonic() + PS1_NO2_WARMUP_S
        logger.debug(
            "PS1-NO2-50-MOD found on UART tx=IO17 rx=IO18; "
            f"warming up for {round(PS1_NO2_WARMUP_S)}s"
        )
        return True

    def deinit(self):
        if self.uart is not None:
            try:
                self.uart.deinit()
            except Exception:
                pass
            self.uart = None

    def read(self):
        if self.uart is None:
            return
        if self.warmup_until is not None:
            remaining = self.warmup_until - time.monotonic()
            if remaining > 0:
                self.current_values[Dimension.NO2] = None
                if not self._warmup_logged:
                    logger.info(
                        "PS1-NO2-50-MOD warming up; NO2 unavailable for "
                        f"{round(remaining)}s"
                    )
                    self._warmup_logged = True
                return

        try:
            frame = self._query_gas_frame()
            if not ps1_no2_frame_valid(frame):
                logger.error(
                    "PS1-NO2-50-MOD invalid read frame: "
                    f"{_ps1_uart_hex(frame) if frame else None}"
                )
                return
            self.current_values[Dimension.NO2] = ps1_no2_decode_ppb(frame)
        except Exception as e:
            logger.error(f"PS1-NO2-50-MOD read error: {e}")

    def _uart_test_gas_frame(self):
        """
        Run several passive gas queries at connect time (only used from
        attempt_connection). Returns the first valid 9-byte frame, or the last
        response received (may be None / invalid) after all attempts.
        """
        last = None
        for a in range(1, PS1_NO2_TEST_ATTEMPTS + 1):
            logger.debug(
                f"PS1-NO2 UART: connection test {a}/{PS1_NO2_TEST_ATTEMPTS} "
                "(gas read query)"
            )
            if a > 1:
                time.sleep(PS1_NO2_TEST_RETRY_DELAY_S)
            last = self._query_gas_frame()
            if ps1_no2_frame_valid(last):
                logger.debug("PS1-NO2 UART: connection test passed (valid 0x86 frame)")
                return last
        logger.debug("PS1-NO2 UART: connection test failed (no valid frame)")
        return last

    def _query_gas_frame(self):
        self._drain_uart()
        cmd = PS1_NO2_READ_GAS
        logger.debug(
            "PS1-NO2 UART tx "
            f"{len(cmd)} B: {_ps1_uart_hex(cmd)}"
        )
        self.uart.write(cmd)
        return self._read_gas_frame(timeout_s=1.0)

    def _drain_uart(self):
        drained = bytearray()
        while self.uart.in_waiting:
            n = self.uart.in_waiting
            chunk = self.uart.read(n)
            if chunk:
                drained.extend(chunk)
        if drained:
            logger.debug(
                "PS1-NO2 UART drain "
                f"{len(drained)} B: {_ps1_uart_hex(drained, max_bytes=64)}"
            )

    def _read_gas_frame(self, timeout_s=1.0):
        buf = bytearray()
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            n = self.uart.in_waiting
            if n:
                data = self.uart.read(n)
                if data:
                    logger.debug(
                        "PS1-NO2 UART rx chunk "
                        f"{len(data)} B: {_ps1_uart_hex(data)}"
                    )
                    buf.extend(data)
                    frame = self._find_gas_frame(buf)
                    if frame is not None:
                        return frame
            time.sleep(0.02)
        if buf:
            logger.debug(
                "PS1-NO2 UART: no valid frame in "
                f"{timeout_s}s, {len(buf)} B buffered: "
                f"{_ps1_uart_hex(buf, max_bytes=48)}"
            )
        else:
            logger.debug(
                f"PS1-NO2 UART: no response in {timeout_s}s (0 B read). "
                "Wiring: host tx must drive sensor rx (IO17), "
                "host rx from sensor tx (IO18), common GND, 3.3 V only."
            )
        return None

    def _find_gas_frame(self, buf):
        i = 0
        while i <= len(buf) - PS1_NO2_RESPONSE_LEN:
            if buf[i] == 0xFF and buf[i + 1] == 0x86:
                frame = bytes(buf[i:i + PS1_NO2_RESPONSE_LEN])
                if ps1_no2_frame_valid(frame):
                    return frame
            i += 1
        return None
