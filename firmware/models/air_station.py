from models.ld_product_model import LdProductModel
from enums import LdProduct, Color, BleCommands
from wifi_client import WifiUtil
import wifi
import rtc
import time
from config import Config
from util import Util
import json

class AirStation(LdProductModel): 
    def __init__(self, ble_service, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.polling_interval = 2  # TODO is this the best value?
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = True 
        data = Util.get_from_settings([
            'SSID',
            'PASSWORD',
            'longitude',
            'latitude',
            'hight'
        ])

        self.longitude = data['longitude']
        self.latitude = data['latitude']
        self.hight = data['hight']

        Config.SSID = data['SSID']
        Config.PASSWORD = data['PASSWORD']

        WifiUtil.connect()
        
    def receive_command(self, command):
        if len(command) == 0:
            return

        cmd, *data = command
        print(command)
        print(cmd, data)

    def receive_button_press(self):
        self.ble_on = not self.ble_on
        # Possibly change polling interval?
        if self.ble_on:
            self.status_led.fill(Color.BLUE)
        else:
            self.status_led.fill(Color.OFF)
        self.status_led.show()

    def get_info(self):
        # Get current time from RTC
        current_time = time.localtime()

        # Format the time into ISO 8601 string
        formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"

        # Get latitude, longitude, and height from settings using Util
        settings = Util.get_from_settings(['latitude', 'longitude', 'hight'])

        # Construct the device information
        device_info = {
            "station": {
                "time": formatted_time,  # ISO format date and time with Z for UTC
                "device": self.model_id,  # Placeholder, replace with actual device ID
                "location": {
                    "lat": settings.get("latitude", "0"),  # Default to "0" if not set
                    "lon": settings.get("longitude", "0"),  # Default to "0" if not set
                    "height": settings.get("hight", "0")  # Default to "0" if not set
                }
            }
        }

        return device_info

    def save_data(self, data: dict):
        file_name = data["station"]["time"].replace(':', '_').replace('.', '_')
        with open(f'json_queue/{file_name}.json', 'w') as f:
            json.dump(data, f)
    
    def tick(self):
        if not Config.rtc_is_set:
            WifiUtil.set_RTC()

        if not Config.rtc_is_set or not all(Util.get_from_settings(['latitude', 'longitude', 'hight']).values()):
            print('DATA CANNOT BE TRANSMITTED')
            print('Not all configurations have been made')
            return 

        sensor_values = {}
        for id, sensor in enumerate(self.sensors):
            try:
                sensor.read()
            except:
                print(f"Error reading sensor {sensor.model_id}, using previous values")

            sensor_values[id] = {
                "type": sensor.model_id,
                "data": sensor.current_values
            } 

        data = self.get_info()
        data["sensors"] = sensor_values

        self.save_data(data)
