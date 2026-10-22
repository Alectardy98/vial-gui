# RGB Strips live-color fix

The investigation in `RGB-REALTIME-DIAGNOSTICS.md` found an unselected strip
index preventing the existing timer from requesting colors. The fix is confined
to `src/main/python/amk/rgb_strip.py`; RGB Grid and protocol code are unchanged.

## Behavior

- Rebuilding the strip/effect lists selects the first available strip unless the
  current strip index is still valid. Visible and internal selection match.
- Tab changes retain selection on the same opened keyboard. A newly opened
  keyboard starts at strip 0 so an index from another definition is not reused.
- Disconnect/empty strip definitions clear selection and stop polling. A valid
  in-place rebuild preserves an already active timer.
- Programmatic effect, synchronization, custom-color and brightness refreshes
  use QSignalBlocker. The synchronization helper now restores any enclosing
  blocker correctly. No refresh is interpreted as a user setting change.
- Selecting a strip refreshes all existing cached controls, including brightness
  and Custom-mode availability, without transmitting SET commands.
- The original activation read, 50 ms QTimer, selected-strip frame getter,
  addressing, protocol-version handling and user edit handlers are retained.
  No background loop or additional polling timer was added.

Only the selected strip is sampled periodically. Other strip previews retain
their last sampled colors. External effect/settings changes are not continuously
reread; this fix concerns rendered colors. RGB Grid remains unchanged.

## Regression coverage

`test_rgb_strip_live.py` adds eight cases covering automatic selection, V1/V2
frame ranges and preview changes, timer start/stop/resume, same-keyboard rebuild,
disconnect/reconnect/device replacement, invalid-index fallback and two empty
strip-definition shapes. Fake transports accept only rendered-color getters;
any unexpected SET or other command fails the tests. Nondefault synchronization,
custom-color, brightness and Custom-mode states exercise programmatic refreshes.
Existing synchronization capability and full application regressions remain.

Reproduce with:

```sh
./util/native-linux/test.sh
./util/native-linux/build.sh
./util/native-linux/test-appimage.sh
./util/native-linux/test-hardware-readonly.sh
```

Close other clients using the Raw HID interface before hardware validation;
concurrent readers can consume one another's replies. The hardware script checks
for an existing opener and refuses to interfere with it. All hardware validation
uses the getter allowlist; no RGB values, settings, calibration, firmware, macros
or keymaps are written. Device-free automated tests and smoke tests use isolated
profiles. Nothing is installed into GNOME.

See `RGB-STRIP-VALIDATION.md` for the current artifact checksum, suite results and
bounded live GUI captures on Wayland and XWayland.
