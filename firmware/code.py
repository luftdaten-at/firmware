import supervisor
import board
import neopixel
from ugm.upgrade_mananger import Ugm
from ugm.wifi_client import WifiUtil
from ugm.config import Config
from logger import logger


Config.init()
Ugm.init(None, Config)

# check rollback
if Config.settings['ROLLBACK']:
    logger.warning('Performe rollback, boot normally')

    Ugm.rollback()
    
    supervisor.set_next_code_file('main.py')
    supervisor.reload()

Config.init()
WifiUtil.connect()
Ugm.init(WifiUtil, Config)

# check if update available
if WifiUtil.radio.connected and (folder := Ugm.check_if_upgrade_available()):
    # Assume model is AirStation
    status_led = neopixel.NeoPixel(board.IO8, 1)
    status_led[0] = (200, 0, 80)
    logger.debug(f'Installing new firmware from folder: {folder}')
    try:
        Ugm.install_update(folder)
    except Exception as e:
        logger.critical(f'Upgrade failed: {e}')
        supervisor.reload()

# boot normaly
supervisor.set_next_code_file('main.py')
supervisor.reload()
