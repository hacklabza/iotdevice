import sys

import pytest


@pytest.fixture(scope="session", autouse=True)
def cleanup_mocks():
    """Clean up MicroPython mock modules after tests to prevent coverage DB issues."""
    yield
    mock_modules = [
        "ntptime",
        "machine",
        "mip",
        "gc",
        "network",
        "time",
        "umqtt",
        "umqtt.simple",
    ]
    for module in mock_modules:
        sys.modules.pop(module, None)
