"""RGB strip selection, live frames and read-only refresh regressions."""
import struct

import pytest
from PyQt5.QtWidgets import QWidget

from amk.protocol import RgbColor, RgbLed
from amk.rgb_strip import RgbStrip
from protocol.keyboard_comm import Keyboard, KleSerial
from vial_device import VialKeyboard


def make_keyboard(v2=False):
    packets = []
    frame = [0]

    def send(dev, msg, retries=1):
        # Every operation exercised by refresh/polling must be a frame getter.
        assert msg[:2] == b'\xfd\x3c', 'Unexpected write/command: ' + msg.hex()
        if v2:
            start, count = struct.unpack('<HB', msg[2:])
            header = b'\xfd\x3c\xaa' + struct.pack('<HB', start, count)
        else:
            start, count = msg[2:]
            header = bytes([0xfd, 0x3c, 0xaa, start, count])
        packets.append((start, count))
        frame[0] = frame[0] % 200 + 1
        colors = b''.join(bytes([(start + i + frame[0] * (1 + (start + i) % 5)) % 255, (start + i) % 255, 60]) for i in range(count))
        return (header + colors).ljust(32, b'\0')

    kb = Keyboard(None, usb_send=send)
    kb.amk_rgb_led = {'protocol_v2': v2}
    kb.amk_feature = {'bright': True, 'use_custom_color': True}
    layout = KleSerial().deserialize([['0,0', '0,1', '0,2'], ['1,0', '1,1']]).keys
    for key in layout:
        key.row, key.col = map(int, key.labels[0].split(','))
        key.encoder_idx = key.encoder_dir = None
        key.layout_index = key.layout_option = -1
    kb.amk_rgb_strip = dict(start=64, count=7, layout=layout, effects=['Static', 'Custom'],
        strips=[dict(name='First', start=2, count=3, mode=0, master=1, sync=1, bright=57, use_custom_color=True),
                dict(name='Second', start=5, count=2, mode=1, master=0, sync=255, bright=123, use_custom_color=False)],
        leds={i: RgbLed(i, 0, 0, 255, 0x81) for i in range(66, 71)})
    kb.amk_rgb_data = [RgbColor(0, 0, 0) for _ in range(128)]
    return kb, packets


def device(kb):
    dev = VialKeyboard(dict(vendor_id=0xdead, product_id=0xbeef, path=b'/mock/strip'))
    dev.keyboard = kb
    return dev


@pytest.fixture
def editor(qtbot):
    owner = QWidget()
    qtbot.addWidget(owner)
    result = RgbStrip(None)
    owner.setLayout(result)
    yield result
    result.deactivate()


def test_first_strip_and_controls_initialize_without_setters(editor):
    kb, packets = make_keyboard()
    editor.rebuild(device(kb))
    assert editor.strip == editor.strip_lst.currentRow() == 0
    assert editor.mode_lst.currentRow() == 0
    assert editor.sync_cbx.isChecked() and editor.sync_cbx.isEnabled()
    assert editor.use_custom_cbx.isChecked()
    assert editor.bright_sld.value() == 57
    assert not editor.on_cbx.isEnabled()
    assert packets == []  # Rebuild only displays cached settings.
    editor.strip_lst.setCurrentRow(1)
    assert editor.strip == 1 and editor.mode_lst.currentRow() == 1
    assert editor.on_cbx.isEnabled()
    assert not editor.sync_cbx.isChecked() and not editor.use_custom_cbx.isChecked()
    assert editor.bright_sld.value() == 123
    assert packets == []


@pytest.mark.parametrize('v2', [False, True])
def test_first_tick_and_selection_update_correct_ranges_and_preview(editor, v2):
    kb, packets = make_keyboard(v2)
    editor.rebuild(device(kb))
    editor.activate()
    packets.clear()
    editor.on_rgb_strip_poller()
    assert packets == [(64, 7)]
    pixel = editor.keyboardWidget.widgets[0]
    before = pixel.mask_color.red()
    editor.on_rgb_strip_poller()
    assert pixel.mask_color.red() != before
    first_color = kb.amk_rgb_data[66]
    editor.strip_lst.setCurrentRow(1)
    packets.clear()
    editor.on_rgb_strip_poller()
    assert packets == [(64, 7)]
    assert kb.amk_rgb_data[66] is not first_color  # Selection cannot freeze other previews.
    assert editor.keyboardWidget.widgets[3].mask_color.red() == kb.amk_rgb_data[69].get_red()


def test_timer_stops_and_resumes_preserving_selection(editor, qtbot):
    kb, packets = make_keyboard()
    editor.rebuild(device(kb))
    timer = editor.timer
    editor.strip_lst.setCurrentRow(1)
    editor.activate()
    assert editor.strip == editor.strip_lst.currentRow() == 1
    assert timer.interval() == 50
    editor.rebuild(editor.device)
    assert timer.isActive() and editor.strip == editor.strip_lst.currentRow() == 1
    initial = len(packets)
    qtbot.waitUntil(lambda: len(packets) > initial, timeout=1000)
    editor.deactivate()
    stopped = len(packets)
    qtbot.wait(120)
    assert len(packets) == stopped and not timer.isActive()
    editor.activate()
    assert editor.timer is timer and editor.strip == editor.strip_lst.currentRow() == 1
    resumed = len(packets)
    qtbot.waitUntil(lambda: len(packets) > resumed, timeout=1000)
    assert packets[-1] == (64, 7)


def test_disconnect_reconnect_and_different_device(editor):
    kb, packets = make_keyboard()
    editor.rebuild(device(kb))
    editor.strip_lst.setCurrentRow(1)
    editor.activate()
    editor.rebuild(None)
    assert editor.strip == -1 and editor.strip_lst.currentRow() == -1
    assert editor.keyboard is None and not editor.timer.isActive()
    editor.on_rgb_strip_poller()
    editor.activate()
    assert not editor.timer.isActive()
    replacement, replacement_packets = make_keyboard()
    replacement.amk_rgb_strip['strips'] = replacement.amk_rgb_strip['strips'][:1]
    editor.rebuild(device(replacement))
    assert editor.strip == editor.strip_lst.currentRow() == 0
    replacement_packets.clear()
    editor.on_rgb_strip_poller()
    assert replacement_packets == [(64, 7)]
    another, _ = make_keyboard()
    editor.rebuild(device(another))
    assert editor.strip == editor.strip_lst.currentRow() == 0


@pytest.mark.parametrize('definition', [{}, {'strips': []}])
def test_no_strips_never_reads_or_indexes(editor, definition):
    kb, packets = make_keyboard()
    kb.amk_rgb_strip = definition
    editor.rebuild(device(kb))
    editor.activate()
    editor.on_rgb_strip_poller()
    assert not editor.valid() and editor.strip == -1
    assert editor.strip_lst.count() == 0 and not editor.timer.isActive()
    assert packets == []


def test_invalid_index_refresh_falls_back_without_setters(editor):
    kb, packets = make_keyboard()
    editor.rebuild(device(kb))
    editor.strip = 999
    editor.reset_keyboard_widget()
    assert editor.strip == editor.strip_lst.currentRow() == 0
    assert packets == []
