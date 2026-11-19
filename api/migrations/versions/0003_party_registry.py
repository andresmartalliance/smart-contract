"""Separate party registration and draft contract cases from workflow assignment.
Revision ID: 0003_party_registry
Revises: 0002_portals
Safe for existing V6.3 data. Backfills case-party relationship.
"""
from alembic import op
import sqlalchemy as sa

revision="0003_party_registry"
down_revision="0002_portals"
branch_labels=None
depends_on=None

def upgrade():
    op.alter_column("contract_parties","contact_email",
       existing_type=sa.String(255),nullable=True)
    op.alter_column("contract_cases","workflow_version_id",
       existing_type=sa.String(36),nullable=True)
    op.add_column("contract_cases",sa.Column("party_id",sa.String(36),
       sa.ForeignKey("contract_parties.id"),nullable=True))
    op.create_index("ix_contract_cases_party_id","contract_cases",["party_id"])
    # Existing invited cases must retain their registered contractor.
    bind=op.get_bind()
    bind.execute(sa.text("""
      UPDATE contract_cases
      SET party_id=(SELECT a.party_id FROM contract_case_access a
                    WHERE a.case_id=contract_cases.id LIMIT 1)
      WHERE party_id IS NULL
    """))

def downgrade():
    bind=op.get_bind()
    missing=bind.execute(sa.text("""
      SELECT COUNT(*) FROM contract_cases WHERE workflow_version_id IS NULL
    """)).scalar() or 0
    if missing:
        raise RuntimeError("Cannot downgrade: draft cases without workflow must first be resolved")
    missing_email=bind.execute(sa.text("""
      SELECT COUNT(*) FROM contract_parties WHERE contact_email IS NULL
    """)).scalar() or 0
    if missing_email:
        raise RuntimeError("Cannot downgrade: party records without contact email must first be completed")
    op.drop_index("ix_contract_cases_party_id",table_name="contract_cases")
    op.drop_column("contract_cases","party_id")
    op.alter_column("contract_cases","workflow_version_id",
       existing_type=sa.String(36),nullable=False)
    op.alter_column("contract_parties","contact_email",
       existing_type=sa.String(255),nullable=False)
