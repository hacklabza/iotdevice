import time


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
    print(value, value < threshold)
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


def timer(pin, rule, **kwargs):
    start_time = int(''.join(kwargs.get('start_time').split(':')))
    end_time = int(''.join(kwargs.get('end_time').split(':')))

    current_time = int(''.join([
        '0' + str(i) if i < 10 else
        str(i) for i in time.localtime()[3:5]
    ]))

    return end_time > current_time > start_time

