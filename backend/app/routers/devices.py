"""Sheet 02/03: device management screen — rename a label or revoke a device
without touching any historical updates/projects row that already used it.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import new_device_token, require_web_user
from app.database import get_db
from app.models import Device

router = APIRouter(prefix="/api/devices", tags=["devices"])


class CreateDeviceRequest(BaseModel):
    label: str


class RenameDeviceRequest(BaseModel):
    label: str


@router.get("")
async def list_devices(db: AsyncSession = Depends(get_db), _user: str = Depends(require_web_user)):
    rows = (await db.execute(select(Device))).scalars().all()
    return [
        {
            "id": str(d.id),
            "label": d.label,
            "last_seen_at": d.last_seen_at,
            "created_at": d.created_at,
            "revoked_at": d.revoked_at,
        }
        for d in rows
    ]


@router.post("")
async def create_device(
    body: CreateDeviceRequest, db: AsyncSession = Depends(get_db), _user: str = Depends(require_web_user)
):
    """Returns the plaintext token exactly once — put it straight into that device's
    MCP config. It is never retrievable again after this response."""
    token, token_hash = new_device_token()
    device = Device(label=body.label, token_hash=token_hash)
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return {"id": str(device.id), "label": device.label, "token": token}


@router.patch("/{device_id}")
async def rename_device(
    device_id: str,
    body: RenameDeviceRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_web_user),
):
    import uuid as _uuid

    device = await db.get(Device, _uuid.UUID(device_id))
    if device is None:
        raise HTTPException(404, "no such device")
    device.label = body.label
    await db.commit()
    return {"id": str(device.id), "label": device.label}


@router.delete("/{device_id}")
async def revoke_device(
    device_id: str, db: AsyncSession = Depends(get_db), _user: str = Depends(require_web_user)
):
    import uuid as _uuid
    from datetime import datetime, timezone

    device = await db.get(Device, _uuid.UUID(device_id))
    if device is None:
        raise HTTPException(404, "no such device")
    device.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(device.id), "revoked_at": device.revoked_at}
