import adafruit_bmp280 # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality

class BMP280Sensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.BMP280
        self.measures_values = [
            Dimension.TEMPERATURE,
            Dimension.PRESSURE,
        ]
        self.current_values = {
            Dimension.TEMPERATURE: None,
            Dimension.PRESSURE: None,
        }
        self.value_quality = {
            Dimension.TEMPERATURE: Quality.HIGH,
            Dimension.PRESSURE: Quality.HIGH,
        }
        
    def attempt_connection(self, i2c):
        try:
            self.bmp280_device = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
            print("BMP280 sensor found at 0x77")
        except:
            print("BMP280 sensor not found at 0x77")
            try:
                self.bmp280_device = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
                print("BMP280 sensor found at 0x76")
            except:
                print("BMP280 sensor not found at 0x76")
                print("BMP280 sensor not detected")
                return False

        print(f"BMP280 device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.bmp280_device.temperature,
                Dimension.PRESSURE: self.bmp280_device.pressure,
            }
        except:
            print("BMP280 Error: ")