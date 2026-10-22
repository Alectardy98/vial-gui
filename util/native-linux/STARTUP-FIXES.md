# Linux startup fixes

The implementation follows `WARNINGS-DIAGNOSTICS.md`. Existing AMK/Vial commands,
RGB synchronization capability handling and custom editors are retained. No
firmware operations or keyboard configuration writes are part of validation.

## Implemented changes

`util/native-linux/runtime_hook.py` replaces the global `XDG_CONFIG_HOME`
redirection with process-local
`QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, astro_config)`.
The existing filename is preserved exactly: `$XDG_CONFIG_HOME/vial-astro/Vial/Vial.conf`,
using `~/.config` when the variable is absent. No migration, copying of official
Vial preferences or preference-value rewrite is required. Qt's shared config
root remains available for IBus discovery. The data/cache environment roots
remain unchanged to preserve existing Astro logs and cache locations.

The application itself creates QSettings in MainWindow with the original
`Vial/Vial` identity. The native Linux launcher applies the isolated settings
path before that object is created. The scope override is local to the process;
it does not change paths for the installed official Vial application. The Linux
source launcher uses the same hook.

`src/main/python/main_window.py` replaces Linux's constructor hard refresh with
local empty-device UI initialization. The Linux discovery worker already starts
with a scan and delivers its initial result through a queued signal. The second
synchronous scan previously raced that result and selected/reloaded the same
keyboard twice. Manual Refresh still calls the original hard-refresh path, and
polling/hotplug/reconnect behavior is unchanged. Windows and WebHID retain their
explicit startup scan: their implementations do not provide the same initial
polling behavior. No protocol code was changed for this fix.

`src/main/python/util.py` logs an expected, well-formed non-Raw HID usage mismatch
at DEBUG. The matching Raw HID open/permission failure remains WARNING. Missing
or malformed usage/path fields now produce an unexpected-descriptor warning
rather than a formatting/key exception. Quiet polling retains its existing
quiet behavior; debug diagnostics are available for verbose/manual scans when
DEBUG logging is enabled. Communication exceptions and their handling are unchanged.

## Regressions and automated results

The complete suite passes **54 tests** (46.56 seconds in this run):

- Existing 42 tests, including RGB synchronization regressions.
- Two settings tests, using default and custom XDG config roots. Existing Astro
  settings are pre-seeded, then read/written/read in separate processes; official
  Vial settings stay byte-identical and the XDG config environment is unchanged.
- Six logging tests for expected DEBUG rejections, malformed-descriptor warnings
  and permission-error warnings.
- Four fresh-process GUI lifecycle cases covering queued initial results and
  cached definitions. They verify one startup initialization, unchanged polling,
  one additional manual reload, disappearance, one reconnect initialization,
  and no subsequent unchanged-device reload. These use real Qt signals from a
  worker thread and entirely virtual HID devices.

The existing GUI fixture now waits for asynchronous initial discovery. Its
retained mock windows lock their pollers after each test, preventing a past
fixture's discovery loop from observing another test's mock HID replacement.
The original protocol expectations and bilingual UI assertions remain intact.
All automated tests run in bubblewrap with synthetic `/dev`, inaccessible
physical HID/input/USB devices and isolated settings/data/cache roots.

Reproduce with `./util/native-linux/test.sh`. JUnit results are in
`target/astro/automated-tests/results.xml`; text in
`target/astro/startup-fixes/tests.log`.

## Qt notifier decision

No Qt binary or private object is patched, IBus is not disabled, and no Qt warning
filter is installed. A device-free supported-API probe confirms that
`QAbstractEventDispatcher.instance()`, `QCoreApplication.eventDispatcher()` and
`QThread.currentThread().eventDispatcher()` all return None before QApplication.
During QApplication construction the QtWayland/IBus watcher is initialized
before the main dispatcher exists, causing the diagnosed notifier warning.
Afterward the dispatcher exists and normal application operation proceeds.

The public setEventDispatcher APIs accept a supplied dispatcher; they do not
provide a simple supported way for this PyQt5 client to request Qt's platform
implementation earlier. A custom dispatcher, two application instances or
manipulation of a private IBus watcher would broaden lifecycle/IME risk. None
is introduced. The remaining warning and possible address-file reconnection
impact are documented. Fixing global config isolation restores IBus validity
but is independent of that early-notifier defect. Full IME restart/reconnection
is not exercised against the user's desktop session.

References: Qt's [application singleton requirements](https://doc.qt.io/qt-6/qapplication.html),
[dispatcher lifecycle](https://doc.qt.io/qt-6/qthread.html#setEventDispatcher), and
[matching Qt5 Wayland initialization source](https://github.com/qt/qtwayland/blob/v5.15.19-lts-lgpl/src/client/qwaylandintegration.cpp#L106).
The bundled runtime is Qt **5.15.19**; `QT_VERSION_STR=5.15.14` is the bindings'
compile-time version, not the actual runtime version.

## Validation and remaining limits

The build and independent checks remain reproducible with:

```sh
./util/native-linux/test.sh
./util/native-linux/build.sh
./util/native-linux/test-appimage.sh
./util/native-linux/test-hardware-readonly.sh
```

The current validation report is `STARTUP-VALIDATION.md`; detailed captures stay
under `target/astro/startup-fixes/`. Desktop integration and existing official
Vial preferences are excluded from changes. Tests involving app preference
writes use temporary Astro profiles. The physical keyboard stays connected;
any live GUI instrumentation uses the getter allowlist. Hotplug/reconnect
regressions simulate discovery removal/reappearance without resetting the board
or changing firmware. Physical cable reconnection, hardware write paths and
other firmware variants remain outside validation. This AppImage is tested on
this Manjaro x86_64 host, not certified for older Linux distributions.
