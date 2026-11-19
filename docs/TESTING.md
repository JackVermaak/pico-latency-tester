# Test protocol

How the published results were measured, so they can be repeated.

## Rules for every run

- **100 samples per run** (the firmware default). For close comparisons, do 3 runs per setup.
- **Alternate setups** (A, B, A, B, …) instead of doing all of A and then all of B, so drift
  (temperature, background tasks) affects both equally.
- **Change one thing at a time.** Everything else stays fixed: resolution, monitor brightness
  (100 %, which also avoids PWM flicker), sensor position, USB port, scene.
- **Same spot on the screen.** A monitor draws from top to bottom, so the sensor's height on the
  screen changes the result by up to one refresh period. Mark the cup's position with tape.
- **Close overlays** (Steam, Discord, GeForce) unless they are what's being tested.
- **Offline only.** The tester is an automated clicker: use it in local practice servers, never in
  online matches.
- Compare **medians**; report the 5th–95th percentile range and the sample count with them.

## Commands

Log a run (appends to `results.csv`):

```
python pc/latency_log.py COM9 --label "cs2 vsync off"
```

Summarise and chart a set of runs:

```
python pc/analyze.py --only "cs2 vsync off" "cs2 vsync on" --title "CS2: V-Sync" --out docs/results/vsync
```

This writes `vsync.md` (a Markdown table) and `vsync.png` (a chart).

## Tests

| # | Test | Setups (labels) | What it shows |
| --- | --- | --- | --- |
| 1 | Repeatability | `flash 240hz run1`, `run2`, `run3` | How consistent the tester itself is |
| 2 | Refresh rate | `flash 60hz`, `flash 144hz`, `flash 240hz` | Latency vs refresh rate |
| 3 | V-Sync | `cs2 vsync off`, `cs2 vsync on` | The cost of V-Sync |
| 4 | NVIDIA Reflex | `cs2 reflex off`, `cs2 reflex on`, `cs2 reflex boost` | What Reflex saves |
| 5 | Frame cap | `cs2 fps unlimited`, `cs2 fps 120`, `cs2 fps 60` | Latency vs frame rate |
| 6 | Macropad impact | `cs2 pad unplugged`, `cs2 pad plugged + app` | Whether the Pico Mixpad adds input lag |

**Browser tests (1, 2):** open `pc/flash_test.html`, press F for fullscreen, place the sensor in
the centre of the screen. Change the refresh rate in Windows Settings → Display → Advanced display.

**CS2 tests (3–6):** start a practice game on an empty map (no bots), then in the console:

```
sv_cheats 1; sv_infinite_ammo 1; mp_roundtime_defuse 60; mp_freezetime 0; bot_kick
```

Stand facing a dark wall, use `getpos` once and paste the printed `setpos` line before every run
so the view is identical. Put the sensor where the muzzle flash appears; check with a few manual
shots that the light level on the OLED jumps. Use a weapon that fires once per click (e.g. a
pistol or the AK-47; the tester holds each click for 40 ms).

The settings for tests 3–5 are in Settings → Video → Advanced Video: Wait for Vertical Sync,
NVIDIA Reflex Low Latency, and the frame-rate cap (`fps_max` in the console).

## Report each result with

The system it was measured on: GPU, CPU, monitor model and refresh rate, resolution,
graphics driver version, game version, and the date.
