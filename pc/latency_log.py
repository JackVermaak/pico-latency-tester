"""Record runs from the Pico Latency Tester to CSV and print a summary.

Usage:
    pip install pyserial
    python latency_log.py COM9 --label "cs2 reflex on"          # starts a run and logs it
    python latency_log.py COM9 --label "browser test" --runs 2  # two runs back to back

Find the COM port in Device Manager > Ports (the tester shows up as a USB serial device).
Each sample is appended to results.csv: timestamp, label, run, sample, latency_ms.
"""

import argparse
import csv
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import serial


def run_once(port: serial.Serial, label: str, run_no: int, writer) -> list:
    port.reset_input_buffer()
    port.write(b"s")
    values, started = [], time.monotonic()
    print(f"run {run_no}: started, keep the window under the sensor in focus...")
    while True:
        line = port.readline().decode("ascii", "ignore").strip()
        if not line:
            if time.monotonic() - started > 180:
                print("  no data for 3 minutes, giving up")
                break
            continue
        started = time.monotonic()
        if line.startswith("sample,"):
            _, n, us = line.split(",")
            ms = int(us) / 1000
            values.append(ms)
            writer.writerow([datetime.now().isoformat(timespec="seconds"), label, run_no, n, f"{ms:.3f}"])
            print(f"  {n:>3}: {ms:6.2f} ms", end="\r")
        elif line.startswith("miss,"):
            print(f"  miss #{line.split(',')[1]} (no brightness change seen)")
        elif line.startswith("summary,"):
            print()
            break
        elif line.startswith("#"):
            pass
    return values


def report(label: str, values: list) -> None:
    if not values:
        print("no samples")
        return
    q = statistics.quantiles(values, n=20) if len(values) >= 20 else None
    print(f"\n{label}: n={len(values)}")
    print(f"  mean   {statistics.mean(values):6.2f} ms")
    print(f"  median {statistics.median(values):6.2f} ms")
    print(f"  min    {min(values):6.2f} ms   max {max(values):6.2f} ms")
    if len(values) > 1:
        print(f"  stdev  {statistics.stdev(values):6.2f} ms")
    if q:
        print(f"  5th-95th percentile {q[0]:.2f}-{q[-1]:.2f} ms")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", help="serial port, e.g. COM9")
    ap.add_argument("--label", default="test", help="what you're measuring, e.g. 'cs2 fullscreen 240fps'")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--out", default="results.csv")
    args = ap.parse_args()

    out = Path(args.out)
    new_file = not out.exists()
    try:
        port = serial.Serial(args.port, 115200, timeout=1)
    except serial.SerialException as err:
        sys.exit(f"could not open {args.port}: {err}")
    time.sleep(0.3)
    all_values = []
    with port, open(out, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp", "label", "run", "sample", "latency_ms"])
        for r in range(1, args.runs + 1):
            all_values += run_once(port, args.label, r, writer)
            f.flush()
    report(args.label, all_values)
    print(f"\nsaved to {out.resolve()}")


if __name__ == "__main__":
    main()
