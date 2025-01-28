import adafruit_bmp3xx
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class Bmp390Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.BMP390
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.PRESSURE,
            Dimension.ALTITUDE
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.PRESSURE: None,
            Dimension.ALTITUDE: None
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.HIGH,
            Dimension.PRESSURE: Quality.HIGH,
            Dimension.ALTITUDE: Quality.HIGH 
        }
        
    def attempt_connection(self, i2c):
        try:
            self.bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)
        except:
            logger.debug("Bmp390 sensor not detected")
            return False

        logger.debug(f"Bmp390 device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.bmp.temperature,
                Dimension.PRESSURE: self.bmp.pressure,
                Dimension.ALTITUDE: self.bmp.altitude
            }
        except:
            logger.error("Bmp390 Error")
