"""One FastAPI app, two front doors — REST for the web app, MCP (streamable HTTP)
for Claude — sharing the same service layer and the same Postgres connection.
See docs/architecture.md (Sheet 07) for why this is one service, not two.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import resolve_device
from app.database import SessionLocal
from app.jobs.scheduler import start_scheduler
from app.mcp_server import mcp, set_current_device
from app.routers import auth, devices, digests, projects


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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_scheduler()
    yield


app = FastAPI(title="Task Manager", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the frontend's real origin before shipping publicly
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MCPDeviceAuthMiddleware)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(digests.router)
app.include_router(devices.router)

app.mount("/mcp", mcp.streamable_http_app())


@app.get("/health")
async def health():
    return {"status": "ok"}
