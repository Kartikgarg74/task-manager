"""Sheet 01: realtime replacement for what Supabase's client SDK used to give for
free. One in-memory connection pool per project — fine at single-instance scale
(this is a personal tool today). If this backend ever runs on more than one
instance, broadcast needs to move through Postgres LISTEN/NOTIFY or Redis pub/sub
instead of living in process memory — that's the upgrade path, not a redesign.
"""

from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, project_slug: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[project_slug].add(ws)

    def disconnect(self, project_slug: str, ws: WebSocket) -> None:
        self._connections[project_slug].discard(ws)

    async def broadcast(self, project_slug: str, message: dict) -> None:
        dead = []
        for ws in self._connections[project_slug]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(project_slug, ws)


manager = ConnectionManager()
