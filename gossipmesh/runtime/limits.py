"""Daily cost and volume limit enforcement (Task 15).
Tracks and enforces per-repository and per-organization daily ceilings for:
- AI execution runs
- Pull Request creations
- LLM Token consumption
- Estimated USD cost
- Changed lines of code
- Sandbox execution minutes
"""

import datetime
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


class LimitExceededError(Exception):
    """Raised when an operation exceeds daily organization or repository ceilings."""

    pass


@dataclass
class DailyQuotas:
    """Configurable daily quotas for an organization or repository."""

    max_runs: int = 50
    max_prs: int = 20
    max_tokens: int = 1_000_000
    max_cost_usd: float = 50.0
    max_changed_lines: int = 5_000
    max_sandbox_minutes: float = 120.0


@dataclass
class DailyUsageRecord:
    """Tracks cumulative usage consumed on a specific UTC day."""

    day: str  # YYYY-MM-DD
    runs: int = 0
    prs: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    changed_lines: int = 0
    sandbox_minutes: float = 0.0


class DailyVolumeLimiter:
    """Thread-safe manager for tracking and enforcing daily volume and cost quotas."""

    def __init__(self, default_quotas: Optional[DailyQuotas] = None):
        self.lock = threading.Lock()
        self.default_quotas = default_quotas or DailyQuotas()
        self.org_quotas: Dict[str, DailyQuotas] = {}
        self.repo_quotas: Dict[str, DailyQuotas] = {}

        # Key: "org:{org_id}:{YYYY-MM-DD}" or "repo:{repo_id}:{YYYY-MM-DD}"
        self._usage: Dict[str, DailyUsageRecord] = {}

    def _today(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    def _get_usage_record(self, prefix: str, entity_id: str) -> DailyUsageRecord:
        today = self._today()
        key = f"{prefix}:{entity_id}:{today}"
        if key not in self._usage:
            self._usage[key] = DailyUsageRecord(day=today)
        return self._usage[key]

    def set_org_quotas(self, org_id: str, quotas: DailyQuotas):
        with self.lock:
            self.org_quotas[org_id] = quotas

    def set_repo_quotas(self, repo_id: str, quotas: DailyQuotas):
        with self.lock:
            self.repo_quotas[repo_id] = quotas

    def check_limits(
        self,
        org_id: str,
        repo_id: Optional[str] = None,
        tokens_est: int = 0,
        cost_est: float = 0.0,
        lines_est: int = 0,
        sandbox_minutes_est: float = 0.0,
        is_pr: bool = False,
    ) -> Tuple[bool, str]:
        """Checks whether the requested operation can proceed within daily limits."""
        with self.lock:
            # Check org limits
            org_quota = self.org_quotas.get(org_id, self.default_quotas)
            org_usage = self._get_usage_record("org", org_id)

            if org_usage.runs + 1 > org_quota.max_runs:
                return False, f"Daily limit exceeded for org '{org_id}': max runs ({org_quota.max_runs}) reached."

            if is_pr and (org_usage.prs + 1 > org_quota.max_prs):
                return False, f"Daily limit exceeded for org '{org_id}': max PRs ({org_quota.max_prs}) reached."

            if org_usage.tokens + tokens_est > org_quota.max_tokens:
                return False, f"Daily limit exceeded for org '{org_id}': token quota ({org_quota.max_tokens}) reached."

            if org_usage.cost_usd + cost_est > org_quota.max_cost_usd:
                return (
                    False,
                    f"Daily limit exceeded for org '{org_id}': cost limit (${org_quota.max_cost_usd:.2f}) reached.",
                )

            if org_usage.changed_lines + lines_est > org_quota.max_changed_lines:
                return (
                    False,
                    f"Daily limit exceeded for org '{org_id}': changed lines limit ({org_quota.max_changed_lines}) reached.",
                )

            if org_usage.sandbox_minutes + sandbox_minutes_est > org_quota.max_sandbox_minutes:
                return (
                    False,
                    f"Daily limit exceeded for org '{org_id}': sandbox minutes limit ({org_quota.max_sandbox_minutes}m) reached.",
                )

            # Check repo limits if provided
            if repo_id:
                repo_quota = self.repo_quotas.get(repo_id, self.default_quotas)
                repo_usage = self._get_usage_record("repo", repo_id)

                if repo_usage.runs + 1 > repo_quota.max_runs:
                    return (
                        False,
                        f"Daily limit exceeded for repo '{repo_id}': max runs ({repo_quota.max_runs}) reached.",
                    )

                if is_pr and (repo_usage.prs + 1 > repo_quota.max_prs):
                    return False, f"Daily limit exceeded for repo '{repo_id}': max PRs ({repo_quota.max_prs}) reached."

                if repo_usage.tokens + tokens_est > repo_quota.max_tokens:
                    return (
                        False,
                        f"Daily limit exceeded for repo '{repo_id}': token quota ({repo_quota.max_tokens}) reached.",
                    )

                if repo_usage.cost_usd + cost_est > repo_quota.max_cost_usd:
                    return (
                        False,
                        f"Daily limit exceeded for repo '{repo_id}': cost limit (${repo_quota.max_cost_usd:.2f}) reached.",
                    )

                if repo_usage.changed_lines + lines_est > repo_quota.max_changed_lines:
                    return (
                        False,
                        f"Daily limit exceeded for repo '{repo_id}': changed lines limit ({repo_quota.max_changed_lines}) reached.",
                    )

                if repo_usage.sandbox_minutes + sandbox_minutes_est > repo_quota.max_sandbox_minutes:
                    return (
                        False,
                        f"Daily limit exceeded for repo '{repo_id}': sandbox minutes limit ({repo_quota.max_sandbox_minutes}m) reached.",
                    )

            return True, ""

    def record_usage(
        self,
        org_id: str,
        repo_id: Optional[str] = None,
        runs: int = 1,
        prs: int = 0,
        tokens: int = 0,
        cost_usd: float = 0.0,
        changed_lines: int = 0,
        sandbox_minutes: float = 0.0,
    ):
        """Records consumed resources against daily meters."""
        with self.lock:
            org_usage = self._get_usage_record("org", org_id)
            org_usage.runs += runs
            org_usage.prs += prs
            org_usage.tokens += tokens
            org_usage.cost_usd += cost_usd
            org_usage.changed_lines += changed_lines
            org_usage.sandbox_minutes += sandbox_minutes

            if repo_id:
                repo_usage = self._get_usage_record("repo", repo_id)
                repo_usage.runs += runs
                repo_usage.prs += prs
                repo_usage.tokens += tokens
                repo_usage.cost_usd += cost_usd
                repo_usage.changed_lines += changed_lines
                repo_usage.sandbox_minutes += sandbox_minutes

    def get_usage(self, org_id: str, repo_id: Optional[str] = None) -> Dict[str, dict]:
        """Returns current daily usage for org and optional repo."""
        with self.lock:
            org_rec = self._get_usage_record("org", org_id)
            res = {
                "organization": {
                    "day": org_rec.day,
                    "runs": org_rec.runs,
                    "prs": org_rec.prs,
                    "tokens": org_rec.tokens,
                    "cost_usd": org_rec.cost_usd,
                    "changed_lines": org_rec.changed_lines,
                    "sandbox_minutes": org_rec.sandbox_minutes,
                }
            }
            if repo_id:
                repo_rec = self._get_usage_record("repo", repo_id)
                res["repository"] = {
                    "day": repo_rec.day,
                    "runs": repo_rec.runs,
                    "prs": repo_rec.prs,
                    "tokens": repo_rec.tokens,
                    "cost_usd": repo_rec.cost_usd,
                    "changed_lines": repo_rec.changed_lines,
                    "sandbox_minutes": repo_rec.sandbox_minutes,
                }
            return res


# Global singleton instance
volume_limiter = DailyVolumeLimiter()
