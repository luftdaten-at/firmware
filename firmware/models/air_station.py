from models.ld_product_model import LdProductModel
from enums import LdProduct, Color, BleCommands
from wifi_client import WifiUtil
import wifi
import rtc
import time
from config import Config
from util import Util

class AirStation(LdProductModel): 
    def __init__(self, ble_service, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.polling_interval = 2  # TODO is this the best value?
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = True 
        self.new_ssid = None
        self.new_password = None
        self.hight = None
        
    def receive_command(self, command):
        if len(command) == 0:
            return

        cmd, *data = command
        if cmd == BleCommands.SET_WIFI_SSID:
            self.new_ssid = bytearray(data).decode('utf-8')

        if cmd == BleCommands.SET_WIFI_PASSWORD:
            self.new_password = bytearray(data).decode('utf-8')

        if cmd == BleCommands.SET_LONGITUDE:
            Util.write_to_settings({
                "longitude": bytearray(data).decode('utf-8')
            })

        if cmd == BleCommands.SET_LATITUDE:
            Util.write_to_settings({
                "latitude": bytearray(data).decode('utf-8')
            })
        
        if cmd == BleCommands.SET_HIGHT:
            Util.write_to_settings({
                "hight": bytearray(data).decode('utf-8')
            })

        if self.new_ssid and self.new_password:
            self.wifi.connect(self.new_ssid, self.new_password)
            WifiUtil.connect(self.new_ssid, self.new_password)
            self.new_ssid = None
            self.new_password = None
        

    def receive_button_press(self):
        self.ble_on = not self.ble_on
        # Possibly change polling interval?
        if self.ble_on:
            self.status_led.fill(Color.BLUE)
        else:
            self.status_led.fill(Color.OFF)
        self.status_led.show()

    def get_info(self):
        # Get the current time from the RTC (real-time clock)
        current_time = self.clock.datetime

        # Format time as an ISO 8601 string (e.g., "2024-04-29T08:25:20.000Z")
        time_str = "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.000Z".format(
            current_time.tm_year,
            current_time.tm_mon,
            current_time.tm_mday,
            current_time.tm_hour,
            current_time.tm_min,
            current_time.tm_sec
        )

        # Return device info with the actual values
    
    def tick(self):
        if not Config.rtc_is_set or not Util.check_if_configs_are_set(['longitude', 'latitude', 'hight']):
            print('DATA CANNOT BE TRANSMITTED')
            print('Not all configurations have been made')
            return 
        '''
        [
        [
            {
                "time": "2024-04-29T08:25:20.766Z",
                "device": "string",
                "location": {
                    "lat": 0,
                    "lon": 0,
                    "hight": 0
            },
            {
                "sen1" : {"dim": "val", "dim2": "val2"},
                "sen2" : {"dim": "val", "dim2": "val2"}
            }
        ]
        ] 
        '''
        sensor_values = {}
        for sensor in self.sensors:
            try:
                sensor.read()
            except:
                print(f"Error reading sensor {sensor.model_id}, using previous values")

            sensor_values[sensor.model_id] = sensor.current_values
        
        data = [self.get_info()] + [sensor_values]

        print(data)

    def connection_update(self, connected):
        pass
