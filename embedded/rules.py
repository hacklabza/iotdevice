import json
import socket
import time


MQTT_SUB_MSG = {}


def get_mqtt_msg(topic, msg):
    global MQTT_SUB_MSG
    if topic and msg:
        MQTT_SUB_MSG[str(topic.decode('utf-8'))] = str(msg.decode('utf-8'))


def get_service_response(url, auth_header):
    response_body = ''

    _, _, host, path = url.split('/', 3)
    port = 80
    if ':' in host:
        host, port = host.split(':', 1)

    address = socket.getaddrinfo(host, int(port))[0][-1]
    request = 'GET /{path} HTTP/1.0\r\nHost: {host}\r\n{auth_header}\r\n\r\n'.format(
        path=path,
        host=host,
        auth_header=auth_header
    )

    _socket = socket.socket()
    try:
        _socket.connect(address)
        _socket.send(bytes(request, 'utf8'))
    except Exception:
        return None

    while True:
        data = _socket.recv(100)
        if data:
            response_body += str(data, 'utf8')
        else:
            break
    _socket.close()

    response_lines = response_body.split()
    if response_lines[1] == '200':
        return json.loads(response_lines[-1])

    return None


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


def run_condition(value, condition):
    try:
        if condition['operator'] == 'eq':
            return value == condition['value']
        elif condition['operator'] == 'gt':
            return value > condition['value']
        elif condition['operator'] == 'lt':
            return value < condition['value']
    except TypeError:
        return False


def read(pin, rule, **kwargs):
    reverse = kwargs.get('reverse', False)
    if reverse:
        return not pin.value()
    return pin.value()


def read_avg_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_min_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return min(readings)


def read_max_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return max(readings)


def read_bool_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return all(readings)


def read_analog(pin, rule, **kwargs):
    return pin.read()


def read_bool_analog(pin, rule, **kwargs):
    threshold = kwargs.get('threshold', 1024)
    value = pin.read()
    return value > threshold


def read_avg_analog_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_bool_analog_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read_bool_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return all(readings)


def toggle(pin, rule, **kwargs):
    on = kwargs.get('on')
    pin.on() if on else pin.off()
    return pin.value()


def mqtt_toggle(pin, rule, **kwargs):
    mqtt = kwargs.get('mqtt')
    queue = kwargs.get('queue')

    mqtt.set_callback(get_mqtt_msg)
    mqtt.subscribe(queue)
    mqtt.check_msg()

    return int(MQTT_SUB_MSG.get(queue, 0))


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
    condition = kwargs.get('condition')

    response = get_service_response(url, auth_header)
    value = None
    if response is not None:
        xpaths = condition['xpath'].split('.')
        xpaths.reverse()
        value = find_xpath_value(response, xpaths)

        return run_condition(value, condition)

    return False
