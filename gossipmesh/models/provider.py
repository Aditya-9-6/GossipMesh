from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gossipmesh.models.base import Base


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String, nullable=False) # e.g. openai, gemini, anthropic
    encrypted_key: Mapped[str] = mapped_column(String, nullable=False)

    organization = relationship("Organization")
