"""AMK synchronization capability and read-only GUI refresh regressions."""
from types import SimpleNamespace

import pytest
from PyQt5.QtWidgets import QCheckBox

from amk.protocol import (AMK_PROTOCOL_GET_RGB_PARAM, AMK_PROTOCOL_OK,
                          AMK_PROTOCOL_PREFIX, RGB_PARAM_SYNC, RGB_TYPE_STRIP)
from amk.rgb_strip import RgbStrip
from protocol.keyboard_comm import Keyboard


def keyboard_with_strips(strips, sync_status=AMK_PROTOCOL_OK, optional=False):
    requests = []

    def send(dev, msg, retries=1):
        # This fake accepts getters only, including when a checkbox is refreshed.
        assert msg[:3] == bytes([AMK_PROTOCOL_PREFIX, AMK_PROTOCOL_GET_RGB_PARAM, RGB_TYPE_STRIP])
        assert len(msg) == 5
        requests.append(bytes(msg))
        param, index = msg[3:5]
        status = sync_status if param == RGB_PARAM_SYNC else AMK_PROTOCOL_OK
        return bytes([0xFD, 0x3D, status, index, 0, 17, 23]).ljust(32, b'\0')

    keyboard = Keyboard(None, usb_send=send)
    keyboard.amk_rgb_strip = {"strips": strips}
    keyboard.amk_feature = {"bright": optional, "use_custom_color": optional}
    return keyboard, requests


@pytest.mark.parametrize('definition', [
    {}, {'master': None}, {'master': False}, {'master': True},
    {'master': -1}, {'master': 2}, {'master': 255},
    {'master': '0'}, {'master': 0.0},
])
def test_unsupported_sync_is_not_requested(definition):
    keyboard, requests = keyboard_with_strips([{}, dict(definition)])
    keyboard.reload_amk_rgb_params(RGB_TYPE_STRIP)
    assert [request[3:] for request in requests] == [b'\0\0', b'\2\0', b'\0\1', b'\2\1']
    assert all('sync' not in strip for strip in keyboard.amk_rgb_strip['strips'])


def test_supported_sync_keeps_original_wire_format_and_zero_master():
    keyboard, requests = keyboard_with_strips([{'master': 1}, {'master': 0}])
    keyboard.reload_amk_rgb_params(RGB_TYPE_STRIP)
    assert [msg.hex() for msg in requests] == [
        'fd3d010000', 'fd3d010200', 'fd3d010300',
        'fd3d010001', 'fd3d010201', 'fd3d010301',
    ]
    assert [strip['sync'] for strip in keyboard.amk_rgb_strip['strips']] == [0, 0]


def test_mixed_strips_keep_optional_rgb_reads():
    keyboard, requests = keyboard_with_strips([{}, {'master': 0}], optional=True)
    keyboard.reload_amk_rgb_params(RGB_TYPE_STRIP)
    assert [(msg[3], msg[4]) for msg in requests] == [
        (0, 0), (2, 0), (4, 0), (5, 0),
        (0, 1), (2, 1), (3, 1), (4, 1), (5, 1),
    ]
    assert 'sync' not in keyboard.amk_rgb_strip['strips'][0]
    assert keyboard.amk_rgb_strip['strips'][1]['sync'] == 0


def test_rejected_supported_sync_remains_visible_and_unavailable(capsys):
    keyboard, requests = keyboard_with_strips([{}, {'master': 0, 'sync': 0}], sync_status=0x55)
    keyboard.reload_amk_rgb_params(RGB_TYPE_STRIP)
    assert any(msg[3:] == bytes([RGB_PARAM_SYNC, 1]) for msg in requests)
    assert 'sync' not in keyboard.amk_rgb_strip['strips'][1]
    assert 'Failed to reload rgb param:' in capsys.readouterr().out


@pytest.mark.parametrize('definition,status,enabled', [
    ({}, AMK_PROTOCOL_OK, False),
    ({'master': '0'}, AMK_PROTOCOL_OK, False),
    ({'master': 0}, AMK_PROTOCOL_OK, True),
    ({'master': 0, 'sync': 0}, 0x55, False),
])
def test_sync_checkbox_refresh_never_writes(qtbot, definition, status, enabled):
    keyboard, requests = keyboard_with_strips([{}, dict(definition)], sync_status=status)
    keyboard.reload_amk_rgb_params(RGB_TYPE_STRIP)
    before = list(requests)
    checkbox = QCheckBox()
    qtbot.addWidget(checkbox)
    # A programmatic refresh must not emit the user-change signal or send SET.
    changes = []
    checkbox.stateChanged.connect(changes.append)
    editor = SimpleNamespace(keyboard=keyboard, strip=1, sync_cbx=checkbox)
    RgbStrip.reset_sync_widgets(editor)
    assert checkbox.isEnabled() == enabled
    if enabled:
        assert checkbox.isChecked()
    assert changes == []
    assert requests == before
