# IoT Device

Generic Micropython based IoT Device (ESP8266/ESP32) - Configurable via https://github.com/hacklabza/iotserver

## ESP8266/ESP32 Node

### Requirements

- esptool.py
- screen (OSX)
- ampy

### Installation

Either a manual install or commandline install is available - the cli is recommended. Once this is done, head over to the iotserver and create the device.

#### CLI (Recommended)

```bash
# Install the python deps
pip install -r requirements.txt

# Get help
./cli.py --help
./cli.py flash --help
./cli.py install --help

# Flash the chip
./cli.py flash --chip esp32 --port /dev/tty.usbserial-02031CC9 --bin-file ~/Downloads/esp32-20220618-v1.19.1.bin

# Install the base firmware and follow the prompts to populate the base config file if --init-config flag is set
./cli.py install --port /dev/tty.usbserial-02031CC9 --init-config

# Connect via screen to get the IP Address of the device
screen /dev/tty.usbserial-02031CC9 115200
```

#### Manual

```bash
# Install the python deps
pip install -r requirements.txt

# Flash your board with the latest version of micropython for ESP8266 (https://micropython.org/download/esp8266/)
esptool.py --chip esp8266 --port /dev/tty.usbserial-01A7B50C erase_flash
esptool.py --port /dev/tty.usbserial-01A7B50C --baud 460800 write_flash --flash_size=detect 0 ~/Downloads/esp8266-20220618-v1.19.1.bin

# OR flash your board with the latest version of micropython for ESP32 (https://micropython.org/download/esp32/)
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

# Connect again via screen to get the IP Address of the device
screen /dev/tty.usbserial-02031CC9 115200
```

### Example JSON config

```json
{
  "wifi": {
    "essid": "********",
    "password": "********",
    "retry_count": 10
  },
  "mqtt": {
    "client_id": "b6d49b8d-c31f-4809-a955-a814de6ab3f3}",
    "host": "192.168.1.5",
    "username": null,
    "password": null,
    "ssl_enabled": false,
    "lastwill": {
      "topic": "iot-devices/b6d49b8d-c31f-4809-a955-a814de6ab3f3/logs",
      "message": "Device disconnected from MQTT"
    }
  },
  "logging": {
    "level": "warning"
  },
  "main": {
    "identifier": "b6d49b8d-c31f-4809-a955-a814de6ab3f3",
    "process_interval": 15,
    "webrepl_password": "ae3200ef1"
  },
  "time": {
    "server": "za.pool.ntp.org"
  },
  "health": {
    "url": "http://192.168.0.101:8000/health/b6d49b8d-c31f-4809-a955-a814de6ab3f3/"
  },
  "pins": [
    {
      "pin_number": null,
      "name": "Day Timer",
      "identifier": "day_timer",
      "analog": false,
      "read": true,
      "rule": {
        "action": "timer",
        "input": {
          "start_time": "07:00",
          "end_time": "15:00"
        }
      }
    },
    {
      "pin_number": 5,
      "name": "Soil Moisture Sensor",
      "identifier": "soil_moisture_sensor",
      "analog": false,
      "read": true,
      "rule": {
        "action": "read_bool_sample",
        "input": {
          "reverse": true,
          "sample_size": 5
        }
      }
    },
    {
      "pin_number": null,
      "name": "Weather Service Forecast",
      "identifier": "weather_service_forecast",
      "analog": false,
      "read": true,
      "rule": {
        "action": "service",
        "input": {
          "url": "http://192.168.1.5:8000/api/devices/locations/1/weather/?type=forecast",
          "auth_header": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXX"
        }
      }
    },
    {
      "pin_number": null,
      "name": "Weather Service Current",
      "identifier": "weather_service_current",
      "analog": false,
      "read": true,
      "rule": {
        "action": "service",
        "input": {
          "url": "http://192.168.1.5:8000/api/devices/locations/1/weather/?type=current",
          "auth_header": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXX"
        }
      }
    },
    {
      "pin_number": null,
      "name": "MQTT Toggle",
      "identifier": "mqtt_toggle",
      "analog": false,
      "read": true,
      "rule": {
        "action": "mqtt_toggle",
        "input": {
          "topic": "iot-devices/b6d49b8d-c31f-4809-a955-a814de6ab3f3/toggle"
        }
      }
    },
    {
      "pin_number": 4,
      "name": "Solenid Relay",
      "identifier": "solenoid_relay",
      "analog": false,
      "read": false,
      "rule": {
        "action": "toggle",
        "input": {
          "on": {
            "conditions": {
              "must": {
                "soil_moisture_sensor": {
                  "operator": "eq",
                  "value": true
                },
                "timer": {
                  "operator": "eq",
                  "value": true
                },
                "weather_service_forecast.0.rain": {
                  "operator": "eq",
                  "value": false
                },
                 "weather_service_forecast.1.rain": {
                  "operator": "eq",
                  "value": false
                },
                "weather_service_current.temperature": {
                  "operator": "gt",
                  "value": 10
                },
                "weather_service_current.rain": {
                  "operator": "eq",
                  "value": false
                }
              },
              "should": {
                "mqtt_toggle": {
                  "operator": "eq",
                  "value": true
                }
              }
            }
          }
        }
      }
    }
  ]
}
```

I.e. The solenoid relay will switch on if the soil moisture returns dry, the time is between 07:00 and 15:00, it will not rain today and tomorrow, the temperature is above 10 and it is not currently raining or it has been toggled on by via MQTT (override).
