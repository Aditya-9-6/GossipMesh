import logging

from sqlalchemy.orm import Session

from gossipmesh.models.runtime import Budget

logger = logging.getLogger(__name__)

class BudgetManager:
    def __init__(self, db: Session):
        self.db = db

    def check_budget(self, organization_id: int) -> bool:
        """Returns True if the organization is within its monthly budget."""
        budget = self.db.query(Budget).filter(Budget.organization_id == organization_id).first()
        if not budget:
            logger.warning(f"No budget found for org {organization_id}. Creating default.")
            budget = Budget(organization_id=organization_id)
            self.db.add(budget)
            self.db.commit()

        return budget.current_spend_usd < budget.monthly_limit_usd

    def record_spend(self, organization_id: int, amount_usd: float):
        """Records spend against the organization's budget."""
        budget = self.db.query(Budget).filter(Budget.organization_id == organization_id).first()
        if budget:
            budget.current_spend_usd += amount_usd
            self.db.commit()
        else:
            logger.error(f"Cannot record spend, no budget exists for org {organization_id}")
