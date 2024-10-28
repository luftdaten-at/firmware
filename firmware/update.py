from firmware.code import Ugm
from wifi_client import WifiUtil
from config import Config

Config.init()
Config.settings['MODEL'] = 3

WifiUtil.connect()

print(Ugm.check_if_upgrade_available())

Ugm.download_firmware(Ugm.get_latest_firmware_version())
