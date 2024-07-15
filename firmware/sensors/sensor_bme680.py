import adafruit_bme680 # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality

class BME680Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.BME680
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.HUMIDITY,
            Dimension.PRESSURE,
            Dimension.GAS_RESISTANCE,
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.HUMIDITY: None,
            Dimension.PRESSURE: None,
            Dimension.GAS_RESISTANCE: None,
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.HIGH,
            Dimension.HUMIDITY: Quality.HIGH,
            Dimension.PRESSURE: Quality.HIGH,
            Dimension.GAS_RESISTANCE: Quality.HIGH,
        }   
        
    def attempt_connection(self, i2c):
        try:
            self.bme680_device = adafruit_bme680.Adafruit_BME680_I2C(i2c)
        except:
            print("BME680 sensor not detected")
            return False

        print(f"BME680 device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.bme680_device.temperature,
                Dimension.HUMIDITY: self.bme680_device.relative_humidity,
                Dimension.PRESSURE: self.bme680_device.pressure,
                Dimension.GAS_RESISTANCE: self.bme680_device.gas,
            }
        except:
            print("BME680")