// tester.cpp - all firmware code (see latency_tester.ino for setup notes)
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ---------------------------------------------------------------- settings
const uint8_t  SENSOR_PIN     = 26;       // ADC0, pin 31
const uint8_t  SENSOR_POWER   = 27;       // pin 32: powers the sensor (it needs < 1 mA), frees the 3V3 pin for the OLED
const uint8_t  BUTTON_PIN     = 15;
const uint8_t  OLED_ADDRESS   = 0x3C;     // some modules use 0x3D
const uint16_t RUNS           = 100;      // samples per run
const uint8_t  POLL_MS        = 1;        // USB polling interval (1 ms = 1000 Hz, like a gaming mouse)
const uint16_t MIN_DELTA      = 60;       // minimum brightness change that counts (ADC counts of 4095)
const uint8_t  NOISE_FACTOR   = 6;        // trigger at NOISE_FACTOR x the measured noise, if that's larger
const uint32_t TIMEOUT_US     = 500000;   // no change within 500 ms = miss
const uint16_t HOLD_MS        = 40;       // how long the click is held down
const uint16_t GAP_MIN_MS     = 350;      // random pause between samples, so clicks don't
const uint16_t GAP_MAX_MS     = 750;      //   line up with the monitor's refresh
const uint32_t SETTLE_US      = 1500000;  // max wait for the screen to return to its resting state

// ---------------------------------------------------------------- USB mouse
uint8_t const desc_hid_report[] = { TUD_HID_REPORT_DESC_MOUSE() };
Adafruit_USBD_HID usb_hid;

Adafruit_SSD1306 oled(128, 64, &Wire, -1);
bool has_oled = false;

uint32_t samples[RUNS];
uint16_t count = 0, misses = 0;
bool running = false;

// ---------------------------------------------------------------- helpers
struct Baseline { float mean; uint16_t noise; };

Baseline measure_baseline() {
  // 128 reads over ~6 ms: average level and the largest deviation (noise, monitor flicker)
  const int n = 128;
  uint16_t v[n];
  uint32_t sum = 0;
  for (int i = 0; i < n; i++) { v[i] = analogRead(SENSOR_PIN); sum += v[i]; delayMicroseconds(45); }
  float mean = sum / float(n);
  uint16_t noise = 0;
  for (int i = 0; i < n; i++) { uint16_t d = abs(int(v[i]) - int(mean)); if (d > noise) noise = d; }
  return { mean, noise };
}

void show(const char *l1, const char *l2 = "", const char *l3 = "", const char *l4 = "") {
  if (!has_oled) return;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1);
  oled.setCursor(0, 2);  oled.print(l1);   // top line sits in the yellow strip on yellow/blue screens
  oled.setTextSize(2);
  oled.setCursor(0, 18); oled.print(l2);
  oled.setTextSize(1);
  oled.setCursor(0, 40); oled.print(l3);
  oled.setCursor(0, 52); oled.print(l4);
  oled.display();
}

bool button_pressed() {
  static bool last = false;
  static uint32_t last_change = 0;
  bool now = digitalRead(BUTTON_PIN) == LOW;
  if (now != last && millis() - last_change > 30) {
    last = now; last_change = millis();
    return now;            // report the press edge only
  }
  return false;
}

bool stop_requested() {
  if (button_pressed()) return true;
  while (Serial.available()) { char c = Serial.read(); if (c == 'x' || c == 'X') return true; }
  return false;
}

void wait_ms_or_stop(uint32_t ms, bool &stop) {
  uint32_t t = millis();
  while (millis() - t < ms) { if (stop_requested()) { stop = true; return; } }
}

int cmp_u32(const void *a, const void *b) {
  uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
  return (x > y) - (x < y);
}

void summary() {
  char l2[24], l3[32], l4[32];
  if (count == 0) {
    Serial.printf("summary,0,,,,,,%u\n", misses);
    snprintf(l3, sizeof l3, "%u misses", misses);
    show("No samples", "--", l3, "Check sensor/threshold");
    return;
  }
  uint32_t sorted[RUNS];
  memcpy(sorted, samples, count * sizeof(uint32_t));
  qsort(sorted, count, sizeof(uint32_t), cmp_u32);
  double sum = 0, sq = 0;
  for (uint16_t i = 0; i < count; i++) sum += sorted[i];
  double mean = sum / count;
  for (uint16_t i = 0; i < count; i++) sq += (sorted[i] - mean) * (sorted[i] - mean);
  double sd = count > 1 ? sqrt(sq / (count - 1)) : 0;
  double median = (count % 2) ? sorted[count / 2] : (sorted[count / 2 - 1] + sorted[count / 2]) / 2.0;
  Serial.printf("summary,%u,%.2f,%.2f,%.2f,%.2f,%.2f,%u\n", count, mean / 1000, median / 1000,
                sorted[0] / 1000.0, sorted[count - 1] / 1000.0, sd / 1000, misses);
  Serial.println("# columns: summary,n,mean_ms,median_ms,min_ms,max_ms,stdev_ms,misses");
  snprintf(l2, sizeof l2, "%.1f ms", mean / 1000);
  snprintf(l3, sizeof l3, "med %.1f  sd %.1f", median / 1000, sd / 1000);
  snprintf(l4, sizeof l4, "%.1f-%.1f ms n=%u", sorted[0] / 1000.0, sorted[count - 1] / 1000.0, count);
  show("Average latency", l2, l3, l4);
}

// ---------------------------------------------------------------- one run
void run() {
  running = true;
  count = 0; misses = 0;
  bool stop = false;
  Serial.println("# run start");
  show("Running...", "0/" , "Keep the mouse still", "Button = stop");

  while (count < RUNS && !stop) {
    if (!TinyUSBDevice.mounted() || !usb_hid.ready()) { delay(5); continue; }

    Baseline b = measure_baseline();
    uint16_t delta = max<uint16_t>(MIN_DELTA, b.noise * NOISE_FACTOR);

    // click and time the screen's response
    usb_hid.mouseButtonPress(0, MOUSE_BUTTON_LEFT);
    uint32_t t0 = micros();
    uint32_t latency = 0;
    while (true) {
      uint32_t dt = micros() - t0;
      if (abs(int(analogRead(SENSOR_PIN)) - int(b.mean)) > delta) { latency = dt; break; }
      if (dt > TIMEOUT_US) break;
    }
    delay(HOLD_MS);
    usb_hid.mouseButtonRelease(0);

    if (latency) {
      samples[count++] = latency;
      Serial.printf("sample,%u,%lu\n", count, (unsigned long)latency);
      char l2[16], l3[24];
      snprintf(l2, sizeof l2, "%u/%u", count, RUNS);
      snprintf(l3, sizeof l3, "last %.1f ms", latency / 1000.0);
      show("Running...", l2, l3, "Button = stop");
    } else {
      misses++;
      Serial.printf("miss,%u\n", misses);
      if (misses > 10 && count == 0) { Serial.println("# too many misses, stopping"); break; }
    }

    // let the screen go back to its resting state, then a random pause
    uint32_t ts = micros();
    while (micros() - ts < SETTLE_US && abs(int(analogRead(SENSOR_PIN)) - int(b.mean)) > delta / 2) {}
    wait_ms_or_stop(random(GAP_MIN_MS, GAP_MAX_MS), stop);
  }
  summary();
  running = false;
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  if (!TinyUSBDevice.isInitialized()) TinyUSBDevice.begin(0);
  Serial.begin(115200);

  usb_hid.setBootProtocol(HID_ITF_PROTOCOL_MOUSE);
  usb_hid.setPollInterval(POLL_MS);
  usb_hid.setReportDescriptor(desc_hid_report, sizeof(desc_hid_report));
  usb_hid.setStringDescriptor("Pico Latency Tester");
  usb_hid.begin();
  if (TinyUSBDevice.mounted()) { TinyUSBDevice.detach(); delay(10); TinyUSBDevice.attach(); }

  pinMode(SENSOR_POWER, OUTPUT);
  digitalWrite(SENSOR_POWER, HIGH);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  delay(20);   // let the sensor output settle
  analogReadResolution(12);
  randomSeed(analogRead(SENSOR_PIN) ^ micros());

  Wire.setSDA(4); Wire.setSCL(5);
  Wire.begin();
  Wire.setClock(400000);
  has_oled = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS);
  show("Latency tester", "Ready", "Sensor on screen,", "press button to start");
}

void loop() {
  if (button_pressed()) run();
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 's' || c == 'S') run();
    if (c == 'l' || c == 'L') {          // live sensor reading, handy for placing the sensor
      Baseline b = measure_baseline();
      Serial.printf("level,%.0f,noise,%u\n", b.mean, b.noise);
    }
  }
  // idle screen shows the live sensor level so you can check placement
  static uint32_t last = 0;
  if (!running && millis() - last > 500) {
    last = millis();
    Baseline b = measure_baseline();
    char l3[24];
    snprintf(l3, sizeof l3, "light %4.0f  noise %u", b.mean, b.noise);
    show("Latency tester", "Ready", l3, "press button to start");
  }
}
