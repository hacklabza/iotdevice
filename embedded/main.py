import hashlib
import json
import ntptime
import machine
import time
import upip

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

# Device pin status state
PREVIOUS_STATE = None


def load_config():
    with open('config/config.json', 'r') as config_file:
        return json.loads(config_file.read())


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
            time.sleep(300)
            machine.reset()

    log_message(
        mqtt, 'Local time set to {now}'.format(now=time.localtime()), DEBUG
    )


def connect_mqtt(mqtt_config):
    try:
        from umqtt.simple import MQTTClient
    except ImportError:
        upip.install('micropython-umqtt.simple')
        from umqtt.simple import MQTTClient

    mqtt = MQTTClient(mqtt_config['client_id'], mqtt_config['host'])
    mqtt.connect()
    log_message(
        mqtt,
        'Connected to MQTT at {host}'.format(host=mqtt_config['host']),
        DEBUG
    )
    return mqtt


def publish_mqtt_message(mqtt, mqtt_queue, message):
    mqtt.publish(mqtt_queue, message)


def subscribe_mqtt_message(mqtt, mqtt_queue, callback):
    mqtt.set_callback(callback)
    mqtt.subscribe(mqtt_queue)
    mqtt.check_msg()


def log_message(mqtt, message, level):
    mqtt_config = CONFIG['mqtt']
    logging_config = CONFIG['logging']

    if LOG_LEVELS.index(level) >= LOG_LEVELS.index(logging_config['level']):
        mqtt_queue = 'iot-devices/{client_id}/logs'.format(
            client_id=mqtt_config['client_id']
        )
        publish_mqtt_message(mqtt, mqtt_queue, message)

    if logging_config['level'] in [INFO, DEBUG]:
        print(message)


def log_status(mqtt, status):
    global PREVIOUS_STATE

    mqtt_config = CONFIG['mqtt']
    mqtt_queue = 'iot-devices/{client_id}/status/'.format(
        client_id=mqtt_config['client_id']
    )

    if PREVIOUS_STATE != hashlib.sha1(status).digest():
        publish_mqtt_message(mqtt, mqtt_queue, status)

    PREVIOUS_STATE = hashlib.sha1(status).digest()


def run(mqtt, pin_config):

    log_message(mqtt, 'Device started.', DEBUG)

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
                ), invert=False)
        else:
            pins[pin['identifier']] = None

    run_count = 0
    while True:
        for pin in pin_config:
            rule = pin['rule']

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

                elif type(value) == dict:
                    rule_params[key] = value

                else:
                    if value in RULE_VALUES:
                        rule_params[key] = RULE_VALUES[value]
                    else:
                        rule_params[key] = value

            if run_count % pin.get('interval', 1) == 0:
                log_message(
                    mqtt,
                    'Running rule: {action} with input: {input}.'.format(
                        action=rule['action'], input=str(rule_params)
                    ),
                    DEBUG
                )

                # Add mqtt to rule params by default
                rule_params['mqtt'] = mqtt

                # Run the rule with the appropriate params and save the result to
                # rule values

                RULE_VALUES[pin['identifier']] = action(
                    pins[pin['identifier']], rule, **rule_params
                )

                log_message(
                    mqtt,
                    'Completed rule: {action} with output: {output}.'.format(
                        action=rule['action'],
                        output=RULE_VALUES[pin['identifier']]
                    ),
                    DEBUG
                )
            else:
                log_message(
                    mqtt,
                    'Skipping rule: {action} with input: {input}.'.format(
                        action=rule['action'], input=str(rule_params)
                    ),
                    DEBUG
                )

        log_status(mqtt, json.dumps(RULE_VALUES))

        time.sleep(CONFIG['main']['process_interval'])

        # Check if the config has been updated, reboot if it has
        if CONFIG != load_config():
            machine.reset()

        run_count += 1


if __name__ == '__main__':
    CONFIG = load_config()

    # Connects to the configured mqtt queue
    mqtt_config = CONFIG['mqtt']
    mqtt = connect_mqtt(mqtt_config)

    # Set the local time
    set_time(mqtt, CONFIG['time'])

    # Get the pin config and run the main method
    pin_config = CONFIG['pins']
    try:
        run(mqtt, pin_config)
    except Exception as exc:
        log_message(mqtt, str(exc), ERROR)
        time.sleep(300)
        machine.reset()
