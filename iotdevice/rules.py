import json
import socket
import time

import utils


MQTT_SUB_MSG = {}


def get_mqtt_msg(topic, msg):
    global MQTT_SUB_MSG
    if topic and msg:
        MQTT_SUB_MSG[str(topic.decode('utf-8'))] = str(msg.decode('utf-8'))


def read(pin, rule, **kwargs):
    """
    Reads the value of a pin, with optional reversal.
    """
    reverse = kwargs.get('reverse', False)
    if reverse:
        return not pin.value()
    return pin.value()


def read_bool(pin, rule, **kwargs):
    """
    Reads the boolean value of a pin.
    """
    return bool(read(pin, rule, **kwargs))


def read_avg_sample(pin, rule, **kwargs):
    """
    Reads the average value from multiple samples of a pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_min_sample(pin, rule, **kwargs):
    """
    Reads the minimum value from multiple samples of a pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return min(readings)


def read_max_sample(pin, rule, **kwargs):
    """
    Reads the maximum value from multiple samples of a pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return max(readings)


def read_bool_sample(pin, rule, **kwargs):
    """
    Reads the boolean value from multiple samples of a pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return all(readings)


def read_analog(pin, rule, **kwargs):
    """
    Reads the analog value of a pin.
    """
    return pin.read()


def read_analog_bool(pin, rule, **kwargs):
    """
    Reads the boolean value of an analog pin based on a threshold.
    """
    threshold = kwargs.get('threshold', 4096)
    return read_analog(pin, rule, **kwargs) > threshold


def read_analog_percentage(pin, rule, **kwargs):
    """
    Reads the analog value of a pin as a percentage based on a threshold.
    """
    threshold = kwargs.get('threshold', 4096)
    return (read_analog(pin, rule, **kwargs) / threshold) * 100


def read_analog_avg_sample(pin, rule, **kwargs):
    """
    Reads the average analog value from multiple samples of a pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_analog_min_sample(pin, rule, **kwargs):
    """
    Reads the minimum analog value from multiple samples of a pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return min(readings)


def read_analog_max_sample(pin, rule, **kwargs):
    """
    Reads the maximum analog value from multiple samples of a pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return max(readings)


def read_analog_bool_sample(pin, rule, **kwargs):
    """
    Reads the boolean value from multiple samples of an analog pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog_bool(pin, rule, **kwargs))
        time.sleep(0.5)
    return all(readings)


def read_analog_percentage_sample(pin, rule, **kwargs):
    """
    Reads the average analog percentage value from multiple samples of an analog
    pin.
    """
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog_percentage(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_dht(pin, rule, **kwargs):
    """
    Reads temperature and humidity from a DHT sensor.
    """
    import dht

    _type = kwargs.get('sensor_type')
    if _type == 'DHT11':
        dht_sensor = dht.DHT11(pin)
    elif _type == 'DHT22':
        dht_sensor = dht.DHT22(pin)
    else:
        return None

    dht_sensor.measure()

    return {
        'temperature': dht_sensor.temperature(),
        'humidity': dht_sensor.humidity(),
    }


def read_bmp180(pin, rule, **kwargs):
    """
    Reads temperature, pressure, and altitude from a BMP180 sensor.
    """
    from drivers.bmp180 import BMP180

    oversample = kwargs.get('oversample', 2)
    baseline = kwargs.get('baseline', 101325)

    bmp180_sensor = BMP180(pin)

    bmp180_sensor.oversample = oversample
    bmp180_sensor.baseline = baseline

    return {
        'temperature': bmp180_sensor.temperature(),
        'pressure': bmp180_sensor.pressure() / 100,
        'altitude': bmp180_sensor.altitude(),
    }


def toggle(pin, rule, **kwargs):
    """
    Toggles the state of a pin based on the 'on' keyword argument.
    """
    on = kwargs.get('on')
    pin.on() if on else pin.off()
    return pin.value()


def mqtt_toggle(pin, rule, retry_count=0, **kwargs):
    """
    Toggles the state of a pin based on MQTT messages.
    """
    mqtt = kwargs.get('mqtt')
    topic = kwargs.get('topic')

    if retry_count > 0:
        mqtt.connect()
    try:
        mqtt.set_callback(get_mqtt_msg)
        mqtt.subscribe(topic)
        mqtt.check_msg()
    except Exception:
        if retry_count <= 3:
            retry_count += 1
            return mqtt_toggle(pin, rule, retry_count, **kwargs)
        else:
            raise Exception('MQTT Service is offline.')

    value = utils.value_to_bool(MQTT_SUB_MSG.get(topic, '0'))
    toggle(pin, rule, on=value)
    return value


def timer(pin, rule, **kwargs):
    """
    Checks if the current time is within a specified GMT start and end time range.
    """
    start_time = kwargs.get('gmt_start_time').replace(':', '')
    end_time = kwargs.get('gmt_end_time').replace(':', '')

    now = time.localtime()
    current_hour = str(now[3] if now[3] > 9 else '0{hour}'.format(hour=now[3]))
    current_minute = str(now[4] if now[4] > 9 else '0{hour}'.format(hour=now[4]))
    current_time = current_hour + current_minute

    return end_time > current_time > start_time


def service(pin, rule, **kwargs):
    """
    Calls a web service and returns its response.
    """
    url = kwargs.get('url')
    auth_header = kwargs.get('auth_header')

    return utils.get_service_response(url, auth_header)
