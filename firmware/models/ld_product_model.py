import time
import storage
import json
import os

from logger import logger
from wifi_client import WifiUtil
from config import Config
from sensors.sensor import Sensor

class LdProductModel:
    def __init__(self, ble_service, sensors: list[Sensor], battery_monitor):
        self.model_id = None
        """Product model."""
        
        self.polling_interval = 0.1
        """Main loop polling interval in seconds."""
        
        self.ble_on = False
        """Whether to advertise over BLE."""
        
        self.number_of_leds = 1
        """Number of LEDs on the device."""
        
        # State injection
        self.ble_service = ble_service
        self.sensors = sensors
        self.battery_monitor = battery_monitor
        self.status = bytearray([0, 0, 0, 0])

        # try to connect to wifi if not connected
        if not WifiUtil.radio.connected:
            WifiUtil.connect()
        # try to send status to API
        if WifiUtil.radio.connected:
            # prepare station info
            data = self.get_initial_info()
            api_url = Config.settings['DATAHUB_TEST_API_URL'] if Config.settings['TEST_MODE'] else Config.settings['DATAHUB_API_URL']
            logger.debug('Try to send initial info to datahub')
            resp = WifiUtil.send_json_to_api(
                data=data,
                api_url=api_url,
            )
            logger.debug(f'Datahub response: {resp.text}')


    def get_initial_info(self):
        """
        returns station info json with additional sensor inforation for datahub status
        """
        device_info = self.get_info()
        # add list of all connected sensors
        device_info['station']['sensor_list'] = [
            {
                "model_id": sensor.model_id,
                "dimension_list": sensor.measures_values
            } for sensor in self.sensors
        ]

        return device_info
    
    def get_info(self):
        """returns json with device info for api"""
        current_time = time.localtime()
        formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"

        device_info = {
            "station": {
                "time": formatted_time,
                "device": Config.settings['device_id'],
                "firmware": f"{Config.settings['FIRMWARE_MAJOR']}.{Config.settings['FIRMWARE_MINOR']}.{Config.settings['FIRMWARE_PATCH']}",
                "model": Config.settings['MODEL'],
                "apikey": Config.settings['api_key'],
                "source": 1,
            },
            "sensors": {}
        }

        return device_info
    
    def save_data(self, data: dict, tag = 'normal'):
        current_time = time.localtime()
        formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"
        storage.remount('/', False) 
        file_name = formatted_time.replace(':', '_').replace('.', '_')
        with open(f'{Config.runtime_settings["JSON_QUEUE"]}/{file_name}_{tag}.json', 'w') as f:
            json.dump(data, f)
        storage.remount('/', False)
    
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
    
    def send_to_api(self):
        for file_path in (f'{Config.runtime_settings["JSON_QUEUE"]}/{f}' for f in os.listdir(Config.runtime_settings["JSON_QUEUE"])):
            logger.debug(f'process file: {file_path}')
            with open(file_path, 'r') as f:
                data = json.load(f)

                if 'tmp_log.txt' in file_path:
                    # send status to Luftdaten APi
                    status_list = []
                    for line in f.readlines():
                        status_list.append(json.loads(line))

                    data = self.get_info()
                    data["status_list"] = status_list

                    response = WifiUtil.send_json_to_api(data, router='status')
                    logger.debug(f'{file_path=}')
                    logger.debug(f'API Response: {response.status_code}')
                    logger.debug(f'API Response: {response.text}')
                    if response.status_code == 200:  # Placeholder for successful sending check
                        storage.remount('/', False)
                        os.remove(file_path) 
                        storage.remount('/', True)
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
                        storage.remount('/', False)
                        os.remove(file_path) 
                        storage.remount('/', True)
                else:
                    # send to Luftdaten APi
                    response = WifiUtil.send_json_to_api(data)
                    logger.debug(f'{file_path=}')
                    logger.debug(f'API Response: {response.status_code}')
                    logger.debug(f'API Response: {response.text}')
                    if response.status_code in (200, 422):  # Placeholder for successful sending check
                        storage.remount('/', False)
                        os.remove(file_path) 
                        storage.remount('/', True)

    def read_all_sensors(self):
        for sensor in self.sensors:
            try:
                sensor.read()
            except:
                logger.error(f"Error reading sensor {sensor.model_id}, using previous values")

        
    def receive_command(self, command):
        """Process a command received on the BLE command characteristic."""
        pass
    
    def receive_button_press(self):
        """Process a button press event."""
        pass
    
    def tick(self):
        """Main loop tick. Called at regular intervals. 
        We do not need to check for commands here, these are passed separately."""
        pass
    
    def connection_update(self, connected):
        """Callback when BLE connection status changes.
        Will be called with False at the start of main loop."""
        pass
    
    # The following methods do not need to be overridden by subclasses.
    def update_ble_sensor_data(self):
        """Read out sensors values and update BLE characteristic."""
        vals_array = bytearray()
        for sensor in self.sensors:
            try:
                sensor.read()
            except:
                logger.error(f"Error reading sensor {sensor.model_id}, using previous values")
            vals_array.extend(sensor.get_current_values())
        self.ble_service.sensor_values_characteristic = vals_array
    
    def update_ble_battery_status(self):
        """Read battery status and update BLE characteristic."""
        if self.battery_monitor is not None:
            self.status[0] = 1 # Has battery status: Yes
            self.status[1] = round(self.battery_monitor.cell_soc()) # Battery percentage
            self.status[2] = round(self.battery_monitor.cell_voltage() * 10) # Battery voltage
        else:
            self.status[0] = 0 # Has battery status: No
            self.status[1] = 0
            self.status[2] = 0
        self.ble_service.device_status_characteristic = self.status

    def update_ble_error_status(self, error_code):
        """Update BLE characteristic with error status."""
        self.status[3] = error_code
        self.ble_service.device_status_characteristic = self.status
        (f"Error status updated: {error_code}")