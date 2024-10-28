import supervisor
from upgrade_mananger import Ugm, WifiUtil, Config

Config.init()
WifiUtil.connect()

# check rollback
if Config.settings['ROLLBACK']:
    Ugm.rollback()
    import sys
    sys.exit()

# check if update available
if (folder := Ugm.check_if_upgrade_available()):
    Ugm.install_update(folder)

print('load into main')

# boot normaly
supervisor.set_next_code_file('main.py')
supervisor.reload()
