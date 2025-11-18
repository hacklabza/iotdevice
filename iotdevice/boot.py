# This file is executed on every boot (including wake-boot from deepsleep)
import machine
import network
import time
import webrepl

import utils


CONFIG = utils.load_config()
WIFI_CONFIG = CONFIG['wifi']
MAIN_CONFIG = CONFIG['main']

# Connect to wifi if enabled
wifi_connected = utils.connect_wifi(WIFI_CONFIG)

# Connect network dependant services
if wifi_connected:

    # Setup webrepl
    webrepl.start(password=MAIN_CONFIG['webrepl_password'])

else:
    machine.reset()
