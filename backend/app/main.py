"""One FastAPI app, three front doors — REST for the web app, MCP (streamable
HTTP) for Claude, and /internal for the external cron trigger — sharing the
same service layer and the same Postgres connection. See README's
"Architecture" section for why this is one service, not several.

No in-process scheduler here on purpose: this deploys on Render's free tier,
which sleeps on idle, so a background scheduler thread can't be trusted to
be alive at 23:59. Scheduling is external instead — see app/routers/internal.py
and .github/workflows/.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import resolve_device
from app.database import SessionLocal
from app.mcp_server import mcp, set_current_device
from app.routers import auth, devices, digests, internal, projects


class MCPDeviceAuthMiddleware(BaseHTTPMiddleware):
    """Runs only for requests under /mcp. Resolves the bearer token to a Device
    (app/auth.py) and stashes it in a contextvar the MCP tool handlers read —
    device_id is never a tool argument, only ever comes from here."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            auth_header = request.headers.get("authorization", "")
            creds = None
            if auth_header.lower().startswith("bearer "):
                from fastapi.security import HTTPAuthorizationCredentials

                creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth_header[7:])
            async with SessionLocal() as db:
                device = await resolve_device(creds, db)
            set_current_device(device)
        return await call_next(request)


app = FastAPI(title="Task Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://task-manager-eight-chi-79.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MCPDeviceAuthMiddleware)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(digests.router)
app.include_router(devices.router)
app.include_router(internal.router)

app.mount("/mcp", mcp.streamable_http_app())


@app.get("/health")
async def health():
    return {"status": "ok"}
