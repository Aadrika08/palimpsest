"""Shared collection policy: historical frozen pins (see tests/frozen_pins.py)."""
import pytest

import frozen_pins


def pytest_collection_modifyitems(config, items):
    affected = frozen_pins.affected_tests()
    for item in items:
        name = affected.get(item.nodeid.split('[', 1)[0])
        if name is not None and frozen_pins.drift(name):
            item.add_marker(pytest.mark.skip(reason=frozen_pins.skip_reason(name)))
