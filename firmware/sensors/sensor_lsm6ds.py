from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class Lsm6ds(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.LSM6DS
        self.measures_values = [
            Dimension.ACCELERATION,
            Dimension.GYRO
        ]
        self.current_values = {
            Dimension.ACCELERATION: None,
            Dimension.GYRO: None,
        }
        self.value_quality = {
            Dimension.ACCELERATION: Quality.HIGH,
            Dimension.GYRO: Quality.HIGH,
        }
        
    def attempt_connection(self, i2c):
        try:
            self.sox = LSM6DSOX(i2c)
        except:
            logger.debug("LSM6DS sensor not detected")
            return False

        logger.debug(f"LSM6DS device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.ACCELERATION: self.sox.acceleration,
                Dimension.GYRO: self.sox.gyro,
            }
        except:
            logger.error("LSM6DS Error")
