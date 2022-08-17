# IoT Device

Generic Micropython based IoT Device (ESP8266/ESP32) - Configurable via https://github.com/hacklabza/iotserver

## ESP8266/ESP32 Node

### Requirements

- esptool.py
- screen (OSX)
- ampy

### Installation

```bash
# Install the python deps
pip install -r requirements.txt

# Flash your board with the latest version of micropython for ESP8266 (https://micropython.org/download/esp8266/)
esptool.py --chip esp8266 --port /dev/tty.usbserial-01A7B50C erase_flash
esptool.py --port /dev/tty.usbserial-01A7B50C --baud 460800 write_flash --flash_size=detect 0 ~/Downloads/esp8266-20220618-v1.19.1.bin

# OR flash your board with the latest version of micropython for ESP32 (https://micropython.org/download/esp32/)
esptool.py --chip esp32 --port /dev/tty.usbserial-02031CC9 erase_flash
esptool.py --chip esp32 --port /dev/tty.usbserial-02031CC9 --baud 460800 write_flash -z 0x1000 ~/Downloads/esp32-20220618-v1.19.1.bin

# Check  that you get a micropython REPL (OSX) - ctrl+a k y to kill session
screen /dev/tty.usbserial-01A7B50C 115200

# Copy the config example and populate it - the wifi network details are essential
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

Once this is done, head over to the iotserver and create the device.
