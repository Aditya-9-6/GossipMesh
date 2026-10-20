from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from gossipmesh.models.base import Base


class OrganizationSAMLConfig(Base):
    __tablename__ = "organization_saml_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), unique=True, nullable=False)
    idp_entity_id: Mapped[str] = mapped_column(String, nullable=False)
    sso_url: Mapped[str] = mapped_column(String, nullable=False)
    x509_cert_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization = relationship("Organization", back_populates="saml_config")
