"""
Unit tests for GossipMesh Automation Outcome Report (Task 16).
"""

import datetime
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    import pytest

    fixture = pytest.fixture
except ImportError:
    pytest = None

    def fixture(fn):
        return fn


from gossipmesh.enterprise.outcome_report import (
    AutomationEvent,
    AutomationEventType,
    AutomationOutcomeReport,
    AutomationOutcomeReporter,
)


@fixture
def temp_reporter():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_file = Path(tmpdir) / "test_events.jsonl"
        reporter = AutomationOutcomeReporter(storage_path=storage_file)
        yield reporter, storage_file


def test_record_and_load_events(temp_reporter):
    reporter, storage_file = temp_reporter
    now = datetime.datetime.now(datetime.timezone.utc)

    ev1 = AutomationEvent(
        event_type=AutomationEventType.ISSUE_PROCESSED,
        repo="Aditya-9-6/GossipMesh",
        issue_number=101,
        tenant_id=1,
        latency_seconds=1.5,
        cost_usd=0.002,
    )
    ev2 = AutomationEvent(
        event_type=AutomationEventType.PR_CREATED,
        repo="Aditya-9-6/GossipMesh",
        pr_number=102,
        tenant_id=1,
        latency_seconds=3.2,
        cost_usd=0.015,
    )

    reporter.record_event(ev1)
    reporter.record_event(ev2)

    assert storage_file.exists()
    loaded = reporter.load_events()
    assert len(loaded) == 2
    assert loaded[0].event_type == AutomationEventType.ISSUE_PROCESSED
    assert loaded[1].event_type == AutomationEventType.PR_CREATED


def test_metrics_aggregation(temp_reporter):
    reporter, _ = temp_reporter
    now = datetime.datetime.now(datetime.timezone.utc)

    # 2 issues processed
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.ISSUE_PROCESSED, repo="test/repo"))
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.ISSUE_PROCESSED, repo="test/repo"))

    # 2 PRs created, 1 merged, 1 rejected
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.PR_CREATED, repo="test/repo"))
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.PR_CREATED, repo="test/repo"))
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.PR_MERGED, repo="test/repo"))
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.PR_REJECTED, repo="test/repo"))

    # 4 CI runs: 3 passed, 1 failed (75% pass rate)
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.CI_RUN, repo="test/repo", ci_passed=True))
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.CI_RUN, repo="test/repo", ci_passed=True))
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.CI_RUN, repo="test/repo", ci_passed=True))
    reporter.record_event(AutomationEvent(event_type=AutomationEventType.CI_RUN, repo="test/repo", ci_passed=False))

    # 2 Reviews: scores 90 and 100 (avg 95), 1 false positive (50% FP rate)
    reporter.record_event(
        AutomationEvent(
            event_type=AutomationEventType.REVIEW_COMPLETED,
            repo="test/repo",
            review_score=90.0,
            is_false_positive=False,
            latency_seconds=10.0,
            cost_usd=0.01,
        )
    )
    reporter.record_event(
        AutomationEvent(
            event_type=AutomationEventType.REVIEW_COMPLETED,
            repo="test/repo",
            review_score=100.0,
            is_false_positive=True,
            latency_seconds=20.0,
            cost_usd=0.02,
        )
    )

    report = reporter.get_daily_report()

    assert report.issues_processed == 2
    assert report.prs_created == 2
    assert report.prs_merged == 1
    assert report.prs_rejected == 1
    assert report.approval_rate == 50.0
    assert report.ci_total_runs == 4
    assert report.ci_passed_runs == 3
    assert report.ci_pass_rate == 75.0
    assert report.avg_review_score == 95.0
    assert report.false_positives_count == 1
    assert report.false_positive_rate == 50.0
    assert report.total_cost_usd == 0.03
    assert report.avg_latency_seconds == 15.0
    assert report.p95_latency_seconds == 20.0

    # Test markdown export
    md = report.to_markdown()
    assert "GossipMesh Automation Outcome Report" in md
    assert "75.0%" in md
    assert "50.0%" in md
    assert "$0.0300" in md


def test_tenant_isolation(temp_reporter):
    reporter, _ = temp_reporter

    reporter.record_event(
        AutomationEvent(
            event_type=AutomationEventType.ISSUE_PROCESSED,
            repo="tenant1/repo",
            tenant_id=1,
        )
    )
    reporter.record_event(
        AutomationEvent(
            event_type=AutomationEventType.ISSUE_PROCESSED,
            repo="tenant2/repo",
            tenant_id=2,
        )
    )

    t1_events = reporter.load_events(tenant_id=1)
    assert len(t1_events) == 1
    assert t1_events[0].tenant_id == 1

    t2_events = reporter.load_events(tenant_id=2)
    assert len(t2_events) == 1
    assert t2_events[0].tenant_id == 2


def test_weekly_report(temp_reporter):
    reporter, _ = temp_reporter
    now = datetime.datetime.now(datetime.timezone.utc)
    three_days_ago = now - datetime.timedelta(days=3)

    reporter.record_event(
        AutomationEvent(
            event_type=AutomationEventType.PR_MERGED,
            repo="test/repo",
            timestamp=three_days_ago.isoformat(),
        )
    )

    report = reporter.get_weekly_report()
    assert report.prs_merged == 1
    assert report.period == "weekly"


if __name__ == "__main__":
    print("[*] Running test_record_and_load_events...")
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "test.jsonl"
        rep = AutomationOutcomeReporter(storage_path=sf)
        test_record_and_load_events((rep, sf))
    print("[OK] test_record_and_load_events passed.")

    print("[*] Running test_metrics_aggregation...")
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "test.jsonl"
        rep = AutomationOutcomeReporter(storage_path=sf)
        test_metrics_aggregation((rep, sf))
    print("[OK] test_metrics_aggregation passed.")

    print("[*] Running test_tenant_isolation...")
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "test.jsonl"
        rep = AutomationOutcomeReporter(storage_path=sf)
        test_tenant_isolation((rep, sf))
    print("[OK] test_tenant_isolation passed.")

    print("[*] Running test_weekly_report...")
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "test.jsonl"
        rep = AutomationOutcomeReporter(storage_path=sf)
        test_weekly_report((rep, sf))
    print("[OK] test_weekly_report passed.")

    print("\n[SUCCESS] ALL OUTCOME REPORT TESTS PASSED 100%!")
