import json
import network
import machine
import time
import upip

from umqtt.simple import MQTTClient


CONFIG = {}
RULE_VALUES = {}


def load_config():
    with open('config/config.json', 'r') as config_file:
        return json.loads(config_file.read())


def install_deps():
    with open('config/requirements.upip.txt', 'r') as requirements_file:
        for requirement in requirements_file:
            requirement = requirement.replace('\n', '')
            if requirement:
                print(
                    'Installing {requirement}'.format(requirement=requirement)
                )
                upip.install(requirement)


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
                time.sleep(10)
                if i == wifi_config['retry_count'] - 1:
                    print('Connection failed')
            else:
                ip_address = wifi.ifconfig()[0]
                print(
                    'Connected to {essid} with IP: {ip_address}'.format(
                        essid=essid, ip_address=ip_address
                    )
                )
                break

    return wifi.isconnected()


def connect_mqtt(mqtt_config):
    mqtt = MQTTClient(mqtt_config['client_id'], mqtt_config['host'])
    mqtt.connect()
    return mqtt


def read_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        print(pin.value())
        readings.append(pin.value())
        time.sleep(1)
    return all(readings)


def toggle(pin, rule, **kwargs):
    off = kwargs.get('off')
    pin.off() if off else pin.on()
    return pin.value()


def run(mqtt, pin_config):
    print('Started...')
    pins = {}
    for pin in pin_config:

        # Setup the initial pin as in or out based on the config
        pins[pin['identifier']] = machine.Signal(machine.Pin(
            pin['pin_number'],
            machine.Pin.IN if pin['read'] else machine.Pin.OUT
        ), invert=True)

    while True:

        for pin in pin_config:

            # Iterate over the rules and run them
            for rule in pin['rules']:

                # Get the rule action method
                action = globals()[rule['action']]

                # Retrieve method parms including return values from previous
                # actions
                rule_params = {}
                for key, value in rule['input'].items():

                    # Determine if the iput value is a return value from a
                    # previous action or set the static value
                    if value in RULE_VALUES:
                        rule_params[key] = RULE_VALUES.get(value, value)
                    else:
                        rule_params[key] = RULE_VALUES.get(key, value)

                print(
                    'Running rule: {action} with input: {input}'.format(
                        action=rule['action'], input=str(rule_params)
                    )
                )

                # Run the rule with the appropriate params
                RULE_VALUES[pin['identifier']] = action(
                    pins[pin['identifier']], rule, **rule_params
                )

                print(
                    'Completed rule: {action} with output: {output}'.format(
                        action=rule['action'],
                        output=RULE_VALUES[pin['identifier']]
                    )
                )

        time.sleep(15)


if __name__ == '__main__':
    CONFIG = load_config()

    # Connect to wifi if enabled
    wifi_config = CONFIG['wifi']
    wifi_connected = connect_wifi(wifi_config)

    # Connect network dependant services
    if wifi_connected:

        # Install all dependancies
        install_deps()

        # Connects to the configured mqtt queue
        mqtt_config = CONFIG['mqtt']
        mqtt = connect_mqtt(mqtt_config)

        # Get the pin config and run the main method
        pin_config = CONFIG['pins']
        run(mqtt, pin_config)
