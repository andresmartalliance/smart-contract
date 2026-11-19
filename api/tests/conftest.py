import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.database import Base, get_session
from app.main import app
from app.models import Tenant, Membership
import jwt
from datetime import datetime, timezone, timedelta

@pytest.fixture
def testing():
    engine = create_engine('sqlite+pysqlite:///:memory:', connect_args={'check_same_thread':False},
                           poolclass=__import__('sqlalchemy').pool.StaticPool)
    Base.metadata.create_all(engine)
    os.environ['SMART_AUTH_JWT_SECRET'] = 'test-only-secret-of-at-least-32-bytes'
    with Session(engine) as db:
        ta = Tenant(id='tenant-a', slug='test-a', name='Test A')
        tb = Tenant(id='tenant-b', slug='test-b', name='Test B')
        db.add_all([ta,tb])
        db.add_all([
          Membership(tenant_id='tenant-a', user_id='alice',roles=['CONFIGURADOR']),
          Membership(tenant_id='tenant-b', user_id='bob',roles=['OPERADOR']),
          Membership(tenant_id='tenant-b', user_id='charlie',roles=['CONFIGURADOR'])
        ])
        db.commit()
    def db_override():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_session] = db_override
    def token(user, tenant):
        return jwt.encode({'sub':user, 'tenant_id': tenant, 'aud':'smart-contract',
          'iss':'smart-contract', 'exp':datetime.now(timezone.utc)+timedelta(hours=1)},
          os.environ['SMART_AUTH_JWT_SECRET'],algorithm='HS256')
    client = TestClient(app)
    try: yield client,token
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()
