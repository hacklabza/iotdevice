# This file is executed on every boot (including wake-boot from deepsleep)
import machine
import network
import time
import webrepl

import utils


def connect_wifi(wifi_config):
    wifi = network.WLAN(network.STA_IF)
    if not wifi.isconnected():
        print('Connecting to wifi...')
        wifi.active(True)
        essid = wifi_config['essid']
        wifi.connect(essid, wifi_config['password'])
        for i in range(wifi_config['retry_count']):
            if not wifi.isconnected():
                print(
                    'Connection attempt {count}/{retry_count}'.format(
                        count=i + 1, retry_count=wifi_config['retry_count']
                    )
                )
                time.sleep(5)
                if i == wifi_config['retry_count'] - 1:
                    print('Connection failed. Rebooting.')
            else:
                ip_address = wifi.ifconfig()[0]
                print(
                    'Connected to {essid} with IP: {ip_address}'.format(
                        essid=essid, ip_address=ip_address
                    )
                )
                break

    return wifi.isconnected()

CONFIG = utils.load_config()
WIFI_CONFIG = CONFIG['wifi']
MAIN_CONFIG = CONFIG['main']

# Connect to wifi if enabled
wifi_connected = connect_wifi(WIFI_CONFIG)

# Connect network dependant services
if wifi_connected:

    # Setup webrepl
    webrepl.start(password=MAIN_CONFIG['webrepl_password'])

else:
    machine.reset()
