import adafruit_ahtx0 # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class AHT20Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.AHT20
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
            self.aht20_device = adafruit_ahtx0.AHTx0(i2c)
        except:
            logger.debug("AHT20 sensor not detected")
            return False
    
        logger.debug(f"AHT20 device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.aht20_device.temperature,
                Dimension.HUMIDITY: self.aht20_device.relative_humidity,
            }
        except:
            logger.error("AHT20 Error")