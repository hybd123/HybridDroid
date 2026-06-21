#!/usr/bin/env python3
"""Parse ablation_simk CSV and summarize line coverage by sim k."""

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_IN = ROOT / "HybirdDroid实验记录 - ablation_simk.csv"
CSV_TIDY = ROOT / "ablation_simk_tidy.csv"
CSV_LINE_PIVOT = ROOT / "ablation_simk_line_coverage_pivot.csv"
CSV_BEST_K = ROOT / "ablation_simk_best_k_per_app.csv"
MD_SUMMARY = ROOT / "ablation_simk_summary.md"

APP_ORDER = [
    "AlarmClock", "AmazeFileManager", "AnkiDroid", "AntennaPod", "Chess", "Feeder",
    "MyExpenses", "NewPipe", "Omni-Notes", "OwnTracks", "RedReader", "Wikipedia",
]
K_ORDER = [5, 6, 7, 8, 9, 10]


def parse_csv(path: Path) -> dict[tuple[int, str], dict[str, float | None]]:
    rows = list(csv.reader(path.open(encoding="utf-8")))
    all_data: dict[tuple[int, str], dict[str, float | None]] = {}
    i = 0
    while i < len(rows):
        row = rows[i]
        ks = re.findall(r"simk=(\d+)", ",".join(row), re.I)
        if ks and (row[0] or "").strip().lower() != "app":
            k_list = [int(x) for x in ks]
            if i + 1 < len(rows) and (rows[i + 1][0] or "").strip().lower() == "app":
                header = rows[i + 1]
                starts = [j for j, c in enumerate(header) if (c or "").strip().lower() == "app"]
                for bi, k in zip(starts, k_list):
                    j = i + 2
                    while j < len(rows):
                        data_row = rows[j]
                        if not data_row or (data_row[0] or "").strip().lower() == "app":
                            break
                        if re.search(r"simk=", ",".join(data_row), re.I):
                            break
                        app = (data_row[bi] or "").strip() if bi < len(data_row) else ""
                        if not app or not re.match(r"^[A-Za-z]", app):
                            j += 1
                            continue

                        def gv(idx: int) -> float | None:
                            if bi + idx >= len(data_row):
                                return None
                            s = (data_row[bi + idx] or "").strip()
                            return float(s) if s else None

                        all_data[(k, app)] = {
                            "line": gv(1),
                            "branch": gv(2),
                            "method": gv(3),
                            "class": gv(4),
                        }
                        j += 1
                i = j
                continue
        i += 1
    return all_data


def main():
    all_data = parse_csv(CSV_IN)
    by_k: dict[int, dict[str, dict]] = defaultdict(dict)
    for (k, app), m in all_data.items():
        by_k[k][app] = m

    apps = [a for a in APP_ORDER if any((k, a) in all_data for k in K_ORDER)]
    for d in by_k.values():
        for a in d:
            if a not in apps:
                apps.append(a)

    # Tidy export
    with CSV_TIDY.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["App", "sim_k", "Line(%)", "Branch(%)", "Method(%)", "Class(%)"])
        for app in apps:
            for k in K_ORDER:
                m = by_k.get(k, {}).get(app, {})
                w.writerow([
                    app, k,
                    m.get("line", ""), m.get("branch", ""),
                    m.get("method", ""), m.get("class", ""),
                ])

    # Line pivot
    with CSV_LINE_PIVOT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["App"] + [f"k={k}" for k in K_ORDER] + ["Best k(s)", "k=8 best?", "k=8 rank"])
        for app in apps:
            vals = {}
            for k in K_ORDER:
                v = by_k.get(k, {}).get(app, {}).get("line")
                vals[k] = v
            present = {k: v for k, v in vals.items() if v is not None}
            if not present:
                continue
            max_v = max(present.values())
            best_ks = sorted([k for k, v in present.items() if v == max_v])
            k8 = vals.get(8)
            if k8 is None:
                k8_best = "N/A (missing)"
                rank = ""
            else:
                k8_best = "Yes" if 8 in best_ks else "No"
                sorted_ks = sorted(present.keys(), key=lambda x: present[x], reverse=True)
                rank = sorted_ks.index(8) + 1 if 8 in sorted_ks else ""
            row = [app] + [f"{vals[k]:.3f}" if vals.get(k) is not None else "" for k in K_ORDER]
            row += [",".join(map(str, best_ks)), k8_best, rank]
            w.writerow(row)
        # Mean row (apps with valid line per k)
        mean_row = ["Mean (across apps)"]
        for k in K_ORDER:
            vs = [by_k[k][a]["line"] for a in apps if by_k.get(k, {}).get(a, {}).get("line") is not None]
            mean_row.append(f"{sum(vs)/len(vs):.3f}" if vs else "")
        w.writerow(mean_row)

    # Best-k detail
    best_rows = []
    for app in apps:
        present = {k: by_k[k][app]["line"] for k in K_ORDER if by_k.get(k, {}).get(app, {}).get("line") is not None}
        if not present:
            continue
        max_v = max(present.values())
        best_ks = [k for k, v in present.items() if v == max_v]
        k8_val = present.get(8)
        best_rows.append({
            "App": app,
            "k=8 Line(%)": f"{k8_val:.3f}" if k8_val is not None else "",
            "Max Line(%)": f"{max_v:.3f}",
            "Best k(s)": ",".join(map(str, sorted(best_ks))),
            "k=8 is unique best": "Yes" if best_ks == [8] else "No",
            "k=8 tied for best": "Yes" if 8 in best_ks else "No",
            "Winner if not k=8": ",".join(map(str, sorted(best_ks))) if 8 not in best_ks else "",
        })

    with CSV_BEST_K.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(best_rows[0].keys()))
        w.writeheader()
        w.writerows(best_rows)

    # Counts
    apps_with_k8 = [r for r in best_rows if r["k=8 Line(%)"]]
    unique_best = sum(1 for r in best_rows if r["k=8 is unique best"] == "Yes")
    tied_best = sum(1 for r in best_rows if r["k=8 tied for best"] == "Yes")
    not_best = sum(1 for r in best_rows if r["k=8 tied for best"] == "No" and r["k=8 Line(%)"])
    n_compare = len(apps_with_k8)
    # Apps with any missing k excluded from "all k" comparison - list incomplete for k=9
    apps_full = []
    for app in apps:
        if all(by_k.get(k, {}).get(app, {}).get("line") is not None for k in K_ORDER):
            apps_full.append(app)

    full_unique = sum(
        1 for app in apps_full
        if by_k[8][app]["line"] == max(by_k[k][app]["line"] for k in K_ORDER)
        and sum(1 for k in K_ORDER if by_k[k][app]["line"] == by_k[8][app]["line"]) == 1
    )
    full_tied = sum(
        1 for app in apps_full
        if by_k[8][app]["line"] == max(by_k[k][app]["line"] for k in K_ORDER)
    )

    with MD_SUMMARY.open("w", encoding="utf-8") as f:
        f.write("# sim_k Ablation — Line Coverage Summary\n\n")
        f.write("Source: `HybirdDroid实验记录 - ablation_simk.csv` (per-app values are averages over runs).\n\n")
        f.write("## k=8 vs other k per app\n\n")
        f.write(f"- Apps with k=8 data: **{len(apps_with_k8)}** / 12\n")
        f.write(f"- k=8 is **unique** best line coverage: **{unique_best}** apps\n")
        f.write(f"- k=8 is **tied** for best (includes unique): **{tied_best}** apps\n")
        f.write(f"- k=8 is **not** among best: **{not_best}** apps\n\n")
        f.write(f"Among apps with **all k∈{{5,6,7,8,9,10}}** present ({len(apps_full)} apps): ")
        f.write(f"k=8 unique best = **{full_unique}**, k=8 tied-or-best = **{full_tied}**.\n\n")
        f.write("> k=9 missing Chess & Feeder (API failures). Mean row uses available apps per k.\n\n")
        f.write("## Line coverage pivot (%)\n\n")
        f.write("| App | " + " | ".join(f"k={k}" for k in K_ORDER) + " | Best k |\n")
        f.write("|-----|" + "|".join(["------"] * len(K_ORDER)) + "|--------|\n")
        for app in apps:
            cells = [app]
            present = {}
            for k in K_ORDER:
                v = by_k.get(k, {}).get(app, {}).get("line")
                if v is not None:
                    present[k] = v
                    cells.append(f"{v:.2f}")
                else:
                    cells.append("—")
            if present:
                mx = max(present.values())
                bk = ",".join(str(k) for k in sorted(present) if present[k] == mx)
            else:
                bk = "—"
            cells.append(bk)
            f.write("| " + " | ".join(cells) + " |\n")
        f.write("\n## Apps where k=8 is not the best\n\n")
        losers = [r for r in best_rows if r["k=8 is unique best"] == "No" and r["k=8 tied for best"] == "No"]
        if not losers:
            f.write("(none among apps with k=8 data)\n")
        else:
            f.write("| App | k=8 | Best k(s) | Max |\n|-----|-----|-----------|-----|\n")
            for r in losers:
                f.write(f"| {r['App']} | {r['k=8 Line(%)']} | {r['Best k(s)']} | {r['Max Line(%)']} |\n")
        ties_only = [r for r in best_rows if r["k=8 tied for best"] == "Yes" and r["k=8 is unique best"] == "No"]
        if ties_only:
            f.write("\n## Apps where k=8 ties for best (not unique)\n\n")
            for r in ties_only:
                f.write(f"- **{r['App']}**: best k = {r['Best k(s)']}\n")

    print(f"Wrote {CSV_TIDY}")
    print(f"Wrote {CSV_LINE_PIVOT}")
    print(f"Wrote {CSV_BEST_K}")
    print(f"Wrote {MD_SUMMARY}")
    print(f"\nSummary: k=8 unique best = {unique_best}/{n_compare}, tied-or-best = {tied_best}/{n_compare}, not best = {not_best}/{n_compare}")
    print(f"Full 6-k apps ({len(apps_full)}): unique best = {full_unique}, tied-or-best = {full_tied}")


if __name__ == "__main__":
    main()
