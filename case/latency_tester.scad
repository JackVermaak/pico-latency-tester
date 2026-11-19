// Pico Latency Tester - printed parts
// OpenSCAD 2021.01 or newer.
//   openscad -D 'part="box"' -o box.stl latency_tester.scad
// Parts: "box", "lid", "oled_clamp", "sensor_cup", "assembly"
//
// The box holds a Pico 2 WH upside down (header pins up, for jumper plugs), with the OLED and the
// start button (one Cherry MX switch) in the lid. The light sensor sits in its own cup on the monitor,
// connected by three long jumper leads through the notch in the back wall.
// Tolerances are at the top: adjust them if holes print too tight or loose on your printer.

part = "assembly";

/* [Fit tolerances] */
switch_cutout  = 14.0;
pilot_hole     = 1.6;
clearance_hole = 2.4;

/* [Box] */
W = 68; D = 71; wall = 2.5; floor_t = 2.4; inner_h = 30; lid_t = 4.0; corner_r = 4;

/* [Layout] */
oled_c   = [-7, 19];    // OLED module centre (pins toward the back)
button_c = [23, 19];    // MX switch
notch_x  = -15;         // sensor cable notch in the back wall

/* [OLED module] */
oled_w = 27.8; oled_h = 27.8; oled_t = 4.1;
oled_window = [25, 14]; oled_window_dy = -1.5;

/* [Pico 2 WH, upside down] */
pico_len = 51; pico_wid = 21;
pico_holes = [[-23.5, -5.7], [23.5, -5.7], [-23.5, 5.7], [23.5, 5.7]];
pico_post_h = 7;
usb_side = -1;          // -1 = USB cable out of the left wall

/* [Sensor: Adafruit ALS-PT19 breakout] */
sensor_w = 7.8; sensor_l = 10.6; sensor_t = 2.4;

$fn = 64;
eps = 0.01;
inner_w = W - 2 * wall;
pico_c = [usb_side * (inner_w / 2 - 0.6 - pico_len / 2), D - wall - 1 - pico_wid / 2];
bosses = [[-(inner_w / 2 - 3.2), wall + 3.2], [inner_w / 2 - 3.2, wall + 3.2],
          [inner_w / 2 - 3.2, D - wall - 3.2], [-(inner_w / 2 - 3.2), 40]];

module rounded_rect(w, d, h, r) {
    translate([-w / 2 + r, r, 0]) minkowski() { cube([w - 2 * r, d - 2 * r, h / 2]); cylinder(r = r, h = h / 2); }
}

module oled_window_cut() {
    translate([-oled_window[0] / 2, -oled_window[1] / 2 + oled_window_dy, -eps]) cube([oled_window[0], oled_window[1], lid_t + 2 * eps]);
    translate([0, oled_window_dy, lid_t - 1.2])
        linear_extrude(height = 1.2 + eps, scale = [(oled_window[0] + 2.4) / oled_window[0], (oled_window[1] + 2.4) / oled_window[1]])
            square(oled_window, center = true);
}

module oled_pocket_walls() {
    difference() {
        translate([-oled_w / 2 - 1.8, -oled_h / 2 - 1.8, -oled_t]) cube([oled_w + 3.6, oled_h + 3.6, oled_t]);
        translate([-oled_w / 2 - 0.3, -oled_h / 2 - 0.3, -oled_t - eps]) cube([oled_w + 0.6, oled_h + 0.6, oled_t + 2 * eps]);
        translate([-6, oled_h / 2 - 1, -oled_t - eps]) cube([12, 4, oled_t + 2 * eps]);
    }
    for (sx = [-1, 1]) translate([sx * (oled_w / 2 + 4.8), -5, -oled_t]) difference() {
        cylinder(d = 6, h = oled_t);
        translate([0, 0, -eps]) cylinder(d = pilot_hole, h = oled_t + 2 * eps);
    }
}

module lid() {
    difference() {
        union() {
            rounded_rect(W, D, lid_t, corner_r);
            difference() {
                translate([0, wall + 0.3, -2]) rounded_rect(inner_w - 0.6, D - 2 * wall - 0.6, 2, 1.2);
                translate([0, wall + 1.5, -2 - eps]) rounded_rect(inner_w - 3.0, D - 2 * wall - 3.0, 2 + 2 * eps, 0.5);
            }
        }
        // start button: MX cutout with a 1.5 mm skin for the clips
        translate([button_c[0] - switch_cutout / 2, button_c[1] - switch_cutout / 2, -2 - eps]) cube([switch_cutout, switch_cutout, lid_t + 2 + 2 * eps]);
        translate([button_c[0] - 7.8, button_c[1] - 7.8, -2 - eps]) cube([15.6, 15.6, 2 + lid_t - 1.5 + eps]);
        translate([oled_c[0], oled_c[1], 0]) oled_window_cut();
        translate([oled_c[0] - oled_w / 2 - 0.3, oled_c[1] - oled_h / 2 - 0.3, -eps]) cube([oled_w + 0.6, oled_h + 0.6, 0.6]);
        for (b = bosses) translate([b[0], b[1], -2 - eps]) {
            cylinder(d = clearance_hole, h = lid_t + 2 + 2 * eps);
            translate([0, 0, 2 + lid_t - 1.6]) cylinder(d = 4.6, h = 1.6 + 2 * eps);
            cylinder(r = 4.3, h = 2 + eps);
        }
        // keep the lip away from the Pico's jumper plugs and the cable notch
        translate([pico_c[0] - pico_len / 2 - 4, pico_c[1] - pico_wid / 2 - 4, -2 - eps]) cube([pico_len + 8, pico_wid + 8, 2 + eps]);
    }
    translate([oled_c[0], oled_c[1], 0]) oled_pocket_walls();
}

module box() {
    difference() {
        union() {
            difference() {
                rounded_rect(W, D, floor_t + inner_h, corner_r);
                translate([0, wall, floor_t]) rounded_rect(inner_w, D - 2 * wall, inner_h + eps, max(corner_r - wall, 0.5));
            }
            for (b = bosses) translate([b[0], b[1], 0]) cylinder(d = 7, h = floor_t + inner_h);
            for (h = pico_holes) translate([pico_c[0] + h[0], pico_c[1] + h[1], 0]) {
                if (h[0] * usb_side > 0) {
                    cylinder(d = 3.0, h = floor_t + pico_post_h);
                    cylinder(d = 1.8, h = floor_t + pico_post_h + 1.2, $fn = 24);
                } else cylinder(d = 5, h = floor_t + pico_post_h);
            }
        }
        for (b = bosses) translate([b[0], b[1], floor_t + inner_h - 12]) cylinder(d = pilot_hole, h = 12 + eps);
        for (h = pico_holes) if (h[0] * usb_side < 0)
            translate([pico_c[0] + h[0], pico_c[1] + h[1], floor_t + 1]) cylinder(d = pilot_hole, h = pico_post_h + eps);
        translate([usb_side * (W / 2 - wall / 2), pico_c[1], floor_t + pico_post_h - 1.5]) cube([wall + 2, 12, 10], center = true);
        // sensor cable notch at the top of the back wall
        translate([notch_x - 4, D - wall - eps - 1, floor_t + inner_h - 5]) cube([8, wall + 2, 5 + eps]);
        for (sx = [-1, 1], y = [9, D - 9]) translate([sx * (W / 2 - 9), y, -eps]) cylinder(d = 12.6, h = 0.6);
    }
}

module oled_clamp() {
    difference() {
        hull() for (sx = [-1, 1]) translate([sx * (oled_w / 2 + 4.8), 0, 0]) cylinder(d = 6, h = 2.5);
        for (sx = [-1, 1]) translate([sx * (oled_w / 2 + 4.8), 0, -eps]) cylinder(d = clearance_hole, h = 2.5 + 2 * eps);
    }
}

module sensor_cup() {
    // holds the sensor board face-down against the monitor and blocks room light;
    // loop an elastic band or a strip of tape through the two side slots
    bw = sensor_w + 0.4; bl = sensor_l + 0.4;
    difference() {
        union() {
            cylinder(d = 28, h = 8);
            for (sy = [-1, 1]) translate([0, sy * 15, 4]) cube([10, 6, 8], center = true);
        }
        translate([-bw / 2, -bl / 2, 1.2]) cube([bw, bl, 10]);                 // board pocket, open at the back for the wires
        translate([-1.5, -bl / 2 + 2, -eps]) cube([3, bl - 4, 1.2 + 2 * eps]);  // sensor window toward the screen
        for (sy = [-1, 1]) translate([0, sy * 15, 4]) cube([12, 2.5, 4], center = true);
    }
}

module assembly() {
    color("lightgrey") box();
    color("dimgrey") translate([0, 0, floor_t + inner_h]) lid();
}

module flip() { translate([0, 0, lid_t]) rotate([180, 0, 0]) children(); }

if (part == "box") box();
else if (part == "lid") flip() lid();
else if (part == "oled_clamp") oled_clamp();
else if (part == "sensor_cup") sensor_cup();
else if (part == "none") { }
else assembly();
