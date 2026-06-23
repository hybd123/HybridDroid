"""
Experiment runner: Tarpit-Region Exit vs Immediate Handoff
==========================================================

Two conditions:
  A (baseline)  - hasTarpit goes False → immediately hand back to random
  B (new)       - hasTarpit goes False → continue LLM until perceptual similarity
                  to tarpit ref drops below theta_exit, or c_max steps

Sensitivity check for theta_exit: 0.80 / 0.85 / 0.90

Usage:
  python scripts/run_exp_tarpit_region.py \\
      --apk_dir benchmark/ \\
      --output_dir results/exp_tarpit_region/ \\
      --device emulator-5554 \\
      --apps Chess SimpleAlarm Wikipedia MyExpenses \\
      --runs 5 --timeout 180

Sensitivity check (Condition B only, vary theta_exit):
  python scripts/run_exp_tarpit_region.py \\
      --apk_dir benchmark/ \\
      --output_dir results/exp_tarpit_region_sensitivity/ \\
      --device emulator-5554 \\
      --apps Chess SimpleAlarm \\
      --runs 3 --timeout 180 \\
      --sensitivity_check
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DROIDBOT_SCRIPT = os.path.join(REPO_ROOT, "HybridDroidbot", "start.py")

# Base conditions
CONDITIONS = [
    ("condition_A", ["-condition", "A"]),
    ("condition_B", ["-condition", "B", "-theta_exit", "0.85", "-c_max", "5"]),
]

# Sensitivity check conditions (Condition B with varying theta_exit)
SENSITIVITY_CONDITIONS = [
    ("condition_B_theta080", ["-condition", "B", "-theta_exit", "0.80", "-c_max", "5"]),
    ("condition_B_theta085", ["-condition", "B", "-theta_exit", "0.85", "-c_max", "5"]),
    ("condition_B_theta090", ["-condition", "B", "-theta_exit", "0.90", "-c_max", "5"]),
]


def run_droidbot(apk_path, output_dir, extra_args, device, timeout_min, interval, dry_run):
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
    print(f"      cmd: {' '.join(cmd)}")
    if dry_run:
        return True
    start = time.time()
    try:
        result = subprocess.run(cmd, timeout=timeout_min * 60 + 120)
        elapsed = time.time() - start
        ok = result.returncode == 0
        print(f"[{'OK' if ok else 'FAIL'}] elapsed {elapsed:.0f}s rc={result.returncode}")
        return ok
    except subprocess.TimeoutExpired:
        print("[TIMEOUT]")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def find_apks(apk_dir, app_filter):
    apks = []
    for fname in sorted(os.listdir(apk_dir)):
        if not fname.endswith(".apk"):
            continue
        if app_filter and not any(f.lower() in fname.lower() for f in app_filter):
            continue
        apks.append(os.path.join(apk_dir, fname))
    return apks


def parse_args():
    p = argparse.ArgumentParser(description="Run tarpit-region exit vs immediate handoff experiment")
    p.add_argument("--apk_dir", required=True)
    p.add_argument("--output_dir", required=True)
    p.add_argument("--device", default=None)
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--timeout", type=int, default=180, help="minutes per run")
    p.add_argument("--interval", type=int, default=1, help="droidbot event interval (s)")
    p.add_argument("--apps", nargs="*", default=None)
    p.add_argument("--conditions", nargs="*", default=None,
                   help="Subset of condition labels to run (e.g. condition_A condition_B)")
    p.add_argument("--sensitivity_check", action="store_true",
                   help="Run theta_exit sensitivity check (0.80/0.85/0.90) instead of A/B")
    p.add_argument("--dry_run", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    apks = find_apks(args.apk_dir, args.apps)
    if not apks:
        print(f"No APKs found in {args.apk_dir}")
        sys.exit(1)

    conditions = SENSITIVITY_CONDITIONS if args.sensitivity_check else CONDITIONS
    if args.conditions:
        conditions = [c for c in conditions if c[0] in args.conditions]

    print(f"Apps      : {[os.path.basename(a) for a in apks]}")
    print(f"Conditions: {[c[0] for c in conditions]}")
    print(f"Runs/cond : {args.runs}")
    print(f"Timeout   : {args.timeout} min")
    print(f"Total runs: {len(apks) * len(conditions) * args.runs}")

    manifest = []
    for apk in apks:
        app_name = os.path.splitext(os.path.basename(apk))[0]
        for cond_label, extra_args in conditions:
            for run_idx in range(args.runs):
                out_dir = os.path.join(
                    args.output_dir, app_name, cond_label, f"run{run_idx:02d}")
                label = f"{app_name}/{cond_label}/run{run_idx:02d}"
                print(f"\n[RUN] {label}")

                success = run_droidbot(
                    apk, out_dir, extra_args,
                    args.device, args.timeout, args.interval, args.dry_run)

                manifest.append({
                    "app": app_name,
                    "condition": cond_label,
                    "run_idx": run_idx,
                    "output_dir": out_dir,
                    "success": success,
                    "timestamp": datetime.datetime.now().isoformat(),
                })

    os.makedirs(args.output_dir, exist_ok=True)
    manifest_path = os.path.join(args.output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    n_ok = sum(1 for m in manifest if m["success"])
    print(f"\nManifest: {manifest_path}")
    print(f"Done: {n_ok}/{len(manifest)} succeeded")


if __name__ == "__main__":
    main()
