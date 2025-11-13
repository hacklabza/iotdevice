import json


def load_config():
    """
    Loads the configuration file from the filesystem."""
    with open('config/config.json', 'r') as config_file:
        return json.loads(config_file.read())


def find_xpath_value(response, xpaths):
    """
    Recursively finds a value in a nested dict/list structure based on a list of xpaths.
    """
    xpath = xpaths.pop()  # paths must be reversed before passing it in

    try:
        response = response[int(xpath)]
    except ValueError:
        try:
            response = response[xpath]
        except (KeyError, TypeError):
            return None
    except (KeyError, IndexError, TypeError):
        return None

    if not len(xpaths):
        return response

    return find_xpath_value(response, xpaths)


def evaluate_condition(input, operator, value):
    """
    Evaluates a condition and returns a boolean.
    """
    try:
        if operator == 'eq':
            return input == value
        elif operator == 'gt':
            return input > value
        elif operator == 'lt':
            return input < value
    except TypeError:
        return False


def handle_conditions(rule_values, input_value):
    """
    Returns a dict of condition boolean values to be evaluated.
    """
    condition_values = {'must': [], 'should': []}
    for condition_type, conditions in input_value['conditions'].items():
        if condition_type in condition_values:
            for pin_identifier, condition in conditions.items():
                xpaths = pin_identifier.split('.')
                xpaths.reverse()
                condition_values[condition_type].append(
                    evaluate_condition(
                        find_xpath_value(rule_values, xpaths),
                        **condition
                    )
                )

    return condition_values
