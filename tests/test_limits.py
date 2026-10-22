import pytest
from gossipmesh.runtime.limits import DailyVolumeLimiter, DailyQuotas


def test_daily_volume_limiter_defaults():
    limiter = DailyVolumeLimiter()
    can_run, _ = limiter.check_limits(org_id="acme-corp")
    assert can_run is True


def test_daily_volume_limiter_run_quota():
    quotas = DailyQuotas(max_runs=2)
    limiter = DailyVolumeLimiter(default_quotas=quotas)

    # 1st run
    ok, _ = limiter.check_limits(org_id="acme")
    assert ok is True
    limiter.record_usage(org_id="acme", runs=1)

    # 2nd run
    ok, _ = limiter.check_limits(org_id="acme")
    assert ok is True
    limiter.record_usage(org_id="acme", runs=1)

    # 3rd run should be blocked
    ok, reason = limiter.check_limits(org_id="acme")
    assert ok is False
    assert "max runs (2) reached" in reason


def test_daily_volume_limiter_pr_quota():
    quotas = DailyQuotas(max_prs=1)
    limiter = DailyVolumeLimiter(default_quotas=quotas)

    # PR 1
    ok, _ = limiter.check_limits(org_id="acme", is_pr=True)
    assert ok is True
    limiter.record_usage(org_id="acme", prs=1)

    # PR 2 blocked
    ok, reason = limiter.check_limits(org_id="acme", is_pr=True)
    assert ok is False
    assert "max PRs (1) reached" in reason


def test_daily_volume_limiter_token_and_cost_ceilings():
    quotas = DailyQuotas(max_tokens=1000, max_cost_usd=5.0)
    limiter = DailyVolumeLimiter(default_quotas=quotas)

    # Tokens check
    ok, reason = limiter.check_limits(org_id="acme", tokens_est=1500)
    assert ok is False
    assert "token quota" in reason

    # Cost check
    ok, reason = limiter.check_limits(org_id="acme", cost_est=10.0)
    assert ok is False
    assert "cost limit" in reason


def test_daily_volume_limiter_repo_specific_override():
    limiter = DailyVolumeLimiter()
    limiter.set_repo_quotas("repo-strict", DailyQuotas(max_runs=1))

    # General repo is fine
    ok, _ = limiter.check_limits(org_id="org1", repo_id="repo-normal")
    assert ok is True

    # Strict repo
    limiter.record_usage(org_id="org1", repo_id="repo-strict", runs=1)
    ok, reason = limiter.check_limits(org_id="org1", repo_id="repo-strict")
    assert ok is False
    assert "repo 'repo-strict': max runs (1) reached" in reason
