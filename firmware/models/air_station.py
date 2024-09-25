from models.ld_product_model import LdProductModel
from enums import LdProduct, Color, BleCommands
from wifi_client import WifiUtil
import wifi
import adafruit_ntp
import rtc
import time
import socketpool
import ipaddress
from config import Config

class AirStation(LdProductModel): 
    def __init__(self, ble_service, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.polling_interval = 2  # TODO is this the best value?
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = True 
        self.new_ssid = None
        self.new_password = None
        self.longitude = None
        self.latitude = None
        self.hight = None
        self.clock = rtc.RTC()
        
    def receive_command(self, command):
        if len(command) == 0:
            return

        cmd, *data = command
        if cmd == BleCommands.SET_WIFI_SSID:
            self.new_ssid = bytearray(data).decode('utf-8')

        if cmd == BleCommands.SET_WIFI_PASSWORD:
            self.new_password = bytearray(data).decode('utf-8')

        if cmd == BleCommands.SET_LONGITUDE:
            self.longitude = bytearray(data).decode('utf-8')

        if cmd == BleCommands.SET_LATITUDE:
            self.latitude = bytearray(data).decode('utf-8')
        
        if cmd == BleCommands.SET_HIGHT:
            self.hight = bytearray(data).decode('utf-8')

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
        return {
            "time": time_str,
            "device": self.model_id,  # Assuming the device name is "AirStation"
            "location": {
                "lat": self.latitude,
                "lon": self.longitude,
                "hight": self.hight
            }
        }
    
    def tick(self):
        if not all([self.longitude, self.latitude, self.hight, Config.rtc_is_set]):
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
