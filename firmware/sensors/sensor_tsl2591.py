import adafruit_tsl2591
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class Tsl2591Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.TSL2591

        self.measures_values = [
            Dimension.LUX,
            Dimension.VISIBLE,
            Dimension.INFRARED,
            Dimension.FULL_SPECTRUM,
            Dimension.RAW_LUMINOSITY
        ]
        self.current_values = {
            Dimension.LUX: None,
            Dimension.VISIBLE: None,
            Dimension.INFRARED: None,
            Dimension.FULL_SPECTRUM: None,
            Dimension.RAW_LUMINOSITY: None
        }
        self.value_quality = {
            Dimension.LUX: Quality.MEDIUM,
            Dimension.VISIBLE: Quality.HIGH,
            Dimension.INFRARED: Quality.HIGH,
            Dimension.FULL_SPECTRUM: Quality.HIGH,
            Dimension.RAW_LUMINOSITY: Quality.MEDIUM
        }

    def get_serial_number(self):
        # TSL2591 does not expose a unique ID via I2C
        return "UNAVAILABLE"

    def attempt_connection(self, i2c):
        try:
            self.sensor = adafruit_tsl2591.TSL2591(i2c)
        except Exception as e:
            logger.debug(f"TSL2591 sensor not detected: {e}")
            return False

        logger.debug("TSL2591 sensor initialized")
        self.sensor_details = bytearray(b'TSL2591')
        return True

    def read(self):
        try:
            self.current_values[Dimension.LUX] = self.sensor.lux
            self.current_values[Dimension.VISIBLE] = self.sensor.visible
            self.current_values[Dimension.INFRARED] = self.sensor.infrared
            self.current_values[Dimension.FULL_SPECTRUM] = self.sensor.full_spectrum
            self.current_values[Dimension.RAW_LUMINOSITY] = self.sensor.raw_luminosity
        except Exception as e:
            logger.error(f"Error reading TSL2591 data: {e}")
