from sqlalchemy import String, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from gossipmesh.models.base import Base


class GossipMessageModel(Base):
    __tablename__ = "gossip_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)  # uuid
    topic: Mapped[str] = mapped_column(String, index=True, nullable=False)
    origin_node: Mapped[str] = mapped_column(String, nullable=False)
    repo: Mapped[str] = mapped_column(String, nullable=False, default="global")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    vector_clock: Mapped[dict] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False, default=10)


class GossipHeartbeat(Base):
    __tablename__ = "gossip_heartbeats"

    node_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_seen: Mapped[float] = mapped_column(Float, nullable=False)
    clock_seq: Mapped[int] = mapped_column(Integer, nullable=False)
