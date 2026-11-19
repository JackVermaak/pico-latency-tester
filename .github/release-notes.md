Ready-to-flash firmware and print files, no Arduino setup needed.

| File | What it is |
| --- | --- |
| `latency_tester_pico2w-*.uf2` | Firmware for the Raspberry Pi Pico 2 W / 2 WH, compiled by GitHub Actions from this tag (arduino-pico core, Adafruit TinyUSB stack for 1 ms polling). |
| `pico-latency-tester-case-*.zip` | Print-ready STLs (box, lid, OLED clamp, sensor cup) and the OpenSCAD source. Print the sensor cup in black. |
| `pico-latency-tester-pc-tools-*.zip` | `latency_log.py` (CSV logger), `analyze.py` (table and chart) and `flash_test.html` (browser test page). |

**Flashing:** hold BOOTSEL, plug the Pico into the PC, and drag the `.uf2` onto the `RP2350` drive. It reboots into the tester.

Wiring, assembly and usage: [README](https://github.com/JackVermaak/pico-latency-tester#readme).
