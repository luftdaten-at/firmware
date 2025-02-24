from lib.cptoml import fetch
from wifi import radio as wifi_radio
from socketpool import SocketPool
from adafruit_requests import Session
import storage
from lib.cptoml import put
from ssl import create_default_context

from logger import logger


class AutoSaveDict(dict):
    def __init__(self, *args, **kwargs):
        self.toml_file = kwargs.pop('toml_file')
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
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
        'TEST_UPDATE_SERVER': 'boot.toml',

        # update config
        'ROLLBACK': 'settings.toml',

        # test mode
        'TEST_MODE': 'settings.toml',

        # path for https certificates
        'CERTIFICATE_PATH': 'boot.toml'
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
        'TEST_UPDATE_SERVER': None,
        'ROLLBACK': False,

        # test mode
        'TEST_MODE': None,

        'CERTIFICATE_PATH': "certs/isrgrootx1.pem" 
    }, toml_file=key_to_toml_file)

    runtime_settings = {
        'UPDATE_SERVER': None
    }

    @staticmethod
    def init(only_settings = False):
        for key in Config.settings:
            if only_settings and Config.key_to_toml_file.get(key, 'settings.toml') != 'settings.toml':
                continue
            val = fetch(key, toml=Config.key_to_toml_file.get(key, 'settings.toml'))
            if val is not None:
                Config.settings[key] = val

        # set correct update server
        Config.runtime_settings['UPDATE_SERVER'] = Config.settings['TEST_UPDATE_SERVER'] if Config.settings['TEST_MODE'] else Config.runtime_settings['UPDATE_SERVER']


class WifiUtil:
    radio = wifi_radio
    pool: SocketPool = None
    session: Session = None

    @staticmethod
    def connect() -> bool:
        if not Config.settings['SSID'] or not Config.settings['PASSWORD']:
            return False
        try:
            logger.debug('Connecting to Wifi:', Config.settings['SSID'])
            wifi_radio.connect(Config.settings['SSID'], Config.settings['PASSWORD'])
            logger.debug('Connection established to Wifi', Config.settings['SSID'])

            # init pool
            WifiUtil.pool = SocketPool(WifiUtil.radio)

            # init session
            api_context = create_default_context()
            with open(Config.settings['CERTIFICATE_PATH'], 'r') as f:
                api_context.load_verify_locations(cadata=f.read())
            WifiUtil.session = Session(WifiUtil.pool, api_context)

        except ConnectionError:
            logger.error("Failed to connect to WiFi with provided credentials")
            return False 

        return True


    @staticmethod
    def get(url: str):
        try:
            response = WifiUtil.session.request(
                method='GET',
                url=url
            )

            if response.status_code != 200:
                logger.error(f'GET failed, url: {url}, status code: {response.status_code}, text: {response.text}')

                return False

            return response.text
        except Exception as e:
            logger.error(f'GET faild: {e}')
            return False
