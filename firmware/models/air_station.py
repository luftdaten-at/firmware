from models.ld_product_model import LdProductModel
from enums import LdProduct, Color, BleCommands, AirstationConfigFlags, Dimension, SensorModel
from wifi_client import WifiUtil
import time
from config import Config
from json import dump, load, loads
from ld_service import LdService
from os import listdir, remove, uname
import struct
from lib.cptoml import fetch
from storage import remount
from logger import logger

class AirStation(LdProductModel): 
    def __init__(self, ble_service: LdService, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = True
        self.polling_interval = 2
        self.last_measurement = None

        # Load settings from boot.toml
        self.device_id = Config.settings['device_id'] 
        self.api_key = Config.settings['api_key']

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

    def save_data(self, data: dict, tag = 'normal'):
        current_time = time.localtime()
        formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"
        remount('/', False) 
        file_name = formatted_time.replace(':', '_').replace('.', '_')
        with open(f'{Config.runtime_settings["JSON_QUEUE"]}/{file_name}_{tag}.json', 'w') as f:
            dump(data, f)
        remount('/', False)

    def read_all_sensors(self):
        for sensor in self.sensors:
            try:
                sensor.read()
            except:
                logger.error(f"Error reading sensor {sensor.model_id}, using previous values")

    def get_json(self):
        self.read_all_sensors()
        sensor_values = {}
        for id, sensor in enumerate(self.sensors):
            sensor_values[id] = {
                "type": sensor.model_id,
                "data": sensor.current_values
            }

        data = self.get_info()
        data["sensors"] = sensor_values

        return data
    
    def get_json_list_sensor_community(self):
        '''
        // header
        Content-Type: application/json  
        X-Pin: ...
        X-Sensor: ...
        // data
        {
            "software_version": "your_version", 
            "sensordatavalues":[
                {"value_type":"temperature","value":"22.30"},
                {"value_type":"humidity","value":"34.70"}
            ]
        } 
        '''
        self.read_all_sensors()
        software_version = f"Luftdaten.at-{Config.settings['FIRMWARE_MAJOR']}.{Config.settings['FIRMWARE_MINOR']}.{Config.settings['FIRMWARE_PATCH']}"

        # Tuple(header, data)
        dict_list = [
            (
                # header
                {
                    'Content-Type': 'application/json',
                    # GPS(Neo-6M) => Pin 9
                    'X-Pin': '9',
                    'X-Sensor': Config.settings['device_id']
                },
                #data
                {
                    "software_version": software_version,
                    "sensordatavalues": [
                        {'value_type': 'latitude', 'value': Config.settings.get("latitude", None)},
                        {'value_type': 'longitude', 'value': Config.settings.get("longitude", None)},
                        {'value_type': 'height', 'value': Config.settings.get("height", None)}
                    ]
                }
            )
        ]

        for sensor in self.sensors:
            header={
                'Content-Type': 'application/json',
                'X-Pin': str(SensorModel.get_pin(sensor.model_id)),
                'X-Sensor': Config.settings['device_id']
            }
            sensordatavalues = []
            for dim, val in sensor.current_values.items():
                sensordatavalues.append({
                    "value_type": Dimension.get_sensor_community_name(dim),
                    "value": val
                })

            data = {
                "software_version": software_version,
                "sensordatavalues": sensordatavalues
            }

            dict_list.append((header, data))

        return dict_list

    def send_to_api(self):
        for file_path in (f'{Config.runtime_settings["JSON_QUEUE"]}/{f}' for f in listdir(Config.runtime_settings["JSON_QUEUE"])):
            logger.debug(f'process file: {file_path}')
            with open(file_path, 'r') as f:
                data = load(f)

                if 'tmp_log.txt' in file_path:
                    # send status to Luftdaten APi
                    status_list = []
                    for line in f.readlines():
                        status_list.append(loads(line))

                    data = self.get_info()
                    data["status_list"] = status_list

                    response = WifiUtil.send_json_to_api(data)
                    logger.debug(f'{file_path=}')
                    logger.debug(f'API Response: {response.status_code}')
                    logger.debug(f'API Response: {response.text}')
                    if response.status_code == 200:  # Placeholder for successful sending check
                        remount('/', False)
                        remove(file_path) 
                        remount('/', True)
                elif 'sensor_community' in file_path:
                    # data = List[Tuple(header, data)]
                    for header, d in data:
                        response = WifiUtil.send_json_to_sensor_community(header=header, data=d)
                        logger.debug(f'{file_path=}')
                        logger.debug(f'API Response: {response.status_code}')
                        logger.debug(f'API Response: {response.text}')
                        if response.status_code != 200:
                            break
                    else:
                        remount('/', False)
                        remove(file_path) 
                        remount('/', True)
                else:
                    # send to Luftdaten APi
                    response = WifiUtil.send_json_to_api(data)
                    logger.debug(f'{file_path=}')
                    logger.debug(f'API Response: {response.status_code}')
                    logger.debug(f'API Response: {response.text}')
                    if response.status_code == 200:  # Placeholder for successful sending check
                        remount('/', False)
                        remove(file_path) 
                        remount('/', True)
                

    def tick(self):
        if not WifiUtil.radio.connected:
            self.status_led.status_led.fill(Color.RED)
            self.status_led.status_led.show()
            time.sleep(2)
            self.status_led.status_led.fill(Color.GREEN)
            self.status_led.status_led.show()

        if not Config.runtime_settings['rtc_is_set'] and WifiUtil.radio.connected:
            WifiUtil.set_RTC()

        if not Config.runtime_settings['rtc_is_set'] or not all([Config.settings['longitude'], Config.settings['latitude'], Config.settings['height']]):
            logger.warning('DATA CANNOT BE TRANSMITTED, Not all configurations have been made')
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
                sensor_community_data = self.get_json_list_sensor_community()

                self.save_data(data)

                if Config.settings['SEND_TO_SENSOR_COMMUNITY']:
                    self.save_data(sensor_community_data, tag='sensor_community')

        if WifiUtil.radio.connected:
            self.send_to_api()
