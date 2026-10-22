"""Changing full-page frames, repainting, range batching and bounded GUI work."""
from types import SimpleNamespace

import pytest
from PyQt5.QtCore import QEvent, QObject

from amk.protocol import RgbColor, RgbLed
from protocol.keyboard_comm import KleSerial
from test.test_rgb_strip_live import editor, make_keyboard, device


def colors(editor):
    return [pixel.mask_color.getRgb()[:3] for pixel in editor.keyboardWidget.widgets]


@pytest.mark.parametrize('v2', [False, True])
def test_every_preview_changes_and_repaints_without_selection(editor, qtbot, v2):
    kb, packets = make_keyboard(v2)
    editor.rebuild(device(kb))
    owner = editor.parentWidget()
    owner.show()

    class PaintObserver(QObject):
        def __init__(self):
            super().__init__()
            self.paints = 0
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Paint:
                self.paints += 1
            return False

    observer = PaintObserver()
    editor.keyboardWidget.installEventFilter(observer)
    editor.activate()
    editor.deactivate()  # Manual ticks make frame comparisons deterministic.
    qtbot.waitUntil(lambda: observer.paints > 0)
    before = colors(editor)
    paints = observer.paints
    for selection in [1, 0, 1]:
        editor.strip_lst.setCurrentRow(selection)
        packets.clear()
        editor.on_rgb_strip_poller()
        after = colors(editor)
        assert all(a != b for a, b in zip(before, after))
        # Independent LED values, correct global offsets, all rows refreshed.
        assert len(set(after)) == len(after)
        for pixel, color in zip(editor.keyboardWidget.widgets, after):
            index = editor.get_led_index(pixel.desc.row, pixel.desc.col)
            value = kb.amk_rgb_data[index]
            assert color == (value.get_red(), value.get_green(), value.get_blue())
        assert packets == [(64, 7)]
        before = after
    qtbot.waitUntil(lambda: observer.paints > paints)
    assert editor.strip == editor.strip_lst.currentRow() == 1
    editor.activate()
    assert colors(editor) != before  # Return to page immediately fetches new data.


def many_strips(number, v2):
    kb, packets = make_keyboard(v2)
    layout = KleSerial().deserialize([[f'{i},0' for i in range(number)]]).keys
    for i, key in enumerate(layout):
        key.row, key.col = i, 0
        key.encoder_idx = key.encoder_dir = None
        key.layout_index = key.layout_option = -1
    kb.amk_rgb_strip.update(start=0, count=number, layout=layout,
        strips=[dict(name=f'Strip {i}', start=i, count=1, mode=0,
                     bright=31, use_custom_color=False) for i in range(number)],
        leds={i: RgbLed(i, 0, 0, 255, 0x81) for i in range(number)})
    kb.amk_rgb_data = [0] * number  # Protocol's real unsampled initial state.
    return kb, packets


@pytest.mark.parametrize('number,v2', [(1, False), (7, False), (61, False), (255, True)])
def test_different_strip_counts_use_feature_batches_not_per_strip(editor, monkeypatch, number, v2):
    import amk.rgb_strip as module
    # Deterministic fast link: the full sweep fits in one callback.
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=lambda: 0))
    kb, packets = many_strips(number, v2)
    editor.rebuild(device(kb))
    editor.activate()
    maximum = 8 if v2 else 9
    assert packets == [(start, min(maximum, number-start)) for start in range(0, number, maximum)]
    assert len(editor.keyboardWidget.widgets) == number
    assert all(pixel.mask_color is not None for pixel in editor.keyboardWidget.widgets)
    before = colors(editor)
    editor.on_rgb_strip_poller()
    assert all(a != b for a, b in zip(before, colors(editor)))


def test_slow_sweep_yields_and_eventually_updates_every_strip(editor, monkeypatch):
    import amk.rgb_strip as module
    clock = [0.0]
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    kb, packets = many_strips(255, True)
    original_send = kb.usb_send
    def slow_send(*args, **kwargs):
        clock[0] += .021  # Two reports consume this callback's 40 ms budget.
        return original_send(*args, **kwargs)
    kb.usb_send = slow_send
    editor.rebuild(device(kb))
    editor.activate()
    assert packets == [(0, 8), (8, 8)]
    assert editor._preview_offset == 16
    assert colors(editor)[-1] == (0, 0, 0)  # Unsampled data safely displays black.
    for tick in range(15):
        before = len(packets)
        editor.on_rgb_strip_poller()
        assert len(packets) - before == 2
    assert editor._preview_offset == 0
    assert packets[-1] == (248, 7)
    assert all(isinstance(color, RgbColor) for color in kb.amk_rgb_data)
    before = colors(editor)
    for tick in range(16):
        editor.on_rgb_strip_poller()
    assert all(a != b for a, b in zip(before, colors(editor)))
    # A selection change must not rewind a partial sweep and starve later LEDs.
    editor.on_rgb_strip_poller()
    offset = editor._preview_offset
    editor.strip_lst.setCurrentRow(200)
    assert editor._preview_offset == offset
    editor.rebuild(None)
    assert editor._preview_offset == 0 and not editor.timer.isActive()
    replacement, _ = many_strips(7, False)
    editor.rebuild(device(replacement))
    editor.activate()
    assert editor._preview_offset == 0
    assert all(isinstance(color, RgbColor) for color in replacement.amk_rgb_data)
