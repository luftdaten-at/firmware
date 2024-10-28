from wifi_client import WifiUtil
from config import Config
import storage
from dirTree import FolderEntry, Entry, walk, join_path, FileEntry
import json
from lib.cptoml import fetch
from wifi import radio as wifi_radio
from socketpool import SocketPool
from adafruit_requests import Session
import supervisor

class AutoSaveDict(dict):
    def __init__(self, *args, **kwargs):
        self.toml_file = kwargs.pop('toml_file')
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        print(key, value)
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
    def init():
        for key in Config.settings:
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

class Ugm:
    # API commands
    LATEST_VERSION = 'latest_version'
    DOWNLOAD = 'download'
    FILE_LIST = 'file_list'
    IGNORE_FILE_PATH = 'ugm/.ignore'
    BACKUP_FOLDER = 'ugm/backup'
    session = None

    @staticmethod
    def get(url: str, error_msg = ''):
        Ugm.session = WifiUtil.new_session() 
        try:
            response = Ugm.session.request(
                method='GET',
                url=url
            )
            if response.status_code != 200:
                print('Status code != 200')
                print(f'{response.status_code=}')
                print(f'{response.text=}')

                return False

            return response.text

        except Exception as e:
            if error_msg:
                print(error_msg)
            print(e)
            return False

    @staticmethod
    def get_latest_firmware_version() -> str:
        '''
        return: str: file_name if update available else None
        '''

        url=f'{Config.settings['UPDATE_SERVER']}/{Ugm.LATEST_VERSION}/{Config.settings['MODEL']}'
        text = ''
        if not (text := Ugm.get(url)):
            return None

        return text[1:-1]

    @staticmethod
    def check_if_upgrade_available() -> str:
        '''
        Gets the latest version number
        Compares it with the current version
        return: folder of new version if upgrade available else False
        '''
        file_name = Ugm.get_latest_firmware_version()

        if file_name is None:
            return False

        # {MODEL_ID}_{FIRMWARE_MAJOR}_{FIRMWARE_MINOR}_{FIRMWARE_PATCH}
        latest_version = file_name

        # unpack version
        try:
            _, firmware_major, firmware_minor, firmware_patch = latest_version.split('_')
            if all([
                firmware_major == Config.settings['FIRMWARE_MAJOR'],
                firmware_minor == Config.settings['FIRMWARE_MINOR'],
                firmware_patch == Config.settings['FIRMWARE_PATCH']
            ]):
                # no upgrade available
                return False 
            
            # upgrade available
            return file_name

        except Exception as e:
            print(f'Could not retrieve version information from file name: {file_name}')
            print(e)

            # no upgrade done
            return False
    
    @staticmethod
    def install_update(folder: str):
        # .ignore
        ignore = set()
        try:
            with open(Ugm.IGNORE_FILE_PATH, 'r') as f:
                ignore = set(f.read().split())
        except FileNotFoundError:
            return False

        # list current dir
        cur_ignore = set(join_path('.', x) for x in ignore)
        cur_tree = FolderEntry('.', ignore=cur_ignore)

        url=f'{Config.settings['UPDATE_SERVER']}/{Ugm.FILE_LIST}/{folder}'
        text = ''
        if not (text := Ugm.get(url)):
            return False

        new_tree = Entry.from_dict(json.loads(text))
        new_ignore = set(join_path(new_tree.path, x) for x in ignore)
        new_tree.drop(new_ignore)

        storage.remount('/', False)

        # clear backup folder
        FolderEntry(Ugm.BACKUP_FOLDER).remove(remove_self = False)

        # backup diff
        cur_tree.move_diff(new_tree, Ugm.BACKUP_FOLDER, move_self = False)

        storage.remount('/', True)

        # overwrite with new files
        Config.settings['ROLLBACK'] = True

        storage.remount('/', False)

        update_tree = new_tree - cur_tree
        for entry in walk(update_tree):
            print('update', entry.path)
            '''
            if isinstance(entry, FolderEntry):
                os.mkdir(entry.path)
            if isinstance(entry, FileEntry):
                # download file
                url=f'{Config.settings['UPDATE_SERVER']}/{Ugm.DOWNLOAD}?{entry.path}'
                content = Ugm.get()
                with open(entry.path, 'w') as f:
                 f.write(content)
            '''
        storage.remount('/', True)

        Config.settings['ROLLBACK'] = False


    @staticmethod
    def rollback():
        pass


Config.init()

# check rollback
if Config.settings['ROLLBACK']:
    Ugm.rollback()
    import sys
    sys.exit()

# check if update available
if False and (folder := Ugm.check_if_upgrade_available()):
    Ugm.install_update(folder)

# boot normaly
supervisor.set_next_code_file('main.py')
supervisor.reload()
