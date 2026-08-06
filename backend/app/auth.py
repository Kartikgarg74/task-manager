"""Two separate auth mechanisms, deliberately not unified:

- Device tokens (MCP): each device in `devices` has its own bcrypt-hashed token.
  A request's device_id is resolved here from the token — Claude never passes a
  device string, so there's nothing for it to get wrong (Sheet 01 / Sheet 02).
- Web auth: single user, private hosting only (Sheet 06's decision). A JWT
  issued on login, checked on every REST/WebSocket call.
"""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Device

bearer_scheme = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"
JWT_TTL = timedelta(days=30)


def hash_secret(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()


def verify_secret(plaintext: str, hashed: str) -> bool:
    return bcrypt.checkpw(plaintext.encode(), hashed.encode())


def new_device_token() -> tuple[str, str]:
    """Returns (plaintext_token, hash_to_store). Plaintext is shown once, never persisted."""
    token = secrets.token_urlsafe(32)
    return token, hash_secret(token)


async def resolve_device(
    creds: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> Device | None:
    """MCP auth: look up the device by comparing the bearer token against every stored
    hash. Small device count (personal tool) makes this fine; index-assisted lookup by
    a token prefix is the upgrade path if that ever stops being true."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing device token")

    result = await db.execute(select(Device).where(Device.revoked_at.is_(None)))
    for device in result.scalars():
        if verify_secret(creds.credentials, device.token_hash):
            device.last_seen_at = datetime.now(timezone.utc)
            await db.commit()
            return device
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown or revoked device token")


async def require_device(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Device:
    return await resolve_device(creds, db)


def create_web_token() -> str:
    settings = get_settings()
    payload = {"sub": settings.web_auth_email, "exp": datetime.now(timezone.utc) + JWT_TTL}
    return jwt.encode(payload, settings.web_auth_secret, algorithm=JWT_ALGORITHM)


async def require_web_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    settings = get_settings()
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    try:
        payload = jwt.decode(creds.credentials, settings.web_auth_secret, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    return payload["sub"]
