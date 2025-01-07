from lib.cptoml import put, fetch
from storage import remount
from enums import AutoUpdateMode, AirStationMeasurementInterval, BatterySaverMode

class AutoSaveDict(dict):
    def __init__(self, *args, **kwargs):
        self.toml_file = kwargs.pop('toml_file', 'settings.toml')
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        remount('/', False)
        put(key, value, toml=f'/{self.toml_file.get(key, 'settings.toml')}')
        remount('/', True)

    def set_toml_file(self, filepath):
        self.toml_file = filepath


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

        # API config
        'TEST_MODE': 'settings.toml',
        'API_URL': 'boot.toml',
        'TEST_API_URL': 'boot.toml',
        'UPDATE_SERVER': 'boot.toml',
        'DATAHUB_API_URL': 'boot.toml',
        'DATAHUB_TEST_API_URL': 'boot.toml',
        'SEND_TO_SENSOR_COMMUNITY': 'settings.toml',

        # AirStationConfig must not be specified in settings.toml
        'longitude': 'settings.toml',
        'latitude': 'settings.toml',
        'height': 'settings.toml',
        'auto_update_mode': 'settings.toml',
        'battery_save_mode': 'settings.toml',
        'measurement_interval': 'settings.toml',

        'CERTIFICATE_PATH': 'boot.toml',
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

        # API config
        'TEST_MODE': None,
        'API_URL': None,
        'TEST_API_URL': None,
        'UPDATE_SERVER': None,
        'DATAHUB_API_URL': None,
        'DATAHUB_TEST_API_URL': None,
        'SEND_TO_SENSOR_COMMUNITY': None,

        # AirStationConfig must not be specified in settings.toml
        'longitude': "",
        'latitude': "",
        'height': "",
        'auto_update_mode': AutoUpdateMode.on,
        'battery_save_mode': BatterySaverMode.off,
        'measurement_interval': AirStationMeasurementInterval.sec30,

        'CERTIFICATE_PATH': 'certs/isrgrootx1.pem',
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
    def init():
        for key in Config.settings:
            val = fetch(key, toml=Config.key_to_toml_file.get(key, 'settings.toml'))
            if val is not None:
                Config.settings[key] = val

        # Handle the API_URL based on TEST_MODE after initialization
        if Config.settings['TEST_MODE']:
            Config.runtime_settings['API_URL'] = Config.settings['TEST_API_URL']
        else:
            Config.runtime_settings['API_URL'] = Config.settings['API_URL']

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
