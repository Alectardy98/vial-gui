> Investigation before implementation. The implemented fix is documented in [RGB-STRIP-FIX.md](RGB-STRIP-FIX.md).

# RGB Grid versus RGB Strips real-time updates

Investigation only, 2026-10-22. Application code and AppImage are unchanged.
No physical keyboard requests, settings writes, firmware operations or new HID
polling were performed. Targeted probes ran with synthetic `/dev`, isolated
preferences and fake transports; existing device captures were inspected offline.

## Finding

There is a confirmed client-side initialization difference. RGB Grid explicitly
selects row 0 and sets `self.grid = 0` in `reset_keyboard_widget()`
(`amk/rgb_grid.py:265`). RGB Strips populates its list but never selects a row
(`amk/rgb_strip.py:226`), leaving the constructor's `self.strip = -1`.

Both editors start a 50 ms QTimer on activation. Their pollers only read the
selected group. With `strip == -1`, no group matches, so the strip timer repaints
old colors without requesting fresh ones. Grid immediately has a valid selection
and therefore requests fresh colors on every tick. This explains a static strip
preview before explicit selection; it is not evidence that Strips lacks a timer
or requires a different polling architecture.

Explicitly selecting a strip enables its existing live-color read path. Clicking
a rendered LED alone does not assign `self.strip`: `on_key_clicked()` reads the
clicked LED's cached controls, whereas the strip list changes the polling target.
Changing an effect or brightness can also implicitly set `self.strip = 0` without
selecting its list row, making behavior appear inconsistent between interactions.

On tab reentry, clearing the strip list can leave an earlier internal strip index
behind while the visible list has no selection. The probe reproduced internal
strip 1 with visible row -1. This is a second manifestation of the same selection
consistency problem.

If the reported failure persists **after explicitly selecting a strip**, this
initialization defect does not fully explain that case. Runtime getter responses,
current selection and timer state would then need a separate bounded read-only
trace. No claim of successful live strip replies is made from the mock probes.

## Implementation comparison

| Path | RGB Grid | RGB Strips |
|---|---|---|
| Initial selection | Selects first grid | No strip selected |
| Enter tab | One full-feature color read, reset UI, start 50 ms timer | Same sequence for strip range |
| Periodic read | Selected grid range | Selected strip range; no read when index -1 |
| Drawing | `amk_rgb_data` RGB colors, plus cached custom LED flags | Same model |
| Leave tab | Stops timer | Stops timer |
| User effect change | `apply_rgb_grid_mode` | `apply_rgb_strip_mode` |
| User custom LED change | `apply_rgb_grid_led` | `apply_rgb_strip_led` |
| Color/speed/brightness | Shared parameter setter, grid type 3 | Shared parameter setter, strip type 1 |
| External effect/config refresh | Not part of color timer | Not part of color timer |

MainWindow's `on_tab_changed()` deactivates the old editor and activates the new
one (`main_window.py:479`). These are GUI-thread Qt timers using synchronous
protocol calls, not USB push notifications or background RGB subscriptions.
The 50 ms interval is nominal, not a guaranteed hard real-time rate; transport
latency/timeouts and the Qt event loop can delay a tick. The discovery worker's
one-second device scan does not refresh RGB state on an unchanged keyboard.

Both editors wire list selection, checkboxes and slider signals to equivalent
handlers. Both set slider tracking to false: dragging does not transmit every
intermediate value; release does. Both use QColorDialog's `finished` signal and
`selectedColor()`, so color changes are submitted after confirming the dialog,
not continuously while moving the picker. Custom LED controls require Custom
mode and selected LEDs in the selected strip/grid. Most strip control handlers
return immediately with `strip == -1`; the grid's initial selection avoids that
state during ordinary use.

## Protocol and cache distinctions

The following are this fork's command definitions/decoders, not an assumption
that all strip/grid firmware operations are interchangeable:

| Operation | Strip command | Grid command |
|---|---|---|
| Read group information | `FD 1C index` | `FD 42 index` |
| Write effect mode | `FD 20 index mode` | `FD 44 index mode` |
| Read custom LED configuration | `FD 1D ...` | `FD 45 ...` |
| Write custom LED configuration | `FD 1E ...` | `FD 46 ...` |
| Read parameter | `FD 3D 01 param index` | `FD 3D 03 param index` |
| Write parameter | `FD 3E 01 param index payload` | `FD 3E 03 param index payload` |
| Read rendered colors | Shared `FD 3C` using global LED indices | Same getter, different ranges |

`reload_rgb_leds()` (`amk/protocol.py:1335`) uses `GET_RGB_DATA`, updates
`amk_rgb_data`, and checks status AA. V1 requests contain an 8-bit start index
and count, with at most nine RGB triples per response; its response count is at
byte 4 and RGB data begins at byte 5. V2 uses a little-endian 16-bit start index,
at most eight triples, count at byte 5 and RGB data at byte 6. The protocol-v2
flag already selects the proper format. The color getter contains no strip/grid
type byte: it reads the shared RGB address space. Group offsets still matter:
feature base + group start + LED offset.

The stored keyboard definition has a 64-LED grid beginning at global 0 and
seven strips totaling 61 LEDs beginning at global 64. For example, the first
strip starts at relative 2 and contains 19 LEDs, so its selected live read should
cover global 66–84. This is the existing addressing code, not a proposed new
command. Existing captures confirm strip/grid information and parameter getters
returned AA, but the 500-exchange diagnostic capture does not contain `FD 3C`
rendered-frame requests; it cannot establish live-color support by itself.

The timer does **not** reload group modes, parameter values or custom LED
configuration. Those were loaded at keyboard initialization. `RgbLed` carries
HSV and custom flags/speed; `RgbColor` in `amk_rgb_data` carries the current RGB
preview. External animation/color changes can appear through the frame getter;
external effect, speed or custom-flag changes can leave both editors' controls
stale. Even the selected LED's checkbox/slider values are copied from cached
`RgbLed` objects. Setters update some caches optimistically and do not provide a
universal confirmation/readback mechanism. A repaint alone is not proof that a
physical change succeeded.

Shared error caveat: `reload_rgb_leds()` catches transport exceptions internally,
prints and breaks, and skips updating colors on non-AA status. An outer editor
poller therefore does not necessarily stop on every transport failure. A stopped
timer can also result from exceptions that do reach the outer handlers. These
shared limitations do not explain the confirmed initial selection asymmetry and
should not be folded into its minimal fix without further evidence.

## Reproduced results

Evidence: `target/astro/rgb-realtime-investigation/probe.py`, `probe.log` and
`probe-results.json`. This temporary diagnostic does not alter application code.
It instantiates the actual editors and uses actual Qt list/slider signals with
fake keyboard state. Fake mode setters use the original protocol method's
same-mode check. Physical HID/USB/input nodes are inaccessible.

| Probe | Strip | Grid |
|---|---|---|
| Internal selection after activation | -1 | 0 |
| First timer tick, fixture base 64 / first group count 3 | No read | Read `(64, 3)` |
| After explicit first-row selection | Read `(64, 3)` | Read `(64, 3)` |
| After second-row selection | Read `(67, 2)` | Read `(67, 2)` |
| Deactivation | Timer stopped | Timer stopped |
| Initialization/selection wire setters | 0 | 0 |
| Slider drag then release | One mocked parameter call on release | Same timing, grid type byte |

A second probe exercised the actual shared decoder with fake AA firmware replies
for the real first-strip range `(66, 19)`:

- V1 requests: `fd3c4209`, `fd3c4b09`, `fd3c5401`.
- V2 requests: `fd3c420008`, `fd3c4a0008`, `fd3c520003`.
- Both decoded and updated all 19 addressed RGB entries correctly.

These establish client request/selection/decoding behavior. They do not test
physical setter acceptance, animation rendering or real firmware V2 support.

## Smallest safe fix to implement later

1. After populating both strip/effect lists, explicitly synchronize the visible
   strip selection with a valid internal index. Restore the previous index when
   valid, otherwise select the first available strip; handle an empty definition
   without indexing it. Keep selection valid across tab reentry and reconnect.
2. Synchronize its effect/control display with signals blocked during programmatic
   changes, so initialization and selection cannot issue configuration writes.
   Retain the existing synchronization/master capability gate.
3. Reuse the current timer, `reload_rgb_leds()` and strip-relative addressing.
   No faster interval, new worker, protocol changes or Grid changes are needed.

This makes the **selected strip's color preview** as responsive as Grid. It does
not make every strip animate concurrently: both pollers intentionally read one
selected group while drawing all groups. Other groups retain their last sampled
colors. Polling all seven strips would increase traffic and is a separate product
choice, not required to fix the missing selection. For V1, reading the first
19-LED strip costs three reports per tick, whereas all 61 strip LEDs cost seven.
Keep the existing selected-group strategy unless whole-layout animation is desired.

Full automatic synchronization of external settings is also a separate change.
There is no proven external-settings polling mechanism in Grid to copy. If that
is needed, start with capability-aware readback on explicit selection/activation,
not parameter polling every 50 ms. All programmatic control updates would need
signal blocking. Do not reintroduce unsupported synchronization parameter reads.

## Regression tests for the proposed improvement

- First activation selects a visible valid strip and the first timer tick reads
  exactly that group's range, using a fake getter transport.
- Selecting another strip switches the range; tab reentry preserves a consistent
  visible/internal selection; an invalid saved index falls back safely after
  reconnect; an empty strip collection does not read or index any strip.
- Successive fake frame responses change displayed strip colors without a manual
  Refresh. Nonselected groups remain untouched under the selected-only policy.
- Verify V1/V2 packet batching and global index offsets, timer start/stop, and
  invalid-device handling. Assert there are no duplicate polling timers.
- Initialization, selection, reconnect and readback send **zero SET commands**,
  including when brightness/custom-color/synchronization values differ from the
  widgets' defaults. Preserve the no-master synchronization regressions.
- Mock-only tests confirm existing effect/LED/parameter handlers keep their strip
  command formats and release/confirmation timing. Never run setter tests against
  the physical keyboard.
- Leave Grid unchanged; run the complete automated suite and Wayland/XWayland
  smoke checks after a future implementation.

No fix, rebuild, new application regression test or additional live polling has
been implemented as part of this investigation.
