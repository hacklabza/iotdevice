import json
import network
import socket
import time


def load_config():
    with open('config/config.json', 'r') as config_file:
        return json.loads(config_file.read())


def connect_wifi():
    network_config = load_config()['network']
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Connecting to network...')
        sta_if.active(True)
        essid = network_config['essid']
        sta_if.connect(essid, network_config['password'])
        for i in range(5):
            if not sta_if.isconnected():
                time.sleep(10)
                print('Connection attempt {count}/5'.format(count=i + 1))
                if i == 4:
                    print('Connection faile')
            else:
                ip_address = sta_if.ifconfig()[0]
                print(
                    'Connected to {essid} with IP: {ip_address}'.format(
                        essid=essid, ip_address=ip_address
                    )
                )
                break

    return sta_if.isconnected()


def simple_http_server():
    address = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    http_socket = socket.socket()
    http_socket.bind(address)
    http_socket.listen(1)

    while True:
        connection, _ = http_socket.accept()
        # connection_file = connection.makefile('rwb', 0)
        # while True:
        #     line = connection_file.readline()
        #     if not line or line == b'\r\n':
        #         break
        # rows = ['<tr><td>%s</td><td>%d</td></tr>' %
        #         (str(p), p.value()) for p in pins]
        response = 'Hello World!'
        connection.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        connection.send(response)
        connection.close()


if __name__ == '__main__':
    if connect_wifi():
        simple_http_server()
