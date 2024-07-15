from sensors.sensor import Sensor
from enums import Dimension, SensorModel, Quality
from adafruit_ags02ma import AGS02MA # type: ignore

class AGS02MASensor(Sensor):
    def __init__(self):
        super().__init__()
        self.model_id = SensorModel.AGS02MA
        self.measures_values = [
            Dimension.TVOC,
            Dimension.GAS_RESISTANCE,
        ]
        self.current_values = {
            Dimension.TVOC: None,
            Dimension.GAS_RESISTANCE: None,
        }
        self.value_quality = {
            Dimension.TVOC: Quality.HIGH,
            Dimension.GAS_RESISTANCE: Quality.HIGH,
        }
        
    def attempt_connection(self, i2c):
        try:
            # MUST connect I2C at 20KHz!
            # It is possible to change the I2C address 'semi-permanently' but
            # note that you'll need to restart the script after adjusting the address!
            # ags.set_address(0x1A)
            self.ags02ma_device = AGS02MA(i2c, address=0x1A)
        except:
            print("AGS02MA sensor not detected")
            return False
    
        print(f"AGS02MA device found on I2C bus {i2c}")
        return True

    def read(self):
        try:
            self.current_values = {
                Dimension.TVOC: self.ags02ma_device.TVOC,
                Dimension.GAS_RESISTANCE: self.ags02ma_device.gas_resistance,
            }
        except:
            print("AGS02MA Error")