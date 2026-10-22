# English UI validation — 2026-10-22

Artifact: `target/astro/Vial-Astro-0.7.5-x86_64.AppImage` (57,383,416 bytes; approximately 55 MiB).
SHA256: `6b2c1cc9b151fae1edd9fffac1f8a6334d58c21dbbc39b79e08a1d08b17f27e9`.
The adjacent `.AppImage.sha256` file verifies the delivered artifact.

[Implementation, conventions, redundancy cleanup and translation ambiguities](LOCALIZATION.md)
and [before/after string catalog](LOCALIZATION-STRINGS.json) document the change.

## Results

| Check | Result | Evidence under `target/astro/` |
|---|---|---|
| Full automated suite | **72 passed in 56.64 s**; 18 new localization cases plus the existing 54 tests | `localization/tests-final.log`, `automated-tests/results.xml` |
| English audit | 483 CJK/bilingual source/resource literal occurrences replaced (including JIS function-key captions); six embedded diagram captions localized | `util/native-linux/LOCALIZATION-STRINGS.json` in the repository; embedded in the AppImage |
| All editors rendered on native Wayland | 23 editors, seven QMK resource tabs, advanced controls and dialogs: 33 captures | `localization/visual/wayland/`, `localization/visual-wayland.log` |
| All editors rendered on XWayland | Same 33 captures; actual Qt backend `xcb` | `localization/visual/xcb/`, `localization/visual-xcb.log` |
| Keycode categories | Nine additional category captures, including international keys; shortened Hangul/Kana caption fits | `localization/visual/wayland/keycodes-*.png`, `keycode-inventory.json` |
| Text/layout review | All 75 captures indexed; no label-width clipping flags at captured sizes. Diagram, keymap instructions, international-key captions, RGB lists and advanced settings visually reviewed | `localization/visual/index.html` |
| Independent final AppImage | Wayland, XWayland and ordinary FUSE launch pass, all 23 editors construct; Python environment/source hidden in independent platform checks | `localization/appimage-startup-final.log`, `independent-test/` |
| Source integrity | Embedded source manifest matches the final checkout; 15 protocol/transport/keycode-number files byte-identical to the pre-localization snapshot | `localization/final-payload-verification.json`, before/after catalog metadata |
| Preferences | Current official Vial/Astro hashes remain unchanged during packaging/validation; tests use temporary profiles and verify persistence/isolation | `localization/preferences-before-packaging.json`, `preferences-after-validation.json`, full suite |
| Existing regressions | RGB capability gating, startup single reload, manual Refresh, reconnect and settings tests remain passing | Full suite |

The automated test warnings are the existing invalid backslash escape in the
Polish keyboard map, reported once on import and once by the new AST audit.
No keyboard map character output was changed to silence them.

## Screenshots

Browse the [complete visual gallery](../../target/astro/localization/visual/index.html).
Representative captures:

- [Keymap and concise instructions](../../target/astro/localization/visual/wayland/01-keymap.png)
- [RGB grid and translated device effects](../../target/astro/localization/visual/wayland/06-rgb-grids.png)
- [English DKS diagram and controls](../../target/astro/localization/visual/wayland/11-dks.png)
- [Advanced settings](../../target/astro/localization/visual/wayland/13-general-advanced.png)
- [International keycodes](../../target/astro/localization/visual/wayland/keycodes-2.png)
- [Key overrides and modifier terminology](../../target/astro/localization/visual/wayland/20-key-overrides.png)

The gallery distinguishes recorded-keyboard panels from synthetic/unsupported
panels. The connected keyboard's prior getter capture supplies the real definition,
configuration and RGB labels; unavailable feature controls use local presentation
fixtures. The calibration panel has no text controls beyond its navigation title
and its unsupported constructor state is not evidence of magnetic calibration
working on this physical keyboard. No unsupported feature was enabled on hardware.

## Safety, compatibility and limits

All visual/test runs use synthetic device nodes, temporary profiles and recorded
responses. No live HID requests, firmware operations or keyboard configuration
writes were needed for localization. The existing getter capture was replayed;
fresh physical-device validation was not run while the user's GUI remained open.
Protocol definitions, command formats, setters, calibration logic, preferences
schema and device identities remain unchanged. No existing Vial installation,
GNOME integration or desktop favorites were modified.

The user's already running AppImage was left running. Packaging initially found
its backing executable busy, so `build.sh` now stages the new image beside the
destination and renames it atomically after successful packaging. This prevents
truncating a mounted image and retains the old running instance. Relaunch the
AppImage to use the new English UI.

The earlier Qt Wayland/IBus notifier warning and GNOME informational line remain
as diagnosed in the startup reports. Synthetic `/dev` rendering can also report
Mesa GPU initialization failures before falling back to software rendering; the
UI checks pass. No warning filter or IBus disabling was added.

Snap Tap First/Second firmware semantics and unknown future Chinese-only device
labels remain the documented translation limits. No timing, mode ordering or
hardware behavior is inferred from the English wording. Other firmware variants,
all hardware write paths and every display scale/window size are outside this
presentation validation. The AppImage remains tested for this Manjaro x86_64 host.
