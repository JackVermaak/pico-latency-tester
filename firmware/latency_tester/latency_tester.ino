// Pico Latency Tester - click-to-photon latency measurement
// Board: Raspberry Pi Pico 2 W (also works on Pico / Pico 2 / Pico W)
// Arduino core: "Raspberry Pi Pico/RP2040/RP2350" by Earle Philhower
// Tools > USB Stack: "Adafruit TinyUSB"   <-- required (sets the 1 ms mouse polling rate)
// Libraries: Adafruit SSD1306 + Adafruit GFX (Library Manager)
//
// How it works: the Pico is a USB mouse. For each sample it records the screen brightness,
// sends a left click and starts a timer, then watches the light sensor until the brightness
// changes. The time in between is the full input-to-screen latency: USB, OS, game/app,
// GPU and the monitor itself.
//
// Wiring (see the README):
//   ALS-PT19  + -> GP27 (pin 32, driven high)   - -> AGND (pin 33)   OUT -> GP26 (pin 31, ADC0)
//   Button    GP15 -> switch -> GND
//   OLED      VCC -> 3V3  GND -> GND  SDA -> GP4  SCL -> GP5
//
// Use: press the button (or send "s" over serial) to start a run; press again (or "x") to stop.
// Each sample is printed over serial as "sample,<n>,<latency_us>", the run ends with a summary line.

// The code is in tester.cpp (the Arduino IDE shows it as a second tab).
