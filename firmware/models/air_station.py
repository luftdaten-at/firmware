from models.ld_product_model import LdProductModel
from enums import LdProduct, Color, BleCommands
from wifi_client import WifiClient
import adafruit_ntp
import rtc
import time
import socketpool
import ipaddress

class AirStation(LdProductModel): 
    def __init__(self, ble_service, sensors, battery_monitor, status_led, wifi: WifiClient):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.polling_interval = 2  # TODO is this the best value?
        self.model_id = LdProduct.AIR_STATION
        self.ble_on = True 
        self.wifi = wifi
        self.new_ssid = None
        self.new_password = None
        self.longitude = None
        self.latitude = None
        self.hight = None
        self.time_is_configured = False
        self.clock = rtc.RTC()
        
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

    def get_info(self):
        # Get the current time from the RTC (real-time clock)
        current_time = self.clock.datetime

        # Format time as an ISO 8601 string (e.g., "2024-04-29T08:25:20.000Z")
        time_str = "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.000Z".format(
            current_time.tm_year,
            current_time.tm_mon,
            current_time.tm_mday,
            current_time.tm_hour,
            current_time.tm_min,
            current_time.tm_sec
        )

        # Return device info with the actual values
        return {
            "time": time_str,
            "device": self.model_id,  # Assuming the device name is "AirStation"
            "location": {
                "lat": self.latitude,
                "lon": self.longitude,
                "hight": self.hight
            }
        }
    
    def tick(self):
        #print('ping test')
        #self.wifi.wifilib.radio.ping(ipaddress.IPv4Address('216.40.34.37'))
        if not self.time_is_configured and self.wifi.connected():

            # Display the assigned IP address
            print(f"IP Address: {self.wifi.wifilib.radio.ipv4_address}")
            
            # Display the assigned gateway
            print(f"Gateway: {self.wifi.wifilib.radio.ipv4_gateway}")
            self.wifi.wifilib.radio.ipv4_dns = ipaddress.IPv4Address('8.8.8.8') 
            # Display the assigned DNS server
            print(f"DNS Server: {self.wifi.wifilib.radio.ipv4_dns}")

            print(self.wifi.wifilib.radio.ping(ipaddress.IPv4Address('8.8.8.8')))

            # get current time
            hostname = 'ntp.pool.org'
            pool = socketpool.SocketPool(self.wifi.wifilib.radio)
        
            # Try to resolve the IP address of the hostname
            print(f"Resolving {hostname}...")
            addr_info = pool.getaddrinfo(hostname, 80)  # Port 80 is used just for resolution
            print(f"Address info: {addr_info}")
            
            # Extract the IP address from the resolved info
            ip_address = addr_info[0][-1][0]
            print(f"Resolved IP address of {hostname}: {ip_address}")

            print(f'Connected? {self.wifi.connected()}')
            pool = socketpool.SocketPool(self.wifi.wifilib.radio)
            ntp = adafruit_ntp.NTP(pool, server="216.40.34.37", tz_offset=0, cache_seconds=3600)
            # NOTE: This changes the system time so make sure you aren't assuming that time
            # doesn't jump.
            rtc.RTC().datetime = ntp.datetime

            '''
            pool = socketpool.SocketPool(self.wifi.wifilib.radio)
            ntp = adafruit_ntp.NTP(pool, tz_offset=0)

            self.wifi.wifilib.radio.ipv4_dns = ipaddress.ip_address("8.8.8.8")
            print(f'NTP pool ip: {pool.getaddrinfo(ntp_server, 123)[0][-1]}')
            print(ntp.datetime)
            self.clock.datetime = ntp.datetime
            '''

            self.time_is_configured = True
        

        if not any([self.longitude, self.latitude, self.hight, self.time_is_configured]):
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

        sensor_values = {}
        for sensor in self.sensors:
            try:
                sensor.read()
            except:
                print(f"Error reading sensor {sensor.model_id}, using previous values")

            sensor_values[sensor.model_id] = sensor.current_values
        
        data = [self.get_info()] + [sensor_values]

        print(data)

    def connection_update(self, connected):
        pass
