from dirTree import FolderEntry, Entry, walk, join_path, FileEntry
import json
import storage
import os

WifiUtil = None
Config = None

class Ugm:
    # API commands
    LATEST_VERSION = 'latest_version'
    DOWNLOAD = 'download'
    FILE_LIST = 'file_list'
    IGNORE_FILE_PATH = 'ugm/.ignore'
    BACKUP_FOLDER = 'ugm/backup'
    session = None

    @staticmethod
    def init(wifiUtil, config):
        global WifiUtil, Config
        WifiUtil = wifiUtil
        Config = config

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

        update_tree = new_tree - cur_tree

        storage.remount('/', False)

        # clear backup folder
        FolderEntry(Ugm.BACKUP_FOLDER).remove(remove_self = False)

        # backup diff
        cur_tree.move_diff(new_tree, Ugm.BACKUP_FOLDER, move_self = False)

        storage.remount('/', True)

        # overwrite with new files
        Config.settings['ROLLBACK'] = True

        storage.remount('/', False)

        for entry in walk(update_tree):
            if entry.path in ('.', ''):
                continue
            print('update', entry.path)
            if isinstance(entry, FolderEntry):
                try:
                    os.mkdir(entry.path)
                except OSError:
                    pass
            if isinstance(entry, FileEntry):
                # download file
                url=f'{Config.settings['UPDATE_SERVER']}/{Ugm.DOWNLOAD}?filename={join_path(folder, entry.path)}'
                content = Ugm.get(url)
                with open(entry.path, 'w') as f:
                    f.write(content)

        storage.remount('/', True)

        Config.settings['ROLLBACK'] = False


    @staticmethod
    def rollback():
        pass
