import time


def read(pin, rule, **kwargs):
    return pin.value()


def read_avg_sample(pin, rule, **kwargs):
    readings = []
    for _ in range(kwargs.get('sample_size', 0)):
        readings.append(pin.value())
        time.sleep(0.5)
    return sum(readings) / len(readings)


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


def toggle(pin, rule, **kwargs):
    off = kwargs.get('off')
    pin.off() if off else pin.on()
    return pin.value()
