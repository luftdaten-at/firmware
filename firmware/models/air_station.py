import time
import board
import struct
import neopixel
from wifi_client import WifiUtil
from storage import remount
from json import dump, load, loads
from lib.cptoml import fetch
from os import listdir, remove, uname

from led_controller import LedController
from config import Config
from models.ld_product_model import LdProductModel
from ld_service import LdService
from enums import LdProduct, Color, BleCommands, AirstationConfigFlags, Dimension, SensorModel
from logger import logger
from led_controller import RepeatMode

class AirStation(LdProductModel):
    NEOPIXEL_PIN = board.IO8
    NEOPIXLE_N = 1
    SCL = None
    SDA = None
    BUTTON_PIN = None

    def __init__(self, ble_service: LdService, sensors, battery_monitor):
        super().__init__(ble_service, sensors, battery_monitor)
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = True
        self.polling_interval = 2
        self.last_measurement = None

        # Load settings from boot.toml
        self.device_id = Config.settings['device_id'] 
        self.api_key = Config.settings['api_key']

        # init status led
        self.status_led = LedController(
            status_led=neopixel.NeoPixel(
                pin=AirStation.NEOPIXEL_PIN,
                n=AirStation.NEOPIXLE_N
            ),
            n=AirStation.NEOPIXLE_N
        )

        self.send_configuration()

        # Ready but not configured
        self.status_led.show_led({
            'repeat_mode': RepeatMode.FOREVER,
                'elements': [
                    {'color': Color.BLUE, 'duration': 0.5},
                    {'color': Color.RED, 'duration': 0.5},
            ],
        })
    
    def connection_update(self, connected):
        if connected:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.FOREVER,
                'elements': [
                    {'color': Color.GREEN, 'duration': 0.5},
                    {'color': Color.OFF, 'duration': 0.5},
                ],
            })
        else:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.FOREVER,
                'elements': [
                    {'color': Color.CYAN, 'duration': 0.5},
                    {'color': Color.OFF, 'duration': 0.5},
                ],
            })

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
        pass

    def get_info(self):
        device_info = super().get_info()
        device_info['station']['location'] = {
            "lat": Config.settings.get("latitude", None),
            "lon": Config.settings.get("longitude", None),
            "height": Config.settings.get("height", None)
        }

        return device_info 
    
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

    def tick(self):
        if not Config.runtime_settings['rtc_is_set'] and WifiUtil.radio.connected:
            WifiUtil.set_RTC()

        if not WifiUtil.radio.connected or not Config.runtime_settings['rtc_is_set'] or not all([Config.settings['longitude'], Config.settings['latitude'], Config.settings['height']]):
            logger.warning('DATA CANNOT BE TRANSMITTED, Not all configurations have been made')
            self.status_led.show_led({
                'repeat_mode': RepeatMode.FOREVER,
                    'elements': [
                        {'color': Color.BLUE, 'duration': 0.5},
                        {'color': Color.RED, 'duration': 0.5},
                ],
            })
        else:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.PERMANENT,
                'color': Color.GREEN_LOW,
            })
            cur_time = time.monotonic()
            if not self.last_measurement or cur_time - self.last_measurement >= Config.settings['measurement_interval']:
                self.last_measurement = cur_time
                data = self.get_json()
                sensor_community_data = self.get_json_list_sensor_community()

                self.save_data(data)

                if Config.settings['SEND_TO_SENSOR_COMMUNITY']:
                    self.save_data(sensor_community_data, tag='sensor_community')

        if not self.last_api_send or time.monotonic() - self.last_api_send > self.api_send_interval:
            if WifiUtil.radio.connected:
                self.last_api_send = time.monotonic()
                self.send_to_api()
