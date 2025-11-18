#!/usr/bin/env python
import json
import subprocess

import click


def mkdir_cmd(port, dir_path):
    return ['ampy', '--port', port, '-d', '0.5', 'mkdir', dir_path]


def put_cmd(port, src_path, dest_path=None):
    cmd_list = ['ampy', '--port', port, '-d', '0.5', 'put', src_path]
    if dest_path:
        cmd_list.append(dest_path)
    return cmd_list


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    '--chip',
    required=True,
    type=click.Choice(['esp8266', 'esp32'], case_sensitive=False),
    help='The chip type you want to flash'
)
@click.option(
    '--port',
    required=True,
    type=str,
    help='The usb port the device is connect to'
)
@click.option('--bin-file', required=True, type=str, help='The path of the bin file')
def flash(chip, port, bin_file):
    """
    Erases the chip's flash and writes it to the chip again.
    """

    # Erase the flash
    click.echo('Erasing flash')
    subprocess.run([
        'esptool.py',
        '--chip',
        chip,
        '--port',
        port,
        'erase-flash'
    ])

    # Flash the chip
    click.echo(f'\n\nFlashing device with `{bin_file.split("/")[-1]}`')
    subprocess.run([
        'esptool.py',
        '--chip',
        chip,
        '--port',
        port,
        '--baud',
        '460800',
        'write-flash',
        '-z',
        '0x1000',
        bin_file,
    ])


@cli.command()
@click.option(
    '--port',
    required=True,
    type=str,
    help='The usb port the device is connect to'
)
@click.option('--init-config', is_flag=True, help='Reinitialise the config file')
@click.option(
    '--config-file',
    type=str,
    required=False,
    help='Reinitialise config from a file'
)
def install(port, init_config, config_file):
    """
    Installs the firmware to the chip
    """

    if init_config:
        with open('iotdevice/config/config.example.json', 'r') as _file:
            config = json.loads(_file.read())

        if config_file:
            with open(config_file, 'r') as _file:
                init_config = dict(
                    [item.strip().split(': ') for item in _file.readlines()]
                )

            config['wifi']['essid'] = init_config['wifi_essid']
            config['wifi']['password'] = init_config['wifi_password']

            config['mqtt']['host'] = init_config['mqtt_host']

            iot_server_host = init_config['iot_server_host']
            config['health']['url'] = (
                f'http://{iot_server_host}:8000/health/' + '{identifier}/'
            )

            config['main']['webrepl_password'] = init_config['webrepl_password']

            drivers = init_config.get('drivers', None)
            if drivers:
                config['drivers'] = [d.strip() for d in drivers.split(',')]

        else:
            config['wifi']['essid'] = click.prompt('WiFi SSID', type=click.STRING)
            config['wifi']['password'] = click.prompt(
                'WiFi Password',
                type=click.STRING,
                hide_input=True,
                confirmation_prompt=True
            )

            config['mqtt']['host'] = click.prompt('MQTT Host', type=click.STRING)

            iot_server_host = click.prompt('Iot Server Host', type=click.STRING)
            config['health']['url'] = (
                f'http://{iot_server_host}:8000/health/' + '{identifier}/'
            )

            config['main']['webrepl_password'] = click.prompt(
                'Web REPL Password',
                type=click.STRING,
                hide_input=True,
                confirmation_prompt=True
            )

            drivers = click.prompt('List of drivers to import', type=click.STRING, default='')
            if drivers:
                config['drivers'] = [d.strip() for d in drivers.split(',')]

        with open('iotdevice/config/config.json', 'w') as _file:
            _file.write(json.dumps(config, indent=4))

    # Write the firmware to the device
    click.echo(f'Writing firmware to `{port}`')
    subprocess.run(mkdir_cmd(port, 'config'))
    subprocess.run(
        put_cmd(port, 'iotdevice/config/config.json', 'config/config.json')
    )
    if config.get('drivers'):
        subprocess.run(mkdir_cmd(port, 'drivers'))
        subprocess.run(
            put_cmd(
                port,
                'iotdevice/drivers/__init__.py',
                'drivers/__init__.py'
            )
        )
        for driver_name in config['drivers']:
            subprocess.run(
                put_cmd(
                    port,
                    f'iotdevice/drivers/{driver_name}.py',
                    f'drivers/{driver_name}.py'
                )
            )

    subprocess.run(put_cmd(port, 'iotdevice/__init__.py'))
    subprocess.run(put_cmd(port, 'iotdevice/utils.py'))
    subprocess.run(put_cmd(port, 'iotdevice/rules.py'))
    subprocess.run(put_cmd(port, 'iotdevice/boot.py'))
    subprocess.run(put_cmd(port, 'iotdevice/main.py'))


if __name__ == '__main__':
    cli()
