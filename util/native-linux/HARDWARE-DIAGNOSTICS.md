# Connected keyboard diagnostic report — 2026-10-22

Historical pre-fix investigation. The authorized implementation and final
validation are documented in [CHANGES-LINUX.md](CHANGES-LINUX.md). Original
captures, results and the old artifact hash below are retained as evidence.

The keyboard communicates reliably with this Linux client. The repeated RGB
message is a synchronization capability mismatch, not an observed HID transport
failure. The Wayland startup warning is a separate Qt/IBus initialization issue.
No application fixes were implemented and the AppImage was not rebuilt.

## Scope and evidence

Repository HEAD: `00157d122b63483523eecaf36cc1691faecc4949`.
Device: `4D58:0103`, FAUKWAA-[MY-2K] 100NG Edition, serial
`vial:f64c2b3c`. Live Vial keyboard UID: `D031F66047701780`.
VIA protocol: 9; Vial protocol: 6. These are protocol versions, not an identified
firmware build revision. The client's `AMK_VERSION=0.9.11` is not proof that the
connected firmware has that version.

Only source-defined getter requests were transmitted. A diagnostic transport
allowlist rejected setters, reset/reboot, unlock/lock, calibration, firmware and
file operations before transmission. HID output reports necessarily use the
host library's `write()` method to send read requests; none was a configuration
write command. No firmware, keyboard settings or existing app preferences were
changed. No HID/USB kernel driver was detached or interface claimed with libusb.
No GUI with unrestricted hardware access was launched for this investigation.
The diagnostic processes closed their HID handles afterward.

Raw captures and results are under `target/astro/diagnostics/`. All 1,422 recorded
transactions, including preliminary diagnostic runs, had a 33-byte host report
and 32-byte reply, with no retry, timeout, short report or I/O error. Measured
exchange latency: minimum 0.975 ms, median 2.289 ms, maximum 24.716 ms. The
harness adds 5 ms between requests, outside that measurement. This establishes
reliability for this sample, not a long-duration soak or multiple concurrent
clients. No other Vial process was found holding the interface during capture.

## Detection and interface selection

| Interface | Linux node | Enumerated usages | Use |
|---|---|---|---|
| 0 | `/dev/hidraw5` | `0001:0006` | Keyboard input |
| 1 | `/dev/hidraw6` | Mouse, pointer, system/consumer controls, keyboard | Composite input/NKRO |
| 2 | `/dev/hidraw7` | `FF60:0061` | Selected Vial Raw HID interface |

The HID paths are observations for this connection and may change after a
reconnect. `util.is_rawhid()` explicitly checks `FF60:0061`; it does not select
an interface just because its VID/PID or serial matches. The selected node opens
as the ordinary user with existing permissions. USB descriptors advertise three
interfaces and high-speed operation. `lsusb -v` could not open the usbfs device
node to obtain every descriptor, but the HID report descriptor was readable in
sysfs; no privilege escalation was needed. Saved descriptors:
`usb-descriptors.txt` and `hidraw*-report-descriptor.hex`.

The compressed keyboard definition is 1,572 bytes, SHA256
`687e4a60b7aa11137fad5f89d657f67c2c7dd7be60680adf666aca85109124a5`.
It decompresses and parses successfully and declares an `mx` keyboard, `hs`
speed, 8 rows, 16 columns, four live layers, a 64-LED grid, seven strips totaling
61 LEDs, and 128 LEDs overall. Generic `lighting: none` does not mean there is no
custom RGB: AMK features declare it separately.

## RGB parameter 3

The client defines:

- `AMK_PROTOCOL_PREFIX = 0xFD`.
- `AMK_PROTOCOL_GET_RGB_PARAM = 61 = 0x3D`.
- `RGB_TYPE_STRIP = 1`.
- `RGB_PARAM_SYNC = 3`.
- `AMK_PROTOCOL_OK = 0xAA`.

Parameter 3 controls a strip's synchronization relationship to a master strip.
The UI enables its synchronization checkbox only for strip definitions with a
`master` field. On success the client reads the relationship from reply byte 4;
a value below the strip count is treated as synchronized. The setter uses the
strip's declared `master` index or `0xFF` for unsynchronized. That setter was
inspected only and never sent.

`reload_amk_rgb_params()` nevertheless sends a synchronization getter for every
strip, regardless of whether that strip declares `master`. None of this
keyboard's seven strip definitions declares it.

Request payload format is `FD 3D 01 03 index`, padded to 32 bytes. hidapi receives
a leading `00` report selector, making its host-side argument 33 bytes. Example:

| Query, strip 0 | Request prefix | Reply prefix |
|---|---|---|
| Color, parameter 0 | `FD 3D 01 00 00` | `FD 3D AA 00 rr gg bb ...` |
| Speed, parameter 2 | `FD 3D 01 02 00` | `FD 3D AA 00 7F 00 ...` |
| Synchronization, parameter 3 | `FD 3D 01 03 00` | `FD 3D 55 03 00 00 ...` |

For strip 1 synchronization, the reply is `FD 3D 55 03 01 00 ...`; the same
pattern holds through index 6. All 126 synchronization requests across the four
captures return status byte `0x55`. Color and speed reads succeed around those
replies, as do subsequent VIA identity and AMK NKRO reads. Full packets are
preserved in each capture's `transactions.jsonl`.

The client checks byte 2 against `0xAA`, prints `Failed to reload rgb param: 3`,
and continues without assigning `sync`. A failure reply's bytes 3 and 4 retain
the request's parameter/index; they must not be interpreted as a successful
synchronization value. The failed packets are complete replies, not a timeout,
missing dependency, wrong endpoint or short-read symptom. Increasing the retry
count cannot repair this deterministic non-success status: `hid_send()` retries
transport failures, not status-byte rejection.

The combination of absent `master` declarations, a disabled sync UI and
consistent non-success replies supports **unsupported synchronization on this
firmware/configuration** as the diagnosis. The exact vendor meaning of `0x55`
is not established by an available firmware specification or matching firmware
source; it is proven here only to be a status other than the client's success
value. Do not claim it specifically means "unsupported command" as a documented
enum value.

A complete reload emits seven warnings, one per strip. Re-selection/hard refresh
can repeat the seven; the ordinary one-second discovery loop does not itself
reload every RGB parameter when the device set is unchanged.

## Other functionality and consistency

Two full reload captures each contain 388 reload transactions after the initial
147 diagnostic reads. Both complete with only the seven RGB sync warnings.
Every other AMK getter in the complete reload returns `0xAA`.

| Read path | Live result |
|---|---|
| Definition, keymap | Valid 8x16 matrix; 420 populated mappings across four layers; identical snapshots |
| Macros | 16 entries, advertised capacity 1,012 bytes; decoded macro data identical |
| QMK settings | 21 supported setting IDs, read successfully; identical snapshots |
| Tap dance, combos, key overrides | 32 entries of each, read successfully; identical snapshots |
| Alternate repeat keys | Count zero; not advertised as available |
| NKRO | `FD 0D AA 01 ...`; parsed enabled; stable |
| Polling/debounce | Poll-rate code 3; down/up debounce 5/5; stable (no undocumented physical units inferred) |
| RGB grid | One 4x16 grid, 64 per-LED entries; color/speed and mode read successfully |
| RGB strips | Seven strip-info entries, 61 per-LED entries; all color/speed reads succeed |
| Indicators | Six configuration entries, including standalone and shared LEDs; read successfully |
| Synchronization | Seven getter failures; unavailable in this keyboard's declared strip capabilities |
| Date/time, auxiliary display | Advertised; behavior not exercised |
| Actuation, rapid trigger, calibration, DKS | Not exercised; this is an MX device, not an advertised AMK magnetic/EC configuration |

The raw downloaded definitions are identical. The client mutates its in-memory
working definition with colors/settings during reload, so a later comparison of
that working object can differ. RGB color replies also vary during running
animations; stable strip/grid modes, speeds, enables and custom-mode codes match
across the captures. Neither observation proves a configuration write.

Evidence: `full-reload-3/summary.json`, `reload-stdout.txt`,
`snapshot-comparison.json`, and both complete captures' `replayed-state.json`.
All data structure comparisons used offline replay of captured replies.
No key presses, writes, uploads, calibration or firmware operations were tested;
read-path success is not a claim that every write path works.

## QSocketNotifier warning

Reproduced with a plain `QApplication([])` on native Wayland, without importing
Vial or fbs. It does not reproduce under `xcb` or `offscreen` in these checks.
The session has `QT_IM_MODULE=ibus`.

A GDB backtrace of a **device-free, disposable test process** with Qt warnings
made fatal shows this creation path:

```text
QApplication initialization / createEventDispatcher
  QWaylandIntegration::reconfigureInputContext
    QIBusPlatformInputContext constructor
      QFileSystemWatcher
        QInotifyFileSystemWatcherEngine::create
          QSocketNotifier constructor -> warning
```

Thus the warning is from the bundled Qt5 Wayland/IBus input-context startup path
before the event dispatcher is ready, not Vial's HID thread or its fbs signal
wakeup socket. Evidence: `qt/native-backtrace.txt` and `qt/wayland-qt.log`.
Qt's documented QSocketNotifier role is event-loop integration for file
descriptors: https://doc.qt.io/qt-6/qsocketnotifier.html (general API reference;
the runtime investigated here is Qt 5.15.14).

The ordinary GUI startup tests pass. A parent process delivering SIGINT 200 ms
after the event loop starts causes the actual fbs application context to return
130 at about 200 ms on Wayland and XWayland. Its wakeup integration works. A
plain Qt control without fbs waits until the 2.5-second fallback timer, confirming
that the fbs test was sensitive to working wakeup delivery. A diagnostic-only
`QT_IM_MODULE=compose` run suppresses the warning, further localizing it to IBus.

No impact on observed HID reads, rendering, timers or fbs signal wakeup was found.
It is not appropriate to prove that all IBus behavior is unaffected: the early
file watch may affect input-method address-file monitoring/reconnection, and
IME composition/reconnection was not tested. Do not suppress the warning or
force a different input method globally as a purported fix.

## Existing tests

Original fixtures do not model `FD 0D` GET_NKRO, which this fork calls
unconditionally in `reload_amk()`. The live keyboard returns a valid complete
`FD 0D AA 01 ...` reply. Protocol fixtures exhaust their expected transactions;
the virtual GUI keyboard instead raises "unknown command ... 0xFD".

An offline diagnostic plugin supplies only that observed reply to the existing
virtual devices. Running all tests with a synthetic `/dev` and no physical HID
nodes yields **23 passed, 3 failed**: all six original protocol failures are
resolved. The three remaining assertions require upstream English labels
(`Basic`, `Combos`, `Tap Dance`) instead of this client's bilingual labels.
Evidence: `offline-adapted.log` and `offline_amk_adapter.py`.

Temporary test copies additionally update those label expectations (and their
resource path after relocation); production source/tests remain unchanged.
This reaches **24 passed, 2 failed**: the remaining two failures occur inside
fixture mouse-position construction, where `QPoint` is given float coordinates.
Modern PyQt requires integers there. Only the temporary copies were changed to
cast those two mouse positions, matching the pattern already used elsewhere in
the fixtures. The targeted rerun is in `offline-adapted-coordinates.log`;
`offline-adapted-labels-final.log` preserves the intermediate result. Both
targeted tests pass (2 passed in 3.66 seconds), so all 26 tests are accounted for
by the 24-pass run plus the two passing reruns after fixture-only adaptations.
No production implementation was changed to obtain these results.
No write-operation tests were connected to real hardware. Virtual setter tests
run only in the sandbox with mock devices.

These fixture failures do not demonstrate live Linux/AMK incompatibility. They
also do not prove untested compatibility with every other Vial keyboard: this
fork unconditionally asks all devices for GET_NKRO and does not validate its
status before reading byte 3. That is a separate compatibility consideration
for non-AMK devices, not a failure seen on `4D58:0103`.

## Proposed changes — not implemented

1. For RGB sync, use the same declared-capability test as the UI: request sync
   only for strips declaring `master`. For declared-capable strips that return
   non-success, preserve an explicit unavailable state and disable the control;
   do not invent a sync value or enable writes. Retain current protocol formats.
   This removes unsupported queries for this keyboard and preserves queries for
   other keyboards that advertise synchronization. It is a client capability
   check, with no evidence that a Linux-specific protocol change is needed.
2. Improve failed-read diagnostics to include RGB type, parameter, strip index
   and status byte. The current message conceals that seven different indexes
   are failing. Avoid automatically retrying deterministic firmware rejection.
3. Update virtual fixtures for AMK GET_NKRO, bilingual labels and integer mouse
   coordinates required by the newer PyQt binding. This changes no
   firmware behavior. Add a regression covering a strip without `master` and a
   non-success response for an advertised-capable strip.
4. For the Qt warning, no Vial thread rewrite is justified. The smallest optional
   workaround is per-launch `QT_QPA_PLATFORM=xcb`, already supported by the
   AppImage, while retaining IBus. A native-Wayland fix belongs in the affected
   Qt input-context startup lifecycle and needs separate IME/reconnection tests.
   Changing to `compose` avoids IBus and should remain an explicit user choice,
   since it changes input-method support. No default was changed.

## Reproduction and limitations

From the repository, use a fresh output directory:

```sh
.venv-linux/bin/python util/native-linux/diagnose-readonly.py \
  --full-reload --output target/astro/diagnostics/new-capture
```

Run when no other client is using the Vial interface, to avoid another reader
consuming replies. The harness selects the exact VID/PID/usage/serial and refuses
an output directory already containing transactions. No root access is needed.
`diagnose-qt.py` is device-free and records Python stacks for Qt messages.

The authoritative hardware-document library was unavailable:
`python3 ~/.codex/skills/read-doc/scripts/search.py AMK` and the USB lookup both
reported missing `/home/alec/Documents/calibre-library/metadata.db`, lookup IDs
`0fa07704f02c` and `6cc4fedfcf13`. No vendor error-code table, errata or exact
connected-firmware implementation was established. A read-only examination of
public `yulei/amk` repository trees did not establish source identity for this
MY-2K firmware. Protocol names and expected layouts above are verified against
this client's source; responses and reliability are measured. Firmware-internal
causes and the precise `0x55` enum meaning remain unverified.

The existing AppImage is unchanged, SHA256:
`0fd2948652551f21e47cf35e36cf3fe544c523a82525bdfe0158df979bacc87f`.
Only diagnostic helpers/report and ignored capture/test artifacts were added.
