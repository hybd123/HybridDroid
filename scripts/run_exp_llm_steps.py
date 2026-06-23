"""
Experiment runner: Single-step vs Multi-step LLM Guidance
==========================================================

Supports both tools: HybridDroidbot (Python) and HybridMonkey (Fastbot/Java).

Fixed-N conditions (x-axis):
  N=0  → pure random  (droidbot: -disable_llm | monkey: max.disableLlm=true)
  N=1  → single-step  (default, 0 post-escape steps)
  N=2  → 1 post-escape LLM step
  N=3  → 2 post-escape LLM steps
  N=5  → 4 post-escape LLM steps

Each condition × app × --runs repetitions, --timeout minutes per run.

Usage – droidbot only:
  python scripts/run_exp_llm_steps.py \\
      --tool droidbot \\
      --apk_dir benchmark/ \\
      --output_dir results/exp_llm_steps/ \\
      --device emulator-5554 \\
      --apps Chess Wikipedia AntennaPod AmazeFileManager \\
      --runs 5 --timeout 180

Usage – HybridMonkey:
  python scripts/run_exp_llm_steps.py \\
      --tool monkey \\
      --apk_dir benchmark/ \\
      --output_dir results/exp_llm_steps/ \\
      --device emulator-5554 \\
      --monkey_jar /path/to/monkeyq.jar \\
      --package com.example.app \\
      --runs 5 --timeout 180

Usage – both tools (for cross-tool validation):
  python scripts/run_exp_llm_steps.py \\
      --tool both \\
      ... (same args, requires --monkey_jar and --package)
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

# ---- Fixed-N conditions ----
# (label, droidbot_extra_args, monkey_config_overrides)
FIXED_N_CONDITIONS = [
    ("N0_pure_random",
     ["-disable_llm"],
     {"max.disableLlm": "true"}),
    ("N1_single_step",
     [],
     {}),
    ("N2_post1",
     ["-llm_n", "1"],
     {"max.llmPostEscapeN": "1"}),
    ("N3_post2",
     ["-llm_n", "2"],
     {"max.llmPostEscapeN": "2"}),
    ("N5_post4",
     ["-llm_n", "4"],
     {"max.llmPostEscapeN": "4"}),
]

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DROIDBOT_SCRIPT = os.path.join(REPO_ROOT, "HybridDroidbot", "start.py")
BASE_MAX_CONFIG = os.path.join(REPO_ROOT, "HybridMonkey", "max.config")


# ---------------------------------------------------------------------------
# HybridDroidbot runner
# ---------------------------------------------------------------------------

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
    return _run_cmd(cmd, timeout_min, dry_run)


# ---------------------------------------------------------------------------
# HybridMonkey runner
# ---------------------------------------------------------------------------

def build_monkey_config(config_overrides):
    """Write a temp max.config with the given key overrides on top of the base config."""
    with open(BASE_MAX_CONFIG) as f:
        base_lines = f.readlines()

    # filter out lines whose key appears in overrides
    filtered = []
    for line in base_lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            filtered.append(line)
            continue
        key = stripped.split("=")[0].strip()
        if key not in config_overrides:
            filtered.append(line)

    # append overrides
    for k, v in config_overrides.items():
        filtered.append(f"{k} = {v}\n")

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".config", delete=False)
    tmp.writelines(filtered)
    tmp.close()
    return tmp.name


def run_monkey(apk_path, output_dir, config_overrides, device, package,
               monkey_jar, throttle_ms, timeout_min, dry_run):
    """
    Run HybridMonkey via adb shell.
    Pushes the generated max.config, then runs:
      adb shell CLASSPATH=... app_process ... Monkey -p <pkg> --running-minutes N ...
    """
    os.makedirs(output_dir, exist_ok=True)

    # write per-condition config
    config_path = build_monkey_config(config_overrides)
    device_flag = ["-s", device] if device else []

    # push config
    push_cmd = ["adb"] + device_flag + ["push", config_path, "/sdcard/fastbot/max.config"]
    # push jar
    push_jar_cmd = ["adb"] + device_flag + ["push", monkey_jar, "/data/local/tmp/monkeyq.jar"]

    monkey_cmd = (
        ["adb"] + device_flag + ["shell",
        f"CLASSPATH=/data/local/tmp/monkeyq.jar:/data/local/tmp/fastbot-thirdpart.jar "
        f"app_process /data/local/tmp com.android.commands.monkey.Monkey "
        f"-p {package} "
        f"--running-minutes {timeout_min} "
        f"--throttle {throttle_ms} "
        f"-v -v"]
    )

    print(f"\n[MONKEY] config overrides: {config_overrides}")
    print(f"         output : {output_dir}")

    if dry_run:
        os.unlink(config_path)
        return True

    try:
        subprocess.run(push_cmd, check=True)
        subprocess.run(push_jar_cmd, check=True)
        result = subprocess.run(monkey_cmd, timeout=timeout_min * 60 + 120)

        # pull output from device
        pull_cmd = ["adb"] + device_flag + ["pull", "/sdcard/fastbot/", output_dir]
        subprocess.run(pull_cmd)

        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False
    finally:
        os.unlink(config_path)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _run_cmd(cmd, timeout_min, dry_run):
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Run llm-step ablation experiment")
    p.add_argument("--tool", choices=["droidbot", "monkey", "both"], default="droidbot")
    p.add_argument("--apk_dir", required=True)
    p.add_argument("--output_dir", required=True)
    p.add_argument("--device", default=None)
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--timeout", type=int, default=180, help="minutes")
    p.add_argument("--interval", type=int, default=1, help="droidbot event interval (s)")
    p.add_argument("--throttle", type=int, default=200, help="monkey throttle (ms)")
    p.add_argument("--apps", nargs="*", default=None)
    p.add_argument("--conditions", nargs="*", default=None,
                   help="Subset of condition labels to run")
    # monkey-specific
    p.add_argument("--monkey_jar", default=None, help="Path to monkeyq.jar")
    p.add_argument("--package", default=None, help="App package name (monkey only)")
    p.add_argument("--dry_run", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    apks = find_apks(args.apk_dir, args.apps)
    if not apks:
        print(f"No APKs found in {args.apk_dir}")
        sys.exit(1)

    conditions = FIXED_N_CONDITIONS
    if args.conditions:
        conditions = [c for c in FIXED_N_CONDITIONS if c[0] in args.conditions]

    tools = ["droidbot", "monkey"] if args.tool == "both" else [args.tool]

    print(f"Tools     : {tools}")
    print(f"Apps      : {[os.path.basename(a) for a in apks]}")
    print(f"Conditions: {[c[0] for c in conditions]}")
    print(f"Runs/cond : {args.runs}")
    print(f"Timeout   : {args.timeout} min")
    print(f"Total runs: {len(tools) * len(apks) * len(conditions) * args.runs}")

    manifest = []
    for tool in tools:
        for apk in apks:
            app_name = os.path.splitext(os.path.basename(apk))[0]
            for cond_label, db_extra_args, monkey_overrides in conditions:
                for run_idx in range(args.runs):
                    out_dir = os.path.join(
                        args.output_dir, tool, app_name, cond_label, f"run{run_idx:02d}")
                    label = f"{tool}/{app_name}/{cond_label}/run{run_idx:02d}"
                    print(f"\n[RUN] {label}")

                    if tool == "droidbot":
                        success = run_droidbot(
                            apk, out_dir, db_extra_args,
                            args.device, args.timeout, args.interval, args.dry_run)
                    else:
                        if not args.monkey_jar or not args.package:
                            print("[SKIP] --monkey_jar and --package required for monkey runs")
                            success = False
                        else:
                            success = run_monkey(
                                apk, out_dir, monkey_overrides,
                                args.device, args.package, args.monkey_jar,
                                args.throttle, args.timeout, args.dry_run)

                    manifest.append({
                        "tool": tool, "app": app_name, "condition": cond_label,
                        "run_idx": run_idx, "output_dir": out_dir,
                        "success": success,
                        "timestamp": datetime.datetime.now().isoformat(),
                    })

    manifest_path = os.path.join(args.output_dir, "manifest.json")
    os.makedirs(args.output_dir, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    n_ok = sum(1 for m in manifest if m["success"])
    print(f"\nManifest: {manifest_path}")
    print(f"Done: {n_ok}/{len(manifest)} succeeded")


if __name__ == "__main__":
    main()
