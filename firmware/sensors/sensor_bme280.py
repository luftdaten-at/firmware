from adafruit_bme280 import basic as adafruit_bme280 # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from logger import logger

class BME280Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.BME280
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.HUMIDITY,
            Dimension.PRESSURE,
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.HUMIDITY: None,
            Dimension.PRESSURE: None,
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.HIGH,
            Dimension.HUMIDITY: Quality.HIGH,
            Dimension.PRESSURE: Quality.HIGH,
        }
        
    def attempt_connection(self, i2c):
        try:
            self.bme280_device = adafruit_bme280.Adafruit_BME280_I2C(i2c)
            logger.debug("BME280 sensor found at 0x77")
        except:
            logger.debug("BME280 sensor not found at 0x77")
            try:
                self.bme280_device = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
                logger.debug("BME280 sensor found at 0x76")
            except:
                logger.debug("BME280 sensor not found at 0x76")
                logger.debug("BME280 sensor not detected")
                return False

        logger.debug("BME280 initialised")
    
        logger.debug(f"BME280 device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.bme280_device.temperature,
                Dimension.HUMIDITY: self.bme280_device.relative_humidity,
                Dimension.PRESSURE: self.bme280_device.pressure,
            }
        except:
            logger.error("BME280 Error: ")