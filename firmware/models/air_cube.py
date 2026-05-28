import time
import board
import neopixel
from os import listdir, remove, uname
from storage import remount
from json import dump, load, loads, dumps

from led_controller import LedController
from wifi_client import WifiUtil
from led_controller import RepeatMode
from models.ld_product_model import API_JSON_DEVICE_KEY, LdProductModel
from logger import logger
from config import Config
from enums import Color, LdProduct, Dimension, Quality, BleCommands
from sensors.virtual_sensor import VirtualSensor
from sd_logger import append_measurement_jsonl


class AirCube(LdProductModel): 
    NEOPIXEL_PIN = board.IO8
    NEOPIXLE_N = 5
    SCL = None
    SDA = None
    BUTTON_PIN = None

    def __init__(self, ble_service, sensors, battery_monitor):
        super().__init__(ble_service, sensors, battery_monitor)
        self.polling_interval = 0.01
        self.model_id = LdProduct.AIR_CUBE
        self.ble_on = False
        self.number_of_leds = 5
        self.last_measurement = None

        self.device_id = Config.settings['device_id'] 
        self.api_key = Config.settings['api_key']

        # init status led
        self.status_led = LedController(
            status_led=neopixel.NeoPixel(
                pin=AirCube.NEOPIXEL_PIN,
                n=AirCube.NEOPIXLE_N
            ),
            n=AirCube.NEOPIXLE_N
        )
        
        calculated_dimension_set = set([Dimension.ADJUSTED_TEMP_CUBE])
        required_sensor_id_set = set(
            sensor_id 
            for calculated_dimension in calculated_dimension_set
                for sensor_id in Dimension.get_required_sensors(calculated_dimension)
        )

        # gather required sensors for virtual sensor
        required_sensor_dict = {}
        for sensor in sensors:
            if sensor.model_id in required_sensor_id_set:
                required_sensor_dict[sensor.model_id] = sensor

        vsen = VirtualSensor(
            required_sensor_dict=required_sensor_dict, # required sensors to calculate dimensions
            calculated_dimension_set=calculated_dimension_set # dimensions to be calculated
        )
        
        # add virtual sensor
        sensors.append(vsen)
        
    def receive_command(self, command):
        if(len(command) == 0):
            return
        cmd = command[0]

        if cmd == BleCommands.SD_LOG_EXPORT:
            from sd_ble_export import export_read_value, handle_export_command

            act = command[1] if len(command) >= 2 else 255
            handle_export_command(act, Config.is_wifiless())
            self.ble_service.sd_log_export_characteristic = export_read_value()
            return

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

        if cmd == BleCommands.SET_CUBE_MQTT_CONFIGURATION:
            from mqtt_ble_tlv import decode_mqtt_settings_tlv
            tail = bytes(command[1:]) if len(command) > 1 else b""
            if decode_mqtt_settings_tlv(tail):
                from mqtt_ha import MqttHa
                MqttHa.notify_settings_changed_from_ble()
            self.status_led.show_led({
                'repeat_mode': RepeatMode.TIMES,
                'repeat_times': 1,
                'elements': [
                    {'color': Color.BLUE, 'duration': 0.15},
                ],
            })
    
    def receive_button_press(self):
        if Config.is_wifiless():
            self._handle_wifiless_button_upload()
            return
        self.ble_on = not self.ble_on
        if self.ble_on:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.PERMANENT,
                'color': Color.BLUE,
            })
        else:
            self.status_led.turn_off_led()
            
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
        if Config.is_wifiless():
            if connected:
                self.status_led.show_led({
                    'repeat_mode': RepeatMode.FOREVER,
                    'elements': [
                        {'color': Color.GREEN, 'duration': 0.5},
                        {'color': Color.OFF, 'duration': 0.5},
                    ],
                })
            return
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

    def get_info(self):
        device_info = super().get_info()
        device_info[API_JSON_DEVICE_KEY]['battery'] = {
            "voltage": self.battery_monitor.cell_voltage() if self.battery_monitor else None,
            "percentage": self.battery_monitor.cell_soc() if self.battery_monitor else None,
        }

        return device_info

    def _send_status_if_due(self):
        if not WifiUtil.radio.connected:
            return
        if (
            not self.last_api_send
            or time.monotonic() - self.last_api_send > self.api_send_interval
        ):
            self.last_api_send = time.monotonic()
            self.send_to_api()

    def _collect_sensor_averages(self):
        sensor_values = {
            Dimension.TEMPERATURE: [],
            Dimension.CO2: [],
            Dimension.PM2_5: [],
            Dimension.TVOC: [],
        }
        for sensor in self.sensors:
            for dimension in sensor.measures_values:
                if sensor.value_quality[dimension] == Quality.HIGH:
                    if dimension in sensor_values:
                        if sensor.current_values[dimension] is not None:
                            sensor_values[dimension].append(sensor.current_values[dimension])
        for sensor in self.sensors:
            for dimension in sensor.measures_values:
                if dimension in sensor_values:
                    if len(sensor_values[dimension]) == 0:
                        if sensor.current_values[dimension] is not None:
                            sensor_values[dimension].append(sensor.current_values[dimension])
        return sensor_values

    def _update_sensor_value_leds(self):
        sensor_values = self._collect_sensor_averages()
        if len(sensor_values[Dimension.TEMPERATURE]) > 0:
            self._updateLed(
                1,
                sum(sensor_values[Dimension.TEMPERATURE]) / len(sensor_values[Dimension.TEMPERATURE]),
                [18, 24],
                [Color.BLUE, Color.GREEN, Color.RED],
            )
        if len(sensor_values[Dimension.PM2_5]) > 0:
            self._updateLed(
                2,
                sum(sensor_values[Dimension.PM2_5]) / len(sensor_values[Dimension.PM2_5]),
                [5, 15],
                [Color.GREEN, Color.YELLOW, Color.RED],
            )
        if len(sensor_values[Dimension.TVOC]) > 0:
            self._updateLed(
                3,
                sum(sensor_values[Dimension.TVOC]) / len(sensor_values[Dimension.TVOC]),
                [220, 1430],
                [Color.GREEN, Color.YELLOW, Color.RED],
            )
        if len(sensor_values[Dimension.CO2]) > 0:
            self._updateLed(
                4,
                sum(sensor_values[Dimension.CO2]) / len(sensor_values[Dimension.CO2]),
                [800, 1000, 1400],
                [Color.GREEN, Color.YELLOW, Color.ORANGE, Color.RED],
            )

    def _show_wifiless_sd_status_led(self, ok):
        if ok and Config.runtime_settings.get("rtc_is_set"):
            self.status_led.show_led({
                'repeat_mode': RepeatMode.PERMANENT,
                'color': Color.GREEN_LOW,
            }, led_id=0)
        elif ok:
            logger.warning('Wifiless: SD write ok but RTC not set from DS3231; timestamps may be wrong')
            self.status_led.show_led({
                'repeat_mode': RepeatMode.PERMANENT,
                'color': Color.YELLOW,
            }, led_id=0)
        else:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.FOREVER,
                'elements': [
                    {'color': Color.RED, 'duration': 0.5},
                    {'color': Color.YELLOW, 'duration': 0.5},
                ],
            }, led_id=0)

    def _tick_wifiless(self):
        cur_time = time.monotonic()
        if (
            self.last_measurement is None
            or cur_time - self.last_measurement >= Config.settings['measurement_interval']
        ):
            self.last_measurement = cur_time
            data = self.get_json()
            ok = append_measurement_jsonl(data)
            self._show_wifiless_sd_status_led(ok)
            self.update_ble_sensor_data()
            self._update_sensor_value_leds()

    def tick(self):
        if Config.is_wifiless():
            self._tick_wifiless()
            self._send_status_if_due()
            return

        # Measure every measurement_interval (allow this to be settable)
        if self.last_measurement is None or time.monotonic() - self.last_measurement >= Config.settings['measurement_interval']:
            # set last measurement to now
            self.last_measurement = time.monotonic()

            # send to API
            data = self.get_json()
            self.save_data(data=data)
            if WifiUtil.radio.connected:
                self.send_to_api()
                self.last_api_send = time.monotonic()
                from mqtt_ha import MqttHa
                MqttHa.publish_measurement_if_enabled(data)

            # This reads sensors & updates BLE - we don't mind updating BLE even if it is off
            self.update_ble_sensor_data()
            self._update_sensor_value_leds()

        self._send_status_if_due()
