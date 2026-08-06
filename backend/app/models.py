import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# Sheet 02: devices — real parent of projects.created_via_device_id and updates.device_id.
# Each row gets its own token_hash so revoked_at on one row actually cuts off just that device.
class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = _uuid_pk()
    label: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "archived", name="project_status"), nullable=False, server_default="active"
    )
    # Nullable: null means created by hand on the site, not via an MCP create_project call.
    created_via_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    columns: Mapped[list["Column"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    cards: Mapped[list["Card"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    digests: Mapped[list["Digest"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Column(Base):
    __tablename__ = "columns"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    # Stable identifier independent of the freely-renameable `name` — everything downstream
    # (the cron, move_card, resolved-gating) checks role, never name. See Sheet 02.
    role: Mapped[str] = mapped_column(
        Enum("backlog", "in_progress", "blocked", "done", name="column_role"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    project: Mapped[Project] = relationship(back_populates="columns")
    cards: Mapped[list["Card"]] = relationship(back_populates="column")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    column_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("columns.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(
        Enum("high", "medium", "low", name="card_priority"), nullable=False, server_default="medium"
    )
    complexity: Mapped[str] = mapped_column(
        Enum("small", "medium", "large", name="card_complexity"), nullable=False, server_default="medium"
    )
    # Trigger-set/cleared on column-role change (see migration) — survives partial-progress
    # updates without resetting, unlike computing "days blocked" from the latest update.
    blocked_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="cards")
    column: Mapped[Column] = relationship(back_populates="cards")
    updates: Mapped[list["Update"]] = relationship(back_populates="card", cascade="all, delete-orphan")


class Update(Base):
    __tablename__ = "updates"

    id: Mapped[uuid.UUID] = _uuid_pk()
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    # Nullable: null means the web app wrote this row directly (no MCP round trip).
    # Never a client-supplied string — resolved server-side from the caller's auth token.
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"))
    resolved: Mapped[str] = mapped_column(
        Enum("done", "partial", "blocked", name="update_resolved"), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    commit_hash: Mapped[str | None] = mapped_column(String)
    # Starts false — Claude never pushes, so it can't confirm at log_update time.
    # Flipped by mark_commit_landed (opportunistic git check) or by hand on the site.
    commit_landed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Trigger-set (never app code) — see migration. Only ever fires on a manual site edit,
    # since MCP always inserts a fresh row instead of touching an existing one.
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    card: Mapped[Card] = relationship(back_populates="updates")


class Digest(Base):
    __tablename__ = "digests"
    __table_args__ = (UniqueConstraint("project_id", "digest_date", name="uq_digest_project_date"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    digest_date: Mapped[date] = mapped_column(Date, nullable=False)
    done_points: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    tomorrow_points: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    minutes_worked: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    efficiency_score: Mapped[float] = mapped_column(Integer, nullable=False, server_default="0")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="digests")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = _uuid_pk()
    notification_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
