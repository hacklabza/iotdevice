#!/usr/bin/env python
import json
import logging
import subprocess

import click

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def mkdir_cmd(dir_path):
    cmd_list = ['mpremote', 'mkdir', dir_path]
    logger.info("Executing mkdir command: %s", " ".join(cmd_list))
    return cmd_list


def put_cmd(src_path, dest_path=None):
    cmd_list = ['mpremote', 'cp', src_path]
    if dest_path:
        cmd_list.append(f':{dest_path}')
    logger.info("Executing put command: %s", " ".join(cmd_list))
    return cmd_list


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    '--chip',
    required=True,
    type=click.Choice(['esp8266', 'esp32'], case_sensitive=False),
    help='The chip type you want to flash',
)
@click.option(
    '--port',
    required=True,
    type=str,
    help='The usb port the device is connect to',
)
@click.option(
    '--bin-file', required=True, type=str, help='The path of the bin file'
)
def flash(chip, port, bin_file):
    """
    Erases the chip's flash and writes it to the chip again.
    """

    # Erase the flash
    click.echo('Erasing flash')
    subprocess.run(['esptool', '--chip', chip, '--port', port, 'erase-flash'])

    # Flash the chip
    click.echo(f'\n\nFlashing device with `{bin_file.split("/")[-1]}`')
    subprocess.run(
        [
            'esptool',
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
        ]
    )


@cli.command()
@click.option(
    '--init-config-file', is_flag=True, help='Reinitialise the config file'
)
@click.option(
    '--config-file',
    type=str,
    required=False,
    help='Reinitialise config from a file',
)
def install(init_config_file, config_file):
    """
    Installs the firmware to the chip
    """

    if init_config_file:
        with open('iotdevice/config/config.example.json', 'r') as _file:
            config = json.loads(_file.read())

        if config_file:
            init_config = {}
            with open(config_file, 'r') as _file:
                for line in _file.readlines():
                    key, value = line.strip().split(': ')
                    init_config[key] = value

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
            config['wifi']['essid'] = click.prompt(
                'WiFi SSID', type=click.STRING
            )
            config['wifi']['password'] = click.prompt(
                'WiFi Password',
                type=click.STRING,
                hide_input=True,
                confirmation_prompt=True,
            )

            config['mqtt']['host'] = click.prompt(
                'MQTT Host', type=click.STRING
            )

            iot_server_host = click.prompt('Iot Server Host', type=click.STRING)
            config['health']['url'] = (
                f'http://{iot_server_host}:8000/health/' + '{identifier}/'
            )

            config['main']['webrepl_password'] = click.prompt(
                'Web REPL Password',
                type=click.STRING,
                hide_input=True,
                confirmation_prompt=True,
            )

            drivers = click.prompt(
                'List of drivers to import', type=click.STRING, default=''
            )
            if drivers:
                config['drivers'] = [d.strip() for d in drivers.split(',')]

        with open('iotdevice/config/config.json', 'w') as _file:
            _file.write(json.dumps(config, indent=4))

    # Write the firmware to the device
    click.echo('Writing firmware')
    subprocess.run(mkdir_cmd('config'), check=True)
    subprocess.run(
        put_cmd('iotdevice/config/config.json', 'config/config.json'),
        check=True,
    )
    if config.get('drivers'):
        subprocess.run(mkdir_cmd('drivers'), check=True)
        subprocess.run(
            put_cmd('iotdevice/drivers/__init__.py', 'drivers/__init__.py'),
            check=True,
        )
        for driver_name in config['drivers']:
            subprocess.run(
                put_cmd(
                    f'iotdevice/drivers/{driver_name}.py',
                    f'drivers/{driver_name}.py',
                ),
                check=True,
            )

    subprocess.run(put_cmd('iotdevice/__init__.py', '__init__.py'), check=True)
    subprocess.run(put_cmd('iotdevice/utils.py', 'utils.py'), check=True)
    subprocess.run(put_cmd('iotdevice/rules.py', 'rules.py'), check=True)
    subprocess.run(put_cmd('iotdevice/main.py', 'main.py'), check=True)
    subprocess.run(put_cmd('iotdevice/boot.py', 'boot.py'), check=True)


if __name__ == '__main__':
    cli()
