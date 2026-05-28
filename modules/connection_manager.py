# Copyright (C) 2026 Donovan Torres
# Licensed under the GNU Affero General Public License v3.0
# https://www.gnu.org/licenses/agpl-3.0.html

# 1. Standard library imports
from collections import defaultdict
import json

# 2. Third-party imports
from fastapi import WebSocket


# Singleton connection handler
class ConnectionManager:
    def __init__(self):
        # Avoid keyerror (key does not exist) with defaultdict -> returns empty list
        self.active_connections: defaultdict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, chat_id: int, websocket: WebSocket):
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, chat_id: int, websocket: WebSocket):
        self.active_connections[chat_id].remove(websocket)

        # Clean up empty keys
        if not self.active_connections[chat_id]:
            del self.active_connections[chat_id]

    async def broadcast(self, payload: dict, chat_id: int):

        # Make sure we don't send just spaces
        if payload["type"] == "message" and not payload.get("content", "").strip():
            return

        for connection in self.active_connections[chat_id]:
            await connection.send_text(json.dumps(payload))

# Create importable object
manager = ConnectionManager()

if __name__ == "__main__":
    print("connection_manager.py: Connection handler, mutable state")