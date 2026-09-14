from lib.cptoml import fetch
from enums import AutoUpdateMode, AirStationMeasurementInterval, BatterySaverMode, LdProduct
from fs_rw import persist_toml_value, persist_toml_values

_GEO_STRING_KEYS = frozenset(("longitude", "latitude", "height"))


class AutoSaveDict(dict):
    def __init__(self, *args, **kwargs):
        self.toml_file = kwargs.pop('toml_file', 'settings.toml')
        super().__init__(*args, **kwargs)
        self._batch_depth = 0
        self._dirty = {}

        for key in self:
            val = fetch(key, toml=self.toml_file.get(key, 'settings.toml'))
            if val is not None:
                if key in _GEO_STRING_KEYS:
                    val = str(val)
                super().__setitem__(key, val)

    def __setitem__(self, key, value):
        if key in _GEO_STRING_KEYS and value is not None:
            value = str(value)
        super().__setitem__(key, value)
        if self._batch_depth > 0:
            self._dirty[key] = value
            return
        persist_toml_value(key, value, self.toml_file.get(key, "settings.toml"))

    def batch_persist(self):
        return _BatchPersist(self)

    def _flush_dirty(self) -> bool:
        by_file = {}
        for key, value in self._dirty.items():
            path = self.toml_file.get(key, "settings.toml")
            if path not in by_file:
                by_file[path] = {}
            by_file[path][key] = value
        self._dirty = {}
        ok = True
        for path, items in by_file.items():
            if not persist_toml_values(items, path):
                ok = False
        return ok

    def set_toml_file(self, filepath):
        self.toml_file = filepath


class _BatchPersist:
    def __init__(self, store):
        self._store = store

    def __enter__(self):
        self._store._batch_depth += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        self._store._batch_depth -= 1
        if self._store._batch_depth == 0:
            self._store._flush_dirty()
        return False


class Config:
    '''
    settings.toml: holds all the device spcific settings and informations
    boot.toml: information not bound to a single device, variables arent ever changed by the code itself
    '''

    key_to_toml_file = {
        # model id 
        'MODEL': 'settings.toml',

        # boot option
        'boot_into': 'settings.toml',

        # wifi mac should not be changed
        'mac': 'settings.toml',
        'api_key': 'settings.toml',
        'device_id': 'settings.toml',

        # firmware Config
        'FIRMWARE_MAJOR': 'boot.toml',
        'FIRMWARE_MINOR': 'boot.toml',
        'FIRMWARE_PATCH': 'boot.toml',
        'PROTOCOL_VERSION': 'boot.toml',
        'MANUFACTURE_ID': 'boot.toml',

        # wifi Config
        'SSID': 'settings.toml',
        'PASSWORD': 'settings.toml',
        'EAP_IDENTITY': 'settings.toml',
        'EAP_USERNAME': 'settings.toml',
        'EAP_PASSWORD': 'settings.toml',

        # API config
        'TEST_MODE': 'settings.toml',
        'CALIBRATION_MODE': 'settings.toml',
        'API_URL': 'boot.toml',
        'TEST_API_URL': 'boot.toml',
        'UPDATE_SERVER': 'boot.toml',
        'TEST_UPDATE_SERVER': 'boot.toml',
        'DATAHUB_API_URL': 'boot.toml',
        'DATAHUB_TEST_API_URL': 'boot.toml',
        'SEND_TO_SENSOR_COMMUNITY': 'settings.toml',
        'LOG_LEVEL': 'settings.toml',

        # AirStationConfig must not be specified in settings.toml
        'longitude': 'settings.toml',
        'latitude': 'settings.toml',
        'height': 'settings.toml',
        'auto_update_mode': 'settings.toml',
        'battery_save_mode': 'settings.toml',
        'measurement_interval': 'settings.toml',

        'SCL': 'settings.toml',
        'SDA': 'settings.toml',
        'BUTTON_PIN': 'settings.toml',

        'TZ': 'settings.toml',

        'CERTIFICATE_PATH': 'boot.toml',

        'ROLLBACK': 'settings.toml'
    }
    # Normal settings (persistent)
    settings = AutoSaveDict({
        # model id 
        'MODEL': None,

        # boot option
        'boot_into': None,

        # wifi mac should not be changed
        'mac': None,
        'api_key': None,
        'device_id': None,

        # firmware Config
        'FIRMWARE_MAJOR': None,
        'FIRMWARE_MINOR': None,
        'FIRMWARE_PATCH': None,
        'PROTOCOL_VERSION': None,
        'MANUFACTURE_ID': None,

        # wifi Config
        'SSID': None,
        'PASSWORD': None,
        'EAP_IDENTITY': None,
        'EAP_USERNAME': None,
        'EAP_PASSWORD': None,

        # API config
        'TEST_MODE': None,
        'CALIBRATION_MODE': None,
        'API_URL': None,
        'TEST_API_URL': None,
        'UPDATE_SERVER': None,
        'TEST_UPDATE_SERVER': None,
        'DATAHUB_API_URL': None,
        'DATAHUB_TEST_API_URL': None,
        'SEND_TO_SENSOR_COMMUNITY': None,
        'LOG_LEVEL': 'DEBUG',

        # AirStationConfig must not be specified in settings.toml
        'longitude': "",
        'latitude': "",
        'height': "",
        'auto_update_mode': AutoUpdateMode.on,
        'battery_save_mode': BatterySaverMode.off,
        'measurement_interval': AirStationMeasurementInterval.sec30,

        'SCL': None,
        'SDA': None,
        'BUTTON_PIN': None,

        'TZ': 'Europe/Vienna',

        'CERTIFICATE_PATH': 'certs/isrgrootx1.pem',

        'ROLLBACK': False,
    }, toml_file=key_to_toml_file)

    # Runtime settings (non-persistent)
    runtime_settings = {
        'rtc_is_set': False,
        'JSON_QUEUE': 'json_queue',
        'FIRMWARE_FOLDER': 'new_firmware',
        'CERTIFICATE_PATH': 'certs/isrgrootx1.pem',
        'SENSOR_COMMUNITY_CERTIFICATE_PATH': 'certs/api-sensor-community-chain.pem',
        'SENSOR_COMMUNITY_API': 'https://api.sensor.community/v1/push-sensor-data',
        'API_KEY_LENGTH': 32,
    }

    @staticmethod
    def generate_random_api_key() -> str:
        import random

        vorrat = ''.join(chr(ord('a') + i) for i in range(26)) + ''.join(str(i) for i in range(10))
        api_key = ''.join(random.choice(vorrat) for _ in range(Config.runtime_settings['API_KEY_LENGTH']))

        return api_key
    
    @staticmethod
    def set_api_url():
        if Config.settings['MODEL'] == LdProduct.AIR_STATION:
            Config.runtime_settings['API_URL'] = Config.settings['API_URL']
            if Config.settings['TEST_MODE']:
                #Config.runtime_settings['API_URLS'] = [Config.settings['TEST_API_URL']]
                Config.runtime_settings['API_URL'] = Config.settings['TEST_API_URL']

        elif Config.settings['MODEL'] in (LdProduct.AIR_CUBE, LdProduct.AIR_BADGE, LdProduct.AIR_AROUND):
            Config.runtime_settings['API_URL'] = Config.settings['DATAHUB_TEST_API_URL'] if Config.settings['TEST_MODE'] else Config.settings['DATAHUB_API_URL']

    @staticmethod
    def init(): 
        # Calibration mode
        Config.runtime_settings['CALIBRATION_MODE'] = Config.settings['CALIBRATION_MODE']
        if Config.settings['CALIBRATION_MODE'] is not None:
            Config.runtime_settings['CALIBRATION_MODE'] = Config.settings['CALIBRATION_MODE']
        else:
            # if we are connected to our special notwork always active calibration mode
            Config.runtime_settings['CALIBRATION_MODE'] = (Config.settings['SSID'] == 'luftdaten.at')

        # Handle the API_URL based on TEST_MODE after initialization
        Config.set_api_url()

        # set correct update server
        Config.runtime_settings['UPDATE_SERVER'] = Config.settings['TEST_UPDATE_SERVER'] if Config.settings['TEST_MODE'] else Config.settings['UPDATE_SERVER']
        
        # when the device boots the first time
        # some informations have to be generated
        # mac
        if Config.settings['mac'] is None:
            import wifi
            Config.settings['mac'] = wifi.radio.mac_address_ap.hex().upper()
        # generate api key
        if Config.settings['api_key'] is None:
            Config.settings['api_key'] = Config.generate_random_api_key()

        # set device id
        if Config.settings['device_id'] is None:
            Config.settings['device_id'] = f'{Config.settings['mac']}{Config.settings["MANUFACTURE_ID"]}'
