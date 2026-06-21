"""
Experiment runner: Single-step vs Multi-step LLM Guidance
==========================================================

Layer 1 – Fixed-N scan:
  N=0  → --disable_llm (pure random, x-axis origin)
  N=1  → default (LLM fires on tarpit only, 0 post-escape steps)
  N=2  → -llm_n 1
  N=3  → -llm_n 2
  N=5  → -llm_n 4

Layer 2 – Conditional continuation:
  -conditional  (LLM continues post-escape until widget count ≥ threshold)

Each condition × app × RUNS_PER_CONDITION (default 5) runs for TIMEOUT_MIN minutes.

Usage:
  python scripts/run_exp_llm_steps.py \
      --apk_dir benchmark/ \
      --output_dir results/exp_llm_steps/ \
      --device emulator-5554 \
      --runs 5 \
      --timeout 180 \
      --interval 1 \
      --apps Chess Wikipedia AntennaPod AmazeFileManager  # subset; omit for all
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

# ---- Fixed-N conditions: (label, extra_args) ----
FIXED_N_CONDITIONS = [
    ("N0_pure_random",  ["-disable_llm"]),
    ("N1_single_step",  []),                     # default behaviour
    ("N2_post1",        ["-llm_n", "1"]),
    ("N3_post2",        ["-llm_n", "2"]),
    ("N5_post4",        ["-llm_n", "4"]),
]

CONDITIONAL_CONDITIONS = [
    ("conditional_t8",  ["-conditional", "-cond_threshold", "8"]),
]

ALL_CONDITIONS = FIXED_N_CONDITIONS + CONDITIONAL_CONDITIONS

DROIDBOT_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "HybridDroidbot", "start.py"
)


def parse_args():
    p = argparse.ArgumentParser(description="Run llm-step ablation experiment")
    p.add_argument("--apk_dir", required=True, help="Directory containing APK files")
    p.add_argument("--output_dir", required=True, help="Root output directory")
    p.add_argument("--device", default=None, help="ADB device serial (omit for default)")
    p.add_argument("--runs", type=int, default=5, help="Runs per condition per app (default 5)")
    p.add_argument("--timeout", type=int, default=180, help="Test duration in minutes (default 180)")
    p.add_argument("--interval", type=int, default=1, help="Event interval in seconds (default 1)")
    p.add_argument("--apps", nargs="*", default=None,
                   help="App name substrings to include (default: all APKs in apk_dir)")
    p.add_argument("--conditions", nargs="*", default=None,
                   help="Condition labels to run (default: all)")
    p.add_argument("--dry_run", action="store_true",
                   help="Print commands without executing")
    return p.parse_args()


def find_apks(apk_dir, app_filter):
    apks = []
    for fname in sorted(os.listdir(apk_dir)):
        if not fname.endswith(".apk"):
            continue
        if app_filter:
            if not any(f.lower() in fname.lower() for f in app_filter):
                continue
        apks.append(os.path.join(apk_dir, fname))
    return apks


def run_one(apk_path, output_dir, condition_label, extra_args, device, timeout_min, interval, dry_run):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        sys.executable, DROIDBOT_SCRIPT,
        "-a", apk_path,
        "-o", output_dir,
        "-timeout", str(timeout_min),
        "-interval", str(interval),
        "-grant_perm",
    ]
    if device:
        cmd += ["-d", device]
    cmd += extra_args

    print(f"\n[RUN] {condition_label}")
    print(f"      apk    : {os.path.basename(apk_path)}")
    print(f"      output : {output_dir}")
    print(f"      cmd    : {' '.join(cmd)}")

    if dry_run:
        return True

    start = time.time()
    try:
        result = subprocess.run(cmd, timeout=timeout_min * 60 + 120)
        elapsed = time.time() - start
        success = result.returncode == 0
        print(f"[{'OK' if success else 'FAIL'}] elapsed {elapsed:.0f}s, returncode {result.returncode}")
        return success
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] process killed after hard deadline")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    args = parse_args()
    apks = find_apks(args.apk_dir, args.apps)
    if not apks:
        print(f"No APKs found in {args.apk_dir} matching filter {args.apps}")
        sys.exit(1)

    conditions = ALL_CONDITIONS
    if args.conditions:
        conditions = [(lbl, extra) for lbl, extra in ALL_CONDITIONS if lbl in args.conditions]

    print(f"Apps      : {[os.path.basename(a) for a in apks]}")
    print(f"Conditions: {[c[0] for c in conditions]}")
    print(f"Runs/cond : {args.runs}")
    print(f"Timeout   : {args.timeout} min")
    total = len(apks) * len(conditions) * args.runs
    print(f"Total runs: {total}")

    manifest = []
    run_id = 0
    for apk in apks:
        app_name = os.path.splitext(os.path.basename(apk))[0]
        for cond_label, extra_args in conditions:
            for run_idx in range(args.runs):
                out_dir = os.path.join(
                    args.output_dir, app_name, cond_label, f"run{run_idx:02d}"
                )
                success = run_one(
                    apk_path=apk,
                    output_dir=out_dir,
                    condition_label=f"{app_name}/{cond_label}/run{run_idx:02d}",
                    extra_args=extra_args,
                    device=args.device,
                    timeout_min=args.timeout,
                    interval=args.interval,
                    dry_run=args.dry_run,
                )
                manifest.append({
                    "run_id": run_id,
                    "app": app_name,
                    "condition": cond_label,
                    "run_idx": run_idx,
                    "output_dir": out_dir,
                    "success": success,
                    "timestamp": datetime.datetime.now().isoformat(),
                })
                run_id += 1

    manifest_path = os.path.join(args.output_dir, "manifest.json")
    os.makedirs(args.output_dir, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved to {manifest_path}")
    n_ok = sum(1 for m in manifest if m["success"])
    print(f"Completed: {n_ok}/{len(manifest)} runs succeeded")


if __name__ == "__main__":
    main()
