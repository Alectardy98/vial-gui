"""Exercise Linux discovery with real Qt signals and virtual HID, in a fresh process."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
                                reason='Linux native launcher/discovery regression')


@pytest.mark.parametrize('queued_initial', [False, True])
@pytest.mark.parametrize('cached_definitions', [False, True])
def test_linux_startup_refresh_and_hotplug(tmp_path, queued_initial, cached_definitions):
    env = os.environ.copy()
    env.update(QT_QPA_PLATFORM='offscreen', XDG_CONFIG_HOME=str(tmp_path / 'config'),
               XDG_CACHE_HOME=str(tmp_path / 'cache'), XDG_DATA_HOME=str(tmp_path / 'data'))
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                             str(int(queued_initial)), str(int(cached_definitions))],
                            env=env, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'LIFECYCLE PASS' in result.stdout


def lifecycle_probe(queued_initial, cached_definitions):
    import json
    import threading
    import time
    from PyQt5.QtCore import QStandardPaths
    from PyQt5.QtWidgets import QApplication
    import hidraw
    from autorefresh.autorefresh_thread import AutorefreshThread
    from main_window import MainWindow
    from protocol.keyboard_comm import Keyboard
    from test.test_gui import FAKE_KEYBOARD, FakeAppctx, MockDevice, VirtualKeyboard, mock_enumerate

    app = QApplication([])
    app.setApplicationName('Vial Astro')
    present = [True]
    scans = []
    def enumerate_mock():
        scans.append(True)
        return mock_enumerate() if present[0] else []
    hidraw.enumerate = enumerate_mock
    hidraw.device = MockDevice
    MockDevice.vk = VirtualKeyboard(FAKE_KEYBOARD)
    reloads = []
    original_reload = Keyboard.reload
    def count_reload(self, *args, **kwargs):
        reloads.append(self)
        return original_reload(self, *args, **kwargs)
    Keyboard.reload = count_reload

    def scan_from_worker(worker):
        errors = []
        def run():
            try:
                worker.update()
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=run)
        thread.start()
        thread.join(5)
        assert not thread.is_alive() and not errors, errors

    # No indefinite background loop in this regression. Emit the first result
    # either before the constructor returns (the old race) or afterward.
    AutorefreshThread.start = lambda worker: scan_from_worker(worker) if queued_initial else None
    if cached_definitions:
        cache = Path(QStandardPaths.writableLocation(QStandardPaths.CacheLocation))
        cache.mkdir(parents=True, exist_ok=True)
        (cache / 'via_keyboards.json').write_text(json.dumps({'definitions': {}, 'fixture_marker': True}))
    window = MainWindow(FakeAppctx())
    window.show()
    assert len(scans) == int(queued_initial), 'Constructor performed a second hardware scan'
    if cached_definitions:
        assert window.autorefresh.thread.via_stack_json['fixture_marker']

    def settle():
        for _ in range(6):
            app.processEvents()
    worker = window.autorefresh.thread
    if not queued_initial:
        assert window.autorefresh.current_device is None
        assert not window.tabs.isVisible()
        scan_from_worker(worker)
    settle()
    assert len(reloads) == 1
    assert window.combobox_devices.count() == 1
    assert window.autorefresh.current_device.keyboard is not None
    scan_from_worker(worker)
    settle()
    assert len(reloads) == 1, 'Unchanged poll reloaded a connected device'
    window.on_click_refresh()
    settle()
    assert len(reloads) == 2, 'Manual hard refresh must still reload'
    present[0] = False
    scan_from_worker(worker)
    settle()
    assert window.autorefresh.current_device is None
    assert window.combobox_devices.count() == 0
    assert not window.tabs.isVisible()
    present[0] = True
    scan_from_worker(worker)
    settle()
    assert len(reloads) == 3, 'Reconnect/hotplug did not initialize exactly once'
    assert window.tabs.isVisible()
    scan_from_worker(worker)
    settle()
    assert len(reloads) == 3
    print('LIFECYCLE PASS: one startup, one manual refresh, one reconnect', flush=True)
    window.autorefresh.current_device.close()


if __name__ == '__main__':
    lifecycle_probe(bool(int(sys.argv[1])), bool(int(sys.argv[2])))
