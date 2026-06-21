"""
Analyze results from run_exp_llm_steps.py
==========================================

Produces three outputs matching the experiment design:

  Figure 1 (fig_fixed_n.png):
    Line chart – N (x-axis, 0..5) vs coverage / bug count / entropy / RSI rate
    N=0 = pure random, N=1 = single-step (current), N=2..5 = post-escape steps

  Table 1 (table_conditional_vs_fixedn.csv):
    Conditional continuation vs fixed-N comparison on four metrics

  Table 2 (table_bug_cases.csv):
    Template for the 5-10 bug-level case analysis (filled manually after inspection)

Usage:
  python scripts/analyze_llm_steps.py \
      --results_dir results/exp_llm_steps/ \
      --coverage_dir results/exp_llm_steps/coverage/  # optional: JaCoCo XML root

Expects each run to contain a llm_step_metrics.json written by MetricsLogger.
Coverage and crash data must come from external instrumentation (JaCoCo / logcat);
pass --coverage_dir and --crash_dir if available, otherwise those columns are omitted.
"""

import argparse
import csv
import json
import math
import os
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---- condition → N on the x-axis ----
CONDITION_TO_N = {
    "N0_pure_random": 0,
    "N1_single_step": 1,
    "N2_post1": 2,
    "N3_post2": 3,
    "N5_post4": 5,
}

FIXED_N_ORDER = ["N0_pure_random", "N1_single_step", "N2_post1", "N3_post2", "N5_post4"]
CONDITIONAL_LABEL = "conditional_t8"


def load_metrics(results_dir):
    """Return list of dicts, one per run that has a llm_step_metrics.json."""
    rows = []
    for app_name in sorted(os.listdir(results_dir)):
        app_dir = os.path.join(results_dir, app_name)
        if not os.path.isdir(app_dir):
            continue
        for cond in sorted(os.listdir(app_dir)):
            cond_dir = os.path.join(app_dir, cond)
            if not os.path.isdir(cond_dir):
                continue
            for run in sorted(os.listdir(cond_dir)):
                metrics_path = os.path.join(cond_dir, run, "llm_step_metrics.json")
                if not os.path.exists(metrics_path):
                    continue
                with open(metrics_path) as f:
                    data = json.load(f)
                summary = data.get("summary", {})
                rows.append({
                    "app": app_name,
                    "condition": cond,
                    "run": run,
                    "total_escapes": summary.get("total_escapes", 0),
                    "functional_escapes": summary.get("functional_escapes", 0),
                    "partial_escapes": summary.get("partial_escapes", 0),
                    "rsi_rate": summary.get("rsi_rate", 0.0),
                    "mean_entropy": summary.get("mean_post_escape_entropy", 0.0),
                    "mean_new_states": summary.get("mean_new_states_in_window", 0.0),
                    "total_unique_states": summary.get("total_unique_states", 0),
                    # placeholders – filled from external coverage/crash data
                    "line_coverage": None,
                    "bug_count": None,
                })
    return rows


def merge_coverage(rows, coverage_dir):
    """Try to read JaCoCo line coverage from coverage_dir/<app>/<cond>/<run>/coverage.json."""
    if not coverage_dir or not os.path.isdir(coverage_dir):
        return
    for row in rows:
        cov_path = os.path.join(
            coverage_dir, row["app"], row["condition"], row["run"], "coverage.json"
        )
        if os.path.exists(cov_path):
            with open(cov_path) as f:
                cov = json.load(f)
            row["line_coverage"] = cov.get("line_coverage")
            row["bug_count"] = cov.get("crash_count")


def group_by_condition(rows):
    """Return {condition: {metric: [values across apps/runs]}}."""
    from collections import defaultdict
    groups = defaultdict(lambda: defaultdict(list))
    metrics = ["rsi_rate", "mean_entropy", "mean_new_states", "total_unique_states",
                "line_coverage", "bug_count"]
    for row in rows:
        cond = row["condition"]
        for m in metrics:
            if row[m] is not None:
                groups[cond][m].append(row[m])
    return groups


def mean_std(values):
    if not values:
        return None, None
    m = statistics.mean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return round(m, 4), round(s, 4)


# ---------------------------------------------------------------------------
# Figure 1: Fixed-N line chart
# ---------------------------------------------------------------------------

def plot_fixed_n(groups, out_path):
    present = [c for c in FIXED_N_ORDER if c in groups]
    if len(present) < 2:
        print("[analyze] not enough fixed-N conditions to plot – skipping figure 1")
        return

    ns = [CONDITION_TO_N[c] for c in present]
    metrics_to_plot = [
        ("rsi_rate",        "RSI failure rate",   "tab:red"),
        ("mean_entropy",    "Post-escape entropy", "tab:blue"),
        ("mean_new_states", "New states / escape", "tab:green"),
    ]
    # add coverage and bug count only if data exists
    if any(groups[c]["line_coverage"] for c in present):
        metrics_to_plot.insert(0, ("line_coverage", "Line coverage (%)", "tab:orange"))
    if any(groups[c]["bug_count"] for c in present):
        metrics_to_plot.insert(0, ("bug_count", "Unique crashes", "tab:purple"))

    n_plots = len(metrics_to_plot)
    fig, axes = plt.subplots(1, n_plots, figsize=(4 * n_plots, 4))
    if n_plots == 1:
        axes = [axes]

    for ax, (metric, ylabel, color) in zip(axes, metrics_to_plot):
        means = []
        stds = []
        for c in present:
            m, s = mean_std(groups[c][metric])
            means.append(m if m is not None else float("nan"))
            stds.append(s if s is not None else 0.0)
        ax.errorbar(ns, means, yerr=stds, marker="o", color=color, capsize=4)
        ax.set_xlabel("N (post-escape LLM steps)")
        ax.set_ylabel(ylabel)
        ax.set_xticks(ns)
        ax.set_title(ylabel)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[analyze] Figure 1 saved → {out_path}")


# ---------------------------------------------------------------------------
# Table 1: Fixed-N vs Conditional comparison
# ---------------------------------------------------------------------------

def write_comparison_table(groups, out_path):
    metrics = ["rsi_rate", "mean_entropy", "mean_new_states", "line_coverage", "bug_count"]
    header = ["condition"] + [f"{m}_mean" for m in metrics] + [f"{m}_std" for m in metrics]
    rows = []
    for cond in FIXED_N_ORDER + [CONDITIONAL_LABEL]:
        if cond not in groups:
            continue
        row = {"condition": cond}
        for m in metrics:
            mean, std = mean_std(groups[cond][m])
            row[f"{m}_mean"] = mean
            row[f"{m}_std"] = std
        rows.append(row)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[analyze] Table 1 saved → {out_path}")


# ---------------------------------------------------------------------------
# Table 2: Bug-case template
# ---------------------------------------------------------------------------

def write_bug_case_template(out_path):
    header = [
        "case_id", "app", "bug_description",
        "single_step_trigger_action", "multi_step_trigger_action",
        "single_step_found", "multi_step_found",
        "llm_decision_point_step", "tarpit_name",
        "notes",
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for i in range(1, 11):
            writer.writerow({h: "" for h in header} | {"case_id": i})
    print(f"[analyze] Table 2 template saved → {out_path}")


# ---------------------------------------------------------------------------
# Per-app summary (escape counts per condition)
# ---------------------------------------------------------------------------

def write_per_app_summary(rows, out_path):
    from collections import defaultdict
    summary = defaultdict(lambda: defaultdict(list))
    for row in rows:
        summary[row["app"]][row["condition"]].append(row)

    header = ["app", "condition",
              "n_runs", "mean_escapes", "mean_functional", "mean_rsi_rate",
              "mean_entropy", "mean_new_states"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for app, cond_runs in sorted(summary.items()):
            for cond, run_rows in sorted(cond_runs.items()):
                writer.writerow({
                    "app": app,
                    "condition": cond,
                    "n_runs": len(run_rows),
                    "mean_escapes": round(statistics.mean(r["total_escapes"] for r in run_rows), 2),
                    "mean_functional": round(statistics.mean(r["functional_escapes"] for r in run_rows), 2),
                    "mean_rsi_rate": round(statistics.mean(r["rsi_rate"] for r in run_rows), 4),
                    "mean_entropy": round(statistics.mean(r["mean_entropy"] for r in run_rows), 4),
                    "mean_new_states": round(statistics.mean(r["mean_new_states"] for r in run_rows), 4),
                })
    print(f"[analyze] Per-app summary saved → {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Analyze llm-step experiment results")
    p.add_argument("--results_dir", required=True)
    p.add_argument("--coverage_dir", default=None)
    p.add_argument("--out_dir", default=None,
                   help="Output directory for figures/tables (default: results_dir/analysis/)")
    args = p.parse_args()

    out_dir = args.out_dir or os.path.join(args.results_dir, "analysis")
    os.makedirs(out_dir, exist_ok=True)

    rows = load_metrics(args.results_dir)
    if not rows:
        print(f"[analyze] No metrics files found under {args.results_dir}")
        return
    print(f"[analyze] Loaded {len(rows)} run(s)")

    merge_coverage(rows, args.coverage_dir)
    groups = group_by_condition(rows)

    plot_fixed_n(groups, os.path.join(out_dir, "fig_fixed_n.png"))
    write_comparison_table(groups, os.path.join(out_dir, "table_conditional_vs_fixedn.csv"))
    write_bug_case_template(os.path.join(out_dir, "table_bug_cases.csv"))
    write_per_app_summary(rows, os.path.join(out_dir, "per_app_summary.csv"))

    print(f"\n[analyze] All outputs in {out_dir}")


if __name__ == "__main__":
    main()
