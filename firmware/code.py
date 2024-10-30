import supervisor
from ugm.upgrade_mananger import Ugm
from ugm.upgrade_manager_util import Config, WifiUtil
from logger import logger


Config.init(only_settings=True)
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
if (folder := Ugm.check_if_upgrade_available()):
    logger.debug(f'Installing new firmware from folder: {folder}')
    try:
        Ugm.install_update(folder)
    except Exception as e:
        logger.critical(f'Upgrade failed: {e}')
        supervisor.reload()

# boot normaly
supervisor.set_next_code_file('main.py')
supervisor.reload()
