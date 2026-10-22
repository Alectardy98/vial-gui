# RGB Strips fix validation — 2026-10-22

Artifact: `target/astro/Vial-Astro-0.7.5-x86_64.AppImage` (57,383,416 bytes).
SHA256: `c9482da636038df06f1163d8007c7809a42b361f20f7be6ff173909f5c166d36`. The adjacent `.sha256` file verifies the delivered artifact.
Implementation and reproduction: [RGB-STRIP-FIX.md](RGB-STRIP-FIX.md).

| Check | Result | Evidence under `target/astro/` |
|---|---|---|
| Full automated suite | **80 passed in 56.08 s**; eight new strip regressions | `rgb-strip-fix/tests-final.log`, `automated-tests/results.xml` |
| Focused strip/sync tests | 24 passed | `rgb-strip-fix/tests-targeted.log` |
| Native Wayland live GUI | First strip polls automatically; selecting strip 1 reads global 85–103; preview equals received colors; tab departure stops reads; return preserves strip 1 | `rgb-strip-fix/live-wayland/`, `live-summary.json` |
| XWayland live GUI | Same behavior, actual backend `xcb` | `rgb-strip-fix/live-xcb/`, `live-summary.json` |
| Live RGB Grid regression check | Original Grid polls global 0–63 while active, then stops on return to Strips | Both live GUI captures |
| Live read-only safety | 470 exchanges per backend, including 65 RGB frame getter reports; all AMK statuses AA; zero blocked writes/probe errors | Per-backend `transactions.jsonl`, `result.json` |
| Fresh frame data | 21 identical getter request shapes received changing replies on each backend | `rgb-strip-fix/live-summary.json` |
| Final AppImage startup | Wayland, XWayland and ordinary FUSE pass; 23 editors construct; source/venv hidden for independent platform checks | `rgb-strip-fix/appimage-startup.log`, `independent-test/` |
| Final packaged hardware diagnostics | 500 reads; no transport errors, blocked writes or unsupported synchronization requests | `rgb-strip-fix/packaged-hardware.log`, `hardware-validation/` |
| Grid/protocol unchanged | Both files match pre-fix SHA256 hashes | `rgb-strip-fix/protected-before.sha256` |
| Preferences/source integrity | Existing official Vial and Astro preference hashes unchanged; embedded source manifest matches checkout | `rgb-strip-fix/preferences-before.json`, `preferences-after.json`, AppDir source manifest |

Live GUI validation used the source application with the actual connected
`4D58:0103` keyboard and its existing settings. Every HID output was getter-
allowlisted, other physical device nodes were hidden and direct USB operations
were disabled. Qt timers performed the existing selected-group reads; the
bounded observer only checked state and changed tabs/list selection. No RGB
control, effect, speed, synchronization, calibration, keymap, macro or firmware
was written. Logs include exact getter requests and replies.

The live checks began with automatically selected strip 0 (global 66–84), moved
to strip 1 (85–103), left the page and verified no strip reads, checked the original
Grid, then returned to Strips with index 1 preserved. Reconnection/device-change
cases were tested with virtual devices; no physical unplug/reset was performed.
Both RGB protocol versions were exercised by automated fake responders; the
physical keyboard uses the existing V1 path.

Screenshots:

- [Native Wayland](../../target/astro/rgb-strip-fix/live-wayland/rgb-strips.png)
- [XWayland](../../target/astro/rgb-strip-fix/live-xcb/rgb-strips.png)

Only the selected strip is polled periodically. The original one-time activation
read still samples the whole strip feature. The fix does not continuously reread
external settings or animate every strip preview concurrently. The existing
50 ms interval, getter formats, capabilities and custom edit handlers are retained.
No new timer/thread/polling architecture or RGB Grid change was introduced.

Existing Qt notifier/GNOME messages remain as previously documented. Device-node
isolation can cause Mesa warnings before software rendering fallback. The two
pytest warnings come from the pre-existing Polish-map backslash escape (import
and source audit); no unrelated keyboard-map change was made.

The application remains repository-local. No GNOME installation, desktop
integration or favorites change was made. Reproduce the suite/build/packaged
checks with the commands in `RGB-STRIP-FIX.md`; the bounded live observer and
launcher are retained in `target/astro/rgb-strip-fix/gui-readonly.py` and
`run-gui-readonly.sh`. Close other Raw HID clients before read-only hardware tests.
