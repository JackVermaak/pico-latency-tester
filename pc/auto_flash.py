"""Automated flash test for Windows: no browser, no clicking around.

Opens a full-screen black window on the main monitor, puts the mouse cursor in the middle of
it, and starts a run on the tester. The window turns white on mouse-down and black on mouse-up,
so the tester measures the OS + display path. Can also switch the main monitor's refresh rate
for the run and put it back afterwards (temporary: a restart always restores your settings).

Usage (from the project folder):
    py pc/auto_flash.py --list-hz
    py pc/auto_flash.py COM5 --label "flash 240hz run1"
    py pc/auto_flash.py COM5 --label "flash 240hz" --runs 3
    py pc/auto_flash.py COM5 --hz 60 --label auto        # label becomes "flash 60hz"

Samples are appended to docs/results/raw.csv (change with --out), in the same format as
latency_log.py, so pc/analyze.py reads them.
"""

import argparse
import csv
import ctypes
import statistics
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import serial

# ---------------------------------------------------------------------------
# Refresh rate (Windows display settings API)
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    from ctypes import wintypes

    class DEVMODEW(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
            ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD), ("dmDriverExtra", wintypes.WORD),
            ("dmFields", wintypes.DWORD), ("dmPositionX", wintypes.LONG), ("dmPositionY", wintypes.LONG),
            ("dmDisplayOrientation", wintypes.DWORD), ("dmDisplayFixedOutput", wintypes.DWORD),
            ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
            ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short), ("dmFormName", wintypes.WCHAR * 32),
            ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD), ("dmPelsWidth", wintypes.DWORD),
            ("dmPelsHeight", wintypes.DWORD), ("dmDisplayFlags", wintypes.DWORD),
            ("dmDisplayFrequency", wintypes.DWORD), ("dmICMMethod", wintypes.DWORD),
            ("dmICMIntent", wintypes.DWORD), ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
            ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
            ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD),
        ]

    ENUM_CURRENT_SETTINGS = 0xFFFFFFFF
    DM_DISPLAYFREQUENCY = 0x00400000
    user32 = ctypes.windll.user32
    user32.EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODEW)]
    user32.ChangeDisplaySettingsW.argtypes = [ctypes.POINTER(DEVMODEW), wintypes.DWORD]


def _mode(index):
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    return dm if user32.EnumDisplaySettingsW(None, index, ctypes.byref(dm)) else None


def current_mode():
    return _mode(ENUM_CURRENT_SETTINGS)


def available_hz():
    """Refresh rates the main monitor offers at its current resolution."""
    cur = current_mode()
    rates, i = set(), 0
    while True:
        dm = _mode(i)
        if dm is None:
            break
        if (dm.dmPelsWidth, dm.dmPelsHeight) == (cur.dmPelsWidth, cur.dmPelsHeight) and dm.dmDisplayFrequency > 1:
            rates.add(dm.dmDisplayFrequency)
        i += 1
    return sorted(rates)


def nearest_hz(wanted):
    return min(available_hz(), key=lambda r: (abs(r - wanted), -r))


def set_hz(hz):
    dm = current_mode()
    dm.dmDisplayFrequency = hz
    dm.dmFields = DM_DISPLAYFREQUENCY
    result = user32.ChangeDisplaySettingsW(ctypes.byref(dm), 0)   # 0 = temporary, not saved
    if result != 0:
        raise RuntimeError(f"Windows refused {hz} Hz (code {result})")
    time.sleep(5)                                # monitors blank for a moment while they switch
    return current_mode().dmDisplayFrequency


def restore_display():
    user32.ChangeDisplaySettingsW(None, 0)       # back to the saved settings
    time.sleep(4)


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------

def one_run(port_name, label, run_no, writer, log):
    import tkinter as tk

    result = {"values": [], "misses": 0, "error": None}
    root = tk.Tk()
    root.title("Latency flash test")
    root.configure(bg="black", cursor="none")
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.bind("<ButtonPress-1>", lambda e: root.configure(bg="white"))
    root.bind("<ButtonRelease-1>", lambda e: root.configure(bg="black"))
    root.bind("<Escape>", lambda e: (result.update(error="stopped with Esc"), root.destroy()))

    def worker():
        try:
            with serial.Serial(port_name, 115200, timeout=1) as port:
                time.sleep(2.5)                  # window up and black before the baseline
                root.after(0, lambda: (root.focus_force(), center_cursor(root)))
                time.sleep(0.5)
                port.reset_input_buffer()
                port.write(b"s")
                idle = time.monotonic()
                while True:
                    line = port.readline().decode("ascii", "ignore").strip()
                    if not line:
                        if time.monotonic() - idle > 120:
                            result["error"] = "no data from the tester for 2 minutes"
                            break
                        continue
                    idle = time.monotonic()
                    if line.startswith("sample,"):
                        _, n, us = line.split(",")
                        ms = int(us) / 1000
                        result["values"].append(ms)
                        writer.writerow([datetime.now().isoformat(timespec="seconds"), label, run_no, n, f"{ms:.3f}"])
                    elif line.startswith("miss,"):
                        result["misses"] += 1
                    elif line.startswith("summary,"):
                        break
        except (serial.SerialException, OSError) as err:
            result["error"] = f"serial: {err}"
        finally:
            try:
                root.after(0, root.destroy)
            except RuntimeError:
                pass

    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    v = result["values"]
    if v:
        log(f"  {label} run {run_no}: n={len(v)} median {statistics.median(v):.2f} ms, "
            f"min {min(v):.2f}, max {max(v):.2f}, misses {result['misses']}")
    if result["error"]:
        log(f"  {label} run {run_no}: {result['error']}")
    return result


def center_cursor(root):
    user32.SetCursorPos(root.winfo_screenwidth() // 2, root.winfo_screenheight() // 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", nargs="?", help="tester COM port, e.g. COM5")
    ap.add_argument("--label", default="auto", help='run label; "auto" = "flash <hz>hz"')
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--hz", type=int, help="switch the main monitor to this rate (nearest available) for the run")
    ap.add_argument("--out", default="docs/results/raw.csv")
    ap.add_argument("--list-hz", action="store_true", help="show the main monitor's refresh rates and exit")
    args = ap.parse_args()

    if sys.platform != "win32":
        sys.exit("auto_flash.py runs on Windows only (use flash_test.html elsewhere)")
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # real pixels, so the cursor lands in the middle
    except (AttributeError, OSError):
        pass

    def log(msg):
        print(msg, flush=True)

    cur = current_mode()
    log(f"main monitor: {cur.dmPelsWidth}x{cur.dmPelsHeight} at {cur.dmDisplayFrequency} Hz; "
        f"available: {', '.join(map(str, available_hz()))} Hz")
    if args.list_hz:
        return
    if not args.port:
        sys.exit("give the tester's COM port, e.g. COM5")

    changed = False
    hz = cur.dmDisplayFrequency
    try:
        if args.hz and args.hz != hz:
            target = nearest_hz(args.hz)
            hz = set_hz(target)
            changed = True
            log(f"switched to {hz} Hz")
        label = f"flash {hz}hz" if args.label == "auto" else args.label
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        new_file = not out.exists()
        with open(out, "a", newline="") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["timestamp", "label", "run", "sample", "latency_ms"])
            for r in range(1, args.runs + 1):
                res = one_run(args.port, label, r, writer, log)
                f.flush()
                if res["error"]:
                    sys.exit(1)
    finally:
        if changed:
            restore_display()
            log("display settings restored")


if __name__ == "__main__":
    main()
