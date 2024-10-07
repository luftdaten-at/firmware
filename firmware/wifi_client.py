#import wifi # type: ignore
from wifi import radio as wifi_radio
from config import Config
import gc

# New wifi methods
class WifiUtil:
    radio = wifi_radio
    @staticmethod
    def connect() -> bool:
        if not Config.SSID or not Config.PASSWORD:
            return False
        try:
            print('Connecting to Wifi...')
            print(Config.SSID, Config.PASSWORD)
            wifi_radio.connect(Config.SSID, Config.PASSWORD)
            print('Connection established')

        except ConnectionError:
            print("Failed to connect to WiFi with provided credentials")
            return False 

        WifiUtil.set_RTC()

        return True

    @staticmethod
    def set_RTC():
        from adafruit_ntp import NTP
        import rtc
        from socketpool import SocketPool

        try:
            print('Trying to set RTC via NTP...')
            pool = SocketPool(wifi_radio)
            ntp = NTP(pool, tz_offset=0, cache_seconds=3600)
            rtc.RTC().datetime = ntp.datetime
            Config.rtc_is_set = True
            print('RTC sucessfully configured')

        except Exception as e:
            print(e)
    
    @staticmethod
    def send_json_to_api(data):
        from socketpool import SocketPool
        from ssl import create_default_context
        from adafruit_requests import Session


        pool = SocketPool(wifi_radio)
        context = create_default_context()

        '''
        with open(Config.CERTIFICATE_PATH, 'r') as f:
            context.load_verify_locations(cadata=f.read())
        '''
        gc.collect()
        print(f'Mem requests: {gc.mem_free()}')

        https = Session(pool, context)
        print(f'Request API: {Config.API_URL}')
        return https.request(
            method='post',
            url=Config.API_URL,
            json=data
        )

class ConnectionFailure:
    SSID_NOT_FOUND = 1
    PASSWORD_INCORRECT = 2
    PASSWORD_LENGTH = 3
    INVALID_BSSID = 4
    OTHER = 5