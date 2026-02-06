import logging
from typing import Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class FanoutWebSocketManager:
    def __init__(self):
        # Project-level connections: multiple connections per project allowed
        self.project_connections: Dict[str, List[WebSocket]] = {}
        # Map websocket -> project_id for cleanup
        self.websocket_projects: Dict[WebSocket, str] = {}
        # Debug connections: set of active debug websockets
        self.debug_connections: Set[WebSocket] = set()

    async def connect(
        self, key: str, websocket: WebSocket, already_accepted: bool = False
    ):
        """Connect a websocket for a given key (multiple connections allowed per key)."""
        if not already_accepted:
            await websocket.accept()
        if key not in self.project_connections:
            self.project_connections[key] = []
        self.project_connections[key].append(websocket)
        self.websocket_projects[websocket] = key

    def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket."""
        key = self.websocket_projects.get(websocket)
        if key and key in self.project_connections:
            if websocket in self.project_connections[key]:
                self.project_connections[key].remove(websocket)
            if not self.project_connections[key]:
                del self.project_connections[key]
        self.websocket_projects.pop(websocket, None)

    async def send_to(self, key: str, message: str):
        """Send message to all connections for a given key."""
        connections = self.project_connections.get(key, [])
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to {key}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)
