"""JWT validates identity; membership in the DB grants tenant access.
Never trust tenant IDs or role claims solely from headers or request JSON.
"""
import os
from dataclasses import dataclass
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_session
from .models import Membership, Tenant

bearer = HTTPBearer(auto_error=True)

@dataclass(frozen=True)
class Actor:
    user_id: str
    tenant_id: str
    roles: frozenset[str]


def require_actor(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_session)) -> Actor:
    secret = os.environ.get("SMART_AUTH_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise HTTPException(503, "Authentication not configured")
    try:
        claims = jwt.decode(credentials.credentials, secret, algorithms=["HS256"],
                            audience="smart-contract", issuer="smart-contract",
                            options={"require": ["sub", "tenant_id", "exp", "aud", "iss"]})
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user_id, tenant_id = claims["sub"], claims["tenant_id"]
    membership = db.scalar(select(Membership).where(Membership.user_id == user_id,
                          Membership.tenant_id == tenant_id, Membership.active.is_(True)))
    tenant = db.get(Tenant, tenant_id)
    if not membership or not tenant or not tenant.active:
        raise HTTPException(403, "No active membership")
    return Actor(user_id=user_id, tenant_id=tenant_id, roles=frozenset(membership.roles))


def require_role(actor: Actor, *allowed: str) -> None:
    if not actor.roles.intersection(allowed):
        raise HTTPException(403, "Insufficient permission")
