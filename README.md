# IoT Device

Generic Micropython based IoT Device (ESP8266/ESP32) Configurable Via https://github.com/hacklabza/iotserver

## ESP8266 Node

### Requirements

- esptool.py
- screen (OSX)
- ampy

### Installation

```bash
# Install the python deps
pip install -r requirements.txt

# Flash your board with the latest version of micropyton (https://micropython.org/download/esp8266/)
esptool.py --chip esp8266 --port /dev/tty.usbserial-01A7B50C erase_flash
esptool.py --port /dev/tty.usbserial-01A7B50C --baud 460800 write_flash --flash_size=detect 0 ~/Downloads/esp8266-20220618-v1.19.1.bin

# Check  that you get a micropython REPL (OSX) - ctrl+a k y to kill session
screen /dev/tty.usbserial-01A7B50C 115200

# Copy the config example and populate it
cp embedded/config/config.example.json embedded/config/config.json
vim embedded/config/config.json

# Check the file system on your board
ampy --port /dev/tty.usbserial-01A7B50C -d 0.5 ls

# Copy the config files over to your board
ampy --port /dev/tty.usbserial-01A7B50C -d 0.5 mkdir config
ampy --port /dev/tty.usbserial-01A7B50C -d 0.5 put embedded/config/config.json config/config.json

# Copy the executable files over to your board
ampy --port /dev/tty.usbserial-01A7B50C -d 0.5 put embedded/rules.py
ampy --port /dev/tty.usbserial-01A7B50C -d 0.5 put embedded/main.py
ampy --port /dev/tty.usbserial-01A7B50C -d 0.5 put embedded/boot.py
```
