import adafruit_sht31d # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality

class Sht31Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.SHT31
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.HUMIDITY,
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.HUMIDITY: None,
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.HIGH,
            Dimension.HUMIDITY: Quality.HIGH,
        }
        
    def attempt_connection(self, i2c):
        try:
            self.sht31_device = adafruit_sht31d.SHT31D(i2c)
        except:
            print("SHT31 sensor not detected")
            return False

        print(f"SHT31 device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.sht31_device.temperature,
                Dimension.HUMIDITY: self.sht31_device.relative_humidity,
            }
        except:
            print("SHT31 Error")
