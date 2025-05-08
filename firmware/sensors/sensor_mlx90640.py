import time
import adafruit_mlx90640
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class Mlx90640Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.MLX90640
        self.measures_values = [Dimension.THERMAL_ARRAY]
        self.current_values = {
            Dimension.THERMAL_ARRAY: None
        }
        self.value_quality = {
            Dimension.THERMAL_ARRAY: Quality.MEDIUM  # or HIGH depending on use
        }

    def get_serial_number(self):
        try:
            serial = self.mlx.serial_number
            return ''.join(f'{s:04X}' for s in serial)  # formatted as hex string
        except Exception as e:
            logger.error(f"Error getting MLX90640 serial number: {e}")
            return "UNKNOWN"

    def attempt_connection(self, i2c):
        try:
            self.mlx = adafruit_mlx90640.MLX90640(i2c)
        except Exception as e:
            logger.debug(f"MLX90640 sensor not detected: {e}")
            return False

        logger.debug("MLX90640 sensor initialized")

        try:
            serial = self.get_serial_number()
            logger.debug(f"MLX90640 serial number: {serial}")
            self.sensor_details = bytearray(serial.encode("ascii"))
        except Exception as e:
            logger.warning(f"Could not get sensor details: {e}")
            self.sensor_details = bytearray()

        try:
            self.mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_1_HZ
        except Exception as e:
            logger.warning(f"Failed to set refresh rate: {e}")

        return True

    def read(self):
        frame = [0.0] * 768  # 24x32
        try:
            self.mlx.getFrame(frame)
            self.current_values[Dimension.THERMAL_ARRAY] = frame
        except ValueError:
            logger.warning("MLX90640 frame read error, retrying")
        except Exception as e:
            logger.error(f"Unexpected MLX90640 read error: {e}")
