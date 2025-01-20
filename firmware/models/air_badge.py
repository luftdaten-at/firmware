from firmware.models.air_around import LdProductModel 
from enums import LdProduct, BleCommands
from logger import logger

class AirBadge(LdProductModel):
    model_id = LdProduct.AIR_BADGE

    def __init__(self, ble_service, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
    
    def receive_command(self, command):
        if not command:
            return
        cmd = command[0]
        if cmd == BleCommands.READ_SENSOR_DATA or cmd == BleCommands.READ_SENSOR_DATA_AND_BATTERY_STATUS:
            self.update_ble_sensor_data()
        if cmd == BleCommands.READ_SENSOR_DATA_AND_BATTERY_STATUS:
            self.update_ble_battery_status()
            logger.debug("Battery status updated")
