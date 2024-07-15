import adafruit_sht4x # type: ignore
from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality

class Sht4xSensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.SHT4X
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
            self.sht4x_device = adafruit_sht4x.SHT4x(i2c)
            self.sensor_details = bytearray(hex(self.sht4x_device.serial_number).encode())
        except:
            print("SHT4x sensor not detected")
            return False

        print(f"SHT4x device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TEMPERATURE: self.sht4x_device.temperature,
                Dimension.HUMIDITY: self.sht4x_device.relative_humidity,
            }
        except:
            print("SHT4x Error")
