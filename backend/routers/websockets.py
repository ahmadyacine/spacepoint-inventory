# backend/routers/websockets.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Iterable, Any

router = APIRouter(prefix="/ws", tags=["websockets"])


class ConnectionManager:
    """
    Manages active WebSocket connections per user.

    - Each user_id can have multiple active connections (tabs/devices).
    - Used by other routers (e.g., reports) to push notifications:
        await manager.send_personal_message({...}, user_id)
    """

    def __init__(self) -> None:
        # user_id -> list of WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Accept and register a new connection for the given user_id.
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"[WS] User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Remove a connection from the given user_id.
        """
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"[WS] User {user_id} disconnected.")

    async def send_personal_message(self, message: dict, user_id: int) -> None:
        """
        Send a JSON message to all active connections of a specific user.
        Safe if user has 0 connections (does nothing).
        """
        connections = self.active_connections.get(user_id)
        if not connections:
            return

        dead_connections: List[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WS] Error sending to user {user_id}: {e}")
                dead_connections.append(connection)

        # Clean up any connections that errored
        for conn in dead_connections:
            try:
                connections.remove(conn)
            except ValueError:
                pass

        if not connections:
            self.active_connections.pop(user_id, None)

    async def send_to_many(self, message: dict, user_ids: Iterable[int]) -> None:
        """
        Send the same message to multiple users.
        """
        for uid in user_ids:
            await self.send_personal_message(message, uid)

    async def broadcast(self, message: dict) -> None:
        """
        Send a message to ALL connected users.
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)


manager = ConnectionManager()


@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int) -> None:
    """
    WebSocket endpoint:
    - Frontend connects to: ws://<host>/ws/{user_id}
    - Keeps connection alive by reading messages in a loop.
    - Currently we ignore client messages (except optional 'ping').
    """
    await manager.connect(websocket, user_id)
    try:
        while True:
            # We don't really care about the content for now,
            # but this keeps the connection alive.
            try:
                data: Any = await websocket.receive_text()
            except WebSocketDisconnect:
                raise

            # Optional: simple ping-pong protocol from frontend
            if isinstance(data, str) and data.strip().lower() == "ping":
                try:
                    await websocket.send_text("pong")
                except Exception as e:
                    print(f"[WS] Error replying ping for user {user_id}: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        # Any other exception -> log and disconnect
        print(f"[WS] Unexpected error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
