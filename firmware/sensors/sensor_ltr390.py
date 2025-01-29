import adafruit_ltr390
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class Ltr390Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.LTR390
        self.measures_values = [
            Dimension.UVS,
            Dimension.LIGHT,
            Dimension.UVI,
            Dimension.LUX
        ]
        self.current_values = {
            Dimension.UVS: None,
            Dimension.LIGHT: None,
            Dimension.UVI: None,
            Dimension.LUX: None
        }
        self.value_quality = {
            Dimension.UVS: Quality.HIGH,
            Dimension.LIGHT: Quality.HIGH,
            Dimension.UVI: Quality.HIGH,
            Dimension.LUX: Quality.HIGH 
        }
        
    def attempt_connection(self, i2c):
        try:
            self.ltr = adafruit_ltr390.LTR390(i2c)
        except:
            logger.debug("LTR390 sensor not detected")
            return False

        logger.debug(f"LTR390 device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.UVS: self.ltr.uvs,
                Dimension.LIGHT: self.ltr.light,
                Dimension.UVI: self.ltr.uvi,
                Dimension.LUX: self.ltr.lux
            }
        except:
            logger.error("LTR390 Error")
