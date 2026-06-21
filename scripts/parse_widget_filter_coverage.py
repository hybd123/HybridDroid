#!/usr/bin/env python3
"""Compare coverage before/after widget-filter optimization."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_IN = ROOT / "HybridDroid实验(最新) - RQ1覆盖率数据（控件过滤优化）.csv"
CSV_COMPARE = ROOT / "widget_filter_coverage_comparison.csv"
MD_SUMMARY = ROOT / "widget_filter_coverage_summary.md"

APP_NAMES = {
    "Alarm": "AlarmClock",
    "Amaze": "AmazeFileManager",
    "chess": "Chess",
    "Myexpenses": "MyExpenses",
    "Newpipe": "NewPipe",
    "OmniNotes": "Omni-Notes",
    "Owntracks": "OwnTracks",
    "Redreader": "RedReader",
    "Wikipedia": "Wikipedia",
    "Feeder": "Feeder",
    "Antennapod": "AntennaPod",
    "AnkiDroid": "AnkiDroid",
}

APP_ORDER = [
    "AlarmClock", "AmazeFileManager", "AnkiDroid", "AntennaPod", "Chess", "Feeder",
    "MyExpenses", "NewPipe", "Omni-Notes", "OwnTracks", "RedReader", "Wikipedia",
]

METRICS = ["Line", "Branch", "Method", "Class"]


def load():
    rows = list(csv.reader(CSV_IN.open(encoding="utf-8")))
    data = []
    for row in rows[2:]:
        if len(row) < 12:
            continue
        app_raw = (row[1] or "").strip()
        if not app_raw:
            continue
        app = APP_NAMES.get(app_raw, app_raw)

        def parse4(start):
            out = []
            for i in range(4):
                s = (row[start + i] or "").strip() if start + i < len(row) else ""
                out.append(float(s) if s else None)
            return dict(zip(METRICS, out))

        issues = (row[2] or "").strip()
        data.append({
            "app": app,
            "widget_issues": int(issues) if issues.isdigit() else issues,
            "after": parse4(3),
            "before": parse4(8),
        })
    by_app = {d["app"]: d for d in data}
    return [by_app[a] for a in APP_ORDER if a in by_app]


def mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def main():
    data = load()

    rows_out = []
    for d in data:
        row = {
            "App": d["app"],
            "Widget occlusion issues": d["widget_issues"],
        }
        for m in METRICS:
            b, a = d["before"][m], d["after"][m]
            row[f"Before {m}(%)"] = f"{b:.2f}" if b is not None else ""
            row[f"After {m}(%)"] = f"{a:.2f}" if a is not None else ""
            if b is not None and a is not None:
                row[f"Δ {m} (After-Before)"] = f"{a - b:+.2f}"
            else:
                row[f"Δ {m} (After-Before)"] = ""
        rows_out.append(row)

    # Mean row
    mean_row = {"App": "Mean (12 apps, available values)", "Widget occlusion issues": ""}
    for m in METRICS:
        before_vals = [d["before"][m] for d in data if d["before"][m] is not None]
        after_vals = [d["after"][m] for d in data if d["after"][m] is not None]
        mb, ma = mean(before_vals), mean(after_vals)
        mean_row[f"Before {m}(%)"] = f"{mb:.2f}" if mb is not None else ""
        mean_row[f"After {m}(%)"] = f"{ma:.2f}" if ma is not None else ""
        paired = [
            d["after"][m] - d["before"][m]
            for d in data
            if d["before"][m] is not None and d["after"][m] is not None
        ]
        mean_row[f"Δ {m} (After-Before)"] = f"{mean(paired):+.2f}" if paired else ""

    mean_row_paired = {"App": "Mean (11 apps, both Before & After)", "Widget occlusion issues": ""}
    for m in METRICS:
        paired = [
            (d["before"][m], d["after"][m])
            for d in data
            if d["before"][m] is not None and d["after"][m] is not None
        ]
        mb = mean([p[0] for p in paired])
        ma = mean([p[1] for p in paired])
        mean_row_paired[f"Before {m}(%)"] = f"{mb:.2f}"
        mean_row_paired[f"After {m}(%)"] = f"{ma:.2f}"
        mean_row_paired[f"Δ {m} (After-Before)"] = f"{mean([p[1]-p[0] for p in paired]):+.2f}"

    fieldnames = list(rows_out[0].keys())
    with CSV_COMPARE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)
        w.writerow(mean_row)
        w.writerow(mean_row_paired)

    with MD_SUMMARY.open("w", encoding="utf-8") as f:
        f.write("# Widget Filter Optimization — Coverage Comparison\n\n")
        f.write("Source: `HybridDroid实验(最新) - RQ1覆盖率数据（控件过滤优化）.csv`\n\n")
        f.write("- **Before**: coverage before widget-occlusion filtering fix\n")
        f.write("- **After**: coverage after optimization\n")
        f.write("- **Δ** = After − Before (negative ⇒ reported coverage decreases after fix)\n\n")

        f.write("## Overall average (12 apps)\n\n")
        f.write("| Metric | Before (%) | After (%) | Δ (After−Before) | Apps in After avg |\n")
        f.write("|--------|------------|-----------|------------------|-------------------|\n")
        for m in METRICS:
            bv = [d["before"][m] for d in data if d["before"][m] is not None]
            av = [d["after"][m] for d in data if d["after"][m] is not None]
            paired = [
                d["after"][m] - d["before"][m]
                for d in data
                if d["before"][m] is not None and d["after"][m] is not None
            ]
            f.write(
                f"| {m} | {mean(bv):.2f} | {mean(av):.2f} | {mean(paired):+.2f}* | {len(av)}/12 |\n"
            )
        f.write("\n\\* Δ mean uses **11 apps** with both Before and After (Feeder missing After).\n\n")

        f.write("## Per-app Line coverage\n\n")
        f.write("| App | Issues | Before | After | Δ |\n")
        f.write("|-----|--------|--------|-------|---|\n")
        for d in data:
            b, a = d["before"]["Line"], d["after"]["Line"]
            bs = f"{b:.2f}" if b is not None else "—"
            a_s = f"{a:.2f}" if a is not None else "—"
            delta = f"{a-b:+.2f}" if b is not None and a is not None else "—"
            f.write(f"| {d['app']} | {d['widget_issues']} | {bs} | {a_s} | {delta} |\n")

        improved = [
            d for d in data
            if d["before"]["Line"] is not None and d["after"]["Line"] is not None
            and d["after"]["Line"] > d["before"]["Line"]
        ]
        decreased = [
            d for d in data
            if d["before"]["Line"] is not None and d["after"]["Line"] is not None
            and d["after"]["Line"] < d["before"]["Line"]
        ]
        f.write(f"\n**Line coverage**: After > Before on **{len(improved)}** apps; After < Before on **{len(decreased)}** apps.\n")
        f.write("- Increased: " + ", ".join(d["app"] for d in improved) + "\n")
        f.write("- Decreased: " + ", ".join(d["app"] for d in decreased) + "\n")
        f.write("- Feeder: only Before data available (After missing).\n")

    print(f"Wrote {CSV_COMPARE}")
    print(f"Wrote {MD_SUMMARY}")


if __name__ == "__main__":
    main()
