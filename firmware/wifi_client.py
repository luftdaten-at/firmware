from wifi import radio as wifi_radio
from config import Config
import gc
from socketpool import SocketPool
from ssl import create_default_context
from adafruit_requests import Session

# New wifi methods
class WifiUtil:
    radio = wifi_radio
    pool = SocketPool(radio)

    @staticmethod
    def connect() -> bool:
        if not Config.settings['SSID'] or not Config.settings['PASSWORD']:
            return False
        try:
            print('Connecting to Wifi...')
            print(Config.settings['SSID'], Config.settings['PASSWORD'])
            wifi_radio.connect(Config.settings['SSID'], Config.settings['PASSWORD'])
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

        try:
            print('Trying to set RTC via NTP...')
            ntp = NTP(WifiUtil.pool, tz_offset=0, cache_seconds=3600)
            rtc.RTC().datetime = ntp.datetime
            Config.runtime_settings['rtc_is_set'] = True  # Assuming rtc_is_set is a setting in your Config
            print('RTC successfully configured')

        except Exception as e:
            print(e)
    
    @staticmethod
    def new_session():
        return Session(WifiUtil.pool)
    
    @staticmethod
    def send_json_to_api(data):
        context = create_default_context()

        with open(Config.runtime_settings['CERTIFICATE_PATH'], 'r') as f:
            context.load_verify_locations(cadata=f.read())

        gc.collect()
        print(f'Mem requests: {gc.mem_free()}')

        https = Session(WifiUtil.pool, context)
        print(f'Request API: {Config.runtime_settings["API_URL"]}')
        response = https.request(
            method='POST',
            url=Config.runtime_settings['API_URL'],
            json=data
        )
        return response

class ConnectionFailure:
    SSID_NOT_FOUND = 1
    PASSWORD_INCORRECT = 2
    PASSWORD_LENGTH = 3
    INVALID_BSSID = 4
    OTHER = 5
