import hashlib
import json
import ntptime
import machine
import sys
import time
import upip

import rules

DEVICE_ID = None
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


def reset():
    time.sleep(60)
    machine.reset()


def set_time(mqtt, time_config):
    ntptime.host = time_config['server']
    try:
        ntptime.settime()
    except OSError:
        time.sleep(2)
        try:
            ntptime.settime()
        except Exception:
            log_message(
                mqtt, 'Could not retrieve local time. Retrying.', WARNING
            )
            reset()

    log_message(
        mqtt, 'Local time set to {now}'.format(now=time.localtime()), DEBUG
    )


def init_mqtt(mqtt_config):
    try:
        from umqtt.simple import MQTTClient
    except ImportError:
        upip.install('micropython-umqtt.simple')
        from umqtt.simple import MQTTClient

    mqtt = MQTTClient(
        client_id=mqtt_config['client_id'].format(identifier=DEVICE_ID),
        server=mqtt_config['host'],
        keepalive=mqtt_config.get('keepalive', 65535)
    )

    # Setup last will to detect when the device disconnects ungracefully
    lastwill = mqtt_config.get('lastwill')
    if lastwill:
        mqtt_config = CONFIG['mqtt']
        mqtt.set_last_will(
            topic=lastwill['topic'].format(identifier=DEVICE_ID),
            msg=lastwill['message']
        )

    mqtt.connect()

    log_message(
        mqtt,
        'Initilised MQTT Client at {host}'.format(host=mqtt_config['host']),
        DEBUG
    )

    return mqtt


def publish_mqtt_message(mqtt, mqtt_queue, message, retry_count=0):
    if retry_count > 0:
        mqtt.connect()
    try:
        mqtt.publish(mqtt_queue, message)
    except Exception:
        if retry_count <= 3:
            retry_count += 1
            publish_mqtt_message(mqtt, mqtt_queue, message, retry_count)
        else:
            raise Exception('MQTT Service is offline.')


def subscribe_mqtt_message(mqtt, mqtt_queue, callback, retry_count=0):
    if retry_count > 0:
        mqtt.connect()
    try:
        mqtt.set_callback(callback)
        mqtt.subscribe(mqtt_queue)
        mqtt.check_msg()
    except Exception:
        if retry_count <= 3:
            retry_count += 1
            subscribe_mqtt_message(mqtt, mqtt_queue, callback, retry_count)
        else:
            raise Exception('MQTT Service is offline.')


def log_message(mqtt, message, level):
    logging_config = CONFIG['logging']

    if not mqtt:
        print(message)
        return

    if LOG_LEVELS.index(level) >= LOG_LEVELS.index(logging_config['level']):
        mqtt_queue = 'iot-devices/{identifier}/logs'.format(
            identifier=DEVICE_ID
        )
        publish_mqtt_message(mqtt, mqtt_queue, message)

    if logging_config['level'] in [INFO, DEBUG]:
        print(message)


def log_status(mqtt, status):
    global PREVIOUS_STATE

    mqtt_queue = 'iot-devices/{identifier}/status/'.format(
        identifier=DEVICE_ID
    )

    if PREVIOUS_STATE != hashlib.sha1(status).digest():
        publish_mqtt_message(mqtt, mqtt_queue, status)

    PREVIOUS_STATE = hashlib.sha1(status).digest()


def health_check(mqtt):

    # Check Wifi connection
    rules.get_service_response(
        url=CONFIG['health']['url'].format(identifier=DEVICE_ID)
    )

    # Check MQTT connection
    mqtt.ping()


def find_xpath_value(response, xpaths):
    xpath = xpaths.pop()  # paths must be reversed before passing it in

    try:
        response = response[int(xpath)]
    except ValueError:
        response = response[xpath]
    except (KeyError, IndexError):
        return None

    if not len(xpaths):
        return response

    return find_xpath_value(response, xpaths)


def evaluate_condition(input, operator, value):
    try:
        if operator == 'eq':
            return input == value
        elif operator == 'gt':
            return input > value
        elif operator == 'lt':
            return input < value
    except TypeError:
        return False


def handle_conditions(rule_values, input_value):
    """
    Returns a dict of condition boolean values to be evaluated.
    """
    condition_values = {'must': [], 'should': []}
    for condition_type, conditions in input_value['conditions'].items():
        if condition_type in condition_values:
            for pin_identifier, condition in conditions.items():
                xpaths = pin_identifier.split('.')
                xpaths.reverse()
                condition_values[condition_type].append(
                    evaluate_condition(
                        find_xpath_value(rule_values, xpaths),
                        **condition
                    )
                )

    return condition_values


def get_i2c_pins(read):
    """
    Return scl, sda pins to be used in an i2c inteface.
    """
    pin_mode = machine.Pin.IN if read else machine.Pin.OUT
    return {
        'esp8266': (machine.Pin(5, pin_mode), machine.Pin(4, pin_mode)),
        'esp32': (machine.Pin(22, pin_mode), machine.Pin(21, pin_mode)),
    }[sys.platform]


def create_pins(pin_config):
    """
    Initialise pins based on the configured type.
    """
    pins = {}
    for pin in pin_config:

        # Ignore pin configs which don't have assigned pins, these are pin-less
        # rules
        if pin['pin_number']:

            # Setup the initial pin as in or out based on the config
            if pin['analog']:
                pins[pin['identifier']] = machine.ADC(
                    machine.Pin(pin['pin_number']),
                    atten=machine.ADC.ATTN_11DB
                )

            else:
                if pin['read']:
                    pins[pin['identifier']] = machine.Pin(
                        pin['pin_number'], machine.Pin.IN
                    )
                else:
                    pins[pin['identifier']] = machine.Signal(
                        machine.Pin(
                            pin['pin_number'], machine.Pin.OUT
                        ),
                        invert=False
                    )

        elif pin['i2c']:
            scl, sda = get_i2c_pins(read=pin['read'])
            pins[pin['identifier']] = machine.I2C(
                scl=scl, sda=sda, freq=100000
            )

        else:
            pins[pin['identifier']] = None

    return pins


def run(mqtt, pin_config):

    log_message(mqtt, 'Device started.', DEBUG)

    pins = create_pins(pin_config)

    run_count = 0
    while True:

        health_check(mqtt)

        for pin in pin_config:
            rule = pin['rule']

            # Get the rule action method
            action = getattr(rules, rule['action'])

            # Retrieve method parms including return values from previous
            # actions
            rule_params = {}
            for input_key, input_value in rule['input'].items():

                # Determine if the input contains a condition and evalute the
                # condition against the previously stored rule values.
                if type(input_value) == dict and 'conditions' in input_value:
                    condition_values = handle_conditions(
                        RULE_VALUES,
                        input_value
                    )
                    rule_params[input_key] = any([
                        all(condition_values['must']),
                        any(condition_values['should'])
                    ])

                else:
                    rule_params[input_key] = input_value

            if run_count % pin.get('interval', 1) == 0:
                log_message(
                    mqtt,
                    'Running rule: {action} with input: {input}.'.format(
                        action=rule['action'], input=str(rule_params)
                    ),
                    DEBUG
                )

                # Add mqtt and server config to rule params by default
                rule_params['mqtt'] = mqtt
                rule_params['config'] = CONFIG

                # Run the rule with the appropriate params and save the result
                # to rule values
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
            reset()

        run_count += 1


if __name__ == '__main__':

    CONFIG = load_config()
    DEVICE_ID = CONFIG['main']['identifier']

    # Get the pin config
    pin_config = CONFIG['pins']

    mqtt = None
    try:
        # Raise an exception if the device id is not set and wait for the
        # device to be configured in the server
        if not DEVICE_ID:
            raise Exception('Device not yet configured.')

        # Connects to the configured mqtt queue
        mqtt_config = CONFIG['mqtt']
        mqtt = init_mqtt(mqtt_config)

        # Set the local time
        set_time(mqtt, CONFIG['time'])

        # Run the rules
        run(mqtt, pin_config)

    except Exception as exc:
        log_message(mqtt, str(exc), ERROR)
        reset()
