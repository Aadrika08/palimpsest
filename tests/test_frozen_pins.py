"""Historical frozen pins are checked against main's history, never against the current tree.

Each protocol in tests/frozen_pins.py froze exact file bytes (or a repository location)
before main's integration. Its listed tests are skipped as historical while the current
checkout differs; these checks keep the pins meaningful: every byte pin must name the
exact bytes of the file at some commit in HEAD's history.
"""
from pathlib import Path

import pytest

import frozen_pins

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', sorted(frozen_pins.PROTOCOLS))
def test_every_byte_pin_names_the_file_at_a_commit_in_history(name):
    pins = frozen_pins.pins(name)
    for path, digest in sorted(pins.items()):
        commit = frozen_pins.commit_holding(path, digest)
        assert commit is not None, f'{name}: no commit in history holds {path} with sha256 {digest}'
        assert frozen_pins.sha256(frozen_pins.show(commit, path)) == digest


@pytest.mark.parametrize('name', sorted(frozen_pins.PROTOCOLS))
def test_every_protocol_declares_a_pin_and_an_absolute_frozen_root(name):
    root = frozen_pins.frozen_root(name)
    assert frozen_pins.pins(name) or root is not None
    assert root is None or root.startswith('/')


def test_every_listed_test_exists_once():
    affected = frozen_pins.affected_tests()
    for nodeid in affected:
        path, *parts = nodeid.split('::')
        source = (ROOT / path).read_text()
        assert f'def {parts[-1]}(' in source, nodeid
        if len(parts) == 2:
            assert f'class {parts[0]}(' in source, nodeid


def test_skip_reason_is_explicit_and_only_names_real_drift():
    for name in frozen_pins.PROTOCOLS:
        if frozen_pins.drift(name):
            reason = frozen_pins.skip_reason(name)
            assert reason.startswith(f'historical frozen pin ({name}): ')
            assert frozen_pins.POLICY in reason and 're-pinning' in reason
