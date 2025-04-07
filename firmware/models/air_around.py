import board
import neopixel
import time

from led_controller import LedController
from models.ld_product_model import LdProductModel
from led_controller import RepeatMode
from enums import Color, BleCommands
from logger import logger
from config import Config
from wifi_client import WifiUtil

class AirAround(LdProductModel): 
    NEOPIXEL_PIN = board.IO8
    NEOPIXLE_N = 1
    SCL = None
    SDA = None
    BUTTON_PIN = None

    def __init__(self, model, ble_service, sensors, battery_monitor):
        super().__init__(ble_service, sensors, battery_monitor)
        self.polling_interval = 0.01
        self.model_id = model
        self.ble_on = True

        self.last_measurement = None

        # init status led
        self.status_led = LedController(
            status_led=neopixel.NeoPixel(
                pin=AirAround.NEOPIXEL_PIN,
                n=AirAround.NEOPIXLE_N
            ),
            n=AirAround.NEOPIXLE_N
        )
        
    def receive_command(self, command):
        if not command:
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
        pass
    
    def tick(self):
        if self.last_measurement is None or time.monotonic() - self.last_measurement >= Config.settings['measurement_interval']:
            # set last measurement to now
            self.last_measurement = time.monotonic()

            # send to API
            data = self.get_json()
            self.save_data(data=data)
            if WifiUtil.radio.connected:
                self.send_to_api()

    def get_info(self):
        device_info = super().get_info()
        device_info['station']['battery'] = {
            # cell_voltage() -> returns mili volt / 1000 to convert to volts
            "voltage": self.battery_monitor.cell_voltage() / 1000 if self.battery_monitor else None,
            "percentage": self.battery_monitor.cell_soc() if self.battery_monitor else None,
        }

        return device_info

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
