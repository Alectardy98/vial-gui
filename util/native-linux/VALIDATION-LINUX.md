> Historical RGB-fix validation. For the current artifact and startup fixes, see [STARTUP-VALIDATION.md](STARTUP-VALIDATION.md).

# Final validation — 2026-10-22

Updated artifact: `target/astro/Vial-Astro-0.7.5-x86_64.AppImage` (about 55 MB).
SHA256: `9ee60fe40d6963d9e57cf19008ba62c1bf1497957414ecb87a819e4c9d350327`.
The SHA256 sidecar is beside the AppImage. Source changes and reproduction steps:
[CHANGES-LINUX.md](CHANGES-LINUX.md), [README.md](README.md).

| Check | Result | Evidence under `target/astro/` |
|---|---|---|
| Original full automated suite plus regressions | 42 passed, zero failures/errors/skips, 41.31 s | `tests-final.log`, `automated-tests/results.xml` |
| Native Wayland, source/venv hidden | One visible window, all 23 editors constructed; screenshot checked | `independent-test/wayland.log`, `wayland.png` |
| XWayland (`xcb`), source/venv hidden | Startup passed, all 23 editors constructed | `independent-test/xcb.log`, `xcb.png` |
| Normal AppImage/FUSE runtime | Startup and bundled libusb initialization passed | `independent-test/native-runtime.log` |
| Packaged client detecting physical keyboard | Selected VID/PID `4D58:0103`, interface 2, `/dev/hidraw7`, usage `FF60:0061` | `hardware-validation/hid-enumeration.json`, `summary.json` |
| Packaged full configuration reload | Complete; 500 read requests including preliminary samples; zero transport errors or blocked commands | `hardware-validation/transactions.jsonl`, `packaged.log` |
| RGB sync warnings | Zero unsupported sync requests, zero RGB reload warnings; all AMK replies status `0xAA` | `hardware-validation/reload-stdout.txt` (only `Use RGB Protocol V1`) |
| Preserved keyboard configuration | Keymaps, macros, QMK settings, dynamic entries, NKRO, polling, debounce, RGB modes/speeds/enables/custom codes match the pre-fix snapshot | `hardware-validation/configuration-comparison.json` |

The live test used a copied finished AppImage with the repository, venv and uv
Python hidden. Only the intended Raw HID node was exposed; the bundled harness
applied its getter allowlist before every transmitted request and exited before
the interactive GUI began. No firmware, calibration, RGB, keymap or macro writes
were made. All handles were closed. The full live reload has 381 transactions,
seven fewer than before; preliminary sampling avoids a further 28 unsupported
sync queries, giving 500 total instead of 535. All read reports were complete.
Measured live transaction time: median 2.256 ms, maximum 12.244 ms.

The keyboard still identifies as VIA protocol 9 / Vial protocol 6, UID
`D031F66047701780`, four layers. Its compressed definition hash remains
`687e4a60b7aa11137fad5f89d657f67c2c7dd7be60680adf666aca85109124a5`.
Runtime RGB colors may change with existing animations; the saved mode and speed
comparisons above agree. No hardware write paths were tested.

Synchronization-enabled hardware support is covered by virtual regression
responses and UI behavior, including master index zero. No second physical
sync-capable keyboard was available. Other custom functionality remains present;
this MX keyboard cannot validate every magnetic/EC/animation/firmware variant.

The Qt5 Wayland/IBus QSocketNotifier warning remains as diagnosed. It has no
observed effect on these startup/read tests; IME reconnection is untested. GPU
initialization warnings in the strict Wayland sandbox result from hiding GPU
nodes; rendering and screenshot checks passed. The app still needs host glibc,
graphics services and optional polkit, and has not been certified on older
Linux distributions.

No system desktop integration or existing Vial installation was modified.
