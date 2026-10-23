from sqlalchemy import String, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from gossipmesh.models.base import Base
from gossipmesh.models.mixins import SoftDeleteMixin
from typing import Any, Dict


class Repository(SoftDeleteMixin, Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    index_state: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    policy: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=True)
