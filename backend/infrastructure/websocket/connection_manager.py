"""
Oneiros Infrastructure Layer - WebSocket Connection Manager

Manages active clients and handles broadcasting of events to visual dashboards.
"""

import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("oneiros.infrastructure.websocket")

class ConnectionManager:
    """
    Tracks and broadcasts telemetry over WebSocket connections.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Registers a new socket connection.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Unregisters a socket connection.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Direct messaging to a single connection.
        """
        await websocket.send_text(message)

    async def broadcast_json(self, data: dict):
        """
        Broadcasts structured JSON payload to all active clients.
        """
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to broadcast message to connection: {e}")
                # Connection might be dead, but let's clean up outside of loop or handle gracefully
