"""Add Entra users and associate comments without fabricating legacy owners."""

from alembic import op
import sqlalchemy as sa


revision = "20261023_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("entra_object_id", sa.String(length=36), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "tenant_id",
                "entra_object_id",
                name="uq_user_entra_identity",
            ),
        )
        op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    if "comments" not in tables:
        op.create_table(
            "comments",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_comments_user_id", "comments", ["user_id"])
    else:
        comment_columns = {
            column["name"] for column in sa.inspect(op.get_bind()).get_columns("comments")
        }
        if "user_id" not in comment_columns or "author" in comment_columns:
            with op.batch_alter_table("comments") as batch_op:
                if "user_id" not in comment_columns:
                    batch_op.add_column(
                        sa.Column("user_id", sa.Integer(), nullable=True)
                    )
                    batch_op.create_foreign_key(
                        "fk_comments_user_id_users",
                        "users",
                        ["user_id"],
                        ["id"],
                        ondelete="RESTRICT",
                    )
                if "author" in comment_columns:
                    batch_op.drop_column("author")
            if "user_id" not in comment_columns:
                op.create_index("ix_comments_user_id", "comments", ["user_id"])


def downgrade() -> None:
    raise RuntimeError(
        "This identity migration is intentionally irreversible to avoid deleting "
        "legacy comments or user associations."
    )