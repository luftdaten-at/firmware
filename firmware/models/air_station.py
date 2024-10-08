from models.ld_product_model import LdProductModel
from enums import LdProduct, Color, AutoUpdateMode, AirStationMeasurementInterval, BatterySaverMode, BleCommands, AirstationConfigFlags
from wifi_client import WifiUtil
import time
from config import Config
from util import Util
from json import dump, load
from ld_service import LdService
from os import listdir, remove, uname
import struct
from lib.cptoml import fetch

class AirStation(LdProductModel): 
    def __init__(self, ble_service: LdService, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = True
        self.polling_interval = 2
        self.last_measurement = None

        data = Util.get_from_settings([
            'SSID',
            'PASSWORD',
            'longitude',
            'latitude',
            'height',
            'auto_update_mode',
            'battery_save_mode',
            'measurement_interval'
        ])

        self.device_id = fetch('device_id', toml='/boot.toml')
        self.longitude = data['longitude']
        self.latitude = data['latitude']
        self.height = data['height']
        self.auto_update_mode = AutoUpdateMode.off if not data['auto_update_mode'] else data['auto_update_mode']
        self.battery_save_mode = BatterySaverMode.off if not data['battery_save_mode'] else data['battery_save_mode']
        self.measurement_interval = AirStationMeasurementInterval.sec30 if not data['measurement_interval'] else data['measurement_interval']

        Config.SSID = data['SSID']
        Config.PASSWORD = data['PASSWORD']

        self.send_configuration()
        self.status_led.status_led.fill(Color.GREEN)
        self.status_led.status_led.show()

    def send_configuration(self):
        self.ble_service.air_station_configuration = bytearray([self.auto_update_mode, self.battery_save_mode, self.measurement_interval >> 8, self.measurement_interval & ((1<<8)-1)])
        
    def receive_command(self, command):
        if len(command) == 0:
            return

        cmd, *data = command

        data = bytearray(data)
        if cmd == BleCommands.SET_AIR_STATION_CONFIGURATION:
            wifi_config_changed = False
            idx = 0
            while idx < len(data):
                flag = data[idx]                
                idx += 1
                length = data[idx]
                idx += 1
                if flag == AirstationConfigFlags.AUTO_UPDATE_MODE:
                    self.auto_update_mode = struct.unpack('>i', data[idx:idx + length])[0]

                if flag == AirstationConfigFlags.BATTERY_SAVE_MODE:
                    self.battery_save_mode = struct.unpack('>i', data[idx:idx + length])[0]

                if flag == AirstationConfigFlags.MEASUREMENT_INTERVAL:
                    self.measurement_interval = struct.unpack('>i', data[idx:idx + length])[0]

                if flag == AirstationConfigFlags.LONGITUDE:
                    self.longitude = data[idx:idx + length].decode('utf-8')  # Decode as string

                if flag == AirstationConfigFlags.LATITUDE:
                    self.latitude = data[idx:idx + length].decode('utf-8')  # Decode as string

                if flag == AirstationConfigFlags.HEIGHT:
                    self.height = data[idx:idx + length].decode('utf-8')  # Decode as string

                if flag == AirstationConfigFlags.SSID:
                    Config.SSID = data[idx:idx + length].decode('utf-8')  # Decode as string
                    wifi_config_changed = True

                if flag == AirstationConfigFlags.PASSWORD:
                    Config.PASSWORD = data[idx:idx + length].decode('utf-8')  # Decode as string
                    wifi_config_changed = True
                
                idx += length

            Util.write_to_settings({
                'SSID': Config.SSID,
                'PASSWORD': Config.PASSWORD,
                'longitude': self.longitude,
                'latitude': self.latitude,
                'height': self.height,
                'auto_update_mode': self.auto_update_mode,
                'battery_save_mode': self.battery_save_mode,
                'measurement_interval': self.measurement_interval
            })

            if wifi_config_changed:
                WifiUtil.connect()

    def receive_button_press(self):
        self.ble_on = not self.ble_on
        # Possibly change polling interval?
        if self.ble_on:
            self.status_led.status_led.fill(Color.BLUE)
            self.status_led.status_led.show()
        else:
            self.status_led.status_led.fill(Color.OFF)
            self.status_led.status_led.show()
        self.status_led.show()

    def get_info(self):
        # Get current time from RTC
        current_time = time.localtime()

        # Format the time into ISO 8601 string
        formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"

        # Get latitude, longitude, and height from settings using Util
        settings = Util.get_from_settings(['latitude', 'longitude', 'height'])

        # Construct the device information
        device_info = {
            "station": {
                "time": formatted_time,  # ISO format date and time with Z for UTC
                "device": self.device_id,  # Placeholder, replace with actual device ID
                "firmware": uname()[3],
                "apikey": "string",
                "source": 1,
                "location": {
                    "lat": settings.get("latitude", None),  # Default to "0" if not set
                    "lon": settings.get("longitude", None),  # Default to "0" if not set
                    "height": settings.get("height", None)  # Default to "0" if not set
                }
            }
        }

        return device_info

    def save_data(self, data: dict):
        file_name = data["station"]["time"].replace(':', '_').replace('.', '_')
        with open(f'{Config.JSON_QUEUE}/{file_name}.json', 'w') as f:
            dump(data, f)
    
    def get_json(self):
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

        return data
    
    def send_to_api(self):
        for file_path in (f'{Config.JSON_QUEUE}/{f}' for f in listdir(Config.JSON_QUEUE)):
            print(file_path)
            with open(file_path, 'r') as f:
                data = load(f)
                print(data)
                print('Send data: ')
                response = WifiUtil.send_json_to_api(data)
                print(f'Response: {response.status_code}')
                print(f'Response: {response.text}')
                # TODO: if sent sucessfully
                if True:
                    remove(file_path) 

    def tick(self):
        # try to connect to wifi
        if not WifiUtil.radio.connected:
            WifiUtil.connect()

        # if not connected status led should be red 
        if not WifiUtil.radio.connected:
            self.status_led.status_led.fill(Color.RED)
            self.status_led.status_led.show()
            time.sleep(2)
            self.status_led.status_led.fill(Color.GREEN)
            self.status_led.status_led.show()

        # set current time
        if not Config.rtc_is_set and WifiUtil.radio.connected:
            WifiUtil.set_RTC()

        # check if all configurations wich are nessecary are set
        if not Config.rtc_is_set or any([self.longitude is None, self.latitude is None, self.height is None]):
            print('DATA CANNOT BE TRANSMITTED')
            print('Not all configurations have been made')
            self.status_led.status_led.fill(Color.PURPLE)
            self.status_led.status_led.show()
            time.sleep(2)
            self.status_led.status_led.fill(Color.GREEN)
            self.status_led.status_led.show()
        else:
            # ready to send data
            cur_time = time.monotonic()
            if not self.last_measurement or cur_time - self.last_measurement >= self.measurement_interval:
                # make measurement
                self.last_measurement = cur_time
                data = self.get_json()
                self.save_data(data)

        if WifiUtil.radio.connected:
            # send saved data
            self.send_to_api()
