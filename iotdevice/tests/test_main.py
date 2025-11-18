import unittest
import sys
import os
import hashlib
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock MicroPython-specific modules before importing main
sys.modules['ntptime'] = Mock()
sys.modules['machine'] = Mock()
sys.modules['mip'] = Mock()
sys.modules['gc'] = Mock()
sys.modules['network'] = Mock()
sys.modules['time'] = Mock()

import main


# Example config from README
EXAMPLE_CONFIG = {
    "wifi": {
        "essid": "TestNetwork",
        "password": "TestPassword",
        "retry_count": 10
    },
    "mqtt": {
        "client_id": "b6d49b8d-c31f-4809-a955-a814de6ab3f3",
        "host": "192.168.1.5",
        "username": None,
        "password": None,
        "ssl_enabled": False,
        "lastwill": {
            "topic": "iot-devices/b6d49b8d-c31f-4809-a955-a814de6ab3f3/logs",
            "message": "Device disconnected from MQTT"
        }
    },
    "logging": {
        "level": "warning"
    },
    "main": {
        "identifier": "b6d49b8d-c31f-4809-a955-a814de6ab3f3",
        "process_interval": 15,
        "webrepl_password": "ae3200ef1",
        "memory_cleanup_interval": 100
    },
    "time": {
        "server": "za.pool.ntp.org"
    },
    "health": {
        "url": "http://192.168.0.101:8000/health/b6d49b8d-c31f-4809-a955-a814de6ab3f3/",
        "leds": {
            "ok": 2,
            "error": 16
        }
    },
    "pins": [
        {
            "pin_number": None,
            "name": "Day Timer",
            "identifier": "day-timer",
            "analog": False,
            "read": True,
            "i2c": False,
            "interval": 1,
            "rule": {
                "action": "timer",
                "input": {
                    "gmt_start_time": "07:00",
                    "gmt_end_time": "15:00"
                }
            }
        },
        {
            "pin_number": 5,
            "name": "Soil Moisture Sensor",
            "identifier": "soil-moisture-sensor",
            "analog": False,
            "read": True,
            "i2c": False,
            "interval": 1,
            "rule": {
                "action": "read_bool_sample",
                "input": {
                    "reverse": True,
                    "sample_size": 5
                }
            }
        },
        {
            "pin_number": 4,
            "name": "Solenoid Relay",
            "identifier": "solenoid-relay",
            "analog": False,
            "read": False,
            "i2c": False,
            "interval": 1,
            "rule": {
                "action": "toggle",
                "input": {
                    "on": {
                        "conditions": {
                            "must": {
                                "soil-moisture-sensor": {
                                    "operator": "eq",
                                    "value": True
                                }
                            },
                            "should": {}
                        }
                    }
                }
            }
        }
    ]
}


def create_mock_device(config=None):
    """Helper function to create a mocked Device instance for testing"""
    if config is None:
        config = EXAMPLE_CONFIG

    with patch('main.utils.load_config', return_value=config), \
         patch('main.machine') as mock_machine, \
         patch('main.ntptime') as mock_ntptime, \
         patch('main.sys.platform', 'esp8266'), \
         patch('builtins.print'):

        # Set up machine mock attributes
        mock_machine.Pin.IN = 0
        mock_machine.Pin.OUT = 1
        mock_machine.ADC.ATTN_11DB = 3

        # Mock MQTT client
        mock_mqtt_client = Mock()
        with patch.dict('sys.modules', {'umqtt.simple': Mock(MQTTClient=Mock(return_value=mock_mqtt_client))}):
            device = main.Device()
            return device, mock_mqtt_client, mock_machine


class TestDeviceInitialization(unittest.TestCase):
    """Test cases for Device class initialization"""

    def test_device_init_success(self):
        """Test successful device initialization with valid config"""
        device, mock_mqtt, _ = create_mock_device()

        self.assertEqual(device.device_id, 'b6d49b8d-c31f-4809-a955-a814de6ab3f3')
        self.assertEqual(device.config, EXAMPLE_CONFIG)
        self.assertIsNotNone(device.mqtt)
        self.assertEqual(device.rule_values, {})
        self.assertIsNone(device.previous_state)

    def test_device_init_no_identifier_raises_exception(self):
        """Test device initialization fails when identifier is missing"""
        config = EXAMPLE_CONFIG.copy()
        config['main'] = {'identifier': None}

        with patch('main.utils.load_config', return_value=config):
            with self.assertRaises(Exception) as context:
                main.Device()

            self.assertEqual(str(context.exception), 'Device not yet configured.')

    def test_previous_state_property_getter_setter(self):
        """Test previous_state property getter and setter work correctly"""
        device, _, _ = create_mock_device()

        test_state = b'{"test": "state"}'
        device.previous_state = test_state

        expected_hash = hashlib.sha1(test_state).digest()
        self.assertEqual(device.previous_state, expected_hash)


class TestMqttInitialization(unittest.TestCase):
    """Test cases for MQTT initialization with last will"""

    def test_mqtt_init_with_lastwill(self):
        """Test MQTT initialization sets last will when configured"""
        config = EXAMPLE_CONFIG.copy()
        config['mqtt']['lastwill'] = {
            'topic': 'iot-devices/{identifier}/status',
            'message': 'Device offline'
        }

        with patch('main.utils.load_config', return_value=config), \
             patch('main.machine') as mock_machine, \
             patch('main.ntptime'), \
             patch('builtins.print'):

            mock_machine.Pin.IN = 0
            mock_machine.Pin.OUT = 1
            mock_machine.ADC.ATTN_11DB = 3

            mock_mqtt_client = Mock()
            with patch.dict('sys.modules', {'umqtt.simple': Mock(MQTTClient=Mock(return_value=mock_mqtt_client))}):
                device = main.Device()

                # Verify set_last_will was called with the correct formatted topic and message
                mock_mqtt_client.set_last_will.assert_called_once_with(
                    topic='iot-devices/b6d49b8d-c31f-4809-a955-a814de6ab3f3/status',
                    msg='Device offline'
                )
                mock_mqtt_client.connect.assert_called()

    def test_mqtt_init_without_lastwill(self):
        """Test MQTT initialization skips last will when not configured"""
        config = EXAMPLE_CONFIG.copy()
        config['mqtt'].pop('lastwill', None)  # Remove lastwill config

        with patch('main.utils.load_config', return_value=config), \
             patch('main.machine') as mock_machine, \
             patch('main.ntptime'), \
             patch('builtins.print'):

            mock_machine.Pin.IN = 0
            mock_machine.Pin.OUT = 1
            mock_machine.ADC.ATTN_11DB = 3

            mock_mqtt_client = Mock()
            with patch.dict('sys.modules', {'umqtt.simple': Mock(MQTTClient=Mock(return_value=mock_mqtt_client))}):
                device = main.Device()

                # Verify set_last_will was NOT called
                mock_mqtt_client.set_last_will.assert_not_called()
                mock_mqtt_client.connect.assert_called()

    def test_mqtt_init_with_lastwill_none(self):
        """Test MQTT initialization skips last will when explicitly set to None"""
        config = EXAMPLE_CONFIG.copy()
        config['mqtt']['lastwill'] = None

        with patch('main.utils.load_config', return_value=config), \
             patch('main.machine') as mock_machine, \
             patch('main.ntptime'), \
             patch('builtins.print'):

            mock_machine.Pin.IN = 0
            mock_machine.Pin.OUT = 1
            mock_machine.ADC.ATTN_11DB = 3

            mock_mqtt_client = Mock()
            with patch.dict('sys.modules', {'umqtt.simple': Mock(MQTTClient=Mock(return_value=mock_mqtt_client))}):
                device = main.Device()

                # Verify set_last_will was NOT called
                mock_mqtt_client.set_last_will.assert_not_called()
                mock_mqtt_client.connect.assert_called()

    def test_mqtt_init_import_error_installs_package(self):
        """Test MQTT initialization installs package on ImportError"""
        config = EXAMPLE_CONFIG.copy()

        with patch('main.utils.load_config', return_value=config), \
             patch('main.machine') as mock_machine, \
             patch('main.ntptime'), \
             patch('main.mip') as mock_mip, \
             patch('builtins.print'):

            mock_machine.Pin.IN = 0
            mock_machine.Pin.OUT = 1
            mock_machine.ADC.ATTN_11DB = 3

            # Simulate ImportError on first import
            mock_mqtt_client = Mock()
            umqtt_module = Mock(MQTTClient=Mock(return_value=mock_mqtt_client))

            with patch.dict('sys.modules', {'umqtt.simple': None}):
                # First import fails, then succeeds after install
                with patch('builtins.__import__', side_effect=[ImportError, umqtt_module]):
                    with patch.dict('sys.modules', {'umqtt': Mock(), 'umqtt.simple': umqtt_module}):
                        device = main.Device()

                        # Verify mip.install was called
                        mock_mip.install.assert_called_with('micropython-umqtt.simple')
                        mock_mqtt_client.connect.assert_called()


class TestDeviceLedStatus(unittest.TestCase):
    """Test cases for LED status management"""

    def test_set_led_status_ok(self):
        """Test setting LED status to 'ok' turns on ok LED and off error LED"""
        device, _, _ = create_mock_device()

        # Mock the status pins
        mock_pin_ok = Mock()
        mock_pin_error = Mock()
        device.status_pins = {'ok': mock_pin_ok, 'error': mock_pin_error}

        device._set_led_status('ok')

        mock_pin_ok.on.assert_called_once()
        mock_pin_error.off.assert_called_once()

    def test_set_led_status_error(self):
        """Test setting LED status to 'error' turns off ok LED and on error LED"""
        device, _, _ = create_mock_device()

        # Mock the status pins
        mock_pin_ok = Mock()
        mock_pin_error = Mock()
        device.status_pins = {'ok': mock_pin_ok, 'error': mock_pin_error}

        device._set_led_status('error')

        mock_pin_ok.off.assert_called_once()
        mock_pin_error.on.assert_called_once()


class TestDeviceReset(unittest.TestCase):
    """Test cases for device reset functionality"""

    @patch('main.time.sleep')
    @patch('main.machine.reset')
    def test_reset_sleeps_and_resets_machine(self, mock_reset, mock_sleep):
        """Test device reset waits 60 seconds then resets machine"""
        device, _, _ = create_mock_device()

        device._reset()

        mock_sleep.assert_called_once_with(60)
        mock_reset.assert_called_once()

class TestMqttPublishing(unittest.TestCase):
    """Test cases for MQTT message publishing"""

    def test_publish_mqtt_message_success(self):
        """Test successful MQTT message publishing"""
        device, mock_mqtt, _ = create_mock_device()

        device._publish_mqtt_message('test/topic', 'test message')

        mock_mqtt.publish.assert_called_once_with('test/topic', 'test message')

    def test_publish_mqtt_message_retry_on_failure(self):
        """Test MQTT publish retries on failure and eventually succeeds"""
        device, mock_mqtt, _ = create_mock_device()

        # Reset connect call count after device init
        mock_mqtt.connect.reset_mock()

        mock_mqtt.publish.side_effect = [Exception('connection error'), None]
        device._publish_mqtt_message('test/topic', 'test message')

        # Should reconnect once and publish twice
        mock_mqtt.connect.assert_called_once()
        self.assertEqual(mock_mqtt.publish.call_count, 2)

    def test_publish_mqtt_message_max_retries_exceeded(self):
        """Test MQTT publish raises exception after max retries"""
        device, mock_mqtt, _ = create_mock_device()

        # Reset connect call count after device init
        mock_mqtt.connect.reset_mock()

        mock_mqtt.publish.side_effect = Exception('connection error')

        with self.assertRaises(Exception) as context:
            device._publish_mqtt_message('test/topic', 'test message')

        self.assertEqual(str(context.exception), 'MQTT Service is offline.')
        # Should have reconnected 4 times (retries 1, 2, 3, 4)
        self.assertEqual(mock_mqtt.connect.call_count, 4)


class TestLogging(unittest.TestCase):
    """Test cases for logging functionality"""

    def test_log_message_below_configured_level_not_published(self):
        """Test messages below configured level are not published to MQTT"""
        device, mock_mqtt, _ = create_mock_device()

        device.log_message('Test info message', main.INFO)

        # INFO is below WARNING, should not publish
        mock_mqtt.publish.assert_not_called()

    def test_log_message_at_configured_level_is_published(self):
        """Test messages at or above configured level are published"""
        device, mock_mqtt, _ = create_mock_device()

        device.log_message('Test warning message', main.WARNING)

        # WARNING matches configured level, should publish
        mock_mqtt.publish.assert_called_once()

    def test_log_message_above_configured_level_is_published(self):
        """Test messages above configured level are published"""
        device, mock_mqtt, _ = create_mock_device()

        device.log_message('Test error message', main.ERROR)

        # ERROR is above WARNING, should publish
        mock_mqtt.publish.assert_called_once()

    def test_log_info_wrapper(self):
        """Test _log_info wrapper method"""
        device, mock_mqtt, _ = create_mock_device()

        device._log_info('Info message')

        # INFO is below WARNING, should not publish
        mock_mqtt.publish.assert_not_called()

    def test_log_debug_wrapper(self):
        """Test _log_debug wrapper method"""
        device, mock_mqtt, _ = create_mock_device()

        device._log_debug('Debug message')

        # DEBUG is below WARNING, should not publish
        mock_mqtt.publish.assert_not_called()

    def test_log_warning_wrapper(self):
        """Test _log_warning wrapper method"""
        device, mock_mqtt, _ = create_mock_device()

        # Reset call count after device initialization
        mock_mqtt.publish.reset_mock()

        device._log_warning('Warning message')

        # WARNING matches configured level, should publish
        mock_mqtt.publish.assert_called_once()

    def test_log_error_wrapper(self):
        """Test _log_error wrapper method"""
        device, mock_mqtt, _ = create_mock_device()

        # Reset call count after device initialization
        mock_mqtt.publish.reset_mock()

        device._log_error('Warning message')

        # WARNING matches configured level, should publish
        mock_mqtt.publish.assert_called_once()

    @patch('builtins.print')
    def test_log_message_without_mqtt(self, mock_print):
        """Test log_message prints to console when mqtt is None"""
        device, _, _ = create_mock_device()
        device.mqtt = None

        device.log_message('Test message', main.INFO)

        mock_print.assert_called_with('Test message')

    @patch('builtins.print')
    def test_log_message_prints_in_debug_mode(self, mock_print):
        """Test log_message prints to console when level is DEBUG"""
        config = EXAMPLE_CONFIG.copy()
        config['logging']['level'] = 'debug'
        device, _, _ = create_mock_device(config)

        device.log_message('Debug message', main.DEBUG)

        mock_print.assert_called()

    @patch('builtins.print')
    def test_log_message_prints_in_info_mode(self, mock_print):
        """Test log_message prints to console when level is INFO"""
        config = EXAMPLE_CONFIG.copy()
        config['logging']['level'] = 'info'
        device, _, _ = create_mock_device(config)

        device.log_message('Info message', main.INFO)

        mock_print.assert_called()


class TestStatusLogging(unittest.TestCase):
    """Test cases for status logging"""

    def test_log_status_first_time_is_published(self):
        """Test first status is published"""
        device, mock_mqtt, _ = create_mock_device()

        # Reset call count after device initialization
        mock_mqtt.publish.reset_mock()

        device._log_status('{"state": "active"}')

        mock_mqtt.publish.assert_called_once()

    def test_log_status_unchanged_not_published(self):
        """Test unchanged status is not published again"""
        device, mock_mqtt, _ = create_mock_device()

        status = '{"state": "active"}'
        device._log_status(status)
        mock_mqtt.reset_mock()
        device._log_status(status)

        # Same status should not be published again
        mock_mqtt.publish.assert_not_called()

    def test_log_status_changed_is_published(self):
        """Test changed status is published"""
        device, mock_mqtt, _ = create_mock_device()

        device._log_status('{"state": "active"}')
        mock_mqtt.reset_mock()
        device._log_status('{"state": "inactive"}')

        # Changed status should be published
        mock_mqtt.publish.assert_called_once()


class TestTimeSettings(unittest.TestCase):
    """Test cases for time synchronization"""

    @patch('main.time.localtime')
    def test_set_time_success(self, mock_localtime):
        """Test successful time setting from NTP server"""
        mock_localtime.return_value = (2025, 11, 13, 14, 30, 0, 0, 0)

        with patch('main.utils.load_config', return_value=EXAMPLE_CONFIG), \
             patch('main.machine') as mock_machine, \
             patch('main.ntptime') as mock_ntptime, \
             patch('builtins.print'):

            # Set up machine mock attributes
            mock_machine.Pin.IN = 0
            mock_machine.Pin.OUT = 1
            mock_machine.ADC.ATTN_11DB = 3

            # Mock MQTT client
            mock_mqtt_client = Mock()
            with patch.dict('sys.modules', {'umqtt.simple': Mock(MQTTClient=Mock(return_value=mock_mqtt_client))}):
                device = main.Device()

                # Verify NTP server was set and settime was called
                self.assertEqual(mock_ntptime.host, 'za.pool.ntp.org')
                mock_ntptime.settime.assert_called()

    @patch('main.time.localtime')
    @patch('main.time.sleep')
    def test_set_time_retry_on_oserror(self, mock_sleep, mock_localtime):
        """Test time setting retries on OSError"""
        mock_localtime.return_value = (2025, 11, 13, 14, 30, 0, 0, 0)

        with patch('main.utils.load_config', return_value=EXAMPLE_CONFIG), \
             patch('main.machine') as mock_machine, \
             patch('main.ntptime') as mock_ntptime, \
             patch('builtins.print'):

            # Set up machine mock attributes
            mock_machine.Pin.IN = 0
            mock_machine.Pin.OUT = 1
            mock_machine.ADC.ATTN_11DB = 3

            # First call raises OSError, second succeeds
            mock_ntptime.settime.side_effect = [OSError('Network error'), None]

            # Mock MQTT client
            mock_mqtt_client = Mock()
            with patch.dict('sys.modules', {'umqtt.simple': Mock(MQTTClient=Mock(return_value=mock_mqtt_client))}):
                device = main.Device()

                # Should have retried
                self.assertEqual(mock_ntptime.settime.call_count, 2)
                mock_sleep.assert_called_once_with(2)

    @patch('main.time.localtime')
    @patch('main.time.sleep')
    def test_set_time_exception_resets_device(self, mock_sleep, mock_localtime):
        """Test time setting resets device on repeated failure"""
        mock_localtime.return_value = (2025, 11, 13, 14, 30, 0, 0, 0)

        with patch('main.utils.load_config', return_value=EXAMPLE_CONFIG), \
             patch('main.machine') as mock_machine, \
             patch('main.ntptime') as mock_ntptime:

            mock_machine.Pin.IN = 0
            mock_machine.Pin.OUT = 1
            mock_machine.ADC.ATTN_11DB = 3

            # First call raises OSError, second call raises generic Exception
            mock_ntptime.settime.side_effect = [OSError('Network error'), Exception('Fatal error')]

            # Mock MQTT client
            mock_mqtt_client = Mock()
            with patch.dict('sys.modules', {'umqtt.simple': Mock(MQTTClient=Mock(return_value=mock_mqtt_client))}):
                with patch.object(main.Device, '_reset') as mock_reset:
                    with patch.object(main.Device, '_log_warning'):
                        device = main.Device()

                        # Should have called reset after logging warning
                        mock_reset.assert_called_once()


class TestMemoryManagement(unittest.TestCase):
    """Test cases for memory cleanup"""

    @patch('main.gc')
    def test_cleanup_memory_with_low_memory_logs_warning(self, mock_gc):
        """Test memory cleanup logs warning when memory is low"""
        mock_gc.mem_free.return_value = 5000  # Less than 10KB

        device, mock_mqtt, _ = create_mock_device()
        device._cleanup_memory()

        mock_gc.collect.assert_called_once()
        # Should log warning about low memory
        mock_mqtt.publish.assert_called()

    @patch('main.gc')
    def test_cleanup_memory_with_normal_memory(self, mock_gc):
        """Test memory cleanup with sufficient memory"""
        mock_gc.mem_free.return_value = 50000  # More than 10KB

        device, _, _ = create_mock_device()
        device._cleanup_memory()

        mock_gc.collect.assert_called_once()


class TestI2cPins(unittest.TestCase):
    """Test cases for I2C pin configuration"""

    @patch('main.sys.platform', 'esp8266')
    def test_get_i2c_pins_esp8266(self):
        """Test I2C pins for ESP8266 platform"""
        device, _, mock_machine = create_mock_device()

        scl, sda = device._get_i2c_pins()

        # Should have created pins (5 for SCL, 4 for SDA on ESP8266)
        self.assertTrue(mock_machine.Pin.call_count >= 2)

    @patch('main.sys.platform', 'esp32')
    def test_get_i2c_pins_esp32(self):
        """Test I2C pins for ESP32 platform"""
        device, _, mock_machine = create_mock_device()

        scl, sda = device._get_i2c_pins()

        # Should have created pins (22 for SCL, 21 for SDA on ESP32)
        self.assertTrue(mock_machine.Pin.call_count >= 2)


class TestPinCreation(unittest.TestCase):
    """Test cases for pin creation and initialization"""

    def test_create_pins_includes_all_configured_pins(self):
        """Test all pins from config are created"""
        device, _, _ = create_mock_device()

        # Should have created pins for all identifiers in config
        self.assertIn('day-timer', device.pins)
        self.assertIn('soil-moisture-sensor', device.pins)
        self.assertIn('solenoid-relay', device.pins)

    def test_create_pins_without_pin_number_is_none(self):
        """Test pins without pin numbers are set to None"""
        device, _, _ = create_mock_device()

        # day-timer has no pin_number, should be None
        self.assertIsNone(device.pins['day-timer'])

    def test_create_pins_digital_input(self):
        """Test digital input pin creation"""
        device, _, mock_machine = create_mock_device()

        # soil-moisture-sensor is digital input (read=True, analog=False)
        self.assertIsNotNone(device.pins['soil-moisture-sensor'])

    def test_create_pins_digital_output(self):
        """Test digital output pin creation"""
        device, _, mock_machine = create_mock_device()

        # solenoid-relay is digital output (read=False, analog=False)
        self.assertIsNotNone(device.pins['solenoid-relay'])

    def test_create_pins_analog_input(self):
        """Test analog pin is created with ADC"""
        import copy
        config = copy.deepcopy(EXAMPLE_CONFIG)
        config['pins'].append({
            "pin_number": 36,
            "name": "Analog Sensor",
            "identifier": "analog-sensor",
            "analog": True,
            "read": True,
            "i2c": False,
            "interval": 1,
            "rule": {"action": "read_analog", "input": {}}
        })

        device, _, mock_machine = create_mock_device(config)

        # Should have created an ADC pin
        self.assertIn('analog-sensor', device.pins)
        mock_machine.ADC.assert_called()

    def test_create_pins_i2c_interface(self):
        """Test I2C interface pin is created"""
        import copy
        config = copy.deepcopy(EXAMPLE_CONFIG)
        config['pins'].append({
            "pin_number": None,
            "name": "I2C Sensor",
            "identifier": "i2c-sensor",
            "analog": False,
            "read": True,
            "i2c": True,
            "interval": 1,
            "rule": {"action": "read_bmp180", "input": {}}
        })

        with patch('main.sys.platform', 'esp8266'):
            device, _, mock_machine = create_mock_device(config)

            # Should have created a SoftI2C interface
            self.assertIn('i2c-sensor', device.pins)
            mock_machine.SoftI2C.assert_called()


class TestHealthCheck(unittest.TestCase):
    """Test cases for health check functionality"""

    @patch('main.utils.get_service_response')
    def test_health_check_calls_service_and_mqtt_ping(self, mock_get_service):
        """Test health check calls both service endpoint and MQTT ping"""
        mock_get_service.return_value = {"status": "ok"}

        device, mock_mqtt, _ = create_mock_device()
        device.health_check()

        # Should call health service endpoint
        mock_get_service.assert_called_once_with(
            url='http://192.168.0.101:8000/health/b6d49b8d-c31f-4809-a955-a814de6ab3f3/'
        )
        # Should ping MQTT broker
        mock_mqtt.ping.assert_called_once()


class TestHandleFatalError(unittest.TestCase):
    """Test cases for fatal error handling"""

    @patch('main.machine.reset')
    @patch('main.time.sleep')
    @patch('builtins.print')
    def test_handle_fatal_error_without_device(self, mock_print, mock_sleep, mock_reset):
        """Test fatal error handling when device is not available"""
        main.handle_fatal_error('Critical error occurred')

        mock_print.assert_called_once_with('Fatal Error: Critical error occurred')
        mock_sleep.assert_called_once_with(10)
        mock_reset.assert_called_once()

    @patch('main.time.sleep')
    @patch('main.machine.reset')
    def test_handle_fatal_error_with_device(self, mock_reset, mock_sleep):
        """Test fatal error handling when device is available"""
        device, mock_mqtt, _ = create_mock_device()

        main.handle_fatal_error('Critical error occurred', device)

        # Should log error via MQTT
        mock_mqtt.publish.assert_called()
        mock_sleep.assert_called_once_with(10)
        mock_reset.assert_called_once()


class TestRunLoop(unittest.TestCase):
    """Tests for the main run() loop"""

    def test_run_single_iteration_updates_rule_values(self):
        """run() executes one iteration and updates rule_values for all pins"""
        # Arrange device
        device, _, _ = create_mock_device()

        # Patch rule actions to deterministic values
        with patch('main.rules.timer', return_value=True) as mock_timer, \
             patch('main.rules.read_bool_sample', return_value=False) as mock_read_bool_sample, \
             patch('main.rules.toggle', return_value='on') as mock_toggle, \
             patch.object(device, 'health_check'), \
             patch.object(device, '_set_led_status'), \
             patch('main.utils.load_config', return_value=EXAMPLE_CONFIG), \
             patch('main.time.sleep', side_effect=StopIteration):

            # Act: break the infinite loop by raising StopIteration on sleep
            with self.assertRaises(StopIteration):
                device.run()

        # Assert rule values were set from actions
        self.assertIn('day-timer', device.rule_values)
        self.assertIn('soil-moisture-sensor', device.rule_values)
        self.assertIn('solenoid-relay', device.rule_values)
        self.assertTrue(device.rule_values['day-timer'])
        self.assertFalse(device.rule_values['soil-moisture-sensor'])
        self.assertEqual(device.rule_values['solenoid-relay'], 'on')

        # Ensure actions were called once in the single iteration
        mock_timer.assert_called_once()
        mock_read_bool_sample.assert_called_once()
        mock_toggle.assert_called_once()

    def test_run_skips_rules_based_on_interval(self):
        """run() performs skip branch for pins with higher interval on second iteration"""
        import copy
        config = copy.deepcopy(EXAMPLE_CONFIG)
        # Set day-timer to run every 2 iterations so it will be skipped on the second
        config['pins'][0]['interval'] = 2

        # Create device with modified config
        device, _, _ = create_mock_device(config)

        with patch('main.rules.timer', return_value=True) as mock_timer, \
             patch('main.rules.read_bool_sample', return_value=True) as mock_read_bool_sample, \
             patch('main.rules.toggle', return_value=True) as mock_toggle, \
             patch.object(device, 'health_check'), \
             patch.object(device, '_set_led_status'), \
             patch.object(device, '_cleanup_memory'), \
             patch('main.utils.load_config', return_value=config), \
             patch('main.time.sleep', side_effect=[None, StopIteration]):

            # Two iterations: first completes, second raises to exit
            with self.assertRaises(StopIteration):
                device.run()

        # day-timer (interval=2) should have run only once, others twice
        self.assertEqual(mock_timer.call_count, 1)
        self.assertEqual(mock_read_bool_sample.call_count, 2)
        self.assertEqual(mock_toggle.call_count, 2)

    def test_run_triggers_reset_on_config_change(self):
        """run() calls _reset when config changes between iterations"""
        import copy
        base = copy.deepcopy(EXAMPLE_CONFIG)
        changed = copy.deepcopy(EXAMPLE_CONFIG)
        changed['main']['process_interval'] = 30  # any change to make dict differ

        device, _, _ = create_mock_device(base)

        with patch('main.rules.timer', return_value=True), \
             patch('main.rules.read_bool_sample', return_value=True), \
             patch('main.rules.toggle', return_value=True), \
             patch.object(device, 'health_check'), \
             patch.object(device, '_set_led_status'), \
             patch.object(device, '_cleanup_memory'), \
             patch.object(device, '_reset') as mock_reset, \
             patch('main.utils.load_config', side_effect=[changed, changed]), \
             patch('main.time.sleep', side_effect=[None, StopIteration]):

            with self.assertRaises(StopIteration):
                device.run()

        mock_reset.assert_called_once()


if __name__ == '__main__':
    unittest.main()
