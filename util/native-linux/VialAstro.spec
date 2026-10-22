from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules
root = Path(SPECPATH).parents[1]
usb_data, usb_binaries, usb_hidden = collect_all('libusb_package')
a = Analysis([str(root / 'src/main/python/main.py')],
    pathex=[str(root / 'src/main/python')],
    binaries=usb_binaries,
    datas=usb_data + [(str(root / 'src/main/resources/base'), '.'),
                     (str(root / 'src/main/icons/Icon.ico'), '.'),
                     (str(root / 'src/build/settings/base.json'), '.'),
                     (str(root / 'COPYING'), '.'),
                     (str(root / 'util/native-linux/diagnose-readonly.py'), '.'),
                     (str(root / 'target/astro/build-settings.json'), '.')],
    hiddenimports=usb_hidden + collect_submodules('usb.backend') + collect_submodules('keymap') + ['argparse', 'statistics'],
    runtime_hooks=[str(root / 'util/native-linux/runtime_hook.py')],
    excludes=['PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='VialAstro',
          debug=False, strip=False, upx=False, console=True, contents_directory='.')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='VialAstro')
