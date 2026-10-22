# Startup fixes validation — 2026-10-22

Delivered artifact: `target/astro/Vial-Astro-0.7.5-x86_64.AppImage`.
SHA256: `182ca38d0e468194c9e3ba1466ae70f8ddbffecfc9325381ce24f563d00480f0`.
The adjacent `.sha256` file verifies the artifact. Implementation and reproduction
commands are in [STARTUP-FIXES.md](STARTUP-FIXES.md) and [README.md](README.md).

## Results

| Check | Result | Evidence below `target/astro/` |
|---|---|---|
| Full automated suite | 54 passed in 46.56 s; physical devices inaccessible | `startup-fixes/tests.log`, `automated-tests/results.xml` |
| Independent final AppImage | Native Wayland, XWayland/xcb and ordinary FUSE launch pass; source/venv hidden for independent platform checks; all 23 editors construct | `startup-fixes/final-startup.log`, `independent-test/` |
| IBus integration | Actual bundled Qt IBus context reports valid on both platforms, without Compose fallback | `startup-fixes/ibus-wayland.log`, `ibus-xcb.log` |
| Guarded live GUI lifecycle, both platforms | Startup: 1 reload; manual Refresh: 2 cumulative; discovery removal: still 2; reconnect: 3; unchanged polling adds none | `startup-fixes/gui-lifecycle-summary.json`, `packaged-wayland/`, `packaged-xcb/` under `startup-fixes/` |
| Guarded live GUI communication | 1,230 getter exchanges per platform, all 32-byte replies, zero blocked commands; RGB protocol print once per legitimate reload | Same lifecycle captures |
| Final packaged hardware diagnostics | 500 getter exchanges; no communication errors, blocked writes or unsupported RGB synchronization requests | `startup-fixes/final-hardware.log`, `hardware-validation/summary.json`, `transactions.jsonl` |
| Settings isolation/persistence | Existing Astro theme retained; separate packaged processes write/read a temporary Astro preference; shared config root unchanged; official fixture untouched | `startup-fixes/settings-persistence.json`, `settings-write.log`, `settings-read.log` |
| Existing user preferences | Real official Vial and Astro files remain byte-identical | `startup-fixes/preferences-before.json`, `preferences-after.json` |
| Expected HID filtering | DEBUG messages for normal non-Raw interfaces; permission and unexpected-descriptor warnings retained | `test_hid_logging.py`, full test results |
| RGB regression | No repeated sync errors; unsupported synchronization remains gated by declared capability | Full suite, hardware and GUI captures |

Connected device: VID `4D58`, PID `0103`, Raw HID interface 2, usage
`FF60:0061`, `/dev/hidraw7`; Vial UID `D031F66047701780`, VIA 9 / Vial 6.
Only documented getter requests were allowed during live GUI/diagnostic tests.
No keyboard settings, firmware, calibration, RGB values, macros or keymaps were
written. No official installation or desktop integration was changed.

The instrumented GUI and GDB IBus checks used a disposable extracted copy of the
packaged executable and temporary profiles, with the real session IBus address
files exposed for discovery. Hotplug was simulated by removing/reintroducing the
connected device in discovery results; the physical device stayed connected.
The final rebuild includes test portability annotations and documentation.
Its frozen main module, runtime hook and complete Python archive are byte-identical
to the payload used in those live GUI/IBus checks:
`startup-fixes/final-payload-comparison.json`. The final source manifest was
verified against the checkout, and final independent startup and getter diagnostics
were rerun against the delivered AppImage.

## Remaining limitations

- Qt 5.15.19 on native Wayland still initializes the IBus file watcher before the
  main event dispatcher, emitting `QSocketNotifier`. Restoring IBus discovery
  fixes context validity but does not repair that watcher lifecycle. IME address
  file replacement/reconnection may remain affected; desktop IBus restart was
  not exercised. No supported minimal public-API fix was found; no Qt binary
  patch, warning filter, IBus disabling or custom dispatcher was introduced.
- QtGui may still print the GNOME/XDG informational message before honoring the
  explicit platform override. Actual `platformName()` confirms native Wayland.
- Physical USB unplug/replug, IME text composition/restart, other keyboard firmware,
  and hardware write paths were not validated. Discovery removal/reappearance,
  unchanged polling and manual Refresh were validated with real reads and virtual
  regression fixtures.
- The AppImage bundles its Python/Qt/application dependencies but uses host kernel,
  glibc, display/session and graphics services. Validation covers this Manjaro
  x86_64 host; compatibility with older distributions is not certified.

The custom editors and AMK/Vial command formats are preserved. Windows/WebHID
retain their explicit startup refresh because their discovery implementations
lack Linux's initial polling scan. No unrelated application refactoring was made.
