import time
import storage
import json
import os
import gc

from logger import logger
from wifi_client import WifiUtil
from config import Config
from sensors.sensor import Sensor

class LdProductModel:
    def __init__(self, ble_service, sensors: list[Sensor], battery_monitor):
        self.model_id = None
        self.measurements = {}
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
        self.last_api_send = None
        self.api_send_interval = 30 # 30 seconds

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
                "dimension_list": sensor.measures_values,
                "serial_number": sensor.get_serial_number()
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
                "test_mode": Config.settings['TEST_MODE'],
                "calibration_mode": Config.settings['CALIBRATION_MODE']
            },
            "sensors": {}
        }

        return device_info
    
    def save_data(self, data: dict, tag = 'normal'):
        self.measurements[tag] = self.measurements.get(tag, []) + [data]
        '''
        storage.remount('/', False)
        current_time = time.localtime()
        formatted_time = f"{current_time.tm_year:04}-{current_time.tm_mon:02}-{current_time.tm_mday:02}T{current_time.tm_hour:02}:{current_time.tm_min:02}:{current_time.tm_sec:02}.000Z"
        file_name = formatted_time.replace(':', '_').replace('.', '_')
        with open(f'{Config.runtime_settings["JSON_QUEUE"]}/{file_name}_{tag}.json', 'w') as f:
            json.dump(data, f)
        storage.remount('/', False)
        '''
    
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
        # contains all measurements that failed to transmitt
        new_measurements = {}
        for tag, data_list in self.measurements.items():
            if tag == 'sensor_community':
                for data in data_list:
                    transmission_failed = False 
                    for header, d in data:
                        response = WifiUtil.send_json_to_sensor_community(header=header, data=d)
                        if response.status_code != 200:
                            transmission_failed = True
                            break
                    if transmission_failed:
                        new_measurements[tag] = new_measurements.get(tag, []) + [data]
            elif tag == 'normal':
                for data in data_list:
                    response = WifiUtil.send_json_to_api(data)
                    if response.status_code not in (200, 422):
                        new_measurements[tag] = new_measurements.get(tag, []) + [data]
                
        self.measurements = new_measurements

        data = self.get_info()
        data["status_list"] = logger.log_list
        api_url = Config.settings['DATAHUB_TEST_API_URL'] if Config.settings['TEST_MODE'] else Config.settings['DATAHUB_API_URL']
        response = WifiUtil.send_json_to_api(
            data=data, 
            api_url=api_url,
            router='status/'
        )
        if response.status_code == 200:
            logger.log_list.clear()
            # updaet flags if they exist
            print(response.json())


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