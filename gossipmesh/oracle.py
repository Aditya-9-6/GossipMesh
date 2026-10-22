"""
Empirical Performance & Zero-Allocation Regression Oracle.
Tracks time-series benchmark metrics and vetoes regressions on hot paths.
"""

import time
from typing import Dict, List, Optional, Tuple, Any

class BenchmarkRecord:
    def __init__(self, metric_name: str, ns_per_op: float, bytes_per_op: int, allocs_per_op: int, commit: str = ""):
        self.metric_name = metric_name
        self.ns_per_op = ns_per_op
        self.bytes_per_op = bytes_per_op
        self.allocs_per_op = allocs_per_op
        self.commit = commit
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "ns_per_op": self.ns_per_op,
            "bytes_per_op": self.bytes_per_op,
            "allocs_per_op": self.allocs_per_op,
            "commit": self.commit,
            "timestamp": self.timestamp,
        }

class PerformanceOracle:
    """Monitors telemetry and vetoes PRs that introduce memory regressions."""
    def __init__(self):
        self.history: Dict[str, List[BenchmarkRecord]] = {}

    def record(self, metric_name: str, ns_per_op: float, bytes_per_op: int, allocs_per_op: int, commit: str = "") -> BenchmarkRecord:
        rec = BenchmarkRecord(metric_name, ns_per_op, bytes_per_op, allocs_per_op, commit)
        if metric_name not in self.history:
            self.history[metric_name] = []
        self.history[metric_name].append(rec)
        return rec

    def evaluate_regression(self, metric_name: str, current_allocs: int, current_bytes: int) -> Tuple[bool, str]:
        """
        Enforces Zero-Allocation Invariants:
        Returns (is_regressed: bool, explanation: str).
        """
        # Hard hot-path zero-allocation invariant
        if current_allocs > 0:
            return True, f"VETO: Hot-path allocation regression ({current_allocs} allocs/op, {current_bytes} B/op). Strict zero-allocation required."

        if metric_name in self.history and self.history[metric_name]:
            baseline = self.history[metric_name][-1]
            if current_bytes > baseline.bytes_per_op:
                delta = current_bytes - baseline.bytes_per_op
                return True, f"VETO: Memory regression detected (+{delta} B/op relative to baseline {baseline.bytes_per_op} B/op)."

        return False, "PASSED: Invariants satisfied. Zero-allocation verified."
