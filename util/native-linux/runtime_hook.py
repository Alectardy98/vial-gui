"""Keep fbs's runtime API while using a current PyInstaller packager."""
import json
import os
import sys
from pathlib import Path

# Keep the existing Astro preference file without hiding shared session config
# (notably IBus's address file) from Qt plugins. This override is process-local.
from PyQt5.QtCore import QSettings
config_home = Path(os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config'))
QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(config_home / 'vial-astro'))

# Retain the established Astro log/cache locations.
for key, default in [('XDG_DATA_HOME', '.local/share'), ('XDG_CACHE_HOME', '.cache')]:
    os.environ[key] = str(Path(os.environ.get(key, str(Path.home() / default))) / 'vial-astro')
os.environ.setdefault('QT_QPA_PLATFORM', 'wayland;xcb')

if getattr(sys, 'frozen', False):
    import fbs_runtime._frozen
    fbs_runtime._frozen.BUILD_SETTINGS = json.loads(
        (Path(sys._MEIPASS) / 'build-settings.json').read_text())

# An explicit diagnostic invocation exits before the interactive GUI starts.
# The bundled harness enforces its getter allowlist on every HID transaction.
if getattr(sys, 'frozen', False) and os.environ.get('VIAL_ASTRO_READONLY_DIAGNOSTICS'):
    import runpy
    sys.argv = [sys.argv[0], '--full-reload', '--output',
                os.environ['VIAL_ASTRO_READONLY_DIAGNOSTICS']]
    runpy.run_path(str(Path(sys._MEIPASS) / 'diagnose-readonly.py'), run_name='__main__')
    raise SystemExit(0)

# Opt-in, device-free GUI verification for both source and packaged builds.
if os.environ.get('VIAL_ASTRO_SMOKE_TEST'):
    import certifi
    import libusb_package
    from usb.backend import libusb1
    assert Path(certifi.where()).is_file(), 'Missing CA certificates'
    assert libusb_package.get_library_path(), 'Missing bundled libusb'
    import ctypes
    assert ctypes.CDLL(str(libusb_package.get_library_path())).libusb_init
    if os.environ.get('VIAL_ASTRO_TEST_USB_INIT'):
        assert libusb1.get_backend(find_library=libusb_package.find_library) is not None, 'Cannot initialize libusb backend'
    print('SMOKE: bundled CA certificates and libusb shared library loaded', flush=True)
    import hidraw
    hidraw.enumerate = lambda *a, **kw: []
    def no_device(*a, **kw):
        raise RuntimeError('Hardware access disabled during GUI smoke test')
    hidraw.device = no_device
    import usb.core
    usb.core.find = no_device
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
    original_exec = QApplication.exec_
    def smoke_exec(app):
        def verify():
            windows = [w for w in app.topLevelWidgets() if isinstance(w, QMainWindow) and w.isVisible()]
            errors = [w for w in app.topLevelWidgets() if isinstance(w, QMessageBox) and w.isVisible()]
            if len(windows) != 1 or errors:
                print('SMOKE FAIL: windows={}, errors={}'.format(len(windows), [w.text() for w in errors]), flush=True)
                app.exit(1)
                return
            window = windows[0]
            screenshot = os.environ.get('VIAL_ASTRO_SCREENSHOT')
            if screenshot:
                if not window.grab().save(screenshot):
                    app.exit(2)
                    return
            print('SMOKE PASS: platform={}, editors={}, size={}x{}'.format(
                app.platformName(), len(window.editors), window.width(), window.height()), flush=True)
            app.quit()
        QTimer.singleShot(3000, verify)
        return original_exec()
    QApplication.exec_ = smoke_exec
