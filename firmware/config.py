from lib.cptoml import put, fetch
from enums import AutoUpdateMode, AirStationMeasurementInterval, BatterySaverMode

class AutoSaveDict(dict):
    def __init__(self, *args, **kwargs):
        self.toml_file = kwargs.pop('toml_file', 'settings.toml')
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        # Call the parent method to set the value in the dictionary
        # TODO: check if key already exists
        super().__setitem__(key, value)
        
        # Automatically save the key-value pair to the TOML file
        put(key, value, toml=self.toml_file)

    def set_toml_file(self, filepath):
        # Optionally set the TOML file path to save changes
        self.toml_file = filepath


class Config:
    settings = AutoSaveDict({
        'SSID': None,
        'PASSWORD': None,
        'API_URL': None,
        'FIRMWARE_MAJOR': None,
        'FIRMWARE_MINOR': None,
        'FIRMWARE_PATCH': None,
        'PROTOCOL_VERSION': None,
        'MODEL': None,
        'MANUFACTURE_ID': None,
        'TEST_MODE': None
    }, toml_file='settings.toml')

    runtime_settings = {
        'rtc_is_set': False,
        'JSON_QUEUE': 'json_queue',
        'CERTIFICATE_PATH': 'certs/isrgrootx1.pem',
        'API_KEY_LENGTH': 32
    }

    @staticmethod
    def init():
        # Fetch and initialize settings using a loop
        for key in Config.settings:
            Config.settings[key] = fetch(key)

        # Handle the API_URL based on TEST_MODE after initialization
        if Config.settings['TEST_MODE']:
            Config.settings['API_URL'] = fetch('TEST_API_URL')
        else:
            Config.settings['API_URL'] = fetch('API_URL')

class AirStationConfig:
    settings = AutoSaveDict({
        'longitude': None,
        'latitude': None,
        'height': None,
        'auto_update_mode': AutoUpdateMode.off,
        'battery_save_mode': BatterySaverMode.off,
        'measurement_interval': AirStationMeasurementInterval.sec30 
    }, toml_file='settings.toml')

    @staticmethod
    def init():
        # Fetch and initialize settings using a loop
        for key in AirStationConfig.settings:
            AirStationConfig.settings[key] = fetch(key)
