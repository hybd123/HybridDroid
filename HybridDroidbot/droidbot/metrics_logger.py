import collections
import json
import logging
import math
import os


POST_ESCAPE_WINDOW = 20  # steps to observe after each escape


class MetricsLogger:
    def __init__(self, output_dir, config):
        self.output_dir = output_dir
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        self.escape_events = []
        self._seen_states = set()

        # state for the currently-open escape window
        self._current_escape = None
        self._steps_in_window = 0
        self._window_phashes = set()

    # ------------------------------------------------------------------
    # Public hooks called from InputPolicy.start()
    # ------------------------------------------------------------------

    def on_escape(self, step, current_state, tarpit_name):
        """Called when control is truly handed back to random (after any Condition-B extension).

        The diversity window starts here, aligned for both conditions A and B.
        """
        if self._current_escape is not None:
            self._finalize_escape()

        self._current_escape = {
            "step": step,
            "tarpit_name": tarpit_name,
            "post_escape_activity": current_state.foreground_activity,
            "post_escape_structure_str": current_state.structure_str,
            "state_str": current_state.state_str,
            "event_type_counts": collections.Counter(),
            "new_states_in_window": 0,
            "unique_phashes_in_window": 0,
            "total_window_steps": 0,
            # filled in by on_continuation_complete (Condition B only)
            "continuation_steps": None,
            "continuation_stop_reason": None,
        }
        self._steps_in_window = 0
        self._window_phashes = set()
        self.logger.info(f"[metrics] escape at step {step} from tarpit {tarpit_name}")

    def on_continuation_complete(self, continuation_steps, stop_reason):
        """Called by _extend_until_exit_region when Condition B finishes."""
        if self._current_escape is None:
            return
        self._current_escape["continuation_steps"] = continuation_steps
        self._current_escape["continuation_stop_reason"] = stop_reason

    def on_event(self, event, current_state, step):
        """Called after every event (except the very first two startup events)."""
        is_new = current_state.state_str not in self._seen_states
        self._seen_states.add(current_state.state_str)

        if self._current_escape is None:
            return

        if self._steps_in_window < POST_ESCAPE_WINDOW:
            self._current_escape["event_type_counts"][event.get_event_name()] += 1
            if is_new:
                self._current_escape["new_states_in_window"] += 1
            self._current_escape["total_window_steps"] += 1
            self._steps_in_window += 1

            # track perceptual hash diversity
            screenshot = current_state.get_state_screen()
            if screenshot:
                phash = self._compute_phash(screenshot)
                if phash is not None:
                    self._window_phashes.add(phash)

            if self._steps_in_window >= POST_ESCAPE_WINDOW:
                self._finalize_escape()

    def save(self):
        """Flush any open window and write JSON to output_dir."""
        if self._current_escape is not None:
            self._finalize_escape()

        total = len(self.escape_events)
        mean_entropy = (
            sum(e["entropy"] for e in self.escape_events) / total
            if total else 0.0
        )
        mean_new_states = (
            sum(e["new_states_in_window"] for e in self.escape_events) / total
            if total else 0.0
        )
        mean_phash_diversity = (
            sum(e["unique_phashes_in_window"] for e in self.escape_events) / total
            if total else 0.0
        )
        c_max_hits = sum(
            1 for e in self.escape_events
            if e.get("continuation_stop_reason") == "c_max_reached"
        )

        result = {
            "config": self.config,
            "summary": {
                "total_escapes": total,
                "mean_post_escape_entropy": round(mean_entropy, 4),
                "mean_new_states_in_window": round(mean_new_states, 4),
                "mean_unique_phashes_in_window": round(mean_phash_diversity, 4),
                "c_max_reached_count": c_max_hits,
                "c_max_reached_rate": round(c_max_hits / total, 4) if total else 0.0,
                "total_unique_states": len(self._seen_states),
            },
            "escape_events": self.escape_events,
        }

        path = os.path.join(self.output_dir, "tarpit_region_metrics.json")
        with open(path, "w") as f:
            json.dump(result, f, indent=2)
        self.logger.info(f"[metrics] saved to {path}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _finalize_escape(self):
        ec = self._current_escape
        counts = list(ec["event_type_counts"].values())
        total = sum(counts)
        if total > 0:
            entropy = -sum((c / total) * math.log2(c / total) for c in counts if c > 0)
        else:
            entropy = 0.0
        ec["entropy"] = round(entropy, 4)
        ec["event_type_counts"] = dict(ec["event_type_counts"])
        ec["unique_phashes_in_window"] = len(self._window_phashes)
        self.escape_events.append(ec)
        self._current_escape = None
        self._steps_in_window = 0
        self._window_phashes = set()

    @staticmethod
    def _compute_phash(screenshot_path):
        try:
            import cv2
            img = cv2.imread(screenshot_path)
            if img is None:
                return None
            hash_size = 8
            resized = cv2.resize(img, (hash_size + 1, hash_size),
                                 interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            diff = gray[:, 1:] > gray[:, :-1]
            return sum(2 ** i for i, v in enumerate(diff.flatten()) if v)
        except Exception:
            return None
