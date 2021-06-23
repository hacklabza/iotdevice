import json
import network
import socket
import time
import upip


def load_config():
    with open('config/config.json', 'r') as config_file:
        return json.loads(config_file.read())


def install_deps():
    with open('requirements.upip.txt', 'r') as requirements_file:
        for requirement in requirements_file:
            requirement = requirement.replace('\n', '')
            if requirement:
                print(
                    'Installing {requirement}'.format(requirement=requirement)
                )
                upip.install(requirement)


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
                    print('Connection failed')
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
    server_ip = '0.0.0.0'
    server_port = 80
    print(
        'Starting HTTP Server at {server_ip}:{server_port}'.format(
            server_ip=server_ip, server_port=server_port
        )
    )
    address = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    http_socket = socket.socket()
    http_socket.bind(address)
    http_socket.listen(1)

    while True:
        connection, _ = http_socket.accept()
        connection.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        connection.send('Hello World!')
        connection.close()


if __name__ == '__main__':
    if connect_wifi():
        # simple_http_server()
        install_deps()
