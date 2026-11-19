"""Add scoped counterparties, invitations and executable task records.
Revision ID: 0002_portals
Revises: 0001_baseline
"""
from alembic import op
from app.models import ContractParty, ContractCaseAccess, ContractTask

revision = "0002_portals"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    ContractParty.__table__.create(bind, checkfirst=True)
    ContractCaseAccess.__table__.create(bind, checkfirst=True)
    ContractTask.__table__.create(bind, checkfirst=True)

def downgrade():
    bind = op.get_bind()
    ContractTask.__table__.drop(bind, checkfirst=True)
    ContractCaseAccess.__table__.drop(bind, checkfirst=True)
    ContractParty.__table__.drop(bind, checkfirst=True)
