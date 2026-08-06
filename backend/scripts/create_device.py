"""Creates the first device row and prints its token exactly once — put it
straight into that device's MCP config (claude.ai Connector settings, or
Claude Code's .mcp.json). After the first device exists, use the web app's
device management screen (it needs a device-independent web login) instead.

    uv run scripts/create_device.py "macbook"
"""

import asyncio
import sys

from app.auth import new_device_token
from app.database import SessionLocal
from app.models import Device


async def main(label: str) -> None:
    token, token_hash = new_device_token()
    async with SessionLocal() as db:
        db.add(Device(label=label, token_hash=token_hash))
        await db.commit()
    print(f"device {label!r} created. token (shown once):\n{token}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: create_device.py <label>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
