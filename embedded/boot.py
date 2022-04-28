# This file is executed on every boot (including wake-boot from deepsleep)
import json
import gc
import machine
import network
import time
import webrepl

gc.collect()

def load_config():
    with open('config/config.json', 'r') as config_file:
        return json.loads(config_file.read())


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
                    print('Connection failed')
            else:
                ip_address = wifi.ifconfig()[0]
                print(
                    'Connected to {essid} with IP: {ip_address}'.format(
                        essid=essid, ip_address=ip_address
                    )
                )

                led_pin = machine.Signal(machine.Pin(2, machine.Pin.OUT), invert=True)
                led_pin.on()

                break

    return wifi.isconnected()


CONFIG = load_config()

# Connect to wifi if enabled
wifi_config = CONFIG['wifi']
wifi_connected = connect_wifi(wifi_config)

# Connect network dependant services
if wifi_connected:

    # Setup webrepl
    webrepl.start(password=CONFIG['main']['webrepl_password'])
