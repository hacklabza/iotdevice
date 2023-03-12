import json
import socket
import time


MQTT_SUB_MSG = {}


def get_mqtt_msg(topic, msg):
    global MQTT_SUB_MSG
    if topic and msg:
        MQTT_SUB_MSG[str(topic.decode('utf-8'))] = str(msg.decode('utf-8'))


def get_service_response(url, auth_header=None):
    response_body = ''

    _, _, host, path = url.split('/', 3)
    port = 80
    if ':' in host:
        host, port = host.split(':', 1)

    address = socket.getaddrinfo(host, int(port))[0][-1]
    if auth_header:
        request = 'GET /{path} HTTP/1.0\r\nHost: {host}\r\n{auth_header}\r\n\r\n'.format(
            path=path,
            host=host,
            auth_header=auth_header
        )
    else:
        request = 'GET /{path} HTTP/1.0\r\nHost: {host}\r\n\r\n'.format(
            path=path,
            host=host
        )

    _socket = socket.socket()
    _socket.settimeout(15.0)
    _socket.connect(address)
    _socket.send(bytes(request, 'utf8'))

    while True:
        data = _socket.recv(100)
        if data:
            response_body += str(data, 'utf8')
        else:
            break
    _socket.close()

    response_lines = response_body.split()
    if response_lines[1] in ['200', '201', '301']:
        return json.loads(response_lines[-1])

    return None


def read(pin, rule, **kwargs):
    reverse = kwargs.get('reverse', False)
    if reverse:
        return not pin.value()
    return pin.value()


def read_bool(pin, rule, **kwargs):
    return bool(read(pin, rule, **kwargs))


def read_avg_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_min_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return min(readings)


def read_max_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return max(readings)


def read_bool_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return all(readings)


def read_analog(pin, rule, **kwargs):
    return pin.read()


def read_analog_bool(pin, rule, **kwargs):
    threshold = kwargs.get('threshold', 4096)
    return read_analog(pin, rule, **kwargs) > threshold


def read_analog_percentage(pin, rule, **kwargs):
    threshold = kwargs.get('threshold', 4096)
    return (read_analog(pin, rule, **kwargs) / threshold) * 100


def read_analog_avg_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_analog_min_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return min(readings)


def read_analog_max_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return max(readings)


def read_analog_bool_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 5)):
        readings.append(read_analog_bool(pin, rule, **kwargs))
        time.sleep(0.5)
    return all(readings)


def read_dht(pin, rule, **kwargs):
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
        'humidity': dht_sensor.humidity()
    }


def read_bmp180(pin, rule, **kwargs):
    from drivers.bmp180 import BMP180

    oversample = kwargs.get('oversample', 2)
    baseline = kwargs.get('baseline', 101325)

    bmp180_sensor = BMP180(pin)

    bmp180_sensor.oversample = oversample
    bmp180_sensor.baseline = baseline

    return {
        'temperature': f'{bmp180_sensor.temperature():.1f}',
        'pressure': int(bmp180_sensor.pressure() / 100),
        'altitude': int(bmp180_sensor.altitude())
    }


def toggle(pin, rule, **kwargs):
    on = kwargs.get('on')
    pin.on() if on else pin.off()
    return pin.value()


def mqtt_toggle(pin, rule, retry_count=0, **kwargs):
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

    return int(MQTT_SUB_MSG.get(topic, 0))


def timer(pin, rule, **kwargs):
    start_time = kwargs.get('gmt_start_time').replace(':', '')
    end_time = kwargs.get('gmt_end_time').replace(':', '')

    now = time.localtime()
    current_hour = str(now[3] if now[3] > 9 else '0{hour}'.format(hour=now[3]))
    current_minute = str(now[4] if now[4] > 9 else '0{hour}'.format(hour=now[4]))
    current_time = current_hour + current_minute

    return end_time > current_time > start_time


def service(pin, rule, **kwargs):
    url = kwargs.get('url')
    auth_header = kwargs.get('auth_header')

    return get_service_response(url, auth_header)
