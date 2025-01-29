from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class Lsm6dsSensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.LSM6DS
        self.measures_values = [
            Dimension.ACCELERATION_X,
            Dimension.ACCELERATION_Y,
            Dimension.ACCELERATION_Z,
            Dimension.GYRO_X,
            Dimension.GYRO_Y,
            Dimension.GYRO_Z,
        ]
        self.current_values = {
            Dimension.ACCELERATION_X: None,
            Dimension.ACCELERATION_Y: None,
            Dimension.ACCELERATION_Z: None,
            Dimension.GYRO_X: None,
            Dimension.GYRO_Y: None,
            Dimension.GYRO_Z: None,
        }
        self.value_quality = {
            Dimension.ACCELERATION_X: Quality.HIGH,
            Dimension.ACCELERATION_Y: Quality.HIGH,
            Dimension.ACCELERATION_Z: Quality.HIGH,
            Dimension.GYRO_X: Quality.HIGH,
            Dimension.GYRO_Y: Quality.HIGH,
            Dimension.GYRO_Z: Quality.HIGH,
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
            ax, ay, az = self.sox.acceleration
            gx, gy, gz = self.sox.gyro
            self.current_values = {
                Dimension.ACCELERATION_X: ax,
                Dimension.ACCELERATION_Y: ay,
                Dimension.ACCELERATION_Z: az,
                Dimension.GYRO_X: gx,
                Dimension.GYRO_Y: gy,
                Dimension.GYRO_Z: gz,
            }
        except:
            logger.error("LSM6DS Error")
