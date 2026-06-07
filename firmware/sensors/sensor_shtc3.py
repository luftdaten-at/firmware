import adafruit_shtc3  # type: ignore

from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger


class Shtc3Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.SHTC3
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.HUMIDITY,
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.HUMIDITY: None,
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.HIGH,
            Dimension.HUMIDITY: Quality.HIGH,
        }

    def attempt_connection(self, i2c):
        try:
            self.shtc3_device = adafruit_shtc3.SHTC3(i2c)
        except (RuntimeError, OSError, ValueError):
            logger.debug("SHTC3 sensor not detected")
            return False

        logger.debug("SHTC3 device found on I2C bus %s" % i2c)
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.shtc3_device.temperature,
                Dimension.HUMIDITY: self.shtc3_device.relative_humidity,
            }
        except Exception:
            logger.error("SHTC3 Error")
