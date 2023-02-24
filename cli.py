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
@click.option('--debug', is_flag=True)
def flash(chip, port, bin_file, debug):
    """
    Erases the chip's flash and writes it to the chip again.
    """
    # Erase the flash
    if debug:
        click.echo('Erasing flash')
    subprocess.run([
        'esptool.py',
        '--chip',
        chip,
        '--port',
        port,
        'erase_flash'
    ])

    # Flash the chip
    if debug:
        bin_file_name = bin_file.split('/')[-1]
        click.echo(f'\n\nFlashing device with `{bin_file_name}`')
    subprocess.run([
        'esptool.py',
        '--chip',
        chip,
        '--port',
        port,
        '--baud',
        '460800',
        'write_flash',
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
@click.option('--debug', is_flag=True)
def install(port, debug):
    """
    Installs the firmware to the chip
    """
    with open('embedded/config/config.example.json', 'r') as _file:
        config = json.loads(_file.read())

    config['wifi']['essid'] = click.prompt('WiFi SSID', type=str)
    config['wifi']['password'] = click.prompt('WiFi Password', type=str)
    config['mqtt']['host'] = click.prompt('MQTT Host', type=str)
    config['main']['webrepl_password'] = click.prompt(
        'Web REPL Password', type=str
    )

    iot_server_host = click.prompt('Iot Server Host', type=str)
    config['health']['url'] = (
        f'http://{iot_server_host}:8000/health/' + '{identifier}/'
    )

    with open('embedded/config/config.json', 'w') as _file:
        _file.write(json.dumps(config, indent=4))

    # Write the firmware to the device
    if debug:
        click.echo(f'Writing firmware to `{port}`')
    subprocess.run(mkdir_cmd(port, 'config'))
    subprocess.run(
        put_cmd(port, 'embedded/config/config.json', 'config/config.json')
    )
    subprocess.run(put_cmd(port, 'embedded/rules.py'))
    subprocess.run(put_cmd(port, 'embedded/boot.py'))
    subprocess.run(put_cmd(port, 'embedded/main.py'))


if __name__ == '__main__':
    cli()
