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

    # ------------------------------------------------------------------
    # Public hooks called from InputPolicy.start()
    # ------------------------------------------------------------------

    def on_escape(self, step, current_state, tarpit_state_str, tarpit_structure_str, tarpit_name):
        """Called the first step AFTER a tarpit escape is confirmed.

        escape_type is determined by comparing view-tree structure hashes:
          functional → structure_str differs from tarpit (new layout = new screen)
          partial    → same structure_str (same layout, e.g. a dialog opened)

        Using structure_str (content-free) rather than activity so that
        single-Activity / Fragment-based apps are handled correctly.
        """
        if self._current_escape is not None:
            self._finalize_escape()

        escape_type = (
            "functional"
            if current_state.structure_str != tarpit_structure_str
            else "partial"
        )

        self._current_escape = {
            "step": step,
            "tarpit_name": tarpit_name,
            "tarpit_structure_str": tarpit_structure_str,
            "post_escape_activity": current_state.foreground_activity,
            "post_escape_structure_str": current_state.structure_str,
            "state_str": current_state.state_str,
            "escape_type": escape_type,
            "event_type_counts": collections.Counter(),
            "new_states_in_window": 0,
            "total_window_steps": 0,
        }
        self._steps_in_window = 0
        self.logger.info(
            f"[metrics] escape at step {step}: {escape_type} "
            f"(structure {'changed' if escape_type == 'functional' else 'unchanged'})"
        )

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

            if self._steps_in_window >= POST_ESCAPE_WINDOW:
                self._finalize_escape()

    def save(self):
        """Flush any open window and write JSON to output_dir."""
        if self._current_escape is not None:
            self._finalize_escape()

        functional = sum(1 for e in self.escape_events if e["escape_type"] == "functional")
        partial = sum(1 for e in self.escape_events if e["escape_type"] == "partial")
        mean_entropy = (
            sum(e["entropy"] for e in self.escape_events) / len(self.escape_events)
            if self.escape_events
            else 0.0
        )
        mean_new_states = (
            sum(e["new_states_in_window"] for e in self.escape_events) / len(self.escape_events)
            if self.escape_events
            else 0.0
        )

        result = {
            "config": self.config,
            "summary": {
                "total_escapes": len(self.escape_events),
                "functional_escapes": functional,
                "partial_escapes": partial,
                "rsi_rate": round(partial / len(self.escape_events), 4) if self.escape_events else 0.0,
                "mean_post_escape_entropy": round(mean_entropy, 4),
                "mean_new_states_in_window": round(mean_new_states, 4),
                "total_unique_states": len(self._seen_states),
            },
            "escape_events": self.escape_events,
        }

        path = os.path.join(self.output_dir, "llm_step_metrics.json")
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
        self.escape_events.append(ec)
        self._current_escape = None
        self._steps_in_window = 0
