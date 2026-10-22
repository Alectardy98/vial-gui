"""Presentation-only English regressions; no physical device access."""
import ast
import json
from pathlib import Path
import re

import pytest
from PyQt5.QtWidgets import QAbstractButton, QAction, QComboBox, QGridLayout, QLabel, QWidget

from ui_text import device_text

HAN = re.compile(r'[\u4e00-\u9fff]')
ROOT = Path(__file__).resolve().parents[4]


def test_source_ui_and_qmk_resource_are_english():
    for path in (ROOT / 'src/main/python').rglob('*.py'):
        if 'test' in path.parts or path.name == 'ui_text.py':
            continue  # ui_text contains input-side Chinese catalog keys only.
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not HAN.search(node.value), (path, node.lineno, node.value)
    resource = ROOT / 'src/main/resources/base/qmk_settings.json'
    assert not HAN.search(resource.read_text())
    magic = json.loads(resource.read_text())['tabs'][0]['fields']
    # Localizing resource titles must retain firmware settings IDs/bit order.
    assert [(item['qsid'], item['bit'], item['width']) for item in magic] == [(21, bit, 4) for bit in range(10)]


@pytest.mark.parametrize('original,english', [
    ('Right Grid/右上灯阵', 'Upper-right grid'),
    ('右上灯阵', 'Upper-right grid'),
    ('Disabled/关闭', 'Disabled'), ('静态', 'Static'),
    ('Gradient Left Right/左右渐变', 'Gradient left to right'),
    ('Cycle Out In Dual/双重内外循环', 'Dual inward/outward cycle'),
    ('Breath', 'Breathing'), ('Custom', 'Custom'),
    ('APC/RT/按键行程', 'APC/RT'), ('ISO/JIS', 'ISO/JIS'),
    ('配列', 'Layout'), ('分裂空格', 'Split spacebar'),
    ('My custom label', 'My custom label'),
    ('未知的设备标签', '未知的设备标签'),  # Never invent an unknown device's meaning.
])
def test_device_display_labels(original, english):
    assert device_text(original) == english


def test_layout_options_keep_original_values_and_indices(qtbot):
    from editor.layout_editor import SelectChoice
    parent = QWidget()
    qtbot.addWidget(parent)
    container = QGridLayout(parent)
    options = ['Default/默认', '分裂空格']
    calls = []
    choice = SelectChoice(lambda: calls.append(choice.choice), container, 'Layout/配列', options)
    assert choice.widget_label.text() == 'Layout'
    assert [choice.widget_options.itemText(i) for i in range(2)] == ['Default', 'Split spacebar']
    assert choice.options is options
    assert options == ['Default/默认', '分裂空格']
    assert not calls
    choice.widget_options.setCurrentIndex(1)
    assert calls == [1] and choice.pack() == '1'


def test_custom_keycode_names_and_aliases_are_preserved(monkeypatch):
    from keycodes import keycodes
    monkeypatch.setattr(keycodes, 'KEYCODES_USER', [])
    monkeypatch.setattr(keycodes.Keycode, 'qmk_id_to_keycode', {})
    definition = [{'name': 'MY_PROTOCOL_KEY', 'shortName': 'Scan/扫描', 'title': 'Static/静态'}]
    before = json.dumps(definition)
    keycodes.create_custom_user_keycodes(definition)
    key = keycodes.KEYCODES_USER[0]
    assert key.qmk_id == 'USER00'
    assert key.alias == ['USER00', 'MY_PROTOCOL_KEY']
    assert key.label == 'Scan' and key.tooltip == 'Static'
    assert json.dumps(definition) == before


def test_all_editors_and_hidden_controls_use_english(qtbot):
    from test.test_gui import prepare, FAKE_KEYBOARD
    window, _ = prepare(qtbot, FAKE_KEYBOARD)
    try:
        assert len(window.editors) == 23
        assert len({title for _, title in window.editors}) == 23
        assert window.btn_refresh_devices.text() == 'Refresh'
        from keycodes.keycodes import Keycode
        assert Keycode.find_by_qmk_id('KC_LANG1').label == 'Hangul\nKana'
        for editor, title in window.editors:
            assert not HAN.search(title)
            # Editors unsupported by this fixture still have their controls built.
            def layout_widgets(layout):
                for index in range(layout.count()):
                    item = layout.itemAt(index)
                    if item.widget():
                        yield item.widget()
                        yield from item.widget().findChildren(QWidget)
                    if item.layout():
                        yield from layout_widgets(item.layout())
            for widget in layout_widgets(editor):
                texts = [widget.toolTip(), widget.windowTitle()]
                if isinstance(widget, (QLabel, QAbstractButton)):
                    texts.append(widget.text() if callable(widget.text) else widget.text)
                if isinstance(widget, QComboBox):
                    texts += [widget.itemText(i) for i in range(widget.count())]
                assert not any(HAN.search(text) for text in texts), (title, texts)
        assert window.apc_rt.apc_lbl.text() == 'Actuation point (mm):'
        assert window.apc_rt.rt_down_lbl.text() == 'Press distance (mm):'
        assert [window.misc.pr_cbb.itemText(i) for i in range(4)] == [
            '1,000 Hz (full speed)', '2,000 Hz (high speed)',
            '4,000 Hz (high speed)', '8,000 Hz (high speed)']
        assert window.misc.pr_btn.text() == 'Apply && Restart'
        assert window.rgb_strip.sync_cbx.text() == 'Synchronize'
        assert window.rgb_strip.breath_cbx.text() == 'Breathing'
        # Caption localization must not alter arrows, geometry or transparency.
        from PyQt5.QtCore import Qt, QRect
        from PyQt5.QtGui import QImage, QPainter
        original = QImage(str(ROOT / 'src/main/resources/base/dks.png'))
        translated = window.dks.dks_img.copy()
        assert original != translated
        for image in [original, translated]:
            painter = QPainter(image)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            for rect in [QRect(700, 1015, 540, 155), QRect(700, 1500, 550, 75),
                         QRect(50, 860, 510, 210), QRect(50, 1175, 510, 210),
                         QRect(1410, 1175, 515, 210), QRect(1410, 860, 515, 210)]:
                painter.fillRect(rect, Qt.transparent)
            painter.end()
        assert original == translated
        assert window.dks.dks_lbl.accessibleDescription() == 'Switch travel and bottom-out diagram'
        from amk.dks import DKS_TRIGGER_LABELS
        assert DKS_TRIGGER_LABELS == ['Event point 1:', 'Event point 2:', 'Event point 3:', 'Event point 4:']
        for action in window.findChildren(QAction):
            assert not HAN.search(action.text())
    finally:
        window.autorefresh.thread.lock()
