from wifi_client import WifiUtil
from config import Config

class UpgradeManager:
    @staticmethod
    def check_for_update():
        '''
        return: str: file_name if update available else None
        '''

        session = WifiUtil.new_session()
        url=f'{Config.settings['UPDATE_SERVER']}/{Config.settings['MODEL']}'
        print(f'{url=}')
        response = session.request(
            method='GET',
            url=url,
        )

        print(f'Response: {response.status_code}')
        print(f'Response: {response.text}')

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
        UpgradeManager.check_for_update()

        pass