import wifi # type: ignore
import socketpool # type: ignore
import rtc
import socketpool
import adafruit_ntp
from config import Config

# New wifi methods
class WifiUtil:
    radio = wifi.radio
    @staticmethod
    def connect() -> bool:
        try:
            print('Connecting to Wifi...')
            print(Config.SSID, Config.PASSWORD)
            wifi.radio.connect(Config.SSID, Config.PASSWORD)
            print('Connection established')

            WifiUtil.set_RTC()

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
            print('RTC sucessfully configured')

        except Exception as e:
            print(e)

class ConnectionFailure:
    SSID_NOT_FOUND = 1
    PASSWORD_INCORRECT = 2
    PASSWORD_LENGTH = 3
    INVALID_BSSID = 4
    OTHER = 5