Current full-page RGB animation previews: [RGB-ALL-PREVIEWS.md](RGB-ALL-PREVIEWS.md), [validation](RGB-ALL-PREVIEWS-VALIDATION.md).

Current RGB Strips fix and validation: [RGB-STRIP-FIX.md](RGB-STRIP-FIX.md), [RGB-STRIP-VALIDATION.md](RGB-STRIP-VALIDATION.md).

Current English localization and UI cleanup: [LOCALIZATION.md](LOCALIZATION.md); current artifact validation: [LOCALIZATION-VALIDATION.md](LOCALIZATION-VALIDATION.md).

# Vial Astro native Linux build

Built from this fork at `00157d1` with the RGB sync and Linux startup fixes
(documented in `CHANGES-LINUX.md` and `STARTUP-FIXES.md`); application version 0.7.5. The client AMK
version string is 0.9.11, not an identified connected-firmware version. Protocol
definitions and command formats are unchanged. No firmware was flashed, calibration/settings reset, system packages
installed, udev rules installed, or desktop integration changed.

## Run

The output is `target/astro/Vial-Astro-0.7.5-x86_64.AppImage`.

```sh
./target/astro/Vial-Astro-0.7.5-x86_64.AppImage
```

Native Wayland is preferred with XWayland as fallback. Override explicitly if
needed:

```sh
QT_QPA_PLATFORM=xcb ./target/astro/Vial-Astro-0.7.5-x86_64.AppImage
```

If FUSE is unavailable, append `--appimage-extract-and-run`. The AppImage is
portable and can be moved away from the repository. No Python installation or
activated venv is needed. Normal use retains the fork's original keyboard access
and write operations; the smoke-test mode disables physical device access.

The packaging runtime routes native user QSettings to `~/.config/vial-astro`
(or `$XDG_CONFIG_HOME/vial-astro`), without changing `XDG_CONFIG_HOME`. Existing
Astro preferences remain at `Vial/Vial.conf` beneath that root. Qt plugins can
still find shared session configuration such as the IBus address file. The
original `QSettings("Vial", "Vial")` identity is retained within the isolated
process-local settings path. Data/cache XDG roots retain their existing
`vial-astro/` subdirectory (`~/.local/share/vial-astro`, `~/.cache/vial-astro`). This
keeps preferences, cached VIA definitions and logs separate from existing Vial.
No existing layout/configuration is imported automatically.

## Why this build path

The original fbs 0.9.0 workflow pins Python 3.6, PyQt 5.9.2, sip 4.19.8 and
PyInstaller 3.4. Its Docker path compiles Python 3.6 on Ubuntu 18.04 and converts
a Debian package with a Xenial-era pkg2appimage recipe. The host has Python 3.14;
those pins are unsuitable for its normal Python environment.

This build keeps fbs 0.9.0's runtime, using a small runtime hook to supply its
frozen build settings. PyInstaller 6.16 directly packages the unchanged entry
point, using isolated CPython 3.11.17 and PyQt5 5.15.11. The bindings were compiled with Qt 5.15.14; `qVersion()` confirms runtime
Qt 5.15.19 from the PyQt5-Qt5 5.15.19 wheel. The exact original
`vial-kb/cython-hidapi` commit is compiled with Cython 0.29.37 and still supplies
Linux `hidraw`; it has not been substituted with another HID backend. The local
`simpleeval.zip` is retained. PyUSB and the bundled libusb backend preserve the
custom fast animation-transfer path.

The source audit covered all 155 tracked files, all Python imports/classes and
JSON, build workflows/scripts, and the fork's diff against the merge base with
`upstream/main` (46 files, about 9,600 added lines). Machine-readable inventory:
`target/astro/source-inventory.json`. Custom AMK modules include actuation/rapid
trigger, calibration, DKS, Snap Tap, RGB matrix/strip/grid/indicators,
animations/file transfer, auxiliary displays and ESP32 controls. All remain in
the source and packaged dependency graph.

## Rebuild on this Manjaro x86_64 system

Requires a working C/C++ toolchain, Git, curl, hidapi build dependencies
(libusb/udev development files), and appimagetool. These were already available;
this procedure does not run pacman or sudo. uv downloads an isolated CPython.

```sh
mkdir -p .build-tools
curl -LsSf https://astral.sh/uv/0.13.5/install.sh -o .build-tools/install-uv.sh
UV_INSTALL_DIR="$PWD/.build-tools" UV_NO_MODIFY_PATH=1 sh .build-tools/install-uv.sh
./util/native-linux/build.sh
```

`UV=/path/to/uv` and `APPIMAGETOOL=/path/to/appimagetool` may override tool paths.
The tested appimagetool is git version `8c8c91f`, built 2026-08-20, SHA256
`bdff8a800b24337db34fe0711c00d5f938d1c54f9676efa3a8e1f068d19e6d78`.
The AppImage type-2 runtime is cached in `.build-tools/runtime-x86_64` and verified
against SHA256 `617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46`.
Keep that cached file for future builds: if the continuous download changes, the
checksum check stops the build instead of silently accepting a different runtime.
All Python dependency versions are in `requirements.lock`. fbs is installed with
`--no-deps` deliberately so its legacy packaging dependencies cannot downgrade
PyInstaller. `uv pip check` will report that historical fbs requirement mismatch;
its runtime API works independently of its old CLI build implementation.

Build outputs, logs, extracted AppDir, screenshots, and checksum stay under
`target/astro/`; tools stay under `.build-tools/`, Python packages under
`.venv-linux/`. These directories are ignored by Git. The scripts leave the
original Docker/fbs build files and requirements intact. No bit-for-bit identity
across hosts is claimed: host shared libraries, build metadata and tool versions
also affect the binary.

Run from source with the same isolated profile:

```sh
.venv-linux/bin/python util/native-linux/run-source.py
```

## Verification and limits

```sh
./util/native-linux/test.sh
./util/native-linux/test-appimage.sh
# With only the intended keyboard/client connected to its Raw HID interface:
./util/native-linux/test-hardware-readonly.sh
```

The complete suite, including RGB sync, startup/settings and English UI regressions, passes: **87 tests**. `test.sh`
runs with synthetic `/dev`, isolated XDG roots and no physical keyboard nodes.
Results: `target/astro/tests-final.log` and `automated-tests/results.xml`.

This requires bubblewrap. It copies the AppImage to `/tmp`, hides this source tree
(including the venv) and uv's managed Python, clears the environment, provides an
empty temporary home, and exposes a synthetic `/dev` with no keyboard/HID/USB
nodes. Both `wayland` and `xcb` must open one visible main window, construct all
23 editor panels, capture a screenshot, and exit successfully. Test logs and
screenshots are saved in `target/astro/independent-test/`. Qt/XWayland needs the
existing session's XAUTHORITY; the test passes it through explicitly.

`VIAL_ASTRO_SMOKE_TEST=1` activates the packaging hook's device-free test mode.
It additionally checks bundled CA certificates and loads the packaged libusb
shared library. A separate native-runtime test initializes the PyUSB backend
(`VIAL_ASTRO_TEST_USB_INIT=1`); libusb cannot initialize inside the strict sandbox
with its USB device nodes hidden. `VIAL_ASTRO_SCREENSHOT=/absolute/path.png` records the window. This mode
never enumerates actual HID devices and rejects attempts to open them. It does
not exercise real keyboard communication or custom settings writes.

Verified source startup and packaged startup on GNOME Wayland and XWayland;
visually checked the rendered window. Also verified normal AppImage execution
through FUSE with a clean environment and temporary home. Warnings about Mesa
initialization in the strict sandbox are caused by hiding GPU devices; both GUI
checks still pass. A QSocketNotifier warning can appear at startup; see the limitations below.

The original fixture issues are fixed in place: AMK GET_NKRO replies, bilingual
labels and integer mouse coordinates. Sync regressions cover absent/malformed
masters, valid master index zero, unchanged GET packets, mixed capabilities,
optional color/brightness reads, rejected reads and checkbox refresh without SET.

`test-hardware-readonly.sh` copies the finished AppImage outside the repository,
hides the source and venv, exposes only the selected `4D58:0103` Raw HID node,
and invokes its bundled getter-allowlisted diagnostic harness. It verifies a
complete configuration reload, successful AMK reads, and no sync queries for
this keyboard's undeclared capability. It refuses concurrent HID clients and
saves reports in `target/astro/hardware-validation/`. This tests packaged model
reads; GUI startup is tested separately above. The explicit environment variable
`VIAL_ASTRO_READONLY_DIAGNOSTICS=/absolute/new/output/directory` runs that bundled
diagnostic and exits before the interactive GUI starts. It does not enable
normal GUI writes during validation.

All calibration, actuation, firmware operations, animation uploads and other
write paths remain untested on physical hardware. No keyboard configuration or
system permissions were changed. Existing hidraw/USB udev permissions still
apply. Linux global macro recording retains the original `pkexec`/`keyboard`
helper and needs host polkit/device access. The Qt5 Wayland/IBus startup warning
is retained: IBus now initializes correctly, while its early filesystem watcher
registration remains a Qt limitation relevant to reconnection. No safe minimal
public-API remedy was found; no warning filtering, IBus disabling or Qt binary
patching is used. End-to-end IME reconnection was not exercised. The historical investigation
is preserved in `HARDWARE-DIAGNOSTICS.md`; its fixture failures and old AppImage
hash describe the pre-fix build, not this finalized revision.

The AppImage includes Python, Qt/plugins, HID, libusb, resources, CA certificates,
and discovered non-core shared libraries. It still uses host glibc, graphics
stack/compositor, and optional polkit. It is built/tested for this Manjaro host,
not certified for older Linux distributions. A broad-distribution release would
need a separate older-glibc build environment and independent distro testing.

The original GPL license is included as `COPYING` in the AppImage. Keep the fork
and these build files alongside the binary when archiving or redistributing it.
Primary packaging references: https://pyinstaller.org/en/stable/usage.html and
https://doc.qt.io/qt-6.8/linux-deployment.html (Qt plugin/shared-library deployment
principles; this client itself remains on Qt5).
