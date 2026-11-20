"""First Google login of the designated institutional administrator.

The Google ID token verifier is independently exercised in the auth tests.
Here we override only Google identity, not the DB permission checks.
"""
import pytest
from sqlalchemy import select
from app.main import app
from app.database import get_session
from app.routers.portals import verify_google_email
from app.models import ContractParty, PartyProcessPreview, Membership, AuditEvent

INVITED = "yeferson@smart.com.co"
ENVIRONMENT = "6e8d45ca-d6f2-448c-a48a-63e5a2ab1806"


def as_user(email: str):
    app.dependency_overrides[verify_google_email] = lambda: email


def with_db(callback):
    generator = app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        return callback(session)
    finally:
        generator.close()


def add_original_institution(tenant_id="tenant-a", party_name="Hospital Smart"):
    def insert(db):
        party = ContractParty(
            tenant_id=tenant_id, kind="JURIDICA", name=party_name
        )
        db.add(party)
        db.flush()
        db.add(PartyProcessPreview(
            tenant_id=tenant_id, party_id=party.id, filename="Borrador Original",
            status="WORKFLOW_DRAFT",
            workflow={"key": "SMART_CICLO_CONTRATACION_V2", "name": "Ciclo de contratación v2"},
            source_map=[], questions=[], observations=[], created_by="alice"
        ))
        db.commit()
    with_db(insert)


@pytest.fixture
def admin_client(testing, monkeypatch):
    client, _ = testing
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", ENVIRONMENT)
    monkeypatch.setenv("SMART_CONTRACT_INITIAL_ADMIN_EMAIL", INVITED)
    add_original_institution()
    as_user(INVITED)
    yield client
    app.dependency_overrides.pop(verify_google_email, None)


def test_first_google_login_grants_tenant_scoped_admin_once(admin_client):
    initial = admin_client.get("/api/v1/portal/session")
    assert initial.status_code == 200, initial.text
    assert initial.json()["email"] == INVITED
    assert initial.json()["institutions"] == [{
        "id": "tenant-a", "roles": ["ADMIN", "CONFIGURADOR", "OPERADOR"]
    }]
    assert initial.json()["original_flow_preload_enabled"] is True
    assert admin_client.get("/api/v1/portal/parties").status_code == 200
    assert len(admin_client.get("/api/v1/portal/parties").json()) == 1
    assert admin_client.get("/api/v1/portal/session").status_code == 200

    def verify(db):
        members = db.scalars(select(Membership).where(
            Membership.user_id == INVITED
        )).all()
        events = db.scalars(select(AuditEvent).where(
            AuditEvent.event_type == "DESIGNATED_ADMIN_FIRST_LOGIN_GRANTED"
        )).all()
        assert len(members) == 1
        assert members[0].tenant_id == "tenant-a"
        assert len(events) == 1
        assert events[0].actor_id == INVITED
    with_db(verify)


def test_uninvited_google_identity_cannot_claim_admin(admin_client):
    as_user("unknown@smart.com.co")
    response = admin_client.get("/api/v1/portal/session")
    assert response.status_code == 403
    with_db(lambda db: (
        db.scalar(select(Membership).where(
            Membership.user_id == "unknown@smart.com.co"
        )) is None
        or pytest.fail("Non-invited identity received a membership")
    ))


def test_revoked_admin_is_not_reinstated_by_first_login(admin_client):
    assert admin_client.get("/api/v1/portal/session").status_code == 200

    def disable(db):
        member = db.scalar(select(Membership).where(
            Membership.user_id == INVITED
        ))
        member.active = False
        db.commit()
    with_db(disable)
    assert admin_client.get("/api/v1/portal/session").status_code == 403


def test_admin_bootstrap_disabled_outside_development(admin_client, monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "production-environment")
    # No grant has yet occurred in this isolated test fixture.
    assert admin_client.get("/api/v1/portal/session").status_code == 403


def test_admin_bootstrap_requires_exact_existing_original_workflow(testing, monkeypatch):
    client, _ = testing
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", ENVIRONMENT)
    monkeypatch.setenv("SMART_CONTRACT_INITIAL_ADMIN_EMAIL", INVITED)
    add_original_institution(party_name="Different Institution")
    as_user(INVITED)
    try:
        assert client.get("/api/v1/portal/session").status_code == 403
    finally:
        app.dependency_overrides.pop(verify_google_email, None)


def test_ambiguous_institution_fails_closed(admin_client):
    add_original_institution(tenant_id="tenant-b")
    assert admin_client.get("/api/v1/portal/session").status_code == 403
