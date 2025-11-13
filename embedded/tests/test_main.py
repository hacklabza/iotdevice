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

        device._log_warning('Warning message')

        # WARNING matches configured level, should publish
        mock_mqtt.publish.assert_called_once()

    def test_log_error_wrapper(self):
        """Test _log_error wrapper method"""
        device, mock_mqtt, _ = create_mock_device()

        device._log_error('Error message')

        # ERROR is above WARNING, should publish
        mock_mqtt.publish.assert_called_once()


class TestStatusLogging(unittest.TestCase):
    """Test cases for status logging"""

    def test_log_status_first_time_is_published(self):
        """Test first status log is always published"""
        device, mock_mqtt, _ = create_mock_device()

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


class TestHealthCheck(unittest.TestCase):
    """Test cases for health check functionality"""

    @patch('main.rules.get_service_response')
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


if __name__ == '__main__':
    unittest.main()
