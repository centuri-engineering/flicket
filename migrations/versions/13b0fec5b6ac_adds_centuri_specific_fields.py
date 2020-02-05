"""adds centuri specific fields

Revision ID: 13b0fec5b6ac
Revises:
Create Date: 2020-02-05 10:37:49.288262

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "13b0fec5b6ac"
down_revision = "bcac6741b320"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "flicket_topic", sa.Column("requester", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "flicket_topic", sa.Column("requester_role", sa.Integer(), nullable=True)
    )

    op.create_table(
        "flicket_requester_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requester_role", sa.String(length=12), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    pass
