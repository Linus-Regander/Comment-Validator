"""Remove client-controlled author strings from existing comment tables."""

from alembic import op
import sqlalchemy as sa


revision = "20261023_0002"
down_revision = "20261023_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "comments" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("comments")}
    if "author" in columns:
        with op.batch_alter_table("comments") as batch_op:
            batch_op.drop_column("author")


def downgrade() -> None:
    raise RuntimeError(
        "The client-controlled author field is intentionally not restored."
    )