"""Summarise results.csv into a Markdown table and a chart, ready for a README.

Usage:
    pip install matplotlib          # only needed for the chart
    python analyze.py                                   # reads results.csv
    python analyze.py results.csv --out results         # writes results.md + results.png
    python analyze.py --only "cs2 vsync off" "cs2 vsync on" --out vsync --title "CS2: V-Sync"

Each label in the CSV becomes one row. Rows keep the order they were first recorded in,
or use --sort to order them by median.
"""

import argparse
import csv
import statistics
import sys
from collections import OrderedDict
from pathlib import Path


def load(path: Path) -> "OrderedDict[str, list]":
    groups: "OrderedDict[str, list]" = OrderedDict()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                groups.setdefault(row["label"], []).append(float(row["latency_ms"]))
            except (KeyError, ValueError):
                continue
    return groups


def pct(values, p):
    """Percentile with linear interpolation (p in 0-100)."""
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def stats(values):
    return {
        "n": len(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "p5": pct(values, 5),
        "p95": pct(values, 95),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def markdown(rows, title):
    lines = []
    if title:
        lines += [f"### {title}", ""]
    lines += ["| Setup | Median | Mean | 5th–95th pct | Std dev | n |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for label, s in rows:
        lines.append(f"| {label} | **{s['median']:.1f} ms** | {s['mean']:.1f} ms | "
                     f"{s['p5']:.1f}–{s['p95']:.1f} ms | {s['sd']:.1f} ms | {s['n']} |")
    return "\n".join(lines) + "\n"


def chart(groups, rows, title, out_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: skipping the chart (pip install matplotlib)")
        return False

    surface, ink, ink2, grid, mark = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
    labels = [label for label, _ in rows]
    height = 0.9 + 0.55 * len(labels)
    fig, ax = plt.subplots(figsize=(8, height), dpi=200)
    fig.patch.set_facecolor(surface)
    ax.set_facecolor(surface)

    import random
    rnd = random.Random(1)
    xmax = 0
    for i, (label, s) in enumerate(rows):
        y = len(labels) - 1 - i
        vals = groups[label]
        xmax = max(xmax, max(vals))
        ys = [y + rnd.uniform(-0.18, 0.18) for _ in vals]
        ax.scatter(vals, ys, s=9, color=mark, alpha=0.28, linewidths=0, zorder=2)
        ax.plot([s["p5"], s["p95"]], [y, y], color=ink2, linewidth=2, solid_capstyle="round", zorder=3)
        ax.scatter([s["median"]], [y], s=64, color=mark, edgecolors=surface, linewidths=2, zorder=4)
        ax.text(s["p95"], y + 0.3, f"  median {s['median']:.1f} ms", color=ink, fontsize=8,
                va="center", ha="left", zorder=5)

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(list(reversed(labels)), color=ink, fontsize=9)
    ax.set_xlim(0, xmax * 1.25)
    ax.set_ylim(-0.6, len(labels) - 0.4)
    ax.set_xlabel("Click-to-photon latency (ms)", color=ink2, fontsize=9)
    ax.tick_params(axis="x", colors=ink2, labelsize=8)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=grid, linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(grid)
    if title:
        ax.set_title(title, loc="left", color=ink, fontsize=11, fontweight="bold", pad=10)
    fig.text(0.01, 0.005, "Dots: individual clicks. Line: 5th–95th percentile. Large dot: median.",
             color=ink2, fontsize=7, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out_png, facecolor=surface)
    plt.close(fig)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", default="results.csv")
    ap.add_argument("--out", default="summary", help="output name without extension (default: summary)")
    ap.add_argument("--only", nargs="+", metavar="LABEL", help="include only these labels, in this order")
    ap.add_argument("--sort", action="store_true", help="order rows by median, fastest first")
    ap.add_argument("--title", default="", help="title for the table and chart")
    args = ap.parse_args()

    groups = load(Path(args.csv))
    if not groups:
        sys.exit(f"no samples found in {args.csv}")
    if args.only:
        missing = [l for l in args.only if l not in groups]
        if missing:
            sys.exit(f"labels not found: {missing}. Available: {list(groups)}")
        groups = OrderedDict((l, groups[l]) for l in args.only)

    rows = [(label, stats(vals)) for label, vals in groups.items()]
    if args.sort:
        rows.sort(key=lambda r: r[1]["median"])

    md = markdown(rows, args.title)
    Path(args.out + ".md").write_text(md, encoding="utf-8")
    print(md)
    if chart(groups, rows, args.title, args.out + ".png"):
        print(f"wrote {args.out}.md and {args.out}.png")
    else:
        print(f"wrote {args.out}.md")


if __name__ == "__main__":
    main()
