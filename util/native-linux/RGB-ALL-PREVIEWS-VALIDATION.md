# All RGB Strips animation previews — validation

Artifact: `target/astro/Vial-Astro-0.7.5-x86_64.AppImage` (57,387,512 bytes).
SHA256: `658aea6aef17189f177acf2e3a0df8531c11c1389b9fb1fa647d247b7c2b93e8`. The adjacent `.sha256` file verifies the delivered artifact.
Implementation, baseline investigation, packet limits and reproduction commands:
[RGB-ALL-PREVIEWS.md](RGB-ALL-PREVIEWS.md).

## Results

- **87 tests passed in 57.23 s**, including seven new changing-frame, repaint,
  batching and slow-link cases. Focused strip/synchronization suite: 31 passed.
- The baseline probe observed an actual paint event while only the selected
  strip's three fixture LEDs changed. The corrected tests change every displayed
  LED across successive independently varying simulated frames, regardless of
  selection, and observe Qt paint events.
- Live source GUI and copied frozen-payload GUI passed on native Wayland and
  XWayland. Each run completed 849 getter exchanges with all AMK statuses AA,
  zero blocked writes and zero probe errors. Each strip session sampled 60 full
  sweeps / 420 frame-getter reports, sometimes spread across callback boundaries.
- All five physical strips configured with animated effects changed continually:
  Top left (Circle), Top right (Circle), Right circle (Rainbow), LED bar (Static
  Inverse Scan), Left circle (Circle). LED square and 100NG were configured Static;
  their unchanged colors correctly matched unchanged firmware replies. No effect
  or RGB value was changed to manufacture this result.
- Selection changed configuration controls without limiting the read range.
  Leaving Strips stopped its reads, the original Grid polled normally, and
  returning resumed complete-strip previews with the selection retained.
- The final unmodified AppImage passed independent Wayland/XWayland startup and
  ordinary FUSE launch checks, constructing all 23 editors. Independent platform
  checks hid the source and Python environment.
- Final packaged read-only diagnostics passed **500 exchanges**, without transport
  errors, SET commands or unsupported synchronization requests.
- RGB Grid and AMK protocol files match their pre-change SHA256 hashes. The
  embedded source manifest matches the checkout; official Vial and Astro
  preference hashes stayed unchanged during packaged validation.

## Measured frozen GUI performance

| Measurement | Wayland | XWayland |
|---|---:|---:|
| Reports/full 61-LED sweep | 7 | 7 |
| Median poll callback | 33.01 ms | 33.72 ms |
| 95th percentile callback | 42.71 ms | 42.55 ms |
| Maximum callback | 46.23 ms | 45.40 ms |
| Median complete-sweep interval | 50.11 ms | 50.24 ms |
| Median callback CPU time | 0.98 ms | 1.05 ms |
| Instrumented process CPU, one-core basis | 18.9% | 20.8% |
| Selection handler | 0.099 ms | 0.105 ms |
| Actual preview paint events | 63 | 65 |

CPU includes diagnostic observers and software rendering with GPU device nodes
hidden. These figures describe this host and test environment, not a universal
CPU guarantee. A 10 ms observer heartbeat had a roughly 52–54 ms 95th-percentile
interval during active preview sessions. Transition/paint outliers reached about
113–126 ms, including tab activation and the unchanged Grid's existing synchronous
read. The strip callback budget is cooperative, not a hard event-loop deadline.

Before the fix, reading each strip separately would cost 11 reports and 58.33 ms
median. The declared contiguous range costs seven reports and 32.85 ms median
in the isolated transport benchmark. Both methods returned complete valid data;
using the feature range avoids redundant partial packets across strip boundaries.

A fast synthetic 255-strip, one-LED/group V2 fixture uses 32 reports. An injected
21 ms/report link yields after two reports/42 ms per callback and eventually
updates every strip, including later groups even if selection changes. Full-sweep
rate is necessarily lower on that link; its bandwidth cannot support 20 Hz.
The test models the byte-sized group-count boundary, not a promise of firmware
support for 255 groups or smooth 20 Hz animation on every device. A single HID
exchange can still take its existing timeout; no private transport/threading
change or protocol patch was introduced to interrupt it.

## Evidence and screenshots

Evidence lives below `target/astro/rgb-all-previews/`:

- `baseline.json` / `baseline.py`: read-versus-repaint reproduction.
- `benchmark.json` / `benchmark-transactions.jsonl`: 12 bounded cycles per policy.
- `tests-final.log`, `tests-targeted.log`: automated results; JUnit is also in
  `target/astro/automated-tests/results.xml`.
- `performance-summary.json`: source and frozen timings, changing group counts,
  repaint counts and errors.
- `live-wayland/`, `live-xcb/`: source GUI captures, exact getter/reply logs.
- `frozen-wayland/`, `frozen-xcb/`: copied final frozen GUI captures and getter logs.
- `packaged-hardware.log`, `appimage-startup.log`, `build.log`: artifact validation.
- `protected-before.sha256`, `preferences-before-packaged.json`,
  `preferences-after-packaged.json`: integrity checks.

[Wayland screenshot](../../target/astro/rgb-all-previews/frozen-wayland/rgb-strips.png)
and [XWayland screenshot](../../target/astro/rgb-all-previews/frozen-xcb/rgb-strips.png).
Successive frames are in the per-run `result.json` snapshots and exact wire logs.

The frozen GUI probe copies the final AppDir and replaces only its opt-in diagnostic
data payload, then loads the unchanged frozen main module/Python archive with the
original built-in runtime-hook order. It instruments the actual compiled GUI;
the shipped AppImage is unmodified. Separate standalone checks run the unmodified
AppImage. The bounded launchers and probes are retained beside their captures.

## Safety and remaining scope

Every live HID output was getter-allowlisted; only the target Raw HID node was
exposed. No firmware, settings, calibration, macro, keymap, effect or RGB value was
written. Physical reconnect/reset was not performed: lifecycle changes were tested
with virtual devices. Only this keyboard's V1 hardware path was exercised; V2 and
large/slow definitions use simulated responders.

All groups are refreshed progressively from rendered colors, not by rereading
external configuration controls. Hidden editors generate no RGB polling. A large
sweep may contain samples from different moments and span ticks; the protocol
does not provide an atomic full-page frame. Static physical lights correctly stay
static. Existing Qt notifier/GNOME messages and isolated-rendering Mesa warnings
remain unrelated to this fix. The two pytest warnings are the existing Polish-map
escape warning, emitted on import and by the English source audit.

English localization, synchronization capability gating and custom controls are
preserved. Nothing was installed into GNOME or added to desktop integration.
