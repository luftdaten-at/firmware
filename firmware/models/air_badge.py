import neopixel
import board
import time

from wifi_client import WifiUtil
from config import Config
from led_controller import LedController
from models.ld_product_model import LdProductModel
from enums import LdProduct, BleCommands
from logger import logger


class AirBadge(LdProductModel):
    model_id = LdProduct.AIR_BADGE
    NEOPIXEL_PIN = board.IO8
    NEOPIXLE_N = 1
    SCL = None
    SDA = None
    BUTTON_PIN = None

    def __init__(self, ble_service, sensors, battery_monitor):
        super().__init__(ble_service, sensors, battery_monitor)

        self.last_measurement = None

        # init status led
        self.status_led = LedController(
            status_led=neopixel.NeoPixel(
                pin=AirBadge.NEOPIXEL_PIN,
                n=AirBadge.NEOPIXLE_N
            ),
            n=AirBadge.NEOPIXLE_N
        )
    
    def receive_command(self, command):
        if not command:
            return
        cmd = command[0]
        if cmd == BleCommands.READ_SENSOR_DATA or cmd == BleCommands.READ_SENSOR_DATA_AND_BATTERY_STATUS:
            self.update_ble_sensor_data()
        if cmd == BleCommands.READ_SENSOR_DATA_AND_BATTERY_STATUS:
            self.update_ble_battery_status()
            logger.debug("Battery status updated")
    
    def get_info(self):
        device_info = super().get_info()
        device_info['station']['battery'] = {
            # cell_voltage() -> returns mili volt / 1000 to convert to volts
            "voltage": self.battery_monitor.cell_voltage() / 1000 if self.battery_monitor else None,
            "percentage": self.battery_monitor.cell_soc() if self.battery_monitor else None,
        }

        return device_info

    def tick(self):
        if self.last_measurement is None or time.monotonic() - self.last_measurement >= Config.settings['measurement_interval']:
            # set last measurement to now
            self.last_measurement = time.monotonic()

            # send to API
            data = self.get_json()
            self.save_data(data=data)
            if WifiUtil.radio.connected:
                self.send_to_api()