"""Expected HID collection filtering stays diagnosable without false warnings."""
import logging
import sys

import pytest

import util


def test_expected_collection_rejection_is_debug(caplog, monkeypatch):
    def forbidden_open():
        pytest.fail('A non-Raw HID collection must never be opened')
    monkeypatch.setattr(util.hid, 'device', forbidden_open)
    with caplog.at_level(logging.DEBUG):
        assert not util.is_rawhid({'path': b'/input-only', 'usage_page': 1, 'usage': 6}, quiet=False)
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.DEBUG
    assert 'usage_page=0001 usage=06' in caplog.text


@pytest.mark.parametrize('descriptor', [
    {'path': b'/raw'},
    {'path': b'/raw', 'usage_page': None, 'usage': 0x61},
    {'path': b'/raw', 'usage_page': 0xFF60, 'usage': '97'},
    {'usage_page': 0xFF60, 'usage': 0x61},
])
def test_unexpected_descriptor_remains_warning(caplog, descriptor):
    with caplog.at_level(logging.WARNING):
        assert not util.is_rawhid(descriptor, quiet=False)
    assert caplog.records[0].levelno == logging.WARNING
    assert 'unexpected descriptor' in caplog.text


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='Linux hidraw permission check')
def test_rawhid_permission_failure_remains_warning(caplog, monkeypatch):
    class Denied:
        def open_path(self, path):
            raise PermissionError('fixture: permission denied')
    monkeypatch.setattr(util.hid, 'device', Denied)
    with caplog.at_level(logging.WARNING):
        assert not util.is_rawhid({'path': b'/raw', 'usage_page': 0xFF60, 'usage': 0x61}, quiet=False)
    assert 'open_path error' in caplog.text
    assert 'permission denied' in caplog.text
    assert caplog.records[0].levelno == logging.WARNING
