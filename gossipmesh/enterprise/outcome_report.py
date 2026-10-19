"""
GossipMesh Automation Outcome Report & Metrics Engine
======================================================
Milestone Implementation for Phase 0 Task 16.

Persists daily and weekly metrics:
- Issues processed
- PRs created
- CI pass rate
- Merged, rejected, and reverted PRs
- Review scores
- False positives
- Cost & latency
- Approval rate

Exposes metrics through CLI and FastAPI endpoints.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class AutomationEventType:
    ISSUE_PROCESSED = "issue_processed"
    PR_CREATED = "pr_created"
    CI_RUN = "ci_run"
    PR_MERGED = "pr_merged"
    PR_REJECTED = "pr_rejected"
    PR_REVERTED = "pr_reverted"
    REVIEW_COMPLETED = "review_completed"


@dataclass
class AutomationEvent:
    event_type: str
    repo: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    tenant_id: Optional[int] = None
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None
    review_score: Optional[float] = None
    ci_passed: Optional[bool] = None
    is_false_positive: bool = False
    latency_seconds: float = 0.0
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AutomationEvent:
        return cls(**data)


@dataclass
class AutomationOutcomeReport:
    period: str
    start_time: str
    end_time: str
    issues_processed: int = 0
    prs_created: int = 0
    prs_merged: int = 0
    prs_rejected: int = 0
    prs_reverted: int = 0
    ci_total_runs: int = 0
    ci_passed_runs: int = 0
    ci_pass_rate: float = 0.0
    avg_review_score: float = 0.0
    false_positives_count: int = 0
    false_positive_rate: float = 0.0
    approval_rate: float = 0.0
    total_cost_usd: float = 0.0
    avg_latency_seconds: float = 0.0
    p95_latency_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        return f"""# 📊 GossipMesh Automation Outcome Report ({self.period.capitalize()})
**Period**: `{self.start_time}` to `{self.end_time}`

### 🚀 Velocity & Triage
- **Issues Processed**: {self.issues_processed}
- **PRs Created**: {self.prs_created}
- **PRs Merged**: {self.prs_merged}
- **PRs Rejected**: {self.prs_rejected}
- **PRs Reverted**: {self.prs_reverted}
- **Approval Rate**: {self.approval_rate:.1f}%

### 🛡️ Quality & Verification
- **CI Total Runs**: {self.ci_total_runs}
- **CI Pass Rate**: {self.ci_pass_rate:.1f}% ({self.ci_passed_runs}/{self.ci_total_runs} passed)
- **Average Review Score**: {self.avg_review_score:.1f}/100
- **False Positives Detected**: {self.false_positives_count}
- **False Positive Rate**: {self.false_positive_rate:.1f}%

### 💰 Cost & Efficiency
- **Total Automation Cost**: ${self.total_cost_usd:.4f}
- **Average Latency**: {self.avg_latency_seconds:.2f}s
- **P95 Latency**: {self.p95_latency_seconds:.2f}s
"""


class AutomationOutcomeReporter:
    """
    Persists and aggregates operational automation telemetry into actionable
    daily and weekly reports.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            default_dir = Path.home() / ".gossipmesh" / "metrics"
            default_dir.mkdir(parents=True, exist_ok=True)
            self.storage_path = default_dir / "automation_events.jsonl"
        else:
            self.storage_path = Path(storage_path)
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def record_event(self, event: AutomationEvent) -> None:
        """Appends an event to the durable JSONL log."""
        line = json.dumps(event.to_dict()) + "\n"
        with open(self.storage_path, "a", encoding="utf-8") as f:
            f.write(line)

    def load_events(
        self,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        tenant_id: Optional[int] = None,
        repo: Optional[str] = None,
    ) -> List[AutomationEvent]:
        """Loads and filters events within a specified window and scope."""
        if not self.storage_path.exists():
            return []

        events: List[AutomationEvent] = []
        with open(self.storage_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    ev = AutomationEvent.from_dict(data)
                except Exception:
                    continue

                ev_time = datetime.datetime.fromisoformat(ev.timestamp)
                if ev_time.tzinfo is None:
                    ev_time = ev_time.replace(tzinfo=datetime.timezone.utc)

                if start_time:
                    st = start_time if start_time.tzinfo else start_time.replace(tzinfo=datetime.timezone.utc)
                    if ev_time < st:
                        continue
                if end_time:
                    et = end_time if end_time.tzinfo else end_time.replace(tzinfo=datetime.timezone.utc)
                    if ev_time > et:
                        continue
                if tenant_id is not None and ev.tenant_id != tenant_id:
                    continue
                if repo is not None and ev.repo != repo:
                    continue

                events.append(ev)

        return events

    def generate_report(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        period: str = "custom",
        tenant_id: Optional[int] = None,
        repo: Optional[str] = None,
    ) -> AutomationOutcomeReport:
        """Aggregates metrics for the given period."""
        events = self.load_events(start_time=start_time, end_time=end_time, tenant_id=tenant_id, repo=repo)

        issues_processed = 0
        prs_created = 0
        prs_merged = 0
        prs_rejected = 0
        prs_reverted = 0
        ci_total_runs = 0
        ci_passed_runs = 0
        review_scores: List[float] = []
        false_positives = 0
        total_cost = 0.0
        latencies: List[float] = []

        for ev in events:
            total_cost += ev.cost_usd
            if ev.latency_seconds > 0:
                latencies.append(ev.latency_seconds)

            if ev.event_type == AutomationEventType.ISSUE_PROCESSED:
                issues_processed += 1
            elif ev.event_type == AutomationEventType.PR_CREATED:
                prs_created += 1
            elif ev.event_type == AutomationEventType.PR_MERGED:
                prs_merged += 1
            elif ev.event_type == AutomationEventType.PR_REJECTED:
                prs_rejected += 1
            elif ev.event_type == AutomationEventType.PR_REVERTED:
                prs_reverted += 1
            elif ev.event_type == AutomationEventType.CI_RUN:
                ci_total_runs += 1
                if ev.ci_passed:
                    ci_passed_runs += 1
            elif ev.event_type == AutomationEventType.REVIEW_COMPLETED:
                if ev.review_score is not None:
                    review_scores.append(ev.review_score)
                if ev.is_false_positive:
                    false_positives += 1

        ci_pass_rate = (ci_passed_runs / ci_total_runs * 100.0) if ci_total_runs > 0 else 100.0
        avg_score = (sum(review_scores) / len(review_scores)) if review_scores else 0.0
        decided_prs = prs_merged + prs_rejected + prs_reverted
        approval_rate = (prs_merged / decided_prs * 100.0) if decided_prs > 0 else 100.0
        total_reviews = len(review_scores)
        fp_rate = (false_positives / total_reviews * 100.0) if total_reviews > 0 else 0.0

        avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
        p95_latency = 0.0
        if latencies:
            sorted_lat = sorted(latencies)
            idx = int(math.ceil(0.95 * len(sorted_lat))) - 1
            p95_latency = sorted_lat[max(0, idx)]

        return AutomationOutcomeReport(
            period=period,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            issues_processed=issues_processed,
            prs_created=prs_created,
            prs_merged=prs_merged,
            prs_rejected=prs_rejected,
            prs_reverted=prs_reverted,
            ci_total_runs=ci_total_runs,
            ci_passed_runs=ci_passed_runs,
            ci_pass_rate=round(ci_pass_rate, 2),
            avg_review_score=round(avg_score, 2),
            false_positives_count=false_positives,
            false_positive_rate=round(fp_rate, 2),
            approval_rate=round(approval_rate, 2),
            total_cost_usd=round(total_cost, 4),
            avg_latency_seconds=round(avg_latency, 2),
            p95_latency_seconds=round(p95_latency, 2),
        )

    def get_daily_report(
        self,
        target_date: Optional[datetime.date] = None,
        tenant_id: Optional[int] = None,
        repo: Optional[str] = None,
    ) -> AutomationOutcomeReport:
        """Generates report for a 24-hour day window."""
        day = target_date or datetime.datetime.now(datetime.timezone.utc).date()
        start = datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.timezone.utc)
        end = datetime.datetime.combine(day, datetime.time.max, tzinfo=datetime.timezone.utc)
        return self.generate_report(start_time=start, end_time=end, period="daily", tenant_id=tenant_id, repo=repo)

    def get_weekly_report(
        self,
        end_date: Optional[datetime.date] = None,
        tenant_id: Optional[int] = None,
        repo: Optional[str] = None,
    ) -> AutomationOutcomeReport:
        """Generates report for the 7-day window ending on end_date."""
        ed = end_date or datetime.datetime.now(datetime.timezone.utc).date()
        start_day = ed - datetime.timedelta(days=7)
        start = datetime.datetime.combine(start_day, datetime.time.min, tzinfo=datetime.timezone.utc)
        end = datetime.datetime.combine(ed, datetime.time.max, tzinfo=datetime.timezone.utc)
        return self.generate_report(start_time=start, end_time=end, period="weekly", tenant_id=tenant_id, repo=repo)


def main():
    parser = argparse.ArgumentParser(description="GossipMesh Automation Outcome Report CLI")
    parser.add_argument("--period", choices=["daily", "weekly"], default="daily", help="Report time window")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--storage-path", type=str, default=None, help="Custom metrics storage JSONL path")
    args = parser.parse_args()

    reporter = AutomationOutcomeReporter(storage_path=Path(args.storage_path) if args.storage_path else None)
    if args.period == "daily":
        report = reporter.get_daily_report()
    else:
        report = reporter.get_weekly_report()

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.to_markdown())


if __name__ == "__main__":
    main()
