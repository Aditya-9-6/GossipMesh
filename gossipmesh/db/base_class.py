from __future__ import annotations

from typing import Any
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase, MappedAsDataclass):
    pass


from gossipmesh.models.repository import Repository

__all__ = ["Base"]
