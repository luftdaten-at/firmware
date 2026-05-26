from sensirion_i2c_sen63c.device import Sen63cDevice  # type: ignore
from sensirion_i2c_driver import I2cTransceiver, I2cConnection, CrcCalculator  # type: ignore
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel  # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
import time
from logger import logger

# Same default address as Sensirion SEN66 on the SEK cable; distinguish by product name in probe order.
SEN63C_DEFAULT_ADDRESS = 0x6B


def _product_ascii(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (bytes, bytearray)):
        # CircuitPython: decode() may not accept keyword args; mirror errors="replace" for bytes.
        return "".join(chr(b) if b < 128 else "?" for b in raw).split("\x00")[0].strip()
    return str(raw).strip()


def _serial_to_ascii_bytes(serial) -> bytes:
    sn = serial if isinstance(serial, str) else _product_ascii(serial)
    safe = "".join(c if ord(c) < 128 else "?" for c in sn)
    return safe.encode("ascii")


class Sen63cSensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.SEN63C
        self.current_values = {
            Dimension.PM1_0: None,
            Dimension.PM2_5: None,
            Dimension.PM4_0: None,
            Dimension.PM10_0: None,
            Dimension.TEMPERATURE: None,
            Dimension.HUMIDITY: None,
            Dimension.CO2: None,
        }
        self.measures_values = list(self.current_values.keys())
        self.value_quality = {
            Dimension.PM1_0: Quality.HIGH,
            Dimension.PM2_5: Quality.HIGH,
            Dimension.PM4_0: Quality.HIGH,
            Dimension.PM10_0: Quality.HIGH,
            Dimension.TEMPERATURE: Quality.LOW,
            Dimension.HUMIDITY: Quality.LOW,
            Dimension.CO2: Quality.MEDIUM,
        }

    def get_serial_number(self):
        return str(self.sen63c_device.get_serial_number())

    def attempt_connection(self, i2c):
        try:
            transceiver = I2cTransceiver(i2c, SEN63C_DEFAULT_ADDRESS)
            channel = I2cChannel(
                I2cConnection(transceiver),
                slave_address=SEN63C_DEFAULT_ADDRESS,
                crc=CrcCalculator(8, 0x31, 0xff, 0x0),
            )
            self.sen63c_device = Sen63cDevice(channel)
        except (OSError, ValueError):
            logger.debug("SEN63C sensor not detected (I2C)")
            return False

        try:
            pname = _product_ascii(self.sen63c_device.get_product_name())
            # SEN66 also uses 0x6B; refuse so the SEN66 driver can probe next.
            if "SEN63" not in pname.upper():
                logger.debug(f"SEN63C probe: product mismatch ({pname!r}); skipping")
                return False
        except Exception as e:
            logger.debug(f"SEN63C product name read failed: {type(e).__name__}: {e}")
            return False

        logger.debug("SEN63C initialised, resetting, waiting 1 second before read")
        self.sen63c_device.device_reset()
        time.sleep(1.0)

        serial = self.sen63c_device.get_serial_number()
        version = self.sen63c_device.get_version()

        logger.debug(
            f"SEN63C device found on I2C bus {i2c}, version: {version}, serial: {serial}"
        )

        self.sensor_details = bytearray(
            [
                version[0],
                version[1],
            ]
        )
        self.sensor_details.extend(_serial_to_ascii_bytes(serial))

        self.sen63c_device.start_continuous_measurement()
        return True

    def read(self):
        try:
            pm1, pm2_5, pm4, pm10, humidity, temperature, co2 = (
                self.sen63c_device.read_measured_values()
            )
            self.current_values = {
                Dimension.PM1_0: pm1.value,
                Dimension.PM2_5: pm2_5.value,
                Dimension.PM4_0: pm4.value,
                Dimension.PM10_0: pm10.value,
                Dimension.HUMIDITY: humidity.value,
                Dimension.TEMPERATURE: temperature.value,
                Dimension.CO2: co2.value,
            }
        except Exception as e:
            logger.error(f"Error reading SEN63C sensor data: {e}")
