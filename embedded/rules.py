import time


def read(pin, rule, **kwargs):
    return pin.value()


def read_avg_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(pin.value())
        time.sleep(0.5)
    return int(sum(readings) / len(readings))


def read_min_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(pin.value())
        time.sleep(0.5)
    return min(readings)


def read_max_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(pin.value())
        time.sleep(0.5)
    return max(readings)


def read_bool_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(pin.value())
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
    off = kwargs.get('off')
    pin.off() if off else pin.on()
    return pin.value()

