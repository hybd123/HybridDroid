#!/usr/bin/env python3
"""Compute Wilcoxon signed-rank p-values and effect sizes for RQ1 coverage."""

import csv
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
CSV_IN = ROOT / "HybridDroid实验(最新) - RQ1完整覆盖率数据.csv"
CSV_OUT = ROOT / "RQ1_significance_pvalues.csv"
CSV_PIVOT = ROOT / "RQ1_significance_table_all_baselines.csv"
MD_OUT = ROOT / "RQ1_significance_table.md"

TOOL_MAP = {
    "Monkey*-LLM": "HybridMonkey",
    "HybirdDroid": "HybridDroid",
    "Monkey*-Random": "Monkey*",
    "DroidbotRandom": "Droidbot*",
}

APP_ALIASES = {
    "OmniNotes": "Omni-Notes",
}

METRICS = [
    ("Avg Line Cov(%)", "Line"),
    ("Avg Branch Cov(%)", "Branch"),
    ("Avg Method Cov(%)", "Method"),
    ("Avg Class Cov(%)", "Class"),
]

VALID_APPS = {
    "AmazeFileManager", "AntennaPod", "MyExpenses", "NewPipe", "Omni-Notes",
    "OwnTracks", "RedReader", "Wikipedia", "AlarmClock", "Feeder", "Chess", "AnkiDroid",
}

OURS_TOOLS = {"HybridMonkey", "HybridDroid"}
BASELINE_ORDER = ["Monkey", "Monkey*", "Fastbot", "Droidbot*", "GPTDroid", "Aurora"]


def load_data():
    rows = []
    last_app = None
    with CSV_IN.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            app = (row.get("APP") or "").strip()
            tool = (row.get("Tool") or "").strip()
            if not tool:
                continue
            if app:
                app = APP_ALIASES.get(app, app)
                last_app = app
            else:
                app = last_app
            if not app or app not in VALID_APPS:
                continue
            rec = {"APP": app, "ToolNorm": TOOL_MAP.get(tool, tool)}
            for col, _ in METRICS:
                rec[col] = float(row[col])
            rows.append(rec)
    return rows


def discover_baselines(rows):
    tools = {r["ToolNorm"] for r in rows}
    baselines = [b for b in BASELINE_ORDER if b in tools]
    extra = sorted(tools - OURS_TOOLS - set(baselines))
    return baselines + extra


def get_val(rows, app, tool, col):
    for r in rows:
        if r["APP"] == app and r["ToolNorm"] == tool:
            return r[col]
    return None


def collect_diffs(rows, tool_a, tool_b, col):
    diffs = []
    for app in sorted(VALID_APPS):
        va = get_val(rows, app, tool_a, col)
        vb = get_val(rows, app, tool_b, col)
        if va is None or vb is None:
            continue
        diffs.append(va - vb)
    return np.array(diffs, dtype=float)


def cohens_d_paired(diffs):
    """Cohen's d_z for paired samples: mean(d) / SD(d)."""
    if len(diffs) < 2:
        return float("nan")
    sd = np.std(diffs, ddof=1)
    if sd == 0:
        return float("inf") if np.mean(diffs) != 0 else 0.0
    return float(np.mean(diffs) / sd)


def rank_biserial_wilcoxon(diffs):
    """
    Rank-biserial correlation r (paired Wilcoxon effect size).
    r = (2*W+ - n(n+1)/2) / (n(n+1)/2), W+ = sum of ranks of positive differences.

    Note: scipy.stats.wilcoxon returns the sum of ranks of *negative* differences;
    W+ = n(n+1)/2 - W- when there are no ties at zero.
    """
    nonzero = diffs[diffs != 0]
    n = len(nonzero)
    if n < 2:
        return float("nan")
    w_neg, _ = stats.wilcoxon(nonzero, zero_method="wilcox", alternative="two-sided")
    total_rank = n * (n + 1) / 2
    w_plus = total_rank - w_neg
    return float((2 * w_plus - total_rank) / total_rank)


def cliffs_delta_paired(diffs):
    """Cliff's delta for paired differences: (n+ - n-) / n."""
    if len(diffs) == 0:
        return float("nan")
    n_pos = int(np.sum(diffs > 0))
    n_neg = int(np.sum(diffs < 0))
    return float((n_pos - n_neg) / len(diffs))


def interpret_cohens_d(d):
    if d != d:
        return "N/A"
    ad = abs(d)
    if ad < 0.2:
        return "negligible"
    if ad < 0.5:
        return "small"
    if ad < 0.8:
        return "medium"
    return "large"


def interpret_rank_biserial(r):
    """Cohen-like thresholds for correlation magnitude."""
    if r != r:
        return "N/A"
    ar = abs(r)
    if ar < 0.1:
        return "negligible"
    if ar < 0.3:
        return "small"
    if ar < 0.5:
        return "medium"
    return "large"


def paired_analysis(rows, tool_a, tool_b, col):
    diffs = collect_diffs(rows, tool_a, tool_b, col)
    n = len(diffs)
    empty = {
        "n": n,
        "mean_diff": float("nan"),
        "p_two": float("nan"),
        "p_greater": float("nan"),
        "cohens_d": float("nan"),
        "rank_biserial_r": float("nan"),
        "cliffs_delta": float("nan"),
    }
    if n < 3:
        return empty

    mean_diff = float(np.mean(diffs))
    _, p_two = stats.wilcoxon(diffs, alternative="two-sided", zero_method="wilcox")
    _, p_greater = stats.wilcoxon(diffs, alternative="greater", zero_method="wilcox")
    d = cohens_d_paired(diffs)
    r_rb = rank_biserial_wilcoxon(diffs)
    delta = cliffs_delta_paired(diffs)

    return {
        "n": n,
        "mean_diff": mean_diff,
        "p_two": float(p_two),
        "p_greater": float(p_greater),
        "cohens_d": d,
        "rank_biserial_r": r_rb,
        "cliffs_delta": delta,
    }


def fmt_p(p):
    if p != p:
        return "N/A"
    return "<0.001" if p < 0.001 else f"{p:.4f}"


def fmt_num(x, digits=3):
    if x != x:
        return "N/A"
    if abs(x) == float("inf"):
        return "inf"
    return f"{x:.{digits}f}"


def sig_mark(p):
    if p != p:
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def main():
    rows = load_data()
    baselines = discover_baselines(rows)
    print(f"Baselines ({len(baselines)}): {baselines}")

    all_rows = []
    for ours in sorted(OURS_TOOLS):
        for base in baselines:
            label = f"{ours} vs {base}"
            for col, mname in METRICS:
                a = paired_analysis(rows, ours, base, col)
                all_rows.append({
                    "Comparison": label,
                    "Our Tool": ours,
                    "Baseline": base,
                    "Metric": mname,
                    "n": a["n"],
                    "Mean Diff (Ours-Baseline)": round(a["mean_diff"], 2) if a["mean_diff"] == a["mean_diff"] else "",
                    "p (two-sided)": a["p_two"],
                    "p (one-sided, ours>baseline)": a["p_greater"],
                    "p (two-sided, formatted)": fmt_p(a["p_two"]),
                    "Significant (alpha=0.05)": a["p_two"] < 0.05 if a["p_two"] == a["p_two"] else False,
                    "Cohen's d (paired)": round(a["cohens_d"], 3) if a["cohens_d"] == a["cohens_d"] else "",
                    "Cohen's d magnitude": interpret_cohens_d(a["cohens_d"]),
                    "Rank-biserial r": round(a["rank_biserial_r"], 3) if a["rank_biserial_r"] == a["rank_biserial_r"] else "",
                    "Rank-biserial magnitude": interpret_rank_biserial(a["rank_biserial_r"]),
                    "Cliff's delta (paired)": round(a["cliffs_delta"], 3) if a["cliffs_delta"] == a["cliffs_delta"] else "",
                })

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    pivot_header = ["Our Tool", "Metric"]
    for base in baselines:
        pivot_header.extend([
            f"{base} Δ(%)",
            f"{base} p",
            f"{base} Cohen's d",
            f"{base} r_rb",
            f"{base} Cliff δ",
        ])
    pivot_rows = []
    for ours in sorted(OURS_TOOLS):
        for _, mname in METRICS:
            prow = [ours, mname]
            for base in baselines:
                r = next(
                    x for x in all_rows
                    if x["Our Tool"] == ours and x["Baseline"] == base and x["Metric"] == mname
                )
                prow.extend([
                    f"{r['Mean Diff (Ours-Baseline)']:+.2f}" if r["Mean Diff (Ours-Baseline)"] != "" else "N/A",
                    fmt_p(r["p (two-sided)"]) + sig_mark(r["p (two-sided)"]),
                    fmt_num(r["Cohen's d (paired)"]) if r["Cohen's d (paired)"] != "" else "N/A",
                    fmt_num(r["Rank-biserial r"]) if r["Rank-biserial r"] != "" else "N/A",
                    fmt_num(r["Cliff's delta (paired)"]) if r["Cliff's delta (paired)"] != "" else "N/A",
                ])
            pivot_rows.append(prow)

    with CSV_PIVOT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(pivot_header)
        w.writerows(pivot_rows)

    with MD_OUT.open("w", encoding="utf-8") as f:
        f.write("# RQ1 Coverage Significance & Effect Sizes (All Baselines)\n\n")
        f.write("- **Test**: Wilcoxon signed-rank (paired per app)\n")
        f.write("- **Effect sizes**:\n")
        f.write("  - **Cohen's d** (paired): mean(Δ)/SD(Δ); |d|<0.2 negligible, 0.2–0.5 small, 0.5–0.8 medium, ≥0.8 large\n")
        f.write("  - **Rank-biserial r**: Wilcoxon-aligned effect; |r|<0.1 negligible, 0.1–0.3 small, 0.3–0.5 medium, ≥0.5 large\n")
        f.write("  - **Cliff's δ** (paired): (n₊−n₋)/n\n")
        f.write("- **Mapping**: `Monkey*-LLM`→HybridMonkey, `HybirdDroid`→HybridDroid\n\n")

        for ours in sorted(OURS_TOOLS):
            f.write(f"## {ours} — p-values\n\n")
            f.write("| Baseline | Line | Branch | Method | Class |\n")
            f.write("|----------|------|--------|--------|-------|\n")
            for base in baselines:
                cells = [base]
                for _, mname in METRICS:
                    r = next(
                        x for x in all_rows
                        if x["Our Tool"] == ours and x["Baseline"] == base and x["Metric"] == mname
                    )
                    cells.append(f"{fmt_p(r['p (two-sided)'])}{sig_mark(r['p (two-sided)'])}")
                f.write("| " + " | ".join(cells) + " |\n")
            f.write("\n")

            f.write(f"## {ours} — Cohen's d (paired)\n\n")
            f.write("| Baseline | Line | Branch | Method | Class |\n")
            f.write("|----------|------|--------|--------|-------|\n")
            for base in baselines:
                cells = [base]
                for _, mname in METRICS:
                    r = next(
                        x for x in all_rows
                        if x["Our Tool"] == ours and x["Baseline"] == base and x["Metric"] == mname
                    )
                    d = r["Cohen's d (paired)"]
                    mag = r["Cohen's d magnitude"]
                    cells.append(f"{d} ({mag})" if d != "" else "N/A")
                f.write("| " + " | ".join(cells) + " |\n")
            f.write("\n")

            f.write(f"## {ours} — Rank-biserial r\n\n")
            f.write("| Baseline | Line | Branch | Method | Class |\n")
            f.write("|----------|------|--------|--------|-------|\n")
            for base in baselines:
                cells = [base]
                for _, mname in METRICS:
                    r = next(
                        x for x in all_rows
                        if x["Our Tool"] == ours and x["Baseline"] == base and x["Metric"] == mname
                    )
                    rb = r["Rank-biserial r"]
                    mag = r["Rank-biserial magnitude"]
                    cells.append(f"{rb} ({mag})" if rb != "" else "N/A")
                f.write("| " + " | ".join(cells) + " |\n")
            f.write("\n")

    paper_path = ROOT / "RQ1_significance_table_paper.csv"
    with paper_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["Our Tool", "Metric"]
        for base in baselines:
            header.extend([
                f"vs {base} p",
                f"vs {base} Δ(%)",
                f"vs {base} Cohen d",
                f"vs {base} r_rb",
            ])
        w.writerow(header)
        for ours in sorted(OURS_TOOLS):
            for _, mname in METRICS:
                row = [ours, mname]
                for base in baselines:
                    r = next(
                        x for x in all_rows
                        if x["Our Tool"] == ours and x["Baseline"] == base and x["Metric"] == mname
                    )
                    row.extend([
                        fmt_p(r["p (two-sided)"]),
                        f"{r['Mean Diff (Ours-Baseline)']:+.2f}" if r["Mean Diff (Ours-Baseline)"] != "" else "N/A",
                        fmt_num(r["Cohen's d (paired)"]) if r["Cohen's d (paired)"] != "" else "N/A",
                        fmt_num(r["Rank-biserial r"]) if r["Rank-biserial r"] != "" else "N/A",
                    ])
                w.writerow(row)

    print(f"Wrote {CSV_OUT} ({len(all_rows)} rows)")
    print(f"Wrote {CSV_PIVOT}")
    print(f"Wrote {paper_path}")
    print(f"Wrote {MD_OUT}")


if __name__ == "__main__":
    main()
