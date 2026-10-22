# English localization and UI cleanup — 2026-10-22

This change localizes the custom Astro client, preserving its firmware protocol,
settings values, preferences, custom controls and Linux startup fixes. The
before/after catalog is [LOCALIZATION-STRINGS.json](LOCALIZATION-STRINGS.json).
It records 483 Chinese/bilingual Python/resource literal occurrences replaced
across 29 Python files and the QMK settings resource, plus six diagram captions.
Repeated occurrences are counted separately; this is not a count of unique words.

## Audit and implementation

The audit covers all 23 editors, navigation, keycode categories and tooltips,
macro controls, calibration, actuation/Rapid Trigger, DKS, Snap Tap, all RGB
editors, auxiliary display, animations, firmware/error dialogs, QMK resource
tabs, and definition-supplied layout/effect/custom-keycode display labels.
Chinese-only instructions are translated and shortened; existing English labels
are retained or polished where their meaning is clear. No translation catalogs
were present: English remains the source language for the existing `tr()` calls.
Internal translation contexts are retained, along with protocol constants,
QMK IDs, aliases, firmware metadata and numeric option indices.

| Area | Examples |
|---|---|
| Navigation | Keymap, Layout, Matrix Tester, Calibration, General, Firmware Updater |
| Magnetic switches | Actuation point (mm), Rapid Trigger distance (mm), Press/Release distance (mm), switch polarity and sensitivity |
| DKS | Event points 1–4 remain distinct; Travel and Bottom out diagram captions |
| RGB | Enabled, Dynamic, Blink, Breathing, Brightness, Synchronize, Custom color |
| General | N-key rollover (NKRO), Press/Release debounce (ms), distinct 1,000/2,000/4,000/8,000 Hz choices |
| Macros/QMK | English action types, save/revert/reset prompts, memory usage in bytes, 10 bilingual QMK resource titles |
| Errors/safety | Invalid file/protocol/macro errors; keyboard mismatch, restart, reset and firmware confirmations retained |

The DKS PNG embeds Chinese in six captions, including white lettering over
translucent event-point boxes. The original asset is retained. QPainter replaces
only those caption rectangles during UI construction, retaining transparency,
box geometry, arrows, event order, scaling and all controls. A regression checks
that every pixel outside those rectangles remains identical to the original.
No new image-format/plugin dependency is introduced.

`ui_text.device_text()` translates known Chinese-only definition labels, removes
Chinese suffixes when a definition supplies an English equivalent, and polishes
known RGB effect names. It is called only where labels are displayed in RGB
lists, layout selectors and custom keycode labels/tooltips. The original strings,
list ordering, `Custom` effect lookup and custom-keycode aliases stay unchanged.
Device/product identifiers, SSIDs, firmware command selectors and user content
are deliberately excluded from display-label translation.

## Redundancy and conventions

- Removed duplicated English/Chinese versions of labels throughout the UI.
- Consolidated the seven-line keymap instructions into a short operation guide;
  Layout/Matrix Tester help remains available as a tooltip. The immediate-apply
  warning stays visible.
- Shortened combo, Tap Dance and key-override descriptions without removing their
  operating rules or modifier distinctions. Descriptions now wrap to available width.
- Removed the empty `Description` heading from the keycode chooser; focused-key
  descriptions still appear in the same place.
- Replaced repetitive `Set the keyboard's…` labels with setting names, and `Toggle…`
  checkbox captions with their state/feature names.
- Shortened animation upload/status labels, preserving standard versus advanced
  upload modes, and kept explicit restart wording on buttons that restart a keyboard.
- Use title case for editor names/QMK feature names, sentence case within panels,
  established modifiers/NKRO/Rapid Trigger terminology, mm/ms units where known,
  and unambiguous Hz values for polling-rate choices.

## Ambiguities and scope limits

Snap Tap's First/Second source descriptions do not fully establish whether the
firmware means assigned key slots or press order. The UI retains neutral
First/Second priority wording; it does not claim an unverified temporal algorithm.
Firmware documentation would be needed to make those two descriptions more
specific. Mode IDs, order, handlers and behavior are unchanged. The depth/last
press/neutral modes retain their existing distinctions.

Unknown Chinese-only labels from a different or future keyboard definition are
preserved rather than guessed or discarded. All labels in the captured connected
keyboard definition and all application-owned UI text are covered. Names supplied
by users/devices (for example a Chinese SSID or product identifier) are not UI
localization defects and are not altered. Keyboard character outputs/layout maps
remain intact; international function-key captions use English/transliterated names.

Unsupported feature panels use marked presentation fixtures for visual validation;
they are not evidence of those features working on this physical keyboard.
Calibration algorithms, firmware flashing and all hardware write paths are outside
this localization validation. Existing Qt notifier/GNOME informational messages
remain as documented in [STARTUP-FIXES.md](STARTUP-FIXES.md).

## Reproduce

```sh
./util/native-linux/test.sh
# Uses the existing read-only capture; exposes no physical devices:
./util/native-linux/inspect-ui.sh wayland
./util/native-linux/inspect-ui.sh xcb
./util/native-linux/build.sh
./util/native-linux/test-appimage.sh
./util/native-linux/test-hardware-readonly.sh
```

`inspect-ui.sh` requires the existing recorded getter responses in
`target/astro/hardware-validation/transactions.jsonl`. The optional last command
refreshes that recording from the connected keyboard using the getter allowlist.
All visual inspection happens with synthetic `/dev`, temporary app preferences,
recorded responses and local presentation fixtures. The existing source launcher
and packaging workflow remain repository-local. No application installation or
GNOME integration is performed. Packaging stages the AppImage beside its output
path and renames it atomically, allowing an already running older instance to
continue without interruption; no process is stopped. Relaunch to use the new UI.

Current results, screenshots and artifact checksum are in
[LOCALIZATION-VALIDATION.md](LOCALIZATION-VALIDATION.md).
