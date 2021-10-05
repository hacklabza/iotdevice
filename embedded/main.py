import json
import network
import ntptime
import machine
import time
import upip

from umqtt.simple import MQTTClient

import rules


CONFIG = {}
RULE_VALUES = {}
MQTT_SUB_MSG = {}

# Log Levels
INFO = 'info'
DEBUG = 'debug'
WARNING = 'warning'
ERROR = 'error'

LOG_LEVELS = [INFO, DEBUG, WARNING, ERROR]


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


def set_time(mqtt, time_config):
    ntptime.host = time_config['server']
    try:
        ntptime.settime()
    except OSError:
        time.sleep(2)
        try:
            ntptime.settime()
        except:
            log_message(
                mqtt, 'Could not retrieve local time. Process aborted.', ERROR
            )

    log_message(
        mqtt, 'Local time set to {now}'.format(now=time.localtime()), DEBUG
    )


def connect_mqtt(mqtt_config):
    mqtt = MQTTClient(mqtt_config['client_id'], mqtt_config['host'])
    mqtt.connect()
    log_message(
        mqtt,
        'Connected to MQTT at {host}'.format(host=mqtt_config['host']),
        DEBUG
    )
    return mqtt


def publish_mqtt_message(mqtt, mqtt_config, mqtt_queue, message):
    try:
        mqtt.publish(mqtt_queue, message)
    except OSError:
        connect_mqtt(mqtt_config)
        mqtt.publish(mqtt_queue, message)


def log_message(mqtt, message, level):
    mqtt_config = CONFIG['mqtt']
    logging_config = CONFIG['logging']

    if LOG_LEVELS.index(level) >= LOG_LEVELS.index(logging_config['level']):
        mqtt_queue = 'iot-devices/{client_id}/logs'.format(
            client_id=mqtt_config['client_id']
        )
        publish_mqtt_message(mqtt, mqtt_config, mqtt_queue, message)

    if logging_config['level'] in [INFO, DEBUG]:
        print(message)


def log_status(mqtt, identifier, status):
    mqtt_config = CONFIG['mqtt']
    mqtt_queue = 'iot-devices/{client_id}/status/{identifier}'.format(
        client_id=mqtt_config['client_id'],
        identifier=identifier
    )
    publish_mqtt_message(mqtt, mqtt_config, mqtt_queue, status)


def run(mqtt, pin_config):
    log_message(mqtt, 'Started', DEBUG)
    pins = {}
    for pin in pin_config:

        # Ignore pin configs which don't have assigned pins, these are pin-less
        # rules
        if pin['pin_number']:

            # Setup the initial pin as in or out based on the config
            if pin['analog']:
                pins[pin['identifier']] = machine.ADC(pin['pin_number'])
            else:
                pins[pin['identifier']] = machine.Signal(machine.Pin(
                    pin['pin_number'],
                    machine.Pin.IN if pin['read'] else machine.Pin.OUT
                ), invert=True)
        else:
            pins[pin['identifier']] = None

    while True:
        for pin in pin_config:

            # Iterate over the rules and run them
            for rule in pin['rules']:

                # Get the rule action method
                action = getattr(rules, rule['action'])

                # Retrieve method parms including return values from previous
                # actions
                rule_params = {}
                for key, value in rule['input'].items():

                    # Determine if the input value is a return value from a
                    # previous action or set the static value
                    if type(value) == list:
                        value_items = value
                        operator = 'and'
                        values = []
                        for value_item in value_items:
                            if type(value_item) == list:
                                operator = 'or'
                                split_values = []
                                for v in value_item:
                                    split_values.append(
                                        RULE_VALUES[v]
                                    )
                                values.append(all(split_values))
                            else:
                                values.append(RULE_VALUES[value_item])

                        if operator == 'or':
                            rule_params[key] = any(values)
                        else:
                            rule_params[key] = all(values)

                    else:
                        if value in RULE_VALUES:
                            rule_params[key] = RULE_VALUES[value]
                        else:
                            rule_params[key] = value

                log_message(
                    mqtt,
                    'Running rule: {action} with input: {input}'.format(
                        action=rule['action'], input=str(rule_params)
                    ),
                    DEBUG
                )

                # Add mqtt to rule params by default
                rule_params['mqtt'] = mqtt

                # Run the rule with the appropriate params
                RULE_VALUES[pin['identifier']] = action(
                    pins[pin['identifier']], rule, **rule_params
                )

                log_message(
                    mqtt,
                    'Completed rule: {action} with output: {output}'.format(
                        action=rule['action'],
                        output=RULE_VALUES[pin['identifier']]
                    ),
                    DEBUG
                )

        log_status(mqtt, pin['identifier'], json.dumps(RULE_VALUES))

        time.sleep(CONFIG['main']['process_interval'])


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
        mqtt = connect_mqtt(CONFIG['mqtt'])

        # Set the local time
        set_time(mqtt, CONFIG['time'])

        # Get the pin config and run the main method
        pin_config = CONFIG['pins']
        run(mqtt, pin_config)
