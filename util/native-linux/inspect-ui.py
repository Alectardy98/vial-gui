#!/usr/bin/env python3
"""Render all editors offline using previously captured getter responses.

Run through inspect-ui.sh: synthetic /dev and isolated preferences are mandatory.
Unsupported device features use explicitly marked synthetic presentation fixtures.
No keyboard configuration is sent or persisted.
"""
import argparse
import json
import os
from pathlib import Path
import re
import runpy
import sys
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'src/main/python'))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--responses', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
assert os.environ.get('VIAL_ASTRO_OFFLINE_UI') == '1', 'Use inspect-ui.sh sandbox'
runpy.run_path(str(root / 'util/native-linux/runtime_hook.py'))
allowed = runpy.run_path(str(root / 'util/native-linux/diagnose-readonly.py'))['allowed']
responses = {}
for line in args.responses.read_text().splitlines():
    item = json.loads(line)
    responses[bytes.fromhex(item['request']).ljust(32, b'\0')] = bytes.fromhex(item['response'])
requests = []
def replay(dev, msg, retries=1):
    assert allowed(bytes(msg)), 'Only recorded getters may be replayed'
    requests.append(bytes(msg).hex())
    key = bytes(msg).ljust(32, b'\0')
    if key not in responses:
        raise RuntimeError('Getter not present in offline recording: ' + bytes(msg).hex())
    return responses[key]

import hidraw
hidraw.enumerate = lambda *a, **kw: []
def no_hardware(*a, **kw):
    raise RuntimeError('Hardware access disabled in offline UI inspection')
hidraw.device = no_hardware
import usb.core
usb.core.find = no_hardware
from autorefresh.autorefresh_thread import AutorefreshThread
AutorefreshThread.start = lambda self: None
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication, QAbstractButton, QComboBox, QLabel, QWidget
from main_window import MainWindow
from protocol.keyboard_comm import Keyboard
from vial_device import VialKeyboard

class Resources:
    def get_resource(self, name):
        return str(root / 'src/main/resources/base' / name)

app = QApplication([])
app.setApplicationName('Vial Astro UI Inspection')
QFontDatabase.addApplicationFont(Resources().get_resource('wqy-microhei.ttc'))
font = QFont('wqy-microhei'); font.setPointSize(10); app.setFont(font)
window = MainWindow(Resources())
window.resize(1600, 1000)
window.tabs.blockSignals(True)  # Do not activate pollers while browsing captures.
keyboard = Keyboard(None, usb_send=replay)
keyboard.reload()
keyboard.get_unlock_in_progress = lambda: False  # Synthetic locked state; no unlock operation.
device = VialKeyboard(dict(vendor_id=0x4D58, product_id=0x0103,
    manufacturer_string='FAUKWAA-[MY-2K]', product_string='100NG Edition', path=b'/offline/replay'))
device.keyboard = keyboard
window.autorefresh.current_device = device
window.rebuild()
window.refresh_tabs()
window.lbl_no_devices.hide()
window.tabs.show()
window.combobox_devices.blockSignals(True)
window.combobox_devices.addItem(device.title())
window.combobox_devices.blockSignals(False)
window.show()
app.processEvents()

# Populate unavailable advanced panels with UI-only entries, never protocol writes.
from protocol.key_override import KeyOverrideEntry
from protocol.alt_repeat_key import AltRepeatKeyEntry
for editor, attr, data in [
    (window.tap_dance, 'tap_dance_entries_available', ['KC_A', 'KC_LSFT', 'KC_B', 'KC_LCTL', 200]),
    (window.combos, 'combo_entries_available', ['KC_A', 'KC_B', 'KC_NO', 'KC_NO', 'KC_C']),
    (window.key_override, 'key_override_entries_available', KeyOverrideEntry(['KC_A', 'KC_B', 1, 0, 0, 0, 0])),
    (window.alt_repeat_key, 'alt_repeat_key_entries_available', AltRepeatKeyEntry(['KC_A', 'KC_B', 0, 0])),
]:
    entries = getattr(editor, attr, None)
    if entries:
        entry = entries[0]
        entry.load(data)
        if editor.tabs.indexOf(entry.widget()) < 0:
            editor.tabs.addTab(entry.widget(), '1')
        editor.tabs.setCurrentWidget(entry.widget())

# Show all QMK resource tabs with inert local values.
window.qmk_settings.keyboard = SimpleNamespace(
    supported_settings={field['qsid'] for tab in window.qmk_settings.settings_defs['tabs'] for field in tab['fields']},
    settings={field['qsid']: 0 for tab in window.qmk_settings.settings_defs['tabs'] for field in tab['fields']})
window.qmk_settings.recreate_gui()
for tab in window.qmk_settings.tabs:
    for field in tab:
        field.reload(window.qmk_settings.keyboard)

records = []
extras = []
def capture(widget, name, title, fixture):
    app.processEvents()
    widget.grab().save(str(args.output / (name + '.png')))
    texts, clips = [], []
    for child in [widget] + widget.findChildren(QWidget):
        values = [child.toolTip()]
        if isinstance(child, (QLabel, QAbstractButton)):
            values.append(child.text() if callable(child.text) else child.text)
        if isinstance(child, QComboBox):
            values.extend(child.itemText(i) for i in range(child.count()))
        texts.extend(value for value in values if value)
        if child.isVisible() and isinstance(child, QLabel) and child.text() and not child.wordWrap():
            if '<' not in child.text() and child.fontMetrics().horizontalAdvance(child.text()) > child.width() + 3:
                clips.append(dict(text=child.text(), width=child.width()))
    chinese = [text for text in texts if re.search('[\u4e00-\u9fff]', text)]
    assert not chinese, (title, chinese)
    records.append(dict(panel=title, screenshot=name+'.png', fixture=fixture,
                        texts=sorted(set(texts)), possible_clipping=clips))

for index, (editor, title) in enumerate(window.editors):
    name = f'{index+1:02}-' + re.sub('[^a-z0-9]+', '-', title.lower()).strip('-')
    container = editor.parentWidget()
    tab = window.tabs.indexOf(container) if container else -1
    if tab >= 0:
        window.tabs.setCurrentIndex(tab)
        capture(window, name, title, 'recorded keyboard')
    else:
        if container is None:
            container = QWidget(); container.setLayout(editor)
        container.setParent(None)
        container.setWindowTitle(title + ' — offline presentation fixture')
        container.resize(1600, 1000)
        container.show(); extras.append(container)
        capture(container, name, title, 'synthetic/unsupported panel')
        container.hide()
    if editor is window.misc:
        # Expose all advanced controls without changing the keyboard feature set.
        for attr in ['amk_noise_sens', 'amk_apc_sens', 'amk_rt_sens', 'amk_top_sens', 'amk_btm_sens']:
            if not hasattr(keyboard, attr):
                setattr(keyboard, attr, 0)  # Synthetic values for unsupported advanced UI.
        window.misc.show_advance(True)
        capture(window, name+'-advanced', title+' (advanced)', 'synthetic advanced settings')
        window.misc.show_advance(False)
    if editor is window.qmk_settings:
        for tab_index in range(editor.tabs_widget.count()):
            editor.tabs_widget.setCurrentIndex(tab_index)
            capture(container, name+f'-{tab_index+1}', title+' / '+editor.tabs_widget.tabText(tab_index), 'synthetic QMK settings')

# Dialogs that are not on any editor tab.
from any_keycode_dialog import AnyKeycodeDialog
from textbox_window import TextboxWindow
for name, dialog in [('keycode-dialog', AnyKeycodeDialog('KC_A')), ('text-editor-dialog', TextboxWindow())]:
    dialog.show(); extras.append(dialog)
    capture(dialog, name, name, 'dialog fixture')
    dialog.hide()
(args.output/'inventory.json').write_text(json.dumps(records, ensure_ascii=False, indent=2))
(args.output/'replayed-requests.json').write_text(json.dumps(requests, indent=2))
print('UI INSPECTION PASS:', app.platformName(), len(window.editors), 'editors;', len(records), 'captures')
# Avoid application close/save paths: only temporary profile exists regardless.
window.hide()
