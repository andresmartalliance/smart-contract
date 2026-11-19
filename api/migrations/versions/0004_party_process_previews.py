"""Store document-derived workflow previews per registered person or company.
Revision ID: 0004_party_process_previews
Revises: 0003_party_registry
"""
from alembic import op
from app.models import PartyProcessPreview

revision="0004_party_process_previews"
down_revision="0003_party_registry"
branch_labels=None
depends_on=None

def upgrade():
    PartyProcessPreview.__table__.create(op.get_bind(),checkfirst=True)

def downgrade():
    PartyProcessPreview.__table__.drop(op.get_bind(),checkfirst=True)
