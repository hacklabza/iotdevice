import unittest
import sys
import os
import json
from unittest.mock import mock_open, patch, Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock MicroPython modules
sys.modules['network'] = MagicMock()
sys.modules['time'] = MagicMock()

import utils


class TestLoadConfig(unittest.TestCase):
    """Test cases for load_config function"""

    def test_load_config_success(self):
        """Test successful config loading"""
        mock_config = {"key": "value", "number": 42}
        mock_file_content = json.dumps(mock_config)

        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            result = utils.load_config()
            self.assertEqual(result, mock_config)

    def test_load_config_empty_json(self):
        """Test loading empty JSON object"""
        mock_file_content = "{}"

        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            result = utils.load_config()
            self.assertEqual(result, {})

    def test_load_config_complex_structure(self):
        """Test loading complex nested JSON"""
        mock_config = {
            "sensors": {
                "temperature": {"pin": 4, "enabled": True},
                "pressure": {"pin": 5, "enabled": False}
            },
            "thresholds": [10, 20, 30]
        }
        mock_file_content = json.dumps(mock_config)

        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            result = utils.load_config()
            self.assertEqual(result, mock_config)


class TestConnectWifi(unittest.TestCase):
    """Test cases for connect_wifi function"""

    @patch('utils.time')
    @patch('utils.network')
    def test_connect_wifi_already_connected(self, mock_network, mock_time):
        """Test when wifi is already connected"""
        mock_wifi = Mock()
        mock_wifi.isconnected.return_value = True
        mock_network.WLAN.return_value = mock_wifi

        wifi_config = {
            'essid': 'TestNetwork',
            'password': 'testpass123',
            'retry_count': 5
        }

        result = utils.connect_wifi(wifi_config)

        self.assertTrue(result)
        mock_wifi.active.assert_not_called()
        mock_wifi.connect.assert_not_called()

    @patch('utils.time')
    @patch('utils.network')
    def test_connect_wifi_successful_first_attempt(self, mock_network, mock_time):
        """Test successful wifi connection on first attempt"""
        mock_wifi = Mock()
        # First call returns False (not connected), subsequent calls return True
        mock_wifi.isconnected.side_effect = [False, True, True]
        mock_wifi.ifconfig.return_value = ['192.168.1.100', '255.255.255.0', '192.168.1.1', '8.8.8.8']
        mock_network.WLAN.return_value = mock_wifi
        mock_network.STA_IF = 'STA_IF'

        wifi_config = {
            'essid': 'TestNetwork',
            'password': 'testpass123',
            'retry_count': 5
        }

        result = utils.connect_wifi(wifi_config)

        self.assertTrue(result)
        mock_wifi.active.assert_called_once_with(True)
        mock_wifi.connect.assert_called_once_with('TestNetwork', 'testpass123')
        mock_time.sleep.assert_not_called()

    @patch('utils.time')
    @patch('utils.network')
    def test_connect_wifi_successful_after_retries(self, mock_network, mock_time):
        """Test successful wifi connection after multiple retries"""
        mock_wifi = Mock()
        # Not connected initially, fails 2 times, then connects
        mock_wifi.isconnected.side_effect = [False, False, False, True, True]
        mock_wifi.ifconfig.return_value = ['192.168.1.100', '255.255.255.0', '192.168.1.1', '8.8.8.8']
        mock_network.WLAN.return_value = mock_wifi
        mock_network.STA_IF = 'STA_IF'

        wifi_config = {
            'essid': 'TestNetwork',
            'password': 'testpass123',
            'retry_count': 5
        }

        result = utils.connect_wifi(wifi_config)

        self.assertTrue(result)
        mock_wifi.active.assert_called_once_with(True)
        mock_wifi.connect.assert_called_once_with('TestNetwork', 'testpass123')
        self.assertEqual(mock_time.sleep.call_count, 2)

    @patch('utils.time')
    @patch('utils.network')
    def test_connect_wifi_max_retries_reached(self, mock_network, mock_time):
        """Test wifi connection fails after max retries"""
        mock_wifi = Mock()
        # Never connects - always returns False
        mock_wifi.isconnected.return_value = False
        mock_network.WLAN.return_value = mock_wifi
        mock_network.STA_IF = 'STA_IF'

        wifi_config = {
            'essid': 'TestNetwork',
            'password': 'testpass123',
            'retry_count': 3
        }

        result = utils.connect_wifi(wifi_config)

        self.assertFalse(result)
        mock_wifi.active.assert_called_once_with(True)
        mock_wifi.connect.assert_called_once_with('TestNetwork', 'testpass123')
        self.assertEqual(mock_time.sleep.call_count, 3)

    @patch('utils.time')
    @patch('utils.network')
    def test_connect_wifi_prints_connection_attempts(self, mock_network, mock_time):
        """Test that connection attempts are printed correctly"""
        mock_wifi = Mock()
        # Not connected initially, fails once, then connects
        mock_wifi.isconnected.side_effect = [False, False, True, True]
        mock_wifi.ifconfig.return_value = ['10.0.0.50', '255.255.255.0', '10.0.0.1', '8.8.8.8']
        mock_network.WLAN.return_value = mock_wifi
        mock_network.STA_IF = 'STA_IF'

        wifi_config = {
            'essid': 'MyWiFi',
            'password': 'mypassword',
            'retry_count': 5
        }

        with patch('builtins.print') as mock_print:
            result = utils.connect_wifi(wifi_config)

        self.assertTrue(result)
        # Check that appropriate messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Connecting to wifi' in str(call) for call in print_calls))
        self.assertTrue(any('Connection attempt' in str(call) for call in print_calls))
        self.assertTrue(any('Connected to MyWiFi' in str(call) for call in print_calls))
        self.assertTrue(any('10.0.0.50' in str(call) for call in print_calls))


class TestFindXpathValue(unittest.TestCase):
    """Test cases for find_xpath_value function"""

    def test_find_simple_key(self):
        """Test finding a simple key in dict"""
        response = {"key": "value"}
        xpaths = ["key"]
        result = utils.find_xpath_value(response, xpaths)
        self.assertEqual(result, "value")

    def test_find_nested_keys(self):
        """Test finding nested keys"""
        response = {"level1": {"level2": {"level3": "deep_value"}}}
        xpaths = ["level3", "level2", "level1"]  # reversed
        result = utils.find_xpath_value(response, xpaths)
        self.assertEqual(result, "deep_value")

    def test_find_array_index(self):
        """Test finding value by array index"""
        response = {"items": [10, 20, 30]}
        xpaths = ["1", "items"]  # reversed
        result = utils.find_xpath_value(response, xpaths)
        self.assertEqual(result, 20)

    def test_find_mixed_dict_and_array(self):
        """Test finding value with mixed dict and array paths"""
        response = {
            "sensors": [
                {"name": "temp", "value": 25},
                {"name": "pressure", "value": 1013}
            ]
        }
        xpaths = ["value", "0", "sensors"]  # reversed
        result = utils.find_xpath_value(response, xpaths)
        self.assertEqual(result, 25)

    def test_find_nonexistent_key(self):
        """Test finding non-existent key returns None"""
        response = {"key": "value"}
        xpaths = ["nonexistent"]
        result = utils.find_xpath_value(response, xpaths)
        self.assertIsNone(result)

    def test_find_invalid_index(self):
        """Test finding with invalid array index returns None"""
        response = {"items": [1, 2, 3]}
        xpaths = ["10", "items"]  # index out of range
        result = utils.find_xpath_value(response, xpaths)
        self.assertIsNone(result)

    def test_find_key_in_list(self):
        """Test trying to find key in list returns None"""
        response = [1, 2, 3]
        xpaths = ["key"]
        result = utils.find_xpath_value(response, xpaths)
        self.assertIsNone(result)

    def test_find_single_element_xpath(self):
        """Test with single element xpath"""
        response = {"key": "value"}
        xpaths = ["key"]
        result = utils.find_xpath_value(response, xpaths)
        self.assertEqual(result, "value")

    def test_find_index_in_dict(self):
        """Test trying to use numeric index on dict returns None"""
        response = {"key": "value"}
        xpaths = ["0"]
        result = utils.find_xpath_value(response, xpaths)
        self.assertIsNone(result)

    def test_find_nested_array_access(self):
        """Test nested array access"""
        response = {"data": [[1, 2], [3, 4], [5, 6]]}
        xpaths = ["1", "2", "data"]  # reversed: data[2][1]
        result = utils.find_xpath_value(response, xpaths)
        self.assertEqual(result, 6)

    def test_find_with_none_value(self):
        """Test finding path where value is None"""
        response = {"key": None}
        xpaths = ["key"]
        result = utils.find_xpath_value(response, xpaths)
        self.assertIsNone(result)


class TestEvaluateCondition(unittest.TestCase):
    """Test cases for evaluate_condition function"""

    def test_evaluate_eq_true(self):
        """Test equality operator when true"""
        result = utils.evaluate_condition(10, 'eq', 10)
        self.assertTrue(result)

    def test_evaluate_eq_false(self):
        """Test equality operator when false"""
        result = utils.evaluate_condition(10, 'eq', 20)
        self.assertFalse(result)

    def test_evaluate_gt_true(self):
        """Test greater than operator when true"""
        result = utils.evaluate_condition(20, 'gt', 10)
        self.assertTrue(result)

    def test_evaluate_gt_false(self):
        """Test greater than operator when false"""
        result = utils.evaluate_condition(10, 'gt', 20)
        self.assertFalse(result)

    def test_evaluate_gt_equal(self):
        """Test greater than operator when equal"""
        result = utils.evaluate_condition(10, 'gt', 10)
        self.assertFalse(result)

    def test_evaluate_lt_true(self):
        """Test less than operator when true"""
        result = utils.evaluate_condition(10, 'lt', 20)
        self.assertTrue(result)

    def test_evaluate_lt_false(self):
        """Test less than operator when false"""
        result = utils.evaluate_condition(20, 'lt', 10)
        self.assertFalse(result)

    def test_evaluate_lt_equal(self):
        """Test less than operator when equal"""
        result = utils.evaluate_condition(10, 'lt', 10)
        self.assertFalse(result)

    def test_evaluate_string_equality(self):
        """Test equality with strings"""
        result = utils.evaluate_condition("test", 'eq', "test")
        self.assertTrue(result)

    def test_evaluate_string_inequality(self):
        """Test inequality with strings"""
        result = utils.evaluate_condition("test", 'eq', "other")
        self.assertFalse(result)

    def test_evaluate_float_comparison(self):
        """Test comparison with floats"""
        result = utils.evaluate_condition(25.5, 'gt', 25.0)
        self.assertTrue(result)

    def test_evaluate_type_error(self):
        """Test type error returns False"""
        result = utils.evaluate_condition("string", 'gt', 10)
        self.assertFalse(result)

    def test_evaluate_none_comparison(self):
        """Test comparison with None"""
        result = utils.evaluate_condition(None, 'eq', None)
        self.assertTrue(result)

    def test_evaluate_none_vs_value(self):
        """Test None compared to value"""
        result = utils.evaluate_condition(None, 'eq', 10)
        self.assertFalse(result)

    def test_evaluate_unknown_operator(self):
        """Test unknown operator returns None (no match in if/elif)"""
        result = utils.evaluate_condition(10, 'unknown', 10)
        self.assertIsNone(result)


class TestHandleConditions(unittest.TestCase):
    """Test cases for handle_conditions function"""

    def test_handle_must_conditions_all_true(self):
        """Test must conditions when all are true"""
        rule_values = {"sensor1": 25, "sensor2": 30}
        input_value = {
            "conditions": {
                "must": {
                    "sensor1": {"operator": "gt", "value": 20},
                    "sensor2": {"operator": "gt", "value": 25}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [True, True])
        self.assertEqual(result["should"], [])

    def test_handle_must_conditions_some_false(self):
        """Test must conditions when some are false"""
        rule_values = {"sensor1": 15, "sensor2": 30}
        input_value = {
            "conditions": {
                "must": {
                    "sensor1": {"operator": "gt", "value": 20},
                    "sensor2": {"operator": "gt", "value": 25}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [False, True])

    def test_handle_should_conditions(self):
        """Test should conditions"""
        rule_values = {"sensor1": 25, "sensor2": 15}
        input_value = {
            "conditions": {
                "should": {
                    "sensor1": {"operator": "gt", "value": 20},
                    "sensor2": {"operator": "gt", "value": 20}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [])
        self.assertEqual(result["should"], [True, False])

    def test_handle_mixed_conditions(self):
        """Test mixed must and should conditions"""
        rule_values = {"temp": 25, "pressure": 1013, "humidity": 60}
        input_value = {
            "conditions": {
                "must": {
                    "temp": {"operator": "gt", "value": 20}
                },
                "should": {
                    "pressure": {"operator": "gt", "value": 1000},
                    "humidity": {"operator": "lt", "value": 70}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [True])
        self.assertEqual(result["should"], [True, True])

    def test_handle_nested_xpath_conditions(self):
        """Test conditions with nested xpath"""
        rule_values = {
            "sensors": {
                "temperature": 25,
                "pressure": 1013
            }
        }
        input_value = {
            "conditions": {
                "must": {
                    "sensors.temperature": {"operator": "eq", "value": 25},
                    "sensors.pressure": {"operator": "gt", "value": 1000}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [True, True])

    def test_handle_array_xpath_conditions(self):
        """Test conditions with array xpath"""
        rule_values = {
            "readings": [10, 20, 30, 40]
        }
        input_value = {
            "conditions": {
                "must": {
                    "readings.0": {"operator": "eq", "value": 10},
                    "readings.2": {"operator": "gt", "value": 25}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [True, True])

    def test_handle_nonexistent_xpath(self):
        """Test conditions with non-existent xpath"""
        rule_values = {"sensor1": 25}
        input_value = {
            "conditions": {
                "must": {
                    "nonexistent": {"operator": "eq", "value": 25}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [False])

    def test_handle_empty_conditions(self):
        """Test with empty conditions dict"""
        rule_values = {"sensor1": 25}
        input_value = {
            "conditions": {}
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [])
        self.assertEqual(result["should"], [])

    def test_handle_unknown_condition_type(self):
        """Test with unknown condition type (should be ignored)"""
        rule_values = {"sensor1": 25}
        input_value = {
            "conditions": {
                "unknown_type": {
                    "sensor1": {"operator": "eq", "value": 25}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [])
        self.assertEqual(result["should"], [])

    def test_handle_equality_condition(self):
        """Test equality conditions"""
        rule_values = {"status": "active", "count": 5}
        input_value = {
            "conditions": {
                "must": {
                    "status": {"operator": "eq", "value": "active"},
                    "count": {"operator": "eq", "value": 5}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [True, True])

    def test_handle_deep_nested_xpath(self):
        """Test deeply nested xpath conditions"""
        rule_values = {
            "device": {
                "sensors": {
                    "environmental": {
                        "temperature": 25
                    }
                }
            }
        }
        input_value = {
            "conditions": {
                "must": {
                    "device.sensors.environmental.temperature": {"operator": "gt", "value": 20}
                }
            }
        }
        result = utils.handle_conditions(rule_values, input_value)
        self.assertEqual(result["must"], [True])


class TestValueToBool(unittest.TestCase):
    """Test cases for value_to_bool function"""

    def test_value_to_bool_true_string(self):
        """Test 'true' string returns True"""
        self.assertTrue(utils.value_to_bool('true'))

    def test_value_to_bool_true_uppercase(self):
        """Test 'True' string returns True"""
        self.assertTrue(utils.value_to_bool('True'))

    def test_value_to_bool_true_mixed_case(self):
        """Test 'TrUe' string returns True"""
        self.assertTrue(utils.value_to_bool('TrUe'))

    def test_value_to_bool_one_string(self):
        """Test '1' string returns True"""
        self.assertTrue(utils.value_to_bool('1'))

    def test_value_to_bool_yes_string(self):
        """Test 'yes' string returns True"""
        self.assertTrue(utils.value_to_bool('yes'))

    def test_value_to_bool_on_string(self):
        """Test 'on' string returns True"""
        self.assertTrue(utils.value_to_bool('on'))

    def test_value_to_bool_false_string(self):
        """Test 'false' string returns False"""
        self.assertFalse(utils.value_to_bool('false'))

    def test_value_to_bool_zero_string(self):
        """Test '0' string returns False"""
        self.assertFalse(utils.value_to_bool('0'))

    def test_value_to_bool_off_string(self):
        """Test 'off' string returns False"""
        self.assertFalse(utils.value_to_bool('off'))

    def test_value_to_bool_empty_string(self):
        """Test empty string returns False"""
        self.assertFalse(utils.value_to_bool(''))

    def test_value_to_bool_random_string(self):
        """Test random string returns False"""
        self.assertFalse(utils.value_to_bool('random'))

    def test_value_to_bool_bool_true(self):
        """Test boolean True returns True"""
        self.assertTrue(utils.value_to_bool(True))

    def test_value_to_bool_bool_false(self):
        """Test boolean False returns False"""
        self.assertFalse(utils.value_to_bool(False))

    def test_value_to_bool_none(self):
        """Test None returns False"""
        self.assertFalse(utils.value_to_bool(None))

    def test_value_to_bool_int_zero(self):
        """Test integer 0 returns False"""
        self.assertFalse(utils.value_to_bool(0))

    def test_value_to_bool_int_one(self):
        """Test integer 1 returns True"""
        self.assertTrue(utils.value_to_bool(1))

    def test_value_to_bool_int_positive(self):
        """Test positive integer returns True"""
        self.assertTrue(utils.value_to_bool(42))

    def test_value_to_bool_int_negative(self):
        """Test negative integer returns True"""
        self.assertTrue(utils.value_to_bool(-1))


class TestGetServiceResponse(unittest.TestCase):
    """Test cases for get_service_response function"""

    @patch('utils.socket.socket')
    @patch('utils.socket.getaddrinfo')
    def test_get_service_response_success(self, mock_getaddrinfo, mock_socket):
        """Test successful service response"""
        # Setup mocks
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 80))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        # Response body with proper line breaks (split() will separate by whitespace)
        response_body = 'HTTP/1.1\n200\nOK\nContent-Type:\napplication/json\n\n{"result":"success"}'
        mock_sock.recv.side_effect = [
            bytes(response_body, 'utf8'),
            b''
        ]

        result = utils.get_service_response('http://example.com/api/data')

        self.assertEqual(result, {"result": "success"})
        mock_sock.connect.assert_called_once_with(('192.168.1.1', 80))
        mock_sock.settimeout.assert_called_once_with(15.0)

    @patch('utils.socket.socket')
    @patch('utils.socket.getaddrinfo')
    def test_get_service_response_with_auth(self, mock_getaddrinfo, mock_socket):
        """Test service response with auth header"""
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 80))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        response_body = 'HTTP/1.1\n200\nOK\n\n{"data":"value"}'
        mock_sock.recv.side_effect = [bytes(response_body, 'utf8'), b'']

        result = utils.get_service_response('http://example.com/api', 'Authorization: Bearer token')

        self.assertEqual(result, {"data": "value"})
        # Verify auth header was included in request
        sent_request = mock_sock.send.call_args[0][0].decode('utf8')
        self.assertIn('Authorization: Bearer token', sent_request)

    @patch('utils.socket.socket')
    @patch('utils.socket.getaddrinfo')
    def test_get_service_response_with_port(self, mock_getaddrinfo, mock_socket):
        """Test service response with custom port"""
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 8080))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        response_body = 'HTTP/1.1\n200\nOK\n\n{"status":"ok"}'
        mock_sock.recv.side_effect = [bytes(response_body, 'utf8'), b'']

        result = utils.get_service_response('http://example.com:8080/api')

        self.assertEqual(result, {"status": "ok"})

    @patch('utils.socket.socket')
    @patch('utils.socket.getaddrinfo')
    def test_get_service_response_201_status(self, mock_getaddrinfo, mock_socket):
        """Test service response with 201 status"""
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 80))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        response_body = 'HTTP/1.1\n201\nCreated\n\n{"id":123}'
        mock_sock.recv.side_effect = [bytes(response_body, 'utf8'), b'']

        result = utils.get_service_response('http://example.com/api')

        self.assertEqual(result, {"id": 123})

    @patch('utils.socket.socket')
    @patch('utils.socket.getaddrinfo')
    def test_get_service_response_404_status(self, mock_getaddrinfo, mock_socket):
        """Test service response with 404 status returns None"""
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 80))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        response_body = 'HTTP/1.1\n404\nNotFound\n\n{"error":"not found"}'
        mock_sock.recv.side_effect = [bytes(response_body, 'utf8'), b'']

        result = utils.get_service_response('http://example.com/api')

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
