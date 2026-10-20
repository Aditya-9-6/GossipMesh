from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from gossipmesh.models.base import Base
from gossipmesh.models.mixins import SoftDeleteMixin


class ProviderCredential(SoftDeleteMixin, Base):
    __tablename__ = "provider_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String, nullable=False)  # e.g. openai, gemini, anthropic
    encrypted_key: Mapped[str] = mapped_column(String, nullable=False)

    organization = relationship("Organization")
