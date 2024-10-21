from lib.cptoml import put, fetch
from storage import remount
from enums import AutoUpdateMode, AirStationMeasurementInterval, BatterySaverMode

class AutoSaveDict(dict):
    def __init__(self, *args, **kwargs):
        self.toml_file = kwargs.pop('toml_file', 'settings.toml')
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        print(key, value)
        remount('/', False)
        put(key, value, toml=f'/{self.toml_file}')
        remount('/', True)

    def set_toml_file(self, filepath):
        self.toml_file = filepath


class Config:
    # Normal settings (persistent)
    settings = AutoSaveDict({
        # model id 
        'MODEL': None,

        # firmware Config
        'FIRMWARE_MAJOR': None,
        'FIRMWARE_MINOR': None,
        'FIRMWARE_PATCH': None,
        'PROTOCOL_VERSION': None,
        'MANUFACTURE_ID': None,

        # wifi Config
        'SSID': None,
        'PASSWORD': None,

        # API config
        'TEST_MODE': None,
        'API_URL': None,
        'TEST_API_URL': None,
        'UPDATE_SERVER': None,

        # AirStationConfig must not be specified in settings.toml
        'longitude': "",
        'latitude': "",
        'height': "",
        'auto_update_mode': AutoUpdateMode.on,
        'battery_save_mode': BatterySaverMode.off,
        'measurement_interval': AirStationMeasurementInterval.sec30,
    }, toml_file='settings.toml')

    # Runtime settings (non-persistent)
    runtime_settings = {
        'rtc_is_set': False,
        'JSON_QUEUE': 'json_queue',
        'FIRMWARE_FOLDER': 'new_firmware',
        'CERTIFICATE_PATH': 'certs/isrgrootx1.pem',
        'API_KEY_LENGTH': 32,
    }

    @staticmethod
    def init():
        for key in Config.settings:
            val = fetch(key)
            if val is not None:
                Config.settings[key] = fetch(key)

        # Handle the API_URL based on TEST_MODE after initialization
        if Config.settings['TEST_MODE']:
            Config.runtime_settings['API_URL'] = Config.settings['TEST_API_URL']
        else:
            Config.runtime_settings['API_URL'] = Config.settings['API_URL']
