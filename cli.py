#!/usr/bin/env python
import json
import subprocess

import click

'''
esptool.py --chip esp32 --port /dev/tty.usbserial-02031CC9 erase_flash
esptool.py --chip esp32 --port /dev/tty.usbserial-02031CC9 --baud 460800 write_flash -z 0x1000 ~/Downloads/esp32-20220618-v1.19.1.bin

# Check that you get a micropython REPL (OSX) - ctrl+a k y to kill session
screen /dev/tty.usbserial-02031CC9 115200

# Copy the config example and populate it - the wifi network details are essential
cp embedded/config/config.example.json embedded/config/config.json
vim embedded/config/config.json

# Check the file system on your board
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 ls

# Copy the config files over to your board
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 mkdir config
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 put embedded/config/config.json config/config.json

# Copy the executable files over to your board in order
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 put embedded/rules.py
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 put embedded/boot.py
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 put embedded/main.py

# Copy across any plugin and their associated drivers (if any) your project requires
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 mkdir drivers
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 mkdir plugins
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 put embedded/drivers/__init__.py drivers/__init__.py
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 put embedded/plugins/__init__.py plugins/__init__.py
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 put embedded/drivers/oled.py drivers/oled.py
ampy --port /dev/tty.usbserial-02031CC9 -d 0.5 put embedded/plugins/oled.py plugins/oled.py
'''


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

    config['wifi']['essid'] = click.prompt(
        'WiFi SSID', type=str
    )
    config['wifi']['password'] = click.prompt(
        'WiFi Password', type=str
    )
    config['mqtt']['host'] = click.prompt(
        'MQTT Host', type=str
    )
    config['main']['webrepl_password'] = click.prompt(
        'Web REPL Password', type=str
    )

    iot_server_host = click.prompt('Iot Server Host', type=str)
    config['health']['url'] = (
        f'http://{iot_server_host}:8000/health/' + '{identifier}/'
    )

    with open('embedded/config/config.json', 'w') as _file:
        _file.write(json.dumps(config, indent=4))

    mkdir = lambda *args: [
        'ampy', '--port', args[0], '-d', '0.5', 'mkdir', args[1]
    ]
    put = lambda *args: [
        'ampy', '--port', args[0], '-d', '0.5', 'put', args[1], args[2]
    ]

    # Write the firmware to the device
    if debug:
        click.echo(f'Writing firmware to `{port}`')
    subprocess.run(mkdir(port, 'config'))
    subprocess.run(
        put(port, 'embedded/config/config.json', 'config/config.json')
    )
    subprocess.run(put(port, 'embedded/rules.py', 'rules.py'))
    subprocess.run(put(port, 'embedded/boot.py', 'boot.py'))
    subprocess.run(put(port, 'embedded/main.py', 'main.py'))


if __name__ == '__main__':
    cli()
