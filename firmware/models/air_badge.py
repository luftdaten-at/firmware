import neopixel
import board

from led_controller import LedController
from firmware.models.air_around import LdProductModel 
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
