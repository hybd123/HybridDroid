"""
Find Random Strategy Interference (RSI) candidate cases for manual annotation.

Scans Condition A output directories: looks for escape events where, within 5 steps
after escape, the app re-enters a state with perceptual similarity >= 0.90 to the
tarpit ref state. These are candidates where Condition B's extension might have helped.

Usage:
  python scripts/find_rsi_candidates.py \\
      --results_dir results/exp_tarpit_region/ \\
      --output rsi_candidates.json \\
      --sim_threshold 0.90 \\
      --lookback_steps 5
"""

import argparse
import json
import os
import cv2


def dhash(image, hash_size=8):
    resized = cv2.resize(image, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    diff = gray[:, 1:] > gray[:, :-1]
    return sum(2 ** i for i, v in enumerate(diff.flatten()) if v)


def similarity(path_a, path_b):
    img_a = cv2.imread(path_a)
    img_b = cv2.imread(path_b)
    if img_a is None or img_b is None:
        return 0.0
    h_a = dhash(img_a)
    h_b = dhash(img_b)
    return 1.0 - bin(h_a ^ h_b).count("1") / 64.0


def find_rsi_candidates(results_dir, sim_threshold=0.90, lookback_steps=5):
    candidates = []

    for app_name in sorted(os.listdir(results_dir)):
        app_dir = os.path.join(results_dir, app_name, "condition_A")
        if not os.path.isdir(app_dir):
            continue

        for run_name in sorted(os.listdir(app_dir)):
            run_dir = os.path.join(app_dir, run_name)
            metrics_path = os.path.join(run_dir, "tarpit_region_metrics.json")
            if not os.path.exists(metrics_path):
                continue

            with open(metrics_path) as f:
                metrics = json.load(f)

            all_states_dir = os.path.join(run_dir, "all_states")
            if not os.path.isdir(all_states_dir):
                continue

            # Build sorted list of screenshot files by step tag
            screens = {}
            for fname in os.listdir(all_states_dir):
                if fname.startswith("screen_") and (fname.endswith(".png") or fname.endswith(".jpg")):
                    try:
                        tag = int(fname.split("_")[1].split(".")[0])
                        screens[tag] = os.path.join(all_states_dir, fname)
                    except (IndexError, ValueError):
                        pass

            for escape in metrics.get("escape_events", []):
                escaped_step = escape["step"]
                tarpit_name = escape.get("tarpit_name")

                # find the continuation log for ref screenshot
                cont_log = os.path.join(run_dir, "continuation_log.jsonl")
                ref_screenshot = None
                if os.path.exists(cont_log):
                    with open(cont_log) as f:
                        for line in f:
                            rec = json.loads(line)
                            if rec.get("tarpit_escaped_at") == escaped_step:
                                ref_screenshot = rec.get("ref_screenshot")
                                break

                if ref_screenshot is None or not os.path.exists(ref_screenshot):
                    continue

                # check the lookback_steps steps after escape
                is_candidate = False
                for step_offset in range(1, lookback_steps + 1):
                    check_step = escaped_step + step_offset
                    screen = screens.get(check_step)
                    if screen is None:
                        continue
                    sim = similarity(screen, ref_screenshot)
                    if sim >= sim_threshold:
                        is_candidate = True
                        break

                if is_candidate:
                    candidates.append({
                        "app": app_name,
                        "run": run_name,
                        "escaped_step": escaped_step,
                        "tarpit_name": tarpit_name,
                        "ref_screenshot": ref_screenshot,
                        "sim_threshold": sim_threshold,
                        "human_verified": None,  # to be filled in manually
                    })

    return candidates


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--results_dir", required=True)
    p.add_argument("--output", default="rsi_candidates.json")
    p.add_argument("--sim_threshold", type=float, default=0.90)
    p.add_argument("--lookback_steps", type=int, default=5)
    return p.parse_args()


def main():
    args = parse_args()
    candidates = find_rsi_candidates(
        args.results_dir, args.sim_threshold, args.lookback_steps)
    with open(args.output, "w") as f:
        json.dump(candidates, f, indent=2)
    print(f"Found {len(candidates)} RSI candidates → {args.output}")


if __name__ == "__main__":
    main()
