import bmp581  # type: ignore

from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

_BMP581_I2C_ADDRESSES = (0x47, 0x46)


class Bmp581Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.BMP581
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.PRESSURE,
            Dimension.ALTITUDE,
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.PRESSURE: None,
            Dimension.ALTITUDE: None,
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.HIGH,
            Dimension.PRESSURE: Quality.HIGH,
            Dimension.ALTITUDE: Quality.HIGH,
        }

    def attempt_connection(self, i2c):
        for address in _BMP581_I2C_ADDRESSES:
            try:
                self.bmp = bmp581.BMP581(i2c, address=address)
                logger.debug("Bmp581 sensor found at 0x%02x" % address)
                return True
            except (RuntimeError, OSError, ValueError):
                logger.debug("Bmp581 sensor not found at 0x%02x" % address)

        logger.debug("Bmp581 sensor not detected")
        return False

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.bmp.temperature,
                # Driver returns kPa; firmware uses hPa (Dimension.PRESSURE).
                Dimension.PRESSURE: self.bmp.pressure * 10,
                Dimension.ALTITUDE: self.bmp.altitude,
            }
        except Exception:
            logger.error("Bmp581 read error")
