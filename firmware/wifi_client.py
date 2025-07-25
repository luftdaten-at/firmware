import gc
from wifi import radio as wifi_radio
from config import Config
from socketpool import SocketPool
from ssl import create_default_context
from adafruit_requests import Session
from logger import logger

# New wifi methods
class WifiUtil:
    radio = wifi_radio
    pool: SocketPool = None 
    sensor_community_session: Session = None
    api_session: Session = None


    @staticmethod
    def connect() -> bool:
        if not Config.settings['SSID']:
            return False
        try:
            if Config.settings['PASSWORD']:
                logger.debug(f'Try to connect to: {Config.settings['SSID']} with standard encryption')
                wifi_radio.connect(Config.settings['SSID'], Config.settings['PASSWORD'])
                logger.debug('Connection established to Wifi', Config.settings['SSID'])
            elif all([
                Config.settings['EAP_IDENTITY'],
                Config.settings['EAP_USERNAME'],
                Config.settings['EAP_PASSWORD'],
            ]):
                logger.debug(f'Try to connect to: {Config.settings['SSID']} with enterprise encryption')
                wifi_radio.connect(
                    Config.settings['SSID'],
                    eap_identity = Config.settings['EAP_IDENTITY'],
                    eap_username = Config.settings['EAP_USERNAME'],
                    eap_password = Config.settings['EAP_PASSWORD'],
                )
            else:
                logger.debug(f'Try to connect to: {Config.settings['SSID']} without encryption')
                wifi_radio.connect(Config.settings['SSID'])

            # init pool
            WifiUtil.pool = SocketPool(WifiUtil.radio)

            # init sessions
            api_context = create_default_context()
            with open(Config.runtime_settings['CERTIFICATE_PATH'], 'r') as f:
                api_context.load_verify_locations(cadata=f.read())
            WifiUtil.api_session = Session(WifiUtil.pool, api_context)

            sensor_community_context = create_default_context()
            with open(Config.runtime_settings['SENSOR_COMMUNITY_CERTIFICATE_PATH'], 'r') as f:
                sensor_community_context.load_verify_locations(cadata=f.read())
            WifiUtil.sensor_community_session = Session(WifiUtil.pool, sensor_community_context)

        except ConnectionError:
            logger.error("Failed to connect to WiFi with provided credentials")
            return False 

        WifiUtil.set_RTC()

        return True
    

    @staticmethod
    def get(url: str, binary = False):
        try:
            response = WifiUtil.api_session.request(
                method='GET',
                url=url
            )

            if response.status_code != 200:
                logger.error(f'GET failed, url: {url}, status code: {response.status_code}, text: {response.text}')

                return False

            if binary:
                return response.content

            return response.text
        except Exception as e:
            logger.error(f'GET faild: {e}')
            return False


    @staticmethod
    def set_RTC():
        import rtc
        from adafruit_ntp import NTP

        try:
            logger.debug('Trying to set RTC via NTP...')
            ntp = NTP(WifiUtil.pool, tz_offset=0, cache_seconds=3600)
            rtc.RTC().datetime = ntp.datetime
            Config.runtime_settings['rtc_is_set'] = True  # Assuming rtc_is_set is a setting in your Config

            logger.debug('RTC successfully configured')

            # set rtc module
            if rtc_module := Config.runtime_settings.get('rtc_module', None):
                rtc_module.datetime = rtc.RTC().datetime

        except Exception as e:
            logger.error(f'Failed to set RTC via NTP: {e}')
    

    @staticmethod
    def send_json_to_api(data, api_url: str = None, router: str = 'data/'):
        if not api_url:
            api_url = Config.runtime_settings['API_URL']
        gc.collect()
        response = WifiUtil.api_session.request(
            method='POST',
            url=f"{api_url}/{router}",
            json=data
        )
        # send to additional APIs
        # TODO: Handle response
        if Config.settings.get('API_URLS', None):
            for api_url in Config.runtime_settings['API_URLS']:
                WifiUtil.api_session.request(
                    method='POST',
                    url=f"{api_url}/{router}",
                    json=data
                )
        return response
 

    @staticmethod
    def send_json_to_sensor_community(header, data):
        gc.collect()
        response = WifiUtil.sensor_community_session.request(
            method='POST',
            url=Config.runtime_settings['SENSOR_COMMUNITY_API'],
            json=data,
            headers=header 
        )
        return response


class ConnectionFailure:
    SSID_NOT_FOUND = 1
    PASSWORD_INCORRECT = 2
    PASSWORD_LENGTH = 3
    INVALID_BSSID = 4
    OTHER = 5
