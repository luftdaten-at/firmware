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
        self.longitude = None
        self.latitude = None
        self.hight = None
        
    def receive_command(self, command):
        if len(command) == 0:
            return

        cmd, *data = command
        if cmd == BleCommands.SET_WIFI_SSID:
            self.new_ssid = bytearray(data).decode('utf-8')

        if cmd == BleCommands.SET_WIFI_PASSWORD:
            self.new_password = bytearray(data).decode('utf-8')

        if cmd == BleCommands.SET_LONGITUDE:
            self.longitude = bytearray(data).decode('utf-8')

        if cmd == BleCommands.SET_LATITUDE:
            self.latitude = bytearray(data).decode('utf-8')
        
        if cmd == BleCommands.SET_HIGHT:
            self.hight = bytearray(data).decode('utf-8')

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
        if not any(self.longitude, self.latitude, self.hight):
            print('DATA CANNOT BE TRANSMITTED')
            print('Not all configurations have been made')
            return 
        '''
        [
        [
            {
                "time": "2024-04-29T08:25:20.766Z",
                "device": "string",
                "location": {
                    "lat": 0,
                    "lon": 0,
                    "hight": 0
            },
            {
                "sen1" : {"dim": "val", "dim2": "val2"},
                "sen2" : {"dim": "val", "dim2": "val2"}
            }
        ]
        ] 
        '''
        for sensor in self.sensors:
            try:
                sensor.read()
            except:
                print(f"Error reading sensor {sensor.model_id}, using previous values")
            print(sensor.current_values)

    def connection_update(self, connected):
        pass
