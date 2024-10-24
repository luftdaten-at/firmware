from wifi_client import WifiUtil
from config import Config
import storage
import os
from dirTree import FolderEntry

class Ugm:
    # API commands
    LATEST_VERSION = 'latest_version'
    DOWNLOAD = 'download'
    FOLDER_LIST = 'folder_list'
    IGNORE_FILE_PATH = 'ugm/.ignore'
    session = WifiUtil.new_session()

    @staticmethod
    def get(url: str, error_msg = ''):
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
    def install_update(file_path: str):
        # unzip file
        # List the information from a .zip archive

        # replace files
        pass  

    @staticmethod
    def download_firmware(folder: str):
        storage.remount('/', False)
        # .ignore
        ignore = set() 
        try:
            with open(Ugm.IGNORE_FILE_PATH, 'r') as f:
                ignore = set(f.read().split())
        except FileNotFoundError:
            return False

        # init session
        session = WifiUtil.new_session()

        # TODO: include igonre
        cur_tree = FolderEntry('.')
        new_tree = get_firmware_tree()

        cur_tree.move_diff(new_tree, 'target folder')

        update_tree = new_tree - cur_tree

        # set update flag start
        # download update_tree
        for e in update_tree.walk():
            # save e
            pass
        # set update flag finish

    @staticmethod
    def check_if_upgrade_available() -> str:
        '''
        Gets the latest version number
        Compares it with the current version
        return: folder of new version if upgrade available else False
        '''
        file_name = Ugm.get_latest_firmware_version()

        if file_name is None:
            return 

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
