from sqlalchemy import DateTime, Integer, event
from sqlalchemy.orm import Mapped, mapped_column, Session, with_loader_criteria
from sqlalchemy.sql import func
from datetime import datetime
from gossipmesh.models.audit import AuditEvent
from gossipmesh.models.base import Base


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def soft_delete(self, session: Session, actor_id: int | None = None, retention_days: int | None = None):
        """
        Safely mark the record as deleted instead of physically removing it.
        Generates an audit record for the deletion.
        """
        self.deleted_at = func.now()
        self.deleted_by = actor_id
        if retention_days is not None:
            self.retention_days = retention_days

        # Determine organization_id
        if hasattr(self, "organization_id"):
            org_id = self.organization_id
        elif self.__class__.__name__ == "Organization":
            org_id = getattr(self, "id", None)
        else:
            org_id = None

        # Determine ID details for composite keys
        details = {"model": self.__class__.__name__, "retention_days": retention_days}
        if hasattr(self, "id"):
            details["id"] = self.id
        elif hasattr(self, "user_id") and hasattr(self, "organization_id"):
            details["user_id"] = self.user_id
            details["organization_id"] = self.organization_id

        audit_event = AuditEvent(
            action=f"{self.__class__.__name__.lower()}_deleted",
            actor_id=actor_id,
            organization_id=org_id,
            details=details,
        )
        session.add(audit_event)


@event.listens_for(Session, "do_orm_execute")
def _add_filtering_criteria(execute_state):
    """
    Automatically exclude soft-deleted records from all queries by default,
    unless explicitly requested.
    """
    if (
        execute_state.is_select
        and not execute_state.is_column_load
        and not execute_state.is_relationship_load
        and not execute_state.execution_options.get("include_deleted", False)
    ):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                SoftDeleteMixin,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            )
        )
