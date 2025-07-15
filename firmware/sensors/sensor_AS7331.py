from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
import iorodeo_as7331 as as7331
from logger import logger

class AS7331Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.AS7331

        self.measures_values = [
            Dimension.UVA,
            Dimension.UVB,
            Dimension.UVC,
            Dimension.TEMPERATURE,
        ]

        self.current_values = {
            Dimension.UVA: None,
            Dimension.UVB: None,
            Dimension.UVC: None,
            Dimension.TEMPERATURE: None,
        }

        self.value_quality = {
            Dimension.UVA: Quality.HIGH,
            Dimension.UVB: Quality.HIGH,
            Dimension.UVC: Quality.HIGH,
            Dimension.TEMPERATURE: Quality.LOW,
        }

    def attempt_connection(self, i2c):
        try:
            self.sensor = as7331.AS7331(i2c)
            self.sensor.gain = as7331.GAIN_512X
            self.sensor.integration_time = as7331.INTEGRATION_TIME_128MS

            logger.debug(f"AS7331 initialized with chip ID {self.sensor.chip_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AS7331: {e}")
            return False

    def read(self):
        try:
            uva, uvb, uvc, temp = self.sensor.values
            self.current_values[Dimension.UVA] = uva
            self.current_values[Dimension.UVB] = uvb
            self.current_values[Dimension.UVC] = uvc
            self.current_values[Dimension.TEMPERATURE] = temp
        except Exception as e:
            logger.error(f"Error reading AS7331 sensor data: {e}")
