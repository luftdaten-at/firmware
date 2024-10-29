from lib.cptoml import fetch
from wifi import radio as wifi_radio
from socketpool import SocketPool
from adafruit_requests import Session
import storage
from lib.cptoml import put


class AutoSaveDict(dict):
    def __init__(self, *args, **kwargs):
        self.toml_file = kwargs.pop('toml_file')
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        print(key, value)
        storage.remount('/', False)
        put(key, value, toml=f'/{self.toml_file.get(key, 'settings.toml')}')
        storage.remount('/', True)

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

        # firmware Config
        'FIRMWARE_MAJOR': 'boot.toml',
        'FIRMWARE_MINOR': 'boot.toml',
        'FIRMWARE_PATCH': 'boot.toml',

        # wifi Config
        'SSID': 'settings.toml',
        'PASSWORD': 'settings.toml',

        # API config
        'UPDATE_SERVER': 'boot.toml',

        # update config
        'ROLLBACK': 'settings.toml'
    }
    # Normal settings (persistent)
    settings = AutoSaveDict({
        # model id 
        'MODEL': None,

        # firmware Config
        'FIRMWARE_MAJOR': None,
        'FIRMWARE_MINOR': None,
        'FIRMWARE_PATCH': None,

        # wifi Config
        'SSID': None,
        'PASSWORD': None,

        'UPDATE_SERVER': None,
        'ROLLBACK': False
    }, toml_file=key_to_toml_file)

    @staticmethod
    def init(only_settings = False):
        for key in Config.settings:
            if only_settings and Config.key_to_toml_file.get(key, 'settings.toml') != 'settings.toml':
                continue
            val = fetch(key, toml=Config.key_to_toml_file.get(key, 'settings.toml'))
            if val is not None:
                Config.settings[key] = val

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

        return True
    
    @staticmethod
    def new_session():
        return Session(WifiUtil.pool)