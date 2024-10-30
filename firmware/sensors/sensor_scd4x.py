from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
import adafruit_scd4x # type: ignore
from logger import logger

class Scd4xSensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.SCD4X
                
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.HUMIDITY,
            Dimension.CO2,
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.HUMIDITY: None,
            Dimension.CO2: None,
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.LOW,
            Dimension.HUMIDITY: Quality.LOW,
            Dimension.CO2: Quality.HIGH,
        }
        
    def attempt_connection(self, i2c):
        try:
            self.scd4x = adafruit_scd4x.SCD4X(i2c)
            self.sensor_details = bytearray(self.scd4x.serial_number)
            self.scd4x.start_periodic_measurement()
        except:
            logger.debug("SCD4x sensor not detected")
            return False
        
        logger.debug(f"SCD4x device found on I2C bus {i2c}")
        return True

    def read(self):
        pass
        #return NotImplementedError("Not implemented yet")
        try:
            if self.scd4x.data_ready:
                self.current_values = {
                    Dimension.TEMPERATURE: self.scd4x.temperature,
                    Dimension.HUMIDITY: self.scd4x.relative_humidity,
                    Dimension.CO2: self.scd4x.CO2,
                }
        except:
            logger.error("Error reading SEN5x sensor data")
