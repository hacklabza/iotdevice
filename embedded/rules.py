import time


MQTT_SUB_MSG = {}


def get_mqtt_msg(topic, msg):
    global MQTT_SUB_MSG
    if topic and msg:
        MQTT_SUB_MSG[str(topic.decode('utf-8'))] = str(msg.decode('utf-8'))


def read(pin, rule, **kwargs):
    reverse = kwargs.get('reverse', False)
    if reverse:
        return not pin.value()
    return pin.value()


def read_avg_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_min_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return min(readings)


def read_max_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return max(readings)


def read_bool_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read(pin, rule, **kwargs))
        time.sleep(0.5)
    return all(readings)


def read_analog(pin, rule, **kwargs):
    return pin.read()


def read_bool_analog(pin, rule, **kwargs):
    threshold = kwargs.get('threshold', 1024)
    value = pin.read()
    return value > threshold


def read_avg_analog_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_bool_analog_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(read_bool_analog(pin, rule, **kwargs))
        time.sleep(0.5)
    return all(readings)


def toggle(pin, rule, **kwargs):
    on = kwargs.get('on')
    pin.on() if on else pin.off()
    return pin.value()


def mqtt_toggle(pin, rule, **kwargs):
    mqtt = kwargs.get('mqtt')
    queue = kwargs.get('queue')

    mqtt.set_callback(get_mqtt_msg)
    mqtt.subscribe(queue)
    mqtt.check_msg()

    return int(MQTT_SUB_MSG.get(queue, 0))


def timer(pin, rule, **kwargs):
    start_time = int(kwargs.get('gmt_start_time').replace(':', ''))
    end_time = int(kwargs.get('gmt_end_time').replace(':', ''))

    current_time = int(''.join(str(p) for p in time.localtime()[3:5]))

    return end_time > current_time > start_time

