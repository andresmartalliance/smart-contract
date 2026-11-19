"""Create Smart Contract tenant-aware baseline.
Revision ID: 0001_baseline
Revises:
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    for table in Base.metadata.sorted_tables:
        table.create(op.get_bind(), checkfirst=False)

def downgrade():
    for table in reversed(Base.metadata.sorted_tables):
        table.drop(op.get_bind(), checkfirst=False)
