from wifi_client import WifiUtil
from config import Config

class UpgradeManager:
    @staticmethod
    def get_latest_firmware_version():
        '''
        return: str: file_name if update available else None
        '''

        session = WifiUtil.new_session()
        url=f'{Config.settings['UPDATE_SERVER']}/{Config.settings['MODEL']}'

        try:
            response = session.request(
                method='GET',
                url=url,
            )

            if response.status_code != 200:
                print(f'Faild to find latest frimware version: {response.text}')
                return None
            else:
                # found latest version
                return response.text

        except Exception as e:
            print(e)
            return None

    @staticmethod
    def install_update(firmware_version: str):
        pass

    @staticmethod
    def check_and_install_upgrade():
        '''
        check if upgrade available for current device
        download upgrade if available
            install upgrade
        '''
        latest_version = UpgradeManager.get_latest_firmware_version()

        if latest_version is None:
            return 

        # unpack version 