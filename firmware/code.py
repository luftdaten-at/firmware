import supervisor
import board
import neopixel
from config import Config
from logger import logger
from ugm2.upgrade_mananger import Ugm
from wifi_client import WifiUtil
from energy_saving import should_skip_ota_on_wake

Config.init()
Ugm.init(None, Config)

# check rollback
if Config.settings['ROLLBACK']:
    logger.warning('Performe rollback, boot normally')

    Ugm.rollback()
    
    supervisor.set_next_code_file('main.py')
    supervisor.reload()

skip_ota = should_skip_ota_on_wake()
if skip_ota:
    logger.debug('Energy saving timed wake: skipping OTA check in code.py')

if not skip_ota:
    WifiUtil.connect()
    Ugm.init(WifiUtil, Config)
else:
    Ugm.init(None, Config)

# check if update available
if not skip_ota and WifiUtil.radio.connected and (folder := Ugm.check_if_upgrade_available()):
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
