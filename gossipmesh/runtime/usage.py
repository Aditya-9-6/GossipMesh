from datetime import date
from sqlalchemy.orm import Session
from gossipmesh.models.runtime import UsageLimit, DailyUsage
from gossipmesh.core.exceptions import UsageLimitError
import logging

logger = logging.getLogger(__name__)

class UsageManager:
    def __init__(self, db: Session):
        self.db = db

    def check_and_record_usage(
        self,
        organization_id: int,
        repository_id: int | None = None,
        ai_runs: int = 0,
        prs_created: int = 0,
        tokens_used: int = 0,
        estimated_cost_usd: float = 0.0,
        changed_lines: int = 0,
        sandbox_minutes: int = 0,
        commit: bool = True
    ):
        try:
            today = date.today()

            # 1. Fetch current usage for the specific scope (repo or org)
            usage = self.db.query(DailyUsage).filter(
                DailyUsage.organization_id == organization_id,
                DailyUsage.repository_id == repository_id,
                DailyUsage.date == today
            ).with_for_update().first()

            if not usage:
                usage = DailyUsage(
                    organization_id=organization_id,
                    repository_id=repository_id,
                    date=today
                )
                self.db.add(usage)

            # If checking repo level, also check org level
            org_usage = None
            if repository_id is not None:
                org_usage = self.db.query(DailyUsage).filter(
                    DailyUsage.organization_id == organization_id,
                    DailyUsage.repository_id.is_(None),
                    DailyUsage.date == today
                ).with_for_update().first()
                if not org_usage:
                    org_usage = DailyUsage(
                        organization_id=organization_id,
                        repository_id=None,
                        date=today
                    )
                    self.db.add(org_usage)

            # 2. Fetch limits (most specific first: repo then org)
            limits = []
            if repository_id is not None:
                repo_limit = self.db.query(UsageLimit).filter(
                    UsageLimit.organization_id == organization_id,
                    UsageLimit.repository_id == repository_id
                ).first()
                if repo_limit:
                    limits.append(repo_limit)

            org_limit = self.db.query(UsageLimit).filter(
                UsageLimit.organization_id == organization_id,
                UsageLimit.repository_id.is_(None)
            ).first()
            if org_limit:
                limits.append(org_limit)

            # 3. Apply checks
            new_ai_runs = usage.ai_runs + ai_runs
            new_prs_created = usage.prs_created + prs_created
            new_tokens_used = usage.tokens_used + tokens_used
            new_estimated_cost_usd = usage.estimated_cost_usd + estimated_cost_usd
            new_changed_lines = usage.changed_lines + changed_lines
            new_sandbox_minutes = usage.sandbox_minutes + sandbox_minutes

            for limit in limits:
                check_ai = new_ai_runs
                check_prs = new_prs_created
                check_tokens = new_tokens_used
                check_cost = new_estimated_cost_usd
                check_lines = new_changed_lines
                check_minutes = new_sandbox_minutes

                # If checking an org-level limit from a repo-level request, we must add current org usage + the delta
                if limit.repository_id is None and repository_id is not None:
                    check_ai = org_usage.ai_runs + ai_runs
                    check_prs = org_usage.prs_created + prs_created
                    check_tokens = org_usage.tokens_used + tokens_used
                    check_cost = org_usage.estimated_cost_usd + estimated_cost_usd
                    check_lines = org_usage.changed_lines + changed_lines
                    check_minutes = org_usage.sandbox_minutes + sandbox_minutes

                if limit.daily_ai_runs is not None and check_ai > limit.daily_ai_runs:
                    raise UsageLimitError("Daily AI runs limit exceeded")
                if limit.daily_prs_created is not None and check_prs > limit.daily_prs_created:
                    raise UsageLimitError("Daily PR creation limit exceeded")
                if limit.daily_tokens_used is not None and check_tokens > limit.daily_tokens_used:
                    raise UsageLimitError("Daily tokens limit exceeded")
                if limit.daily_estimated_cost_usd is not None and check_cost > limit.daily_estimated_cost_usd:
                    raise UsageLimitError("Daily cost limit exceeded")
                if limit.daily_changed_lines is not None and check_lines > limit.daily_changed_lines:
                    raise UsageLimitError("Daily changed lines limit exceeded")
                if limit.daily_sandbox_minutes is not None and check_minutes > limit.daily_sandbox_minutes:
                    raise UsageLimitError("Daily sandbox minutes limit exceeded")

            # 4. Update usage
            usage.ai_runs = new_ai_runs
            usage.prs_created = new_prs_created
            usage.tokens_used = new_tokens_used
            usage.estimated_cost_usd = new_estimated_cost_usd
            usage.changed_lines = new_changed_lines
            usage.sandbox_minutes = new_sandbox_minutes

            if org_usage:
                org_usage.ai_runs += ai_runs
                org_usage.prs_created += prs_created
                org_usage.tokens_used += tokens_used
                org_usage.estimated_cost_usd += estimated_cost_usd
                org_usage.changed_lines += changed_lines
                org_usage.sandbox_minutes += sandbox_minutes

            if commit:
                self.db.commit()
            else:
                self.db.flush()

            return usage

        except UsageLimitError:
            self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Error checking usage limits: {e}")
            self.db.rollback()
            raise
