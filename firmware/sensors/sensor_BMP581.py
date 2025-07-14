from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger
import adafruit_bmp581
import board
import time

class BMP581Sensor(Sensor):
    def __init__(self, sea_level_pressure=1013.25):
        super().__init__()
        self.model_id = SensorModel.BMP581
        self.sea_level_pressure = sea_level_pressure  # hPa

        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.PRESSURE,
            Dimension.ALTITUDE,
        ]

        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.PRESSURE: None,
            Dimension.ALTITUDE: None,
        }

        self.value_quality = {
            Dimension.TEMPERATURE: Quality.MEDIUM,
            Dimension.PRESSURE: Quality.HIGH,
            Dimension.ALTITUDE: Quality.MEDIUM,
        }

    def attempt_connection(self, i2c):
        try:
            self.sensor = adafruit_bmp581.BMP581_I2C(i2c)
            self.sensor.sea_level_pressure = self.sea_level_pressure
            logger.debug("BMP581 sensor initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"BMP581 initialization failed: {e}")
            return False

    def read(self):
        try:
            self.current_values[Dimension.TEMPERATURE] = self.sensor.temperature  # °C
            self.current_values[Dimension.PRESSURE] = self.sensor.pressure        # hPa
            self.current_values[Dimension.ALTITUDE] = self.sensor.altitude        # meters
        except Exception as e:
            logger.error(f"Error reading BMP581 sensor data: {e}")
