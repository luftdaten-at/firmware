from models.ld_product_model import LdProductModel
from enums import LdProduct, Color, BleCommands, AirstationConfigFlags
from wifi_client import WifiUtil
import time
from config import Config
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

        # Load settings from boot.toml
        self.device_id = fetch('device_id', toml='/boot.toml')
        self.api_key = fetch('api_key', toml='/boot.toml')

        self.send_configuration()
        self.status_led.status_led.fill(Color.GREEN)
        self.status_led.status_led.show()

    def send_configuration(self):
        self.ble_service.air_station_configuration = self.encode_configurations()
        
    def receive_command(self, command):
        if len(command) == 0:
            return

        cmd, *data = command

        data = bytearray(data)
        if cmd == BleCommands.SET_AIR_STATION_CONFIGURATION:
            wifi_config_changed = self.decode_configuration(data) 

            if wifi_config_changed:
                WifiUtil.connect()

            # Update Characteristic with new data
            self.send_configuration()

    def decode_configuration(self, data):
        wifi_config_changed = False
        idx = 0
        while idx < len(data):
            flag = data[idx]                
            idx += 1
            length = data[idx]
            idx += 1

            if flag == AirstationConfigFlags.AUTO_UPDATE_MODE:
                Config.settings['auto_update_mode'] = struct.unpack('>i', data[idx:idx + length])[0]

            if flag == AirstationConfigFlags.BATTERY_SAVE_MODE:
                Config.settings['battery_save_mode'] = struct.unpack('>i', data[idx:idx + length])[0]

            if flag == AirstationConfigFlags.MEASUREMENT_INTERVAL:
                Config.settings['measurement_interval'] = struct.unpack('>i', data[idx:idx + length])[0]

            if flag == AirstationConfigFlags.LONGITUDE:
                Config.settings['longitude'] = data[idx:idx + length].decode('utf-8')  # Decode as string

            if flag == AirstationConfigFlags.LATITUDE:
                Config.settings['latitude'] = data[idx:idx + length].decode('utf-8')  # Decode as string

            if flag == AirstationConfigFlags.HEIGHT:
                Config.settings['height'] = data[idx:idx + length].decode('utf-8')  # Decode as string

            if flag == AirstationConfigFlags.SSID:
                Config.settings['SSID'] = data[idx:idx + length].decode('utf-8')  # Decode as string
                wifi_config_changed = True

            if flag == AirstationConfigFlags.PASSWORD:
                Config.settings['PASSWORD'] = data[idx:idx + length].decode('utf-8')  # Decode as string
                wifi_config_changed = True
            
            idx += length

        return wifi_config_changed

    def encode_configurations(self):
        data = bytearray()
        for flag, value in [
            (AirstationConfigFlags.AUTO_UPDATE_MODE, Config.settings['auto_update_mode']),
            (AirstationConfigFlags.BATTERY_SAVE_MODE, Config.settings['battery_save_mode']),
            (AirstationConfigFlags.MEASUREMENT_INTERVAL, Config.settings['measurement_interval']),
            (AirstationConfigFlags.LONGITUDE, Config.settings['longitude']),
            (AirstationConfigFlags.LATITUDE, Config.settings['latitude']),
            (AirstationConfigFlags.HEIGHT, Config.settings['height']),
            (AirstationConfigFlags.DEVICE_ID, self.device_id)
        ]:
            value_bytes = value.encode('utf-8') if isinstance(value, str) else struct.pack('>i', value)
            data.append(flag)
            data.append(len(value_bytes) if isinstance(value, str) else struct.calcsize('>i'))
            data.extend(value_bytes)
        
        return data

    def receive_button_press(self):
        self.ble_on = not self.ble_on
        if self.ble_on:
            self.status_led.status_led.fill(Color.GREEN)
            self.status_led.status_led.show()
        else:
            self.status_led.status_led.fill(Color.OFF)
            self.status_led.status_led.show()

    def get_info(self):
        current_time = time.localtime()
        formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"

        device_info = {
            "station": {
                "time": formatted_time,
                "device": self.device_id,
                "firmware": uname()[3],
                "apikey": self.api_key,
                "source": 1,
                "location": {
                    "lat": Config.settings.get("latitude", None),
                    "lon": Config.settings.get("longitude", None),
                    "height": Config.settings.get("height", None)
                }
            }
        }

        return device_info

    def save_data(self, data: dict):
        file_name = data["station"]["time"].replace(':', '_').replace('.', '_')
        with open(f'{Config.runtime_settings["JSON_QUEUE"]}/{file_name}.json', 'w') as f:
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
        for file_path in (f'{Config.runtime_settings["JSON_QUEUE"]}/{f}' for f in listdir(Config.runtime_settings["JSON_QUEUE"])):
            print(file_path)
            with open(file_path, 'r') as f:
                data = load(f)
                print(data)
                print('Send data: ')
                response = WifiUtil.send_json_to_api(data)
                print(f'Response: {response.status_code}')
                print(f'Response: {response.text}')
                if True:  # Placeholder for successful sending check
                    remove(file_path) 

    def tick(self):
        if not WifiUtil.radio.connected:
            WifiUtil.connect()

        if not WifiUtil.radio.connected:
            self.status_led.status_led.fill(Color.RED)
            self.status_led.status_led.show()
            time.sleep(2)
            self.status_led.status_led.fill(Color.GREEN)
            self.status_led.status_led.show()

        if not Config.runtime_settings['rtc_is_set'] and WifiUtil.radio.connected:
            WifiUtil.set_RTC()

        if not Config.runtime_settings['rtc_is_set'] or not all([Config.settings['longitude'], Config.settings['latitude'], Config.settings['height']]):
            print('DATA CANNOT BE TRANSMITTED')
            print('Not all configurations have been made')
            self.status_led.status_led.fill(Color.PURPLE)
            self.status_led.status_led.show()
            time.sleep(2)
            self.status_led.status_led.fill(Color.GREEN)
            self.status_led.status_led.show()
        else:
            cur_time = time.monotonic()
            if not self.last_measurement or cur_time - self.last_measurement >= Config.settings['measurement_interval']:
                self.last_measurement = cur_time
                data = self.get_json()
                self.save_data(data)

        if WifiUtil.radio.connected:
            self.send_to_api()
