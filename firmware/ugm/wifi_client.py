import gc
from wifi import radio as wifi_radio
from config import Config
from socketpool import SocketPool
from ssl import create_default_context
from adafruit_requests import Session
from logger import logger

_FALLBACK_SSID = "luftdaten.at"
_FALLBACK_PASSWORD = "clientpassword"

# New wifi methods
class WifiUtil:
    radio = wifi_radio
    pool: SocketPool = None 
    sensor_community_session: Session = None
    api_session: Session = None

    @staticmethod
    def _normalize_ssid(raw):
        if raw is None:
            return ""
        if isinstance(raw, bytes):
            try:
                return raw.decode("utf-8").strip()
            except UnicodeError:
                return ""
        return str(raw).strip()

    @staticmethod
    def _ssid_visible(ssid):
        target = WifiUtil._normalize_ssid(ssid)
        if not target:
            return False
        if not hasattr(wifi_radio, "start_scanning_networks"):
            return True
        try:
            for network in wifi_radio.start_scanning_networks():
                if WifiUtil._normalize_ssid(network.ssid) == target:
                    return True
        except Exception as e:
            logger.debug(
                "WiFi scan failed (%s: %s); will try configured SSID anyway"
                % (type(e).__name__, e)
            )
            return True
        finally:
            try:
                wifi_radio.stop_scanning_networks()
            except Exception:
                pass
        return False

    @staticmethod
    def _fallback_credentials():
        return (_FALLBACK_SSID, _FALLBACK_PASSWORD, None)

    @staticmethod
    def _resolve_connect_credentials():
        primary = WifiUtil._normalize_ssid(Config.settings.get("SSID"))
        if not primary:
            logger.info(
                "WiFi: no SSID configured, trying fallback %s" % _FALLBACK_SSID
            )
            return WifiUtil._fallback_credentials()

        if not WifiUtil._ssid_visible(primary):
            if primary != _FALLBACK_SSID:
                logger.info(
                    "WiFi: %s not found in scan, trying fallback %s"
                    % (primary, _FALLBACK_SSID)
                )
            return WifiUtil._fallback_credentials()

        password = Config.settings.get("PASSWORD")
        if password:
            return (primary, password, None)
        if all([
            Config.settings.get("EAP_IDENTITY"),
            Config.settings.get("EAP_USERNAME"),
            Config.settings.get("EAP_PASSWORD"),
        ]):
            return (
                primary,
                None,
                (
                    Config.settings["EAP_IDENTITY"],
                    Config.settings["EAP_USERNAME"],
                    Config.settings["EAP_PASSWORD"],
                ),
            )
        return (primary, None, None)

    @staticmethod
    def _connect_radio(ssid, password=None, eap=None):
        if eap:
            wifi_radio.connect(
                ssid,
                eap_identity=eap[0],
                eap_username=eap[1],
                eap_password=eap[2],
            )
        elif password:
            wifi_radio.connect(ssid, password)
        else:
            wifi_radio.connect(ssid)

    @staticmethod
    def _init_sessions():
        WifiUtil.pool = SocketPool(WifiUtil.radio)

        api_context = create_default_context()
        with open(Config.runtime_settings["CERTIFICATE_PATH"], "r") as f:
            api_context.load_verify_locations(cadata=f.read())
        WifiUtil.api_session = Session(WifiUtil.pool, api_context)

        sensor_community_context = create_default_context()
        with open(Config.runtime_settings["SENSOR_COMMUNITY_CERTIFICATE_PATH"], "r") as f:
            sensor_community_context.load_verify_locations(cadata=f.read())
        WifiUtil.sensor_community_session = Session(WifiUtil.pool, sensor_community_context)

    @staticmethod
    def connect() -> bool:
        creds = WifiUtil._resolve_connect_credentials()
        if not creds:
            return False
        ssid, password, eap = creds
        try:
            if eap:
                logger.debug("Try to connect to: %s with enterprise encryption" % ssid)
                WifiUtil._connect_radio(ssid, eap=eap)
            elif password:
                logger.debug("Try to connect to: %s with standard encryption" % ssid)
                WifiUtil._connect_radio(ssid, password=password)
            else:
                logger.debug("Try to connect to: %s without encryption" % ssid)
                WifiUtil._connect_radio(ssid)
            logger.debug("Connection established to Wifi %s" % ssid)
            WifiUtil._init_sessions()
        except ConnectionError:
            logger.error("Failed to connect to WiFi (ssid=%s)" % ssid)
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
        import time
        from adafruit_ntp import NTP

        try:
            logger.debug('Trying to set RTC via NTP...')
            ntp = NTP(WifiUtil.pool, tz_offset=0, cache_seconds=3600)
            utc_s = ntp.utc_ns // 1_000_000_000
            if hasattr(time, "gmtime"):
                rtc_st = time.gmtime(utc_s)
            else:
                from tz_format import utc_epoch_to_struct_time

                rtc_st = utc_epoch_to_struct_time(utc_s)
            rtc.RTC().datetime = rtc_st
            Config.runtime_settings['rtc_is_set'] = True  # Assuming rtc_is_set is a setting in your Config

            logger.debug('RTC successfully configured (UTC from NTP utc_ns)')

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
