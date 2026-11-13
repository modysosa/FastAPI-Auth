"""Create users with unique identities and persistent account flags."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("admin", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("disabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
        sqlite_autoincrement=True,
    )


def downgrade():
    op.drop_table("users")
