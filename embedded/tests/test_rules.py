import unittest
import sys
import os
import json
from unittest.mock import Mock, MagicMock, patch, call

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import rules


class TestGetMqttMsg(unittest.TestCase):
    """Test cases for get_mqtt_msg function"""

    def setUp(self):
        """Reset global MQTT_SUB_MSG before each test"""
        rules.MQTT_SUB_MSG = {}

    def test_get_mqtt_msg_success(self):
        """Test successful MQTT message reception"""
        topic = b'iot-devices/1/toggle'
        msg = b'25.5'

        rules.get_mqtt_msg(topic, msg)

        self.assertEqual(rules.MQTT_SUB_MSG['iot-devices/1/toggle'], '25.5')

    def test_get_mqtt_msg_multiple_topics(self):
        """Test multiple MQTT messages"""
        rules.get_mqtt_msg(b'iot-devices/1/toggle', b'25')
        rules.get_mqtt_msg(b'iot-devices/2/toggle', b'60')

        self.assertEqual(rules.MQTT_SUB_MSG['iot-devices/1/toggle'], '25')
        self.assertEqual(rules.MQTT_SUB_MSG['iot-devices/2/toggle'], '60')

    def test_get_mqtt_msg_none_topic(self):
        """Test with None topic (should not add to dict)"""
        rules.get_mqtt_msg(None, b'message')

        self.assertEqual(rules.MQTT_SUB_MSG, {})

    def test_get_mqtt_msg_none_msg(self):
        """Test with None message (should not add to dict)"""
        rules.get_mqtt_msg(b'topic', None)

        self.assertEqual(rules.MQTT_SUB_MSG, {})

    def test_get_mqtt_msg_update_existing(self):
        """Test updating existing topic"""
        rules.get_mqtt_msg(b'iot-devices/1/toggle', b'25')
        rules.get_mqtt_msg(b'iot-devices/1/toggle', b'30')

        self.assertEqual(rules.MQTT_SUB_MSG['iot-devices/1/toggle'], '30')

class TestGetServiceResponse(unittest.TestCase):
    """Test cases for get_service_response function"""

    @patch('rules.socket.socket')
    @patch('rules.socket.getaddrinfo')
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

        result = rules.get_service_response('http://example.com/api/data')

        self.assertEqual(result, {"result": "success"})
        mock_sock.connect.assert_called_once_with(('192.168.1.1', 80))
        mock_sock.settimeout.assert_called_once_with(15.0)

    @patch('rules.socket.socket')
    @patch('rules.socket.getaddrinfo')
    def test_get_service_response_with_auth(self, mock_getaddrinfo, mock_socket):
        """Test service response with auth header"""
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 80))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        response_body = 'HTTP/1.1\n200\nOK\n\n{"data":"value"}'
        mock_sock.recv.side_effect = [bytes(response_body, 'utf8'), b'']

        result = rules.get_service_response('http://example.com/api', 'Authorization: Bearer token')

        self.assertEqual(result, {"data": "value"})
        # Verify auth header was included in request
        sent_request = mock_sock.send.call_args[0][0].decode('utf8')
        self.assertIn('Authorization: Bearer token', sent_request)

    @patch('rules.socket.socket')
    @patch('rules.socket.getaddrinfo')
    def test_get_service_response_with_port(self, mock_getaddrinfo, mock_socket):
        """Test service response with custom port"""
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 8080))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        response_body = 'HTTP/1.1\n200\nOK\n\n{"status":"ok"}'
        mock_sock.recv.side_effect = [bytes(response_body, 'utf8'), b'']

        result = rules.get_service_response('http://example.com:8080/api')

        self.assertEqual(result, {"status": "ok"})

    @patch('rules.socket.socket')
    @patch('rules.socket.getaddrinfo')
    def test_get_service_response_201_status(self, mock_getaddrinfo, mock_socket):
        """Test service response with 201 status"""
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 80))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        response_body = 'HTTP/1.1\n201\nCreated\n\n{"id":123}'
        mock_sock.recv.side_effect = [bytes(response_body, 'utf8'), b'']

        result = rules.get_service_response('http://example.com/api')

        self.assertEqual(result, {"id": 123})

    @patch('rules.socket.socket')
    @patch('rules.socket.getaddrinfo')
    def test_get_service_response_404_status(self, mock_getaddrinfo, mock_socket):
        """Test service response with 404 status returns None"""
        mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.1', 80))]
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        response_body = 'HTTP/1.1\n404\nNotFound\n\n{"error":"not found"}'
        mock_sock.recv.side_effect = [bytes(response_body, 'utf8'), b'']

        result = rules.get_service_response('http://example.com/api')

        self.assertIsNone(result)


class TestReadFunctions(unittest.TestCase):
    """Test cases for read functions"""

    def test_read_normal(self):
        """Test normal read"""
        mock_pin = Mock()
        mock_pin.value.return_value = 1

        result = rules.read(mock_pin, {})

        self.assertEqual(result, 1)
        mock_pin.value.assert_called_once()

    def test_read_with_reverse(self):
        """Test read with reverse flag"""
        mock_pin = Mock()
        mock_pin.value.return_value = 1

        result = rules.read(mock_pin, {}, reverse=True)

        self.assertFalse(result)

    def test_read_bool_true(self):
        """Test read_bool returns True"""
        mock_pin = Mock()
        mock_pin.value.return_value = 1

        result = rules.read_bool(mock_pin, {})

        self.assertTrue(result)

    def test_read_bool_false(self):
        """Test read_bool returns False"""
        mock_pin = Mock()
        mock_pin.value.return_value = 0

        result = rules.read_bool(mock_pin, {})

        self.assertFalse(result)

    @patch('rules.time.sleep')
    def test_read_avg_sample(self, mock_sleep):
        """Test read_avg_sample"""
        mock_pin = Mock()
        mock_pin.value.side_effect = [10, 20, 30, 40, 50]

        result = rules.read_avg_sample(mock_pin, {}, sample_size=5)

        self.assertEqual(result, 30)
        self.assertEqual(mock_sleep.call_count, 5)

    @patch('rules.time.sleep')
    def test_read_avg_sample_default_size(self, mock_sleep):
        """Test read_avg_sample with default sample size"""
        mock_pin = Mock()
        mock_pin.value.side_effect = [10, 20, 30, 40, 50]

        result = rules.read_avg_sample(mock_pin, {})

        self.assertEqual(result, 30)
        self.assertEqual(mock_sleep.call_count, 5)

    @patch('rules.time.sleep')
    def test_read_min_sample(self, mock_sleep):
        """Test read_min_sample"""
        mock_pin = Mock()
        mock_pin.value.side_effect = [50, 20, 30, 40, 10]

        result = rules.read_min_sample(mock_pin, {}, sample_size=5)

        self.assertEqual(result, 10)

    @patch('rules.time.sleep')
    def test_read_max_sample(self, mock_sleep):
        """Test read_max_sample"""
        mock_pin = Mock()
        mock_pin.value.side_effect = [50, 20, 30, 40, 10]

        result = rules.read_max_sample(mock_pin, {}, sample_size=5)

        self.assertEqual(result, 50)

    @patch('rules.time.sleep')
    def test_read_bool_sample_all_true(self, mock_sleep):
        """Test read_bool_sample when all readings are true"""
        mock_pin = Mock()
        mock_pin.value.side_effect = [1, 1, 1, 1, 1]

        result = rules.read_bool_sample(mock_pin, {}, sample_size=5)

        self.assertTrue(result)

    @patch('rules.time.sleep')
    def test_read_bool_sample_one_false(self, mock_sleep):
        """Test read_bool_sample when one reading is false"""
        mock_pin = Mock()
        mock_pin.value.side_effect = [1, 1, 0, 1, 1]

        result = rules.read_bool_sample(mock_pin, {}, sample_size=5)

        self.assertFalse(result)


class TestReadAnalogFunctions(unittest.TestCase):
    """Test cases for analog read functions"""

    def test_read_analog(self):
        """Test read_analog"""
        mock_pin = Mock()
        mock_pin.read.return_value = 2048

        result = rules.read_analog(mock_pin, {})

        self.assertEqual(result, 2048)
        mock_pin.read.assert_called_once()

    def test_read_analog_bool_above_threshold(self):
        """Test read_analog_bool above threshold"""
        mock_pin = Mock()
        mock_pin.read.return_value = 5000

        result = rules.read_analog_bool(mock_pin, {}, threshold=4096)

        self.assertTrue(result)

    def test_read_analog_bool_below_threshold(self):
        """Test read_analog_bool below threshold"""
        mock_pin = Mock()
        mock_pin.read.return_value = 3000

        result = rules.read_analog_bool(mock_pin, {}, threshold=4096)

        self.assertFalse(result)

    def test_read_analog_bool_default_threshold(self):
        """Test read_analog_bool with default threshold"""
        mock_pin = Mock()
        mock_pin.read.return_value = 5000

        result = rules.read_analog_bool(mock_pin, {})

        self.assertTrue(result)

    def test_read_analog_percentage(self):
        """Test read_analog_percentage"""
        mock_pin = Mock()
        mock_pin.read.return_value = 2048

        result = rules.read_analog_percentage(mock_pin, {}, threshold=4096)

        self.assertEqual(result, 50.0)

    def test_read_analog_percentage_full(self):
        """Test read_analog_percentage at 100%"""
        mock_pin = Mock()
        mock_pin.read.return_value = 4096

        result = rules.read_analog_percentage(mock_pin, {}, threshold=4096)

        self.assertEqual(result, 100.0)

    @patch('rules.time.sleep')
    def test_read_analog_avg_sample(self, mock_sleep):
        """Test read_analog_avg_sample"""
        mock_pin = Mock()
        mock_pin.read.side_effect = [1000, 2000, 3000, 4000, 5000]

        result = rules.read_analog_avg_sample(mock_pin, {}, sample_size=5)

        self.assertEqual(result, 3000)
        self.assertEqual(mock_sleep.call_count, 5)

    @patch('rules.time.sleep')
    def test_read_analog_min_sample(self, mock_sleep):
        """Test read_analog_min_sample"""
        mock_pin = Mock()
        mock_pin.read.side_effect = [5000, 2000, 3000, 4000, 1000]

        result = rules.read_analog_min_sample(mock_pin, {}, sample_size=5)

        self.assertEqual(result, 1000)

    @patch('rules.time.sleep')
    def test_read_analog_max_sample(self, mock_sleep):
        """Test read_analog_max_sample"""
        mock_pin = Mock()
        mock_pin.read.side_effect = [5000, 2000, 3000, 4000, 1000]

        result = rules.read_analog_max_sample(mock_pin, {}, sample_size=5)

        self.assertEqual(result, 5000)

    @patch('rules.time.sleep')
    def test_read_analog_bool_sample_all_true(self, mock_sleep):
        """Test read_analog_bool_sample when all readings above threshold"""
        mock_pin = Mock()
        mock_pin.read.side_effect = [5000, 5000, 5000, 5000, 5000]

        result = rules.read_analog_bool_sample(mock_pin, {}, threshold=4096, sample_size=5)

        self.assertTrue(result)

    @patch('rules.time.sleep')
    def test_read_analog_bool_sample_one_false(self, mock_sleep):
        """Test read_analog_bool_sample when one reading below threshold"""
        mock_pin = Mock()
        mock_pin.read.side_effect = [5000, 5000, 3000, 5000, 5000]

        result = rules.read_analog_bool_sample(mock_pin, {}, threshold=4096, sample_size=5)

        self.assertFalse(result)


class TestReadDHT(unittest.TestCase):
    """Test cases for read_dht function"""

    def test_read_dht11(self):
        """Test reading DHT11 sensor"""
        mock_pin = Mock()
        mock_dht_module = Mock()
        mock_dht = Mock()
        mock_dht.temperature.return_value = 25
        mock_dht.humidity.return_value = 60
        mock_dht_module.DHT11.return_value = mock_dht

        with patch.dict('sys.modules', {'dht': mock_dht_module}):
            result = rules.read_dht(mock_pin, {}, sensor_type='DHT11')

        self.assertEqual(result, {'temperature': 25, 'humidity': 60})
        mock_dht.measure.assert_called_once()

    def test_read_dht22(self):
        """Test reading DHT22 sensor"""
        mock_pin = Mock()
        mock_dht_module = Mock()
        mock_dht = Mock()
        mock_dht.temperature.return_value = 25.5
        mock_dht.humidity.return_value = 65.3
        mock_dht_module.DHT22.return_value = mock_dht

        with patch.dict('sys.modules', {'dht': mock_dht_module}):
            result = rules.read_dht(mock_pin, {}, sensor_type='DHT22')

        self.assertEqual(result, {'temperature': 25.5, 'humidity': 65.3})
        mock_dht.measure.assert_called_once()

    def test_read_dht_unknown_type(self):
        """Test reading DHT with unknown sensor type"""
        mock_pin = Mock()
        mock_dht_module = Mock()

        with patch.dict('sys.modules', {'dht': mock_dht_module}):
            result = rules.read_dht(mock_pin, {}, sensor_type='DHT99')

        self.assertIsNone(result)


class TestReadBMP180(unittest.TestCase):
    """Test cases for read_bmp180 function"""

    def test_read_bmp180_default_params(self):
        """Test reading BMP180 with default parameters"""
        mock_pin = Mock()
        mock_bmp = Mock()
        mock_bmp.temperature.return_value = 25.5
        mock_bmp.pressure.return_value = 101325
        mock_bmp.altitude.return_value = 0

        # Create a mock module
        mock_bmp180_module = Mock()
        mock_bmp180_module.BMP180.return_value = mock_bmp

        with patch.dict('sys.modules', {'drivers.bmp180': mock_bmp180_module}):
            result = rules.read_bmp180(mock_pin, {})

        self.assertEqual(result['temperature'], 25.5)
        self.assertEqual(result['pressure'], 1013.25)
        self.assertEqual(result['altitude'], 0)
        self.assertEqual(mock_bmp.oversample, 2)
        self.assertEqual(mock_bmp.baseline, 101325)

    def test_read_bmp180_custom_params(self):
        """Test reading BMP180 with custom parameters"""
        mock_pin = Mock()
        mock_bmp = Mock()
        mock_bmp.temperature.return_value = 20.0
        mock_bmp.pressure.return_value = 95000
        mock_bmp.altitude.return_value = 500

        # Create a mock module
        mock_bmp180_module = Mock()
        mock_bmp180_module.BMP180.return_value = mock_bmp

        with patch.dict('sys.modules', {'drivers.bmp180': mock_bmp180_module}):
            result = rules.read_bmp180(mock_pin, {}, oversample=3, baseline=100000)

        self.assertEqual(result['temperature'], 20.0)
        self.assertEqual(result['pressure'], 950.0)
        self.assertEqual(result['altitude'], 500)
        self.assertEqual(mock_bmp.oversample, 3)
        self.assertEqual(mock_bmp.baseline, 100000)


class TestToggle(unittest.TestCase):
    """Test cases for toggle function"""

    def test_toggle_on(self):
        """Test toggle on"""
        mock_pin = Mock()
        mock_pin.value.return_value = 1

        result = rules.toggle(mock_pin, {}, on=True)

        mock_pin.on.assert_called_once()
        mock_pin.off.assert_not_called()
        self.assertEqual(result, 1)

    def test_toggle_off(self):
        """Test toggle off"""
        mock_pin = Mock()
        mock_pin.value.return_value = 0

        result = rules.toggle(mock_pin, {}, on=False)

        mock_pin.off.assert_called_once()
        mock_pin.on.assert_not_called()
        self.assertEqual(result, 0)


class TestMqttToggle(unittest.TestCase):
    """Test cases for mqtt_toggle function"""

    def setUp(self):
        """Reset global MQTT_SUB_MSG before each test"""
        rules.MQTT_SUB_MSG = {}

    def test_mqtt_toggle_success(self):
        """Test successful MQTT toggle"""
        mock_pin = Mock()
        mock_mqtt = Mock()
        rules.MQTT_SUB_MSG['iot-devices/1/toggle'] = '1'

        result = rules.mqtt_toggle(mock_pin, {}, mqtt=mock_mqtt, topic='iot-devices/1/toggle')

        mock_mqtt.set_callback.assert_called_once()
        mock_mqtt.subscribe.assert_called_once_with('iot-devices/1/toggle')
        mock_mqtt.check_msg.assert_called_once()
        self.assertTrue(result)

    def test_mqtt_toggle_false(self):
        """Test MQTT toggle returning false"""
        mock_pin = Mock()
        mock_mqtt = Mock()
        rules.MQTT_SUB_MSG['iot-devices/1/toggle'] = ''  # Empty string evaluates to False

        result = rules.mqtt_toggle(mock_pin, {}, mqtt=mock_mqtt, topic='iot-devices/1/toggle')

        self.assertFalse(result)

    def test_mqtt_toggle_missing_topic(self):
        """Test MQTT toggle with missing topic"""
        mock_pin = Mock()
        mock_mqtt = Mock()

        result = rules.mqtt_toggle(mock_pin, {}, mqtt=mock_mqtt, topic='iot-devices/1/toggle')

        self.assertFalse(result)

    def test_mqtt_toggle_retry_on_exception(self):
        """Test MQTT toggle retries on exception"""
        mock_pin = Mock()
        mock_mqtt = Mock()
        mock_mqtt.check_msg.side_effect = [Exception('error'), None]
        rules.MQTT_SUB_MSG['iot-devices/1/toggle'] = '1'

        result = rules.mqtt_toggle(mock_pin, {}, mqtt=mock_mqtt, topic='iot-devices/1/toggle')

        # Should connect once for retry
        mock_mqtt.connect.assert_called_once()
        self.assertTrue(result)

    def test_mqtt_toggle_max_retries_exceeded(self):
        """Test MQTT toggle fails after max retries"""
        mock_pin = Mock()
        mock_mqtt = Mock()
        mock_mqtt.check_msg.side_effect = Exception('error')

        with self.assertRaises(Exception) as context:
            rules.mqtt_toggle(mock_pin, {}, mqtt=mock_mqtt, topic='iot-devices/1/toggle')

        self.assertEqual(str(context.exception), 'MQTT Service is offline.')
        # Should try to connect 4 times for retries (retry_count: 1, 2, 3, 4)
        self.assertEqual(mock_mqtt.connect.call_count, 4)


class TestTimer(unittest.TestCase):
    """Test cases for timer function"""

    @patch('rules.time.localtime')
    def test_timer_within_range(self, mock_localtime):
        """Test timer within time range"""
        # Set current time to 14:30 (2:30 PM)
        mock_localtime.return_value = (2025, 11, 13, 14, 30, 0, 0, 0)
        mock_pin = Mock()

        result = rules.timer(mock_pin, {}, gmt_start_time='10:00', gmt_end_time='18:00')

        self.assertTrue(result)

    @patch('rules.time.localtime')
    def test_timer_before_range(self, mock_localtime):
        """Test timer before time range"""
        # Set current time to 08:00 (8:00 AM)
        mock_localtime.return_value = (2025, 11, 13, 8, 0, 0, 0, 0)
        mock_pin = Mock()

        result = rules.timer(mock_pin, {}, gmt_start_time='10:00', gmt_end_time='18:00')

        self.assertFalse(result)

    @patch('rules.time.localtime')
    def test_timer_after_range(self, mock_localtime):
        """Test timer after time range"""
        # Set current time to 20:00 (8:00 PM)
        mock_localtime.return_value = (2025, 11, 13, 20, 0, 0, 0, 0)
        mock_pin = Mock()

        result = rules.timer(mock_pin, {}, gmt_start_time='10:00', gmt_end_time='18:00')

        self.assertFalse(result)

    @patch('rules.time.localtime')
    def test_timer_single_digit_hour(self, mock_localtime):
        """Test timer with single digit hour"""
        # Set current time to 09:30
        mock_localtime.return_value = (2025, 11, 13, 9, 30, 0, 0, 0)
        mock_pin = Mock()

        result = rules.timer(mock_pin, {}, gmt_start_time='08:00', gmt_end_time='12:00')

        self.assertTrue(result)

    @patch('rules.time.localtime')
    def test_timer_single_digit_minute(self, mock_localtime):
        """Test timer with single digit minute"""
        # Set current time to 10:05
        mock_localtime.return_value = (2025, 11, 13, 10, 5, 0, 0, 0)
        mock_pin = Mock()

        result = rules.timer(mock_pin, {}, gmt_start_time='10:00', gmt_end_time='11:00')

        self.assertTrue(result)

    @patch('rules.time.localtime')
    def test_timer_at_boundary_start(self, mock_localtime):
        """Test timer at start boundary"""
        # Set current time to 10:00 (exactly at start)
        mock_localtime.return_value = (2025, 11, 13, 10, 0, 0, 0, 0)
        mock_pin = Mock()

        result = rules.timer(mock_pin, {}, gmt_start_time='10:00', gmt_end_time='18:00')

        self.assertFalse(result)  # Uses > not >=

    @patch('rules.time.localtime')
    def test_timer_at_boundary_end(self, mock_localtime):
        """Test timer at end boundary"""
        # Set current time to 18:00 (exactly at end)
        mock_localtime.return_value = (2025, 11, 13, 18, 0, 0, 0, 0)
        mock_pin = Mock()

        result = rules.timer(mock_pin, {}, gmt_start_time='10:00', gmt_end_time='18:00')

        self.assertFalse(result)  # Uses < not <=


class TestService(unittest.TestCase):
    """Test cases for service function"""

    @patch('rules.get_service_response')
    def test_service_without_auth(self, mock_get_response):
        """Test service call without auth header"""
        mock_pin = Mock()
        mock_get_response.return_value = {"status": "success"}

        result = rules.service(mock_pin, {}, url='http://example.com/api')

        mock_get_response.assert_called_once_with('http://example.com/api', None)
        self.assertEqual(result, {"status": "success"})

    @patch('rules.get_service_response')
    def test_service_with_auth(self, mock_get_response):
        """Test service call with auth header"""
        mock_pin = Mock()
        mock_get_response.return_value = {"data": "value"}

        result = rules.service(
            mock_pin,
            {},
            url='http://example.com/api',
            auth_header='Authorization: Bearer token'
        )

        mock_get_response.assert_called_once_with(
            'http://example.com/api',
            'Authorization: Bearer token'
        )
        self.assertEqual(result, {"data": "value"})

    @patch('embedded.rules.get_service_response')
    def test_service_returns_none(self, mock_get_response):
        """Test service call returning None"""
        mock_pin = Mock()
        mock_get_response.return_value = None

        result = rules.service(mock_pin, {}, url='http://example.com/api')

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
