import wifi # type: ignore
from config import Config
import gc

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
            pool = SocketPool(wifi.radio)
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


        pool = SocketPool(wifi.radio)
        context = create_default_context()

        with open(Config.CERTIFICATE_PATH, 'r') as f:
            context.load_verify_locations(cadata=f.read())


        print(locals())
        gc.collect()
        print(f'Free mem before API: {gc.mem_free()}')
        del locals()['buf']
        gc.collect()
        print(locals())
        print(f'Free mem before API: {gc.mem_free()}')


        https = Session(pool, context)
        return https.post(Config.API_URL, json=data)

class ConnectionFailure:
    SSID_NOT_FOUND = 1
    PASSWORD_INCORRECT = 2
    PASSWORD_LENGTH = 3
    INVALID_BSSID = 4
    OTHER = 5