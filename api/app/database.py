import os
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

@lru_cache(maxsize=1)
def engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL must be configured")
    return create_engine(url, pool_pre_ping=True, future=True)

def get_session():
    session = sessionmaker(engine(), expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
