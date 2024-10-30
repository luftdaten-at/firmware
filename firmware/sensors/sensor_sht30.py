from sht30 import SHT30 # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class Sht30Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.SHT30
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
            self.sht30_device = SHT30()
        except:
            logger.debug("SHT30 sensor not detected")
            return False

        logger.debug(f"SHT30 device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            temperature, humidity = self.sht30_device.measure()
            self.current_values = {
                Dimension.TEMPERATURE: temperature,
                Dimension.HUMIDITY: humidity,
            }
        except:
            logger.error("SHT30 Error")
