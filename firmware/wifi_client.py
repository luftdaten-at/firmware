import gc
from wifi import radio as wifi_radio
from config import Config
from enums import LdProduct
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
    def _copy_air_station_metadata_block(src: dict) -> dict:
        """Shallow copy of station/device block with a fresh ``location`` dict when present."""
        inner = dict(src)
        if isinstance(src.get("location"), dict):
            inner["location"] = dict(src["location"])
        return inner

    @staticmethod
    def _sanitize_station_measurement_location(payload: dict) -> None:
        """Station ``data/`` requires ``location``; lat/lon/height must be float or null, not ``\"\"``."""
        block = payload.get("station")
        if not isinstance(block, dict):
            return
        loc = block.get("location")
        if not isinstance(loc, dict):
            loc = {}
        fixed = {}
        for kk in ("lat", "lon", "height"):
            v = loc.get(kk)
            if v is None or (isinstance(v, str) and not str(v).strip()):
                fixed[kk] = None
            else:
                try:
                    fixed[kk] = float(str(v).strip())
                except (TypeError, ValueError):
                    fixed[kk] = None
        block["location"] = fixed

    @staticmethod
    def _datahub_base_url():
        """Configured Datahub root (``…/api/v1/devices``)."""
        return (
            Config.settings.get("DATAHUB_TEST_API_URL")
            if Config.settings.get("TEST_MODE")
            else Config.settings.get("DATAHUB_API_URL")
        )

    @staticmethod
    def _normalize_datahub_data_payload(payload, api_url: str, router: str):
        """
        Datahub ``devices/data`` expects ``device.id`` (hardware id), optional top-level
        ``location`` with ``lat``/``lon``/``height``, and ``sensors`` — not ``device.device``
        nor ``device.location``. See datahub contract (workshop block is optional).
        """
        if router != "data/":
            return payload
        dh = WifiUtil._datahub_base_url()
        if not dh or str(api_url).rstrip("/") != str(dh).rstrip("/"):
            return payload
        if not isinstance(payload, dict):
            return payload

        meta_key = None
        inner_src = None
        if "device" in payload and isinstance(payload.get("device"), dict):
            meta_key = "device"
            inner_src = payload["device"]
        elif "station" in payload and isinstance(payload.get("station"), dict):
            meta_key = "station"
            inner_src = payload["station"]
        else:
            return payload

        out = {k: v for k, v in payload.items() if k != meta_key}
        dev = dict(inner_src)

        if "device" in dev and "id" not in dev:
            dev["id"] = dev.pop("device")

        loc = dev.pop("location", None)
        if isinstance(loc, dict):
            top_loc = {}
            for kk in ("lat", "lon", "height"):
                if kk in loc:
                    top_loc[kk] = loc[kk]
            if top_loc:
                out["location"] = top_loc

        for remove in ("source", "test_mode", "calibration_mode"):
            dev.pop(remove, None)
        dev.pop("api", None)

        out["device"] = dev
        return out

    @staticmethod
    def _summarize_api_payload(payload) -> str:
        """Short description for logs (no secrets)."""
        if not isinstance(payload, dict):
            return type(payload).__name__
        top = []
        if "device" in payload:
            top.append("device")
        if "station" in payload:
            top.append("station")
        block = payload.get("device") if isinstance(payload.get("device"), dict) else None
        if block is None and isinstance(payload.get("station"), dict):
            block = payload["station"]
        ident = ""
        if isinstance(block, dict):
            raw_id = block.get("id") if block.get("id") is not None else block.get("device")
            if raw_id is not None:
                ident = f"id={raw_id!r} "
        sens = payload.get("sensors")
        n_sens = len(sens) if isinstance(sens, dict) else 0
        st = payload.get("status_list")
        n_log = len(st) if isinstance(st, list) else 0
        sl = payload.get("sensor_list")
        n_sl = len(sl) if isinstance(sl, list) else 0
        return (
            f"toplevel={'+'.join(top) or '-'} {ident}"
            f"sensors={n_sens} status_list={n_log} sensor_list={n_sl}"
        )

    @staticmethod
    def _debug_response_snippet(response, max_len: int = 160) -> str:
        try:
            t = response.text
        except Exception:
            return "(no body)"
        if not t:
            return "(empty)"
        t = t.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        if len(t) > max_len:
            return t[:max_len] + "…"
        return t

    @staticmethod
    def send_json_to_api(data, api_url: str = None, router: str = 'data/'):
        if not api_url:
            api_url = Config.runtime_settings['API_URL']
        # Station `data/` API expects top-level ``station``; firmware uses ``device``
        # (see ``API_JSON_DEVICE_KEY`` in ld_product_model). Datahub uses ``device`` on its own base URL.
        payload = data
        station_measurement = (
            router == "data/"
            and isinstance(data, dict)
            and Config.settings.get("MODEL") == LdProduct.AIR_STATION
            and not Config.is_air_station_wifiless()
            and api_url == Config.runtime_settings.get("API_URL")
        )
        if station_measurement:
            if "station" in data and isinstance(data.get("station"), dict):
                payload = dict(data)
                payload["station"] = WifiUtil._copy_air_station_metadata_block(data["station"])
                if "device" in payload:
                    del payload["device"]
            elif "device" in data and isinstance(data.get("device"), dict):
                payload = dict(data)
                payload["station"] = WifiUtil._copy_air_station_metadata_block(data["device"])
                del payload["device"]
            else:
                payload = data
            if isinstance(payload, dict) and "station" in payload:
                WifiUtil._sanitize_station_measurement_location(payload)
        # Datahub routes (``status/``, ``data/``, …) expect top-level ``device``, not ``station``.
        if isinstance(payload, dict) and "station" in payload and "device" not in payload:
            dh = WifiUtil._datahub_base_url()
            if dh and str(api_url).rstrip("/") == str(dh).rstrip("/"):
                payload = dict(payload)
                payload["device"] = payload.pop("station")
        payload = WifiUtil._normalize_datahub_data_payload(payload, api_url, router)
        url_full = f"{api_url}/{router}"
        logger.debug(f"API POST {url_full} {WifiUtil._summarize_api_payload(payload)}")
        gc.collect()
        response = WifiUtil.api_session.request(
            method='POST',
            url=url_full,
            json=payload,
        )
        logger.debug(
            f"API POST done status={response.status_code} url={url_full} "
            f"body={WifiUtil._debug_response_snippet(response)}"
        )
        # send to additional APIs
        # TODO: Handle response
        if Config.settings.get('API_URLS', None):
            for extra_url in Config.runtime_settings['API_URLS']:
                extra_full = f"{extra_url}/{router}"
                logger.debug(f"API POST extra {extra_full} {WifiUtil._summarize_api_payload(payload)}")
                extra_resp = WifiUtil.api_session.request(
                    method='POST',
                    url=extra_full,
                    json=payload,
                )
                logger.debug(
                    f"API POST extra done status={extra_resp.status_code} url={extra_full} "
                    f"body={WifiUtil._debug_response_snippet(extra_resp)}"
                )
        return response
 

    @staticmethod
    def send_json_to_sensor_community(header, data):
        gc.collect()
        url = Config.runtime_settings['SENSOR_COMMUNITY_API']
        xs = header.get("X-Sensor") if isinstance(header, dict) else None
        logger.debug(f"Sensor.Community POST url={url} X-Sensor={xs!r}")
        response = WifiUtil.sensor_community_session.request(
            method='POST',
            url=url,
            json=data,
            headers=header 
        )
        logger.debug(
            f"Sensor.Community done status={response.status_code} "
            f"body={WifiUtil._debug_response_snippet(response)}"
        )
        return response


class ConnectionFailure:
    SSID_NOT_FOUND = 1
    PASSWORD_INCORRECT = 2
    PASSWORD_LENGTH = 3
    INVALID_BSSID = 4
    OTHER = 5
