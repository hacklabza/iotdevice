import gc
import hashlib
import json
import ntptime
import machine
import sys
import time
import mip

import rules
import utils

# Log Levels
INFO = 'info'
DEBUG = 'debug'
WARNING = 'warning'
ERROR = 'error'

LOG_LEVELS = [INFO, DEBUG, WARNING, ERROR]

# Device pin status state
PREVIOUS_STATE = None


class Device:
    def __init__(self):
        self.config = utils.load_config()
        self.main_config = self.config['main']

        # Raise an exception if the device id is not set and wait for the
        # device to be configured in the server
        self.device_id = self.main_config.get('identifier')
        if not self.device_id:
            raise Exception('Device not yet configured.')

        # Set up logging config
        self.logging_config = self.config['logging']

        # Set up mqtt client
        self.mqtt_config = self.config['mqtt']
        self._init_mqtt(self.mqtt_config)

        # Set the local time on the device
        self.time_config = self.config['time']
        self._set_time()

        # Set health config
        self.health_config = self.config['health']

        # Set pin config
        self.pin_config = self.config['pins']
        self.pins = self._create_pins()

        # Set rule value cache
        self.rule_values = {}

        # Set cached previous state
        self._previous_state = None

        # Set the initial led status
        status_pin_numbers = self.health_config.get('leds', {})
        self.status_pins = {
            _status: machine.Pin(pin_number, machine.Pin.OUT)
            for _status, pin_number in status_pin_numbers.items()
        }
        self._set_led_status('ok')

    @property
    def previous_state(self):
        """
        Get the hashed previous state of the device pins.
        """
        return self._previous_state

    @previous_state.setter
    def previous_state(self, state):
        """
        Set the hashed previous state of the device pins."""
        if isinstance(state, bytes):
            self._previous_state = hashlib.sha1(state).digest()
        else:
            self._previous_state = hashlib.sha1(state.encode()).digest()

    def _set_led_status(self, status):
        """
        Set the status LED based on the current device health.
        """
        for _status, pin in self.status_pins.items():
            if status == _status:
                pin.on()
            else:
                pin.off()

    def _reset(self):
        """
        Reset the device after setting the led status to error.
        """
        self._set_led_status('error')
        time.sleep(60)
        machine.reset()

    def _init_mqtt(self, mqtt_config):
        """
        Initialize the MQTT client with the given configuration and set the last
        will message if provided.
        """
        try:
            from umqtt.simple import MQTTClient
        except ImportError:
            mip.install('micropython-umqtt.simple')
            from umqtt.simple import MQTTClient

        self.mqtt = MQTTClient(
            client_id=mqtt_config['client_id'].format(identifier=self.device_id),
            server=mqtt_config['host'],
            keepalive=mqtt_config.get('keepalive', 65535)
        )

        # Setup last will to detect when the device disconnects ungracefully
        lastwill = mqtt_config.get('lastwill')
        if lastwill:
            self.mqtt.set_last_will(
                topic=lastwill['topic'].format(identifier=self.device_id),
                msg=lastwill['message']
            )

        self.mqtt.connect()

        self._log_debug(
            'Initilised MQTT Client at {host}'.format(host=mqtt_config['host'])
        )

        return self.mqtt

    def _publish_mqtt_message(self, mqtt_queue, message, retry_count=0):
        """
        Publish a message to the specified MQTT queue and retry a limited number
        of times if necessary.
        """
        if retry_count > 0:
            self.mqtt.connect()
        try:
            self.mqtt.publish(mqtt_queue, message)
        except Exception:
            if retry_count <= 3:
                retry_count += 1
                self._publish_mqtt_message(mqtt_queue, message, retry_count)
            else:
                raise Exception('MQTT Service is offline.')

    def log_message(self, message, level):
        """
        Log a message to the MQTT logging queue based on the configured log level.
        """
        if not self.mqtt:
            print(message)
            return

        if LOG_LEVELS.index(level) >= LOG_LEVELS.index(self.logging_config['level']):
            mqtt_queue = 'iot-devices/{identifier}/logs'.format(
                identifier=self.device_id
            )
            self._publish_mqtt_message(mqtt_queue, message)

        if self.logging_config['level'] in [INFO, DEBUG]:
            print(message)

    def _log_info(self, message):
        """
        Log an info level message.
        """
        self.log_message(message, INFO)

    def _log_debug(self, message):
        """
        Log a debug level message.
        """
        self.log_message(message, DEBUG)

    def _log_warning(self, message):
        """
        Log a warning level message.
        """
        self.log_message(message, WARNING)

    def _log_error(self, message):
        """
        Log an error level message.
        """
        self.log_message(message, ERROR)

    def _log_status(self, status):
        """
        Log the current device status to the MQTT status queue if it has
        changed.
        """
        mqtt_queue = 'iot-devices/{identifier}/status/'.format(
            identifier=self.device_id
        )

        if self.previous_state != hashlib.sha1(status.encode()).digest():
            self._publish_mqtt_message(mqtt_queue, status)

        self.previous_state = status

    def _set_time(self):
        """
        Set the local time using the configured NTP server.
        """
        ntptime.host = self.time_config['server']
        try:
            ntptime.settime()
        except OSError:
            time.sleep(2)
            try:
                ntptime.settime()
            except Exception:
                self._log_warning('Could not retrieve local time. Retrying.')
                self._reset()

        self._log_debug('Local time set to {now}'.format(now=time.localtime()))

    def _cleanup_memory(self):
        """
        Periodic memory cleanup.
        """
        gc.collect()
        free_memory = gc.mem_free()
        if free_memory < 10000:  # Less than 10KB free
            self._log_warning(f'Low memory warning: {free_memory} bytes free')

    def _get_i2c_pins(self):
        """
        Return scl, sda pins to be used in an i2c inteface.
        """
        return {
            'esp8266': (machine.Pin(5), machine.Pin(4)),
            'esp32': (machine.Pin(22), machine.Pin(21)),
        }[sys.platform]

    def _create_pins(self):
        """
        Initialise pins based on the configured type.
        """
        pins = {}
        for pin in self.pin_config:

            # Ignore pin configs which don't have assigned pins, these are pin-
            # less rules
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
                scl, sda = self._get_i2c_pins()
                pins[pin['identifier']] = machine.SoftI2C(
                    scl=scl, sda=sda, freq=100_000
                )

            else:
                pins[pin['identifier']] = None

        return pins

    def health_check(self):
        """
        Perform health checks on the device's critical services.
        """

        # Check Wifi connection
        utils.get_service_response(
            url=self.health_config['url'].format(identifier=self.device_id)
        )

        # Check MQTT connection
        self.mqtt.ping()

    def run(self):
        """
        Main device loop. Continuously processes rules based on the configured
        pins and their intervals and sleeps for the configured process interval.
        """
        self._log_debug('Device started.')

        run_count = 0
        while True:

            # Perform health checks on each iteration
            self.health_check()

            # Set the status led
            self._set_led_status('ok')

            for pin in self.pin_config:
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
                        condition_values = utils.handle_conditions(
                            rule_values=self.rule_values,
                            input_value=input_value
                        )
                        rule_params[input_key] = any([
                            all(condition_values['must']),
                            any(condition_values['should'])
                        ])

                    else:
                        rule_params[input_key] = input_value

                # Check if the rule should be run or skipped based on the
                # configured pin interval
                if run_count % pin.get('interval', 1) == 0:
                    self._log_debug(
                        'Running rule: {action} with input: {input}.'.format(
                            action=rule['action'], input=str(rule_params)
                        )
                    )

                    # Add server config to rule params by default
                    rule_params['config'] = self.config

                    # Add mqtt client to rule params if required
                    if 'mqtt' in rule['action']:
                        rule_params['mqtt'] = self.mqtt

                    # Run the rule with the appropriate params and save the result
                    # to rule values
                    self.rule_values[pin['identifier']] = action(
                        self.pins[pin['identifier']], rule, **rule_params
                    )

                    self._log_debug(
                        'Completed rule: {action} with output: {output}.'.format(
                            action=rule['action'],
                            output=self.rule_values[pin['identifier']]
                        )
                    )
                else:
                    self._log_debug(
                        'Skipping rule: {action} with input: {input}.'.format(
                            action=rule['action'], input=str(rule_params)
                        )
                    )
            # Log the current device status
            self._log_status(json.dumps(self.rule_values))

            # Sleep for the configured process interval in seconds
            time.sleep(self.main_config['process_interval'])

            # Check if the config has been updated, reboot if it has
            if self.config != utils.load_config():
                self._reset()

            # Free up memory periodically
            if not run_count % self.main_config.get('memory_cleanup_interval', 100):
                self._cleanup_memory()

            run_count += 1


def handle_fatal_error(error_msg, device=None):
    """
    Handle fatal errors and reset the device.
    """
    if device:
        device.log_message(error_msg, ERROR)
    else:
        print(f'Fatal Error: {error_msg}')
    time.sleep(10)
    machine.reset()


if __name__ == '__main__':
    try:
        device = Device()
        device.run()
    except Exception as exc:
        handle_fatal_error(str(exc), getattr(locals(), 'device', None))
