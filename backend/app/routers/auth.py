"""Single-user login (Sheet 06's decision: private hosting, no public signup).
Password hash is generated once via scripts/set_password.py and stored in the
env, not a users table — there is exactly one account, ever.
"""

from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext

from app.auth import create_web_token
from app.config import get_settings
from app.schemas import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login")
async def login(body: LoginRequest):
    settings = get_settings()
    if body.email != settings.web_auth_email or not pwd_context.verify(
        body.password, settings.web_auth_password_hash
    ):
        raise HTTPException(401, "invalid credentials")
    return {"token": create_web_token()}
