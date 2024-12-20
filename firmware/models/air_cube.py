import time
from os import listdir, remove, uname
from storage import remount
from json import dump

from led_controller import RepeatMode
from models.ld_product_model import LdProductModel
from logger import logger
from config import Config
from enums import Color, LdProduct, Dimension, Quality, BleCommands


class AirCube(LdProductModel): 
    def __init__(self, ble_service, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.polling_interval = 0.01
        self.model_id = LdProduct.AIR_CUBE
        self.ble_on = False
        self.number_of_leds = 5
        self.last_measurement = None
        
    def receive_command(self, command):
        if(len(command) == 0):
            return
        cmd = command[0]
        if cmd == BleCommands.READ_SENSOR_DATA or cmd == BleCommands.READ_SENSOR_DATA_AND_BATTERY_STATUS:
            self.update_ble_sensor_data()
            logger.debug("Sensor values updated")
            self.status_led.show_led({
                'repeat_mode': RepeatMode.TIMES,
                'repeat_times': 1,
                'elements': [
                    {'color': Color.BLUE, 'duration': 0.1},
                ],
            })
        if cmd == BleCommands.READ_SENSOR_DATA_AND_BATTERY_STATUS:
            self.update_ble_battery_status()
            logger.debug("Battery status updated")
    
    def receive_button_press(self):
        self.ble_on = not self.ble_on
        if self.ble_on:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.PERMANENT,
                'color': Color.BLUE,
            })
        else:
            self.status_led.turn_off_led()
    
    def tick(self):
        # Measure every 5 seconds (allow this to be settable)
        if self.last_measurement is None or time.monotonic() - self.last_measurement > 5:
            # This reads sensors & updates BLE - we don't mind updating BLE even if it is off
            self.update_ble_sensor_data()
            self.last_measurement = time.monotonic()
            # Update LEDs
            sensor_values = {
                Dimension.TEMPERATURE: [],
                Dimension.CO2: [],
                Dimension.PM2_5: [],
                Dimension.TVOC: [],
                # TODO AQI should depend on more than just total VOC
            }
            # Add sensor data - note there may be no data for some dimensions
            # Add HIGH quality data
            for sensor in self.sensors:
                for dimension in sensor.measures_values:
                    if sensor.value_quality[dimension] == Quality.HIGH:
                        if dimension in sensor_values.keys():
                            if sensor.current_values[dimension] is not None:
                                sensor_values[dimension].append(sensor.current_values[dimension])
            # If no HIGH quality data, add LOW quality data
            for sensor in self.sensors:
                for dimension in sensor.measures_values:
                    if dimension in sensor_values.keys():
                        if len(sensor_values[dimension]) == 0:
                            if sensor.current_values[dimension] is not None:
                                sensor_values[dimension].append(sensor.current_values[dimension])            
            # Update LEDs
            if len(sensor_values[Dimension.TEMPERATURE]) > 0:
                self._updateLed(1, 
                                sum(sensor_values[Dimension.TEMPERATURE]) / len(sensor_values[Dimension.TEMPERATURE]), 
                                [18, 24], 
                                [Color.BLUE, Color.GREEN, Color.RED],
                                )
            if len(sensor_values[Dimension.PM2_5]) > 0:
                self._updateLed(2, 
                                sum(sensor_values[Dimension.PM2_5]) / len(sensor_values[Dimension.PM2_5]), 
                                [5, 15],
                                [Color.GREEN, Color.YELLOW, Color.RED],
                                )
            if len(sensor_values[Dimension.TVOC]) > 0:
                self._updateLed(3, 
                                sum(sensor_values[Dimension.TVOC]) / len(sensor_values[Dimension.TVOC]), 
                                [220, 1430],
                                [Color.GREEN, Color.YELLOW, Color.RED],
                                )
            if len(sensor_values[Dimension.CO2]) > 0:
                self._updateLed(4,
                                sum(sensor_values[Dimension.CO2]) / len(sensor_values[Dimension.CO2]), 
                                [800, 1000, 1400], 
                                [Color.GREEN, Color.YELLOW, Color.ORANGE, Color.RED],
                                )
            
    def _updateLed(self, led_id, value, color_cutoffs, colors):
        color = colors[0]
        for i in range(len(color_cutoffs)):
            if value > color_cutoffs[i]:
                color = colors[i + 1]
        self.status_led.show_led({
            'repeat_mode': RepeatMode.PERMANENT,
            'color': color,
        }, led_id)

    def connection_update(self, connected):
        if connected:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.TIMES,
                'repeat_times': 1,
                'elements': [
                    {'color': Color.GREEN, 'duration': 1},
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
