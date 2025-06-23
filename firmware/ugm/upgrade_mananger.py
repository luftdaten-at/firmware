import json
import storage
import os
from ssl import create_default_context
from adafruit_requests import Session

from dirTree import FolderEntry, Entry, walk, join_path, FileEntry
from logger import logger

WifiUtil = None
Config = None

class Ugm:
    # API commands
    LATEST_VERSION = 'latest_version'
    DOWNLOAD = 'download'
    FILE_LIST = 'file_list'
    IGNORE_FILE_PATH = 'ugm/.ignore'
    BACKUP_FOLDER = 'ugm/backup'

    @staticmethod
    def init(wifiUtil, config):
        global WifiUtil, Config
        WifiUtil = wifiUtil
        Config = config


    @staticmethod
    def get(url: str, binary = False):
        return WifiUtil.get(url, binary)


    @staticmethod
    def get_latest_firmware_version() -> str:
        '''
        return: str: file_name if update available else None
        '''

        url=f'{Config.runtime_settings['UPDATE_SERVER']}/{Ugm.LATEST_VERSION}/{Config.settings['MODEL']}'
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
            cur_version = (Config.settings['FIRMWARE_MAJOR'], Config.settings['FIRMWARE_MINOR'], Config.settings['FIRMWARE_PATCH'])
            new_versin = (int(firmware_major), int(firmware_minor), int(firmware_patch))

            if cur_version >= new_versin:
                # no upgrade available
                return False 
            
            # upgrade available
            return file_name

        except Exception as e:
            logger.error(f'Could not retrieve version information from file name: {file_name}: {e}')
            # no upgrade done
            return False
    
    @staticmethod
    def install_update(folder: str):
        # .ignore
        ignore = set()
        try:
            with open(Ugm.IGNORE_FILE_PATH, 'r') as f:
                ignore = set(f.read().split())
        except Exception:
            return False

        # list current dir
        cur_ignore = set(join_path('.', x) for x in ignore)
        cur_tree = FolderEntry('.', ignore=cur_ignore)

        url=f'{Config.runtime_settings['UPDATE_SERVER']}/{Ugm.FILE_LIST}/{folder}'
        text = ''
        if not (text := Ugm.get(url)):
            return False

        new_tree = Entry.from_dict(json.loads(text))
        new_ignore = set(join_path(new_tree.path, x) for x in ignore)
        new_tree.drop(new_ignore)

        update_tree = new_tree - cur_tree

        storage.remount('/', False)
        # clear backup folder
        FolderEntry(Ugm.BACKUP_FOLDER).remove(remove_self = False)
        storage.remount('/', True)

        # overwrite with new files
        Config.settings['ROLLBACK'] = True

        storage.remount('/', False)
        # backup diff
        cur_tree.move_diff(new_tree, Ugm.BACKUP_FOLDER, move_self = False)

        for entry in walk(update_tree):
            if entry.path in ('.', ''):
                continue
            if isinstance(entry, FolderEntry):
                try:
                    os.mkdir(entry.path)
                except OSError:
                    pass
            if isinstance(entry, FileEntry):
                # download file
                url=f'{Config.runtime_settings['UPDATE_SERVER']}/{Ugm.DOWNLOAD}?filename={join_path(folder, entry.path)}'
                content = Ugm.get(url, binary=True)
                with open(entry.path, 'wb') as f:
                    f.write(content)

        storage.remount('/', True)

        Config.settings['ROLLBACK'] = False


    @staticmethod
    def rollback():
        backup = FolderEntry(Ugm.BACKUP_FOLDER)
        storage.remount('/', False)
        backup.copy('.', copy_self = False)
        storage.remount('/', True)
        # finish rollback
        Config.settings['ROLLBACK'] = False
