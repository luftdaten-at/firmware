from models.ld_product_model import LdProductModel
from enums import LdProduct, Color, BleCommands
from wifi_client import WifiClient

class AirStation(LdProductModel): 
    def __init__(self, ble_service, sensors, battery_monitor, status_led, wifi: WifiClient):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.polling_interval = 0.1  # TODO is this the best value?
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = True 
        self.wifi = wifi
        self.new_ssid = None
        self.new_password = None
        
    def receive_command(self, command):
        if len(command) == 0:
            return

        cmd, *data = command
        if cmd == BleCommands.SET_WIFI_SSID:
            self.new_ssid = bytearray(data).decode('utf-8')
            print(self.new_ssid)

        if cmd == BleCommands.SET_WIFI_PASSWORD:
            self.new_password = bytearray(data).decode('utf-8')
            print(self.new_password)

        if self.new_ssid and self.new_password:
            self.wifi.connect(self.new_ssid, self.new_password)
            self.new_ssid = None
            self.new_password = None

    def receive_button_press(self):
        self.ble_on = not self.ble_on
        # Possibly change polling interval?
        if self.ble_on:
            self.status_led.fill(Color.BLUE)
        else:
            self.status_led.fill(Color.OFF)
        self.status_led.show()
    
    def tick(self):
        pass
        # We measure in fixed intervals, do this here
        
    def connection_update(self, connected):
        pass