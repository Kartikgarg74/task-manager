"""One FastAPI app, three front doors — REST for the web app, MCP (streamable
HTTP) for Claude, and /internal for the external cron trigger — sharing the
same service layer and the same Postgres connection. See README's
"Architecture" section for why this is one service, not several.

No in-process scheduler here on purpose: this deploys on Render's free tier,
which sleeps on idle, so a background scheduler thread can't be trusted to
be alive at 23:59. Scheduling is external instead — see app/routers/internal.py
and .github/workflows/.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import resolve_device
from app.database import SessionLocal
from app.mcp_server import mcp, set_current_device
from app.routers import auth, devices, digests, internal, projects

# streamable_http_app() must be called once, up front — mcp.session_manager
# only exists after it's called, and the lifespan below needs that manager.
mcp_asgi_app = mcp.streamable_http_app()


class MCPDeviceAuthMiddleware(BaseHTTPMiddleware):
    """Runs only for requests under /mcp. Resolves the bearer token to a Device
    (app/auth.py) and stashes it in a contextvar the MCP tool handlers read —
    device_id is never a tool argument, only ever comes from here.

    Starlette's BaseHTTPMiddleware does NOT convert an HTTPException raised
    inside dispatch() into a real HTTP response the way a route handler's
    would be — it just crashes into an opaque 500. Every auth failure here
    (missing token, wrong token) must be caught explicitly and turned into
    a real response, or every failure looks identical to a server crash.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            auth_header = request.headers.get("authorization", "")
            creds = None
            if auth_header.lower().startswith("bearer "):
                creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth_header[7:])
            try:
                async with SessionLocal() as db:
                    device = await resolve_device(creds, db)
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            set_current_device(device)
        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Mounting mcp_asgi_app alone does NOT propagate lifespan into it — Starlette
    # doesn't forward startup/shutdown to mounted sub-apps. Without this, the
    # session manager's internal task group is never initialized, and every
    # single MCP request 500s with "Task group is not initialized. Make sure
    # to use run()." — found by actually testing a live MCP handshake, not by
    # reading the SDK source.
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Task Manager", lifespan=lifespan)

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


@app.get("/health")
async def health():
    return {"status": "ok"}


# mcp_asgi_app already defines its own internal route at /mcp (that's how the
# MCP SDK's streamable_http_app() works) — mounting it at "/mcp" here too would
# make the real path "/mcp/mcp". Mounting at root lets the sub-app's own /mcp
# route be the final path, matching every place this is documented as ".../mcp".
# Must be the LAST route registered: Starlette matches in registration order,
# and a root mount would otherwise shadow every route defined after it —
# that's exactly what broke /health the first time this was written.
app.mount("/", mcp_asgi_app)
