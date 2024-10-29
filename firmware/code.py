import supervisor
from ugm.upgrade_mananger import Ugm
from ugm.upgrade_manager_util import Config, WifiUtil

Config.init()
WifiUtil.connect()
Ugm.init(WifiUtil, Config)

# check rollback
if Config.settings['ROLLBACK']:
    Ugm.rollback()
    print('Rollback not yet implemented. UPDATE FAILED!!!!!!')
    import sys
    sys.exit()

# check if update available
if (folder := Ugm.check_if_upgrade_available()):
    Ugm.install_update(folder)

print('load into main')

# boot normaly
supervisor.set_next_code_file('main.py')
supervisor.reload()
