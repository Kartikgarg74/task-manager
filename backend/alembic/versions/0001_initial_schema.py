"""Initial schema — Sheet 02 of the design doc, verbatim.

Tables: devices, projects, columns, cards, updates, digests, notifications.
Triggers: cards.blocked_since (set/cleared on column-role change) and
updates.edited_at (set on any UPDATE) — both DB-level so they can't be
forgotten by a code path that doesn't remember to set them.

Revision ID: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String, nullable=False),
        sa.Column("token_hash", sa.String, nullable=False, unique=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Enum("active", "archived", name="project_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_via_device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "role",
            sa.Enum("backlog", "in_progress", "blocked", "done", name="column_role"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("column_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("columns.id"), nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column(
            "priority", sa.Enum("high", "medium", "low", name="card_priority"),
            nullable=False, server_default="medium",
        ),
        sa.Column(
            "complexity", sa.Enum("small", "medium", "large", name="card_complexity"),
            nullable=False, server_default="medium",
        ),
        sa.Column("blocked_since", sa.DateTime(timezone=True)),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )

    op.create_table(
        "updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id")),
        sa.Column(
            "resolved", sa.Enum("done", "partial", "blocked", name="update_resolved"), nullable=False
        ),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("impact", sa.Text, nullable=False, server_default=""),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("commit_hash", sa.String),
        sa.Column("commit_landed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("digest_date", sa.Date, nullable=False),
        sa.Column("done_points", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("tomorrow_points", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("minutes_worked", sa.Integer, nullable=False, server_default="0"),
        sa.Column("efficiency_score", sa.Numeric, nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "digest_date", name="uq_digest_project_date"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("notification_date", sa.Date, nullable=False, unique=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Sheet 02: blocked_since — set the moment a card's column becomes role='blocked',
    # cleared the moment it leaves. Survives partial-progress updates on the same card,
    # unlike computing "days blocked" from the most recent update row.
    op.execute("""
        CREATE OR REPLACE FUNCTION set_blocked_since() RETURNS trigger AS $$
        DECLARE
            new_role column_role;
            old_role column_role;
        BEGIN
            SELECT role INTO new_role FROM columns WHERE id = NEW.column_id;
            IF TG_OP = 'INSERT' THEN
                old_role := NULL;
            ELSE
                SELECT role INTO old_role FROM columns WHERE id = OLD.column_id;
            END IF;

            IF new_role = 'blocked' AND (old_role IS DISTINCT FROM 'blocked') THEN
                NEW.blocked_since := now();
            ELSIF new_role IS DISTINCT FROM 'blocked' THEN
                NEW.blocked_since := NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_cards_blocked_since
        BEFORE INSERT OR UPDATE OF column_id ON cards
        FOR EACH ROW EXECUTE FUNCTION set_blocked_since();
    """)

    # --- Sheet 02: edited_at — set by a DB trigger, never app code, so a corrected update
    # row can't be silently indistinguishable from an original one. Deliberately excludes
    # commit_landed: mark_commit_landed (app/services/updates.py) is a routine, expected
    # lifecycle flip, not a correction, so it must not trip this flag — only content fields
    # changing counts as "edited."
    op.execute("""
        CREATE OR REPLACE FUNCTION set_edited_at() RETURNS trigger AS $$
        BEGIN
            IF (NEW.resolved, NEW.duration_minutes, NEW.summary, NEW.impact,
                NEW.input_tokens, NEW.output_tokens, NEW.commit_hash)
               IS DISTINCT FROM
               (OLD.resolved, OLD.duration_minutes, OLD.summary, OLD.impact,
                OLD.input_tokens, OLD.output_tokens, OLD.commit_hash)
            THEN
                NEW.edited_at := now();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_updates_edited_at
        BEFORE UPDATE ON updates
        FOR EACH ROW EXECUTE FUNCTION set_edited_at();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_updates_edited_at ON updates")
    op.execute("DROP FUNCTION IF EXISTS set_edited_at")
    op.execute("DROP TRIGGER IF EXISTS trg_cards_blocked_since ON cards")
    op.execute("DROP FUNCTION IF EXISTS set_blocked_since")
    op.drop_table("notifications")
    op.drop_table("digests")
    op.drop_table("updates")
    op.drop_table("cards")
    op.drop_table("columns")
    op.drop_table("projects")
    op.drop_table("devices")
    for enum_name in ("update_resolved", "card_complexity", "card_priority", "column_role", "project_status"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
