import supervisor
from ugm.upgrade_mananger import Ugm
from ugm.upgrade_manager_util import Config, WifiUtil


Config.init(only_settings=True)
Ugm.init(None, Config)

# check rollback
if Config.settings['ROLLBACK']:
    print(f'Performe rollback, boot normally')

    Ugm.rollback()
    
    supervisor.set_next_code_file('main.py')
    supervisor.reload()

Config.init()
WifiUtil.connect()
Ugm.init(WifiUtil, Config)

# check if update available
if (folder := Ugm.check_if_upgrade_available()):
    print(f'Installing from folder: {folder}')
    try:
        Ugm.install_update(folder)
    except Exception as e:
        print(f'Upgrade failed: {e}')
        supervisor.reload()

print('load into main')

# boot normaly
supervisor.set_next_code_file('main.py')
supervisor.reload()
