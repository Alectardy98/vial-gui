# Finalized Linux changes

Base: `00157d122b63483523eecaf36cc1691faecc4949`. These are local changes on the
original custom fork, not a replacement client. No firmware operations, keyboard
configuration writes, system package/udev changes, existing Vial installation
changes or desktop integration changes were performed.

## Application sources

- `src/main/python/amk/protocol.py`: add a shared sync capability check. A valid
  `master` is a JSON integer (not bool) in the declared strip range and below
  `0xFF`, the existing unsynchronized sentinel. Index zero is valid. Only those
  strips receive the existing sync GET request; color, speed and optional
  brightness/custom-color queries continue for all applicable strips. Before a
  supported sync read, discard a stale cached sync value; a rejected reply still
  produces the existing error and leaves sync unavailable. No status definition,
  request opcode, byte order, field offset or setter format changes.
- `src/main/python/amk/rgb_strip.py`: apply the same capability check to the UI,
  and enable synchronization only when its current value was read successfully.
  Block checkbox signals during programmatic refresh so reading the value cannot
  emit a configuration-change action. Other custom editors are untouched.

The fix does not broadly suppress RGB warnings: advertised synchronization that
returns a non-success reply remains an error. Missing/malformed capability does
not trigger a speculative firmware request. Supported keyboards retain sync
reads and their existing user-initiated sync control/write path. No new
restriction on self-references is inferred beyond validating the index.

## Linux startup follow-up

See [STARTUP-FIXES.md](STARTUP-FIXES.md) for the startup changes and validation.
The native Linux runtime uses process-local QSettings isolation at the existing
Astro preference path and leaves the session XDG config root available to IBus.
Linux MainWindow startup initializes the empty UI and relies on its existing
discovery worker; explicit Refresh and Windows/web startup behavior are retained.
Expected HID usage mismatches are DEBUG diagnostics; malformed descriptors and
permission errors remain warnings. No additional Qt initialization workaround
is applied; the remaining notifier warning is documented.

## Original fixtures and regression tests

- `test/test_keyboard.py`: expect the custom fork's AMK GET_NKRO transaction
  after standard Vial/encoder reads, with success/NKRO-enabled response.
- `test/test_gui.py`: teach the virtual keyboard GET_NKRO, update label assertions
  to this fork's actual bilingual labels, and use integer QPoint coordinates.
  The original fixture resource lookup remains unchanged.
- `test/test_rgb_sync.py`: 16 regression cases exercise absent/invalid masters,
  supported master zero and nonzero, exact original GET formats, mixed strip
  capabilities, preservation of optional RGB reads, retained warning on rejected
  supported reads, stale-state removal, and checkbox state refresh without a
  user-change signal or SET transaction.

The full automated suite is **54 passed** in the original source tree, with no
external fixture adapter. Virtual write tests run only with synthetic `/dev`;
no physical HID, USB or input nodes are accessible. Run `./util/native-linux/test.sh`.
JUnit: `target/astro/automated-tests/results.xml`; text: `target/astro/tests-final.log`.

## Packaging and validation helpers

The separate Python 3.11/PyQt5/PyInstaller toolchain, fbs runtime hook, resource
collection, pinned dependency lock, AppImage runtime checksum and separate Astro
profile remain in `util/native-linux/`. Existing Docker/fbs workflows and
requirements are not overwritten. `build.sh` builds the original entry point,
includes the license/build notes and records both the Git base and a source
manifest/diff for the local changes. `.gitignore` excludes local tools and venv;
existing `target` ignore covers artifacts and captures.

The diagnostic helper now uses the same capability check as the client and finds
resources correctly in frozen mode. The AppImage bundles it for explicit
`VIAL_ASTRO_READONLY_DIAGNOSTICS` invocation, exiting before GUI startup. Every
HID command still passes its getter allowlist. Normal interactive operation is
unchanged when that variable is absent. The PyInstaller spec includes the helper
and its required standard-library modules.

`test-appimage.sh` validates copied AppImages on native Wayland and XWayland with
the source/venv hidden, checks bundled dependencies, captures screenshots, and
also checks ordinary FUSE startup. It creates its output directory on a clean
checkout. `test-hardware-readonly.sh` validates the packaged client with only the
intended Raw HID node exposed and checks full read completion, successful AMK
statuses, zero unsupported sync requests and no blocked write attempts. Raw
results stay outside the distributed image; user keymaps/macros are not bundled.

Reproduce with:

```sh
./util/native-linux/test.sh
./util/native-linux/build.sh
./util/native-linux/test-appimage.sh
./util/native-linux/test-hardware-readonly.sh
```

The build creates `target/astro/Vial-Astro-0.7.5-x86_64.AppImage` and its SHA256
sidecar. Independent GUI logs/screenshots are in `target/astro/independent-test/`;
packaged live read results are in `target/astro/hardware-validation/`.

## Remaining limits

This release targets the tested Manjaro x86_64 host. Core glibc/graphics services
and optional polkit remain host dependencies; older distributions are not
certified. Global macro recording still uses the existing privileged helper.
The Qt5 native-Wayland/IBus QSocketNotifier startup warning is not a Vial HID
thread failure and is not hidden or patched here; IME reconnection remains
untested. This MX keyboard cannot validate magnetic/EC actuation/calibration or
all other firmware variants. Physical writes/uploads/macros/firmware operations
were deliberately excluded, and sync-enabled hardware was verified with virtual
protocol/GUI regressions rather than a second physical keyboard. The exact
vendor meaning of status `0x55` remains undocumented in the available materials.

## English UI localization

See [LOCALIZATION.md](LOCALIZATION.md) and its before/after string catalog for all 23 editors, resource/definition labels and the six embedded DKS diagram captions. Firmware/transport code and numeric option meanings are unchanged. The UI inspection script renders recorded and synthetic fixtures in a device-free sandbox.

## RGB Strips live preview

Select a valid strip automatically, preserve it across tab changes, clear it on disconnect/device replacement, and block signals during programmatic refresh. Reuse the existing 50 ms timer and rendered-color getter. Eight regressions added; Grid and protocol definitions are unchanged. Details: [RGB-STRIP-FIX.md](RGB-STRIP-FIX.md).

## All RGB Strips previews

Sweep the declared full RGB strip feature through the existing getter and timer, independent of configuration selection. Share packet capacity across strips and yield after a cooperative 40 ms budget for slow/large sweeps. Seven changing-frame/paint/batching/fairness regressions added; Grid and protocol files remain unchanged. See [RGB-ALL-PREVIEWS.md](RGB-ALL-PREVIEWS.md).
