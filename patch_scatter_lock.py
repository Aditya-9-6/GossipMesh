with open("gossipmesh/p2p/scatter.py", "r") as f:
    data = f.read()

data = data.replace(
"""    def get_scatter(self) -> int:
        \"\"\"Returns the current adapted scatter-width.\"\"\"
        with self._lock:
            return max(self.min_scatter, round(self._current_scatter))""",
"""    def get_scatter(self) -> int:
        \"\"\"Returns the current adapted scatter-width.\"\"\"
        return max(self.min_scatter, round(self._current_scatter))"""
)

data = data.replace(
"""    def get_metrics(self) -> dict:
        \"\"\"Returns telemetry information for monitoring.\"\"\"
        with self._lock:
            return {
                "smoothed_cpu": self._smoothed_cpu,
                "smoothed_mem": self._smoothed_mem,
                "current_scatter": self.get_scatter(),
                "base_scatter": self.base_scatter,
            }""",
"""    def get_metrics(self) -> dict:
        \"\"\"Returns telemetry information for monitoring.\"\"\"
        return {
            "smoothed_cpu": self._smoothed_cpu,
            "smoothed_mem": self._smoothed_mem,
            "current_scatter": self.get_scatter(),
            "base_scatter": self.base_scatter,
        }"""
)

with open("gossipmesh/p2p/scatter.py", "w") as f:
    f.write(data)
