# IoT Server

A simple IoT Server which allows the user to control ESP8266 nodes

## Server

### Requirements

## ESP8266 Nodes

### Requirements

- esptool.py
- screen (OSX)
- ampy

### Installation

```bash
pip install esptool

esptool.py --chip esp8266 --port /dev/tty.usbserial-01A7B50C erase_flash
esptool.py --port /dev/tty.usbserial-01A7B50C --baud 460800 write_flash --flash_size=detect 0 ~/Downloads/esp8266-20210418-v1.15.bin

screen /dev/tty.usbserial-01A7B50C 115200

ampy --port /dev/tty.usbserial-01A7B50C ls
```
