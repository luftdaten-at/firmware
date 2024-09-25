import wifi # type: ignore
import ssl # type: ignore
import socketpool # type: ignore
import adafruit_requests # type: ignore
import json
import rtc
import socketpool
import adafruit_ntp
from config import Config
from util import Util

# New wifi methods
class WifiUtil:
    @staticmethod
    def connect(wifi_ssid: str, wifi_password: str) -> bool:
        try:
            print('Connecting to Wifi...')
            wifi.radio.connect(wifi_ssid, wifi_password)
            print('Connection established')
            print('write credentials to settings.toml')
            Util.write_to_settings({
                'SSID': wifi_ssid,
                'PASSWORD': wifi_password
            })
        except ConnectionError:
            print("Failed to connect to WiFi with provided credentials")
            return False 
        return True
    @staticmethod
    def set_RTC():
        try:
            print('Trying to set RTC via NTP...')
            pool = socketpool.SocketPool(wifi.radio)
            ntp = adafruit_ntp.NTP(pool, tz_offset=0, cache_seconds=3600)
            rtc.RTC().datetime = ntp.datetime
            Config.rtc_is_set = True

        except Exception as e:
            print(e)

class ConnectionFailure:
    SSID_NOT_FOUND = 1
    PASSWORD_INCORRECT = 2
    PASSWORD_LENGTH = 3
    INVALID_BSSID = 4
    OTHER = 5