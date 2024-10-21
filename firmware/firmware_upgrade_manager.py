from wifi_client import WifiUtil
from config import Config
import adafruit_hashlib as hashlib
import storage

class UpgradeManager:
    # API commands
    LATEST_VERSION = 'latest_version'
    DOWNLOAD = 'download'

    @staticmethod
    def get_latest_firmware_version() -> str:
        '''
        return: str: file_name if update available else None
        '''

        session = WifiUtil.new_session()
        url=f'{Config.settings['UPDATE_SERVER']}/{UpgradeManager.LATEST_VERSION}/{Config.settings['MODEL']}'

        try:
            response = session.request(
                method='GET',
                url=url,
            )

            if response.status_code != 200:
                print(f'Faild to find latest frimware version')
                print(f'{response.status_code=}')
                print(f'{response.text=}')

                return None
            else:
                # found latest version
                # remove quotes
                return response.text[1:-1]

        except Exception as e:
            print(e)
            return None

    @staticmethod
    def install_update(file_path: str):
        # unzip file
        # replace files
        pass

    @staticmethod
    def download_firmware(file_name: str):
        # TODO: check if already downloaded

        session = WifiUtil.new_session()
        url=f'{Config.settings["UPDATE_SERVER"]}/{UpgradeManager.DOWNLOAD}/{file_name}'
        print(url)
        try:
            response = session.request(
                method='GET',
                url=url,
            )

            if response.status_code != 200:
                print(f'Faild to download file: {file_name}')
                print(f'{response.status_code=}')
                print(f'{response.text=}')
                return None

            else:
                # download succesfull
                # check hach
                print('Download succesfull')
                print(f'{response.status_code=}')
                print(f'{response.text=}')
                print('Verify hash')

                content = response.text
                hexdigest = hashlib.sha256(content).hexdigest()

                if hexdigest != response.headers['sha256_checksum']:
                    print('invalid checksum')
                    return False

                # save to file
                storage.remount('/', False) 
                try:
                    with open(f"{Config.runtime_settings['FIRMWARE_FOLDER']}/{file_name}", 'w') as f:
                        f.write(content)
                except Exception as e:
                    print('cannot save downloaded firmware')
                    print(e)
                    return False
                storage.remount('/', True) 

                return True

        except Exception as e:
            print(e)
            return False

    @staticmethod
    def check_and_install_upgrade():
        '''
        check if upgrade available for current device
        download upgrade if available
            install upgrade
        return: (
            -1: faild to find or install upgrade,
             0: no upgrade available
             1: upgrade succesfully installed
        )
        '''
        file_name = UpgradeManager.get_latest_firmware_version()

        if file_name is None:
            return 

        # {MODEL_ID}_{FIRMWARE_MAJOR}_{FIRMWARE_MINOR}_{FIRMWARE_PATCH}.zip
        latest_version = file_name

        # remove file extension if exists
        if (id := latest_version.rfind('.')) != -1:
            latest_version = latest_version[:id]


        # unpack version
        try:
            model_id, firmware_major, firmware_minor, firmware_patch = latest_version.split('_')
            if all([
                firmware_major == Config.settings['FIRMWARE_MAJOR'],
                firmware_minor == Config.settings['FIRMWARE_MINOR'],
                firmware_patch == Config.settings['FIRMWARE_PATCH']
            ]):
                # no upgrade available
                return 0
            
            # upgrade available
            # download latest firmware
            if not UpgradeManager.download_firmware(file_name):
                # wasn't able to download
                return -1 
            # install latest firmware
            UpgradeManager.install_update()

        except Exception as e:
            print(f'Could not retrieve version information from file name: {file_name}')
            print(e)

            # no upgrade done
            return -1
