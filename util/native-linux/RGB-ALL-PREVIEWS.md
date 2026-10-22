# All RGB Strips animation previews

The earlier selection fix addressed only initial polling. The page still read
only the strip selected for configuration while drawing every strip. The shared
`amk_rgb_data` buffer therefore held fresh colors for one range and old colors
for other ranges. All preview widgets were repainted: a baseline Qt paint-event
probe confirmed a repaint while only the selected row's colors changed. Entering
the page previously fetched the full feature range, explaining tab-switch refreshes.

Grid uses the same getter and cache model but this keyboard has one 64-LED grid,
so its selected-group strategy already refreshes that whole preview. Strips has
seven groups totaling 61 LEDs. Group addressing remains feature base + strip
start + LED offset; selection controls editing, not the new preview read range.

## Supported read path and implementation

The existing activation path already read the declared whole-strip feature range.
A bounded hardware benchmark verified all replies, including chunks crossing
strip boundaries, using GET_RGB_DATA only. No arbitrary range merging or new
firmware command is assumed. The keyboard's declared range is global 64–124;
visible strip LEDs address the correct slices within that range.

The only application implementation change is in `amk/rgb_strip.py`:

- The existing single 50 ms timer sweeps the complete declared strip feature
  independently of the list selection.
- It reuses `reload_rgb_leds()` with one existing protocol packet per batch:
  at most nine LEDs for V1, eight for V2. Contiguous groups share packet capacity.
- A cooperative 40 ms callback budget defers the rest of an unusually large or
  slow sweep to the next tick. The cursor continues forward even when selection
  changes, preventing starvation of later strips. It wraps after one sweep.
- Activation uses the same bounded sweep, rather than a separate unbounded read.
  Newly connected LEDs not yet sampled display black until their batch arrives.
- Each callback redraws all preview colors from the shared cache and requests a
  widget update. Tab departure/disconnect stops the timer as before; activation
  and device replacement reset the sweep cursor appropriately.

RGB Grid, protocol code, settings commands, localization and existing strip
controls are unchanged. The signal-blocked settings refresh and synchronization
capability gate from the previous fix remain intact. No per-strip timers, new
worker, additional persistent polling loop or external-settings polling was added.

## Performance evidence and limits

Pre-change, getter-only benchmark on the connected V1 keyboard, 12 cycles/policy:

| Policy | HID reports/cycle | Median | Maximum |
|---|---:|---:|---:|
| Selected 19-LED strip | 3 | 14.46 ms | 25.27 ms |
| Read seven strips separately | 11 | 58.33 ms | 62.55 ms |
| Read declared contiguous 61-LED feature | 7 | 32.85 ms | 43.53 ms |

This supports batching the declared range instead of issuing one read per strip.
It costs seven reports per complete physical sweep, normally about 140 reports/s
at 20 Hz. The original 64-LED Grid read costs eight reports per sweep. A sweep
can span callbacks when the budget is reached; it is not an atomic firmware frame.

The budget is checked between synchronous HID exchanges. It cannot interrupt one
exchange or its existing timeout; it is a cooperative bound plus one exchange,
not a hard real-time guarantee. Protocol timeout/retry behavior is unchanged.
This avoids introducing invasive cross-thread transport ownership changes.

The wire strip-count field can represent 255 groups; a synthetic 255 one-LED-strip
V2 fixture requires 32 reports per sweep. Fast fake links complete in one callback;
a simulated 21 ms/report link completes in 16 callbacks, with two reports/42 ms
per callback, instead of blocking the UI for a 672 ms sweep. At that link speed,
20 complete frames/s is impossible with this packet format; the cursor provides
continuous, fair progress and responsive controls at a lower preview frame rate.
This fixture exercises the count-field boundary, not a claim that every physical
firmware supports 255 groups. Large LED totals similarly trade frame rate for UI
responsiveness; selection never freezes other previews.

## Tests and reproduction

The suite includes seven new cases in `test_rgb_strip_all_previews.py` and updates
the previous selected-only expectations in `test_rgb_strip_live.py`. It verifies
all pixel colors across changing independent frames, actual Qt paint events,
nonzero base/strip offsets, V1/V2 packet sizes, selection independence, timer
lifecycle, disconnect/reconnect, empty definitions, counts 1/7/61/255, progressive
initial data and slow-link cursor fairness. All fake transports reject SETs.

```sh
./util/native-linux/test.sh
./util/native-linux/build.sh
./util/native-linux/test-appimage.sh
./util/native-linux/test-hardware-readonly.sh
```

Close other Raw HID clients before live testing. Bounded benchmark, source/frozen
GUI instrumentation and captures are retained under `target/astro/rgb-all-previews/`.
Every hardware output is getter-allowlisted. No physical RGB values, effects,
calibration, keyboard settings, firmware, macros or keymaps are written. Device-free
suite/smoke checks use synthetic device nodes and isolated preferences. Nothing is
installed into GNOME.

Current artifact checksum, live timing/repaint results and screenshots:
[RGB-ALL-PREVIEWS-VALIDATION.md](RGB-ALL-PREVIEWS-VALIDATION.md).
