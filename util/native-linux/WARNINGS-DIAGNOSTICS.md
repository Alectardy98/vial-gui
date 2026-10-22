# Remaining Linux startup warnings — investigation, 2026-10-22

Historical investigation. The subsequently authorized fixes and validation are
documented in [STARTUP-FIXES.md](STARTUP-FIXES.md). Findings below describe the
pre-fix artifact and retain its evidence.

The application does run natively on Wayland when requested. The GNOME message
is misleading Qt informational output, and the HID rejection messages describe
expected interface filtering. Two findings deserve actual fixes: the packaging
profile isolation prevents this session's IBus connection, and overlapping
startup discovery results can load the same keyboard twice. There is also a
separate Qt/IBus early file-watcher initialization defect relevant to input-method
reconnection.

**Investigation only:** no application, test, build-script or runtime-hook fixes
were applied, and the distributed AppImage was not rebuilt or changed. Temporary
instrumentation and an instrumented extracted copy are confined to
`target/astro/warnings-investigation/`. This report is the only new deliverable
outside that ignored directory. No firmware, keyboard configuration, existing
Vial installation or GNOME integration was changed. No warnings were filtered
and no logging levels were changed.

## Priority and proposed action

| Finding | Functional significance | Recommended smallest change, not implemented |
|---|---|---|
| Global XDG config isolation hides IBus discovery data | Confirmed IBus invalid/fallback to Compose in this session | Keep the normal XDG config environment; redirect Vial's QSettings path inside this process to the existing Astro config directory |
| Two startup results trigger two keyboard reloads | Confirmed duplicate reads, UI rebuild and latency; no observed corruption | Give initial discovery one owner: initialize the empty UI locally and rely on the already-started worker for initial discovery; retain the manual hard Refresh action |
| Qt/IBus creates its notifier before an event dispatcher | Confirmed early-notifier registration failure mechanism; potential IBus file-monitor/reconnection impairment | Fix/defer the input-context watcher initialization in a matching Qt dependency build; verify IME lifecycle before shipping |
| Expected HID usage mismatch logged as WARNING | Cosmetic severity problem; correct filtering works | In a later change, classify expected usage mismatch as debug; retain warnings for permission/open failures |
| GNOME session warning despite explicit Wayland | Cosmetic Qt info message; requested Wayland backend works | No application behavior change needed; an upstream Qt diagnostic correction is optional |

## Versions, packaging and test method

PyQt is **5.15.11**. `QT_VERSION_STR` is **5.15.14**, the Qt version against which
the bindings were compiled. **`qVersion()` reports the actual runtime as
5.15.19**. Earlier build notes calling 5.15.14 the runtime version were inaccurate.
The selected Qt source files are identical in the public 5.15.14 and 5.15.19
LTS LGPL tags. This is not evidence of an ABI mismatch.

Source and packaged copies of `libQt5Core.so.5` and `libQt5Gui.so.5` have identical
SHA256 hashes. Process maps show Qt libraries and the Wayland/IBus plugins loaded
from the bundled tree. There was no observed system/bundled Qt mixing.

Tests included:

- The **unmodified AppImage** under normal FUSE execution, using its existing
  device-free smoke mode, explicitly selecting `wayland` and `xcb`.
- Source GUI startup with a getter-allowlisted HID wrapper, temporary application
  profile, event/call-stack observers and the physical keyboard attached.
- A disposable extracted copy of the AppImage for the same guarded live GUI
  traces. Only its diagnostic payload was substituted; its compiled entry-point
  code, Python modules, libraries and Qt plugins were retained. The normal
  built-in PyInstaller runtime hooks were executed in their original order.
  Thus original-image backend tests and instrumented-bundle call traces are
  distinct forms of evidence, not a claim that the distributed image contains
  this instrumentation.
- Device-free GDB breakpoints on the existing Qt warning and IBus validity calls;
  no fatal-warning setting, warning filter or log-level override was used.
- A temporary-file-only watcher test before versus after QApplication creation.
- A diagnostic-only QSettings-path experiment. It changed a setting lookup path
  in that disposable process, never a stored preference value.

Seven completed guarded GUI traces recorded **4,515 getter output reports and
4,515 complete 32-byte replies**, with zero blocked write attempts. Only
`/dev/hidraw7` was opened. Every completed GUI trace displayed the physical
FAUKWAA-[MY-2K] 100NG Edition keyboard and its configuration. The initial failed
instrumentation trial (a diagnostic callback naming error) is excluded from
these counts. No physical write tests were run. Handles were closed afterward.

Evidence base: `target/astro/warnings-investigation/summary.json`, individual
`events.jsonl` files and their adjacent console logs. Temporary scripts and
matched Qt source snapshots are retained there for review.

## 1. GNOME / XDG_SESSION_TYPE message

**Emitter:** bundled `libQt5Gui.so.5`,
`QGuiApplicationPrivate::createPlatformIntegration()`, in
`qtbase/src/gui/kernel/qguiapplication.cpp`, source lines 1410–1435. It is emitted
with **qInfo / QtInfoMsg (type 4)**, despite beginning with the word “Warning”.
It is not emitted by GNOME, Vial, AppRun or the AppImage mount runtime.

Qt first calculates its default platform from the session/desktop environment.
On this GNOME Wayland session the default-selection branch prints the message.
Only afterward does it read `QT_QPA_PLATFORM` and replace the candidate platform.
The diagnostic therefore precedes the explicit override; its presence does not
mean that override was ignored. The same message also appears with explicit
`xcb`. [Matching Qt source](https://github.com/qt/qtbase/blob/v5.15.19-lts-lgpl/src/gui/kernel/qguiapplication.cpp#L1410).

**Native Wayland is verified.** The original AppImage reports
`platform=wayland`; a client protocol trace includes Wayland registry activity
and creation of an `xdg_toplevel`. The guarded packaged GUI reports the same
platform and loads `libqwayland-generic.so`. With explicit `xcb`, the reported
platform is `xcb` and no Wayland/IBus notifier warning appears in these runs.

`AppRun` preserves a supplied `QT_QPA_PLATFORM`; absent one, it supplies
`wayland;xcb`. The project runtime hook uses `setdefault`, so it also preserves
an explicit value. AppRun clears inherited Qt plugin-path/Python overrides;
PyInstaller subsequently points `QT_PLUGIN_PATH` at the bundled plugin tree.
These controls were inspected and the loaded libraries match them. No
`QT_QPA_PLATFORM=wayland` override was lost.

Evidence: `appimage-original-wayland.log`, `appimage-original-xcb.log`,
`packaged-wayland/events.jsonl` and `mapped-libraries.txt`.

**Recommendation/risk:** leave backend behavior unchanged. If the diagnostic is
corrected upstream, it should describe default selection or account for an
explicit override. Unsetting XDG session/desktop variables, removing plugins or
forcing XWayland merely to avoid this text can alter integration and is not a
justified application fix.

## 2. QSocketNotifier warning

**Exact warning emitter:** bundled `libQt5Core.so.5`,
`QSocketNotifier::QSocketNotifier`, `qsocketnotifier.cpp` lines 163–170. The
condition is that this thread currently has **no event dispatcher**. It does not
prove that Vial started an illegal thread. The constructor warns and does not
register that notifier. [Matching Qt source](https://github.com/qt/qtbase/blob/v5.15.19-lts-lgpl/src/corelib/kernel/qsocketnotifier.cpp#L163).

The native stack on the main thread is:

```text
QApplication initialization / createEventDispatcher
  QGuiApplicationPrivate::createPlatformIntegration
    QWaylandIntegration constructor
      reconfigureInputContext
        QIBusPlatformInputContext constructor
          QFileSystemWatcher constructor
            QInotifyFileSystemWatcherEngine::create
              QSocketNotifier constructor
```

QtWayland calls `reconfigureInputContext()` from its integration constructor,
before its event dispatcher is ready. The IBus input-context object owns a
filesystem watcher; constructing its inotify engine creates the notifier at
that early point. This occurs in a minimal QApplication without importing Vial
or fbs. The session requests IBus through `QT_IM_MODULE=ibus`.
[QtWayland constructor](https://github.com/qt/qtwayland/blob/v5.15.19-lts-lgpl/src/client/qwaylandintegration.cpp#L106),
[IBus input context](https://github.com/qt/qtbase/blob/v5.15.19-lts-lgpl/src/plugins/platforminputcontexts/ibus/qibusplatforminputcontext.cpp#L112).

**Impact:** GUI display, timers and the observed HID reads work. Previous
signal-wakeup tests also passed, and this trace occurs before fbs installs its
own signal handler. It is unrelated to Vial's discovery QThread. However,
calling it entirely harmless would be too strong: a watcher created before the
application missed a temporary file modification, while the otherwise identical
watcher created afterward received `fileChanged`. That confirms an actual
registration problem for this initialization pattern. IBus uses file monitoring
for address-file changes, so reconnect behavior may be impaired; the session's
IBus daemon was not restarted and full IME reconnection was not tested.

Evidence: `qt-gdb-shared-xdg.log` (native stack), `watch-early.log` (no event),
`watch-late.log` (event received), `watch_probe.py`.

**Proposed smallest behavior-preserving direction:** defer creation/registration
of the input-context watcher until the dispatcher exists. A targeted QtWayland
lifecycle patch could move input-context initialization into its initialized
phase and guard early registry-driven reconfiguration. This needs validation,
not an untested one-line patch in Vial. It is a dependency fix, not a Vial
threading rewrite. Do not repair a private Qt object from Python, disable IBus,
or filter the message as a reliability fix.

**Compatibility risk:** input-context creation timing affects compositor seat
setup, focus, composition, dead keys and IME reconnect. A patched Qt plugin must
match the bundled Qt private ABI. Using a host Qt plugin or migrating the whole
client to Qt6 just for this message would broaden risk substantially. XWayland
is already an optional workaround, but changes the display backend and does not
by itself repair the separate XDG isolation issue below.

## 2a. Confirmed packaging problem: IBus config discovery is isolated away

`util/native-linux/runtime_hook.py` appends `vial-astro` to `XDG_CONFIG_HOME`
before QApplication creation. This successfully separates Vial preferences,
but it also changes the shared Qt config location used by IBus. Qt's IBus code
builds its address-file path from `QStandardPaths::ConfigLocation` unless an
explicit `IBUS_ADDRESS_FILE` override is present. None is set in this session.
The normal Wayland address file exists under `~/.config/ibus/bus/`; it does not
exist under `~/.config/vial-astro/ibus/bus/`.

GDB measurements on the same Qt build and session:

| Process config setup | IBus `isValid()` | Compose fallback constructed |
|---|---|---|
| Normal shared XDG config root | true | no |
| Temporary Astro-style isolated root | false | yes |
| Actual existing `~/.config/vial-astro` root | false | yes |
| Normal XDG root, only QSettings redirected to Astro | true | no |

The last diagnostic retains the existing preference filename
`~/.config/vial-astro/Vial/Vial.conf` and leaves the shared config root
`~/.config`. It runs natively on Wayland. The notifier warning still occurs,
showing these are **two independent problems**. No stored settings values were
written by the experiment. Logs: `qt-gdb-actual-astro-xdg.log`,
`qt-gdb-settings-path-only.log`, `qt_settings_probe.py`.

**Recommended first fix:** replace the global `XDG_CONFIG_HOME` redirection with
Linux process-local `QSettings.setPath(NativeFormat, UserScope, astro_config)`
before creating Vial's settings. Keep the inherited XDG config root available
to Qt plugins. The tested path reproduces the current Astro settings filename,
so it need not touch or import the existing official Vial configuration. The
current data/cache paths can remain for this minimal correction.

This is a concrete input-method compatibility issue even though ordinary
keyboard configuration works. Normal Compose/dead-key behavior is not equivalent
to a working IBus input method. Do not force `QT_IM_MODULE=compose` as the fix.
An `IBUS_ADDRESS_FILE` bridge could address only this dependency, but duplicates
session discovery logic and requires correct custom-XDG/display/portal handling;
application-scoped settings isolation is the safer direction.

**Risk/tests before shipping:** preserve the existing Astro preference path,
respect custom XDG roots, keep user/system settings scopes separate, verify
Wayland and XWayland input methods, and verify that official Vial settings are
never read or overwritten. QSettings path overrides are process-local but affect
QSettings users within that process; audit those consumers. No changes are
needed to the keyboard protocol or firmware.

## 3. HID enumeration warnings

**Emitter:** Python `logging.warning()` in `util.is_rawhid()`,
`src/main/python/util.py` lines 70–75. `find_vial_devices()` notices the Vial
serial on every collection, then filters by usage. Explicit initial/manual
refresh uses `quiet=False`, so expected rejections are printed. Ordinary polling
uses `quiet=True`.

The device has one serial across multiple HID collections:

| Interface / node | Reported usages | Result |
|---|---|---|
| 0 / hidraw5 | `0001:0006` | Expected keyboard-input rejection |
| 1 / hidraw6 | `0001:0002`, `0001:0001`, `0001:0080`, `000C:0001`, `0001:0006` | Expected composite-input collection rejections |
| 2 / hidraw7 | `FF60:0061` | Accepted Vial Raw HID |

Repeated hidraw6 records are multiple collections on one interface, not five
additional physical interfaces. Six mismatch warnings on a verbose scan are
therefore expected. The correct Raw HID node opens successfully and is the only
node opened by the guarded probes. The live configurations load successfully on
both backends. The wrapper forbids opening any other node and forbids setters;
no block was triggered.

Evidence: `packaged-wayland/interfaces.json`, console warnings and
`hid_open` events; corresponding `packaged-xcb` records.

**Recommendation:** no change to selection criteria. Expected usage mismatches
would be better debug diagnostics. Keep the separate open/permission-error
warning (`util.py` lines 86–91), because failure to open the matching interface
is actionable. Changing every `is_rawhid` message to debug would hide real
permission failures. This severity proposal was not applied during investigation.

## 4. Two “Use RGB Protocol V1” messages

**Emitter:** plain Python `print()` at
`src/main/python/protocol/keyboard_comm.py:178`, inside `Keyboard.reload_amk()`.
This is not a firmware protocol-version request. The client chooses the RGB LED
index width from the definition's `rgb_led.total`: totals above 254 select V2,
otherwise V1. This keyboard declares 128. There is one relevant `rgb_led`
declaration, and the line prints once per complete keyboard reload.

**The two lines are duplicate initialization, not two legitimate RGB components.**
The overlapping paths are:

1. `Autorefresh.__init__()` connects and starts the discovery worker.
2. `AutorefreshThread.run()` immediately calls `update()`.
3. Before queued initial results are delivered, MainWindow's constructor also
   calls `on_click_refresh()` → `update(quiet=False, hard=True)` synchronously.
4. Both scans can publish a reload-triggering result. The synchronous result
   selects and reads the keyboard immediately. The queued background result can
   then select it again, close/reopen its handle and reload it a second time.

Both `MainWindow.on_device_selected()` calls run on the GUI thread; this is a
startup ordering race, not two simultaneous settings writers. `hard=True`
forces the explicit update to publish even when paths match; the worker can
also have computed “current device absent/changed” before selection finishes.
The identical path therefore arrives twice with a true reload flag.

Natural guarded extracted-bundle runs on **both Wayland and XWayland** each
recorded **two `Keyboard.reload()` calls, two RGB lines, and 825 complete getter
replies**. At about 1.1 s the first selection starts; around 3.7 s the queued
selection starts. Initial source runs yielded one selection, demonstrating the
timing dependence. A diagnostic-only 200 ms delay before startup hard refresh
lets the worker result arrive first and reproduces the double reload in source
as well. That delay exists only in the scratch probe and is not a proposed fix.
The RGB call stacks lead through `Autorefresh.select_device()` →
`VialKeyboard.open()` → `Keyboard.reload()` in both cases.

Evidence: `packaged-wayland/events.jsonl`, `packaged-xcb/events.jsonl`,
`source-background-first/events.jsonl`, scratch `gui_probe.py`.

**Recommended small fix:** initialize the no-device UI locally, then rely on
the worker already started for the initial discovery; remove the constructor's
second hardware hard refresh. Retain a deliberate user Refresh as a hard reload.
A broader worker-owned request queue could serialize later scans, but is not
needed merely to address the confirmed startup duplication. Suppressing a
second print would leave the duplicate hardware reads and UI work in place.

**Risk/tests:** startup with zero/one device, hotplug while initializing,
disconnect/reconnect, VIA cache loading and explicit Refresh should be covered.
Avoid indiscriminately dropping every same-path hard refresh: that would break
intentional refresh behavior. No settings corruption or transport failure was
observed; the proven effect is redundant reads/rebuilds and startup latency.

## Unchanged artifacts and limits

The distributed AppImage SHA256 remains:
`9ee60fe40d6963d9e57cf19008ba62c1bf1497957414ecb87a819e4c9d350327`.
A pre/post hash comparison of all existing application, tests, packaging code
and build documents found no changes. Only this report was added; captures,
source snapshots and test scripts stay in the ignored investigation directory.

No live IBus restart, global IME engine change, keyboard write, calibration,
firmware operation or desktop integration change was performed. The early-watcher
mechanism and input-method validity were tested separately; actual end-to-end
IME composition/reconnection should be verified after any authorized fix.
The previous unavailable vendor documentation is not reinterpreted here as
proof of new firmware semantics: HID observations and client filtering are
reported as measured behavior. All proposed fixes remain unapplied.
