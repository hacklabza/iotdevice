import json
import socket
import time

import network


def load_config():
    """
    Loads the configuration file from the filesystem."""
    with open('config/config.json', 'r') as config_file:
        return json.loads(config_file.read())


def connect_wifi(wifi_config):
    wifi = network.WLAN(network.STA_IF)
    if not wifi.isconnected():
        print('Connecting to wifi...')
        wifi.active(True)
        essid = wifi_config['essid']
        wifi.connect(essid, wifi_config['password'])
        for i in range(wifi_config['retry_count']):
            if not wifi.isconnected():
                print(
                    'Connection attempt {count}/{retry_count}'.format(
                        count=i + 1, retry_count=wifi_config['retry_count']
                    )
                )
                time.sleep(5)
                if i == wifi_config['retry_count'] - 1:
                    print('Connection failed. Rebooting.')
            else:
                ip_address = wifi.ifconfig()[0]
                print(
                    'Connected to {essid} with IP: {ip_address}'.format(
                        essid=essid, ip_address=ip_address
                    )
                )
                print('MAC address: {mac}'.format(mac=get_mac_address()))
                break

    return wifi.isconnected()


def get_mac_address():
    """
    Returns the device's WLAN MAC address as a colon-separated hex string.
    """
    mac = network.WLAN(network.STA_IF).config('mac')
    return ':'.join('{:02x}'.format(b) for b in mac)


def get_wifi_signal_strength():
    """Estimate Wi-Fi strength as 0-100% (-100 to -50 dBm), or 0 offline."""
    wifi = network.WLAN(network.STA_IF)
    if not wifi.isconnected():
        return 0

    rssi = wifi.status('rssi')
    return max(0, min(100, int(2 * (rssi + 100))))


def find_xpath_value(response, xpaths):
    """
    Recursively finds a value in a nested dict/list structure based on a list of xpaths.
    """
    xpath = xpaths.pop()  # paths must be reversed before passing it in

    try:
        response = response[int(xpath)]
    except ValueError:
        try:
            response = response[xpath]
        except (KeyError, TypeError):
            return None
    except (KeyError, IndexError, TypeError):
        return None

    if not len(xpaths):
        return response

    return find_xpath_value(response, xpaths)


def evaluate_condition(input, operator, value):
    """
    Evaluates a condition and returns a boolean.
    """
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
                        find_xpath_value(rule_values, xpaths), **condition
                    )
                )

    return condition_values


def value_to_bool(value):
    """
    Converts a string, int, or None to a boolean.
    """
    if isinstance(value, str):
        value = value.strip().lower()
        return value in ['true', '1', 'yes', 'on']
    return bool(value)


def call_service(url, auth_header=None, method='GET', payload=None):
    """Call an HTTP service, optionally sending a JSON payload with POST."""
    method = method.upper()
    if method not in ('GET', 'POST'):
        raise ValueError('Only GET and POST are supported')

    response_body = ''

    _, _, host, path = url.split('/', 3)
    port = 80
    if ':' in host:
        host, port = host.split(':', 1)

    address = socket.getaddrinfo(host, int(port))[0][-1]
    request = f'{method} /{path} HTTP/1.0\r\nHost: {host}\r\n'
    if auth_header:
        request += f'{auth_header}\r\n'
    body = b''
    if method == 'POST':
        if payload is not None:
            body = json.dumps(payload).encode('utf8')
        request += (
            f'Content-Type: application/json\r\nContent-Length: {len(body)}\r\n'
        )

    _socket = socket.socket()
    _socket.settimeout(15.0)
    _socket.connect(address)
    _socket.send(request.encode('utf8') + b'\r\n' + body)

    while True:
        data = _socket.recv(100)
        if data:
            response_body += str(data, 'utf8')
        else:
            break
    _socket.close()

    headers, body = response_body.split('\r\n\r\n', 1)
    if headers.split()[1] in ['200', '201', '301']:
        return json.loads(body)

    return None
