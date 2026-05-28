# Copyright (C) 2026 Donovan Torres
# Licensed under the GNU Affero General Public License v3.0
# https://www.gnu.org/licenses/agpl-3.0.html

# 1. Standard library imports
import json
from typing import Optional
from datetime import datetime, timezone

# 2. Third-party imports
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import joinedload

# 3. Local application imports
from modules import models, utils
from modules.dependencies import DBSession, CurrentUser
from modules.connection_manager import manager

router = APIRouter()

# chat_id is received as a query param in the WebSocket connection URL
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user: CurrentUser, db: DBSession, chat_id: Optional[int] = None):

    # USER VERIFICATION
    if not user:
        # Connection does not complete code=1006, prevents XSS, in case the client
        # sends an invalid cookie in the handshake without going through login
        await websocket.close()
        print("Invalid Cookie")

        return
    
    # VERIFY PRIMARY CHAT MEMBERSHIP
    # A user will never be able to be a member of a non-existent chat
    if chat_id is not None and not await utils.user_in_chat(user.id, chat_id, db):
        await websocket.close()
        return
    
    # Accepts connection and then chooses room
    await websocket.accept()

    # CONNECT TO RAM
    # Avoid adding the same websocket twice in RAM
    # If chat_id does not exist, an empty list is returned
    if chat_id is not None:
        if websocket not in manager.active_connections[chat_id]:
            await manager.connect(chat_id, websocket)

        # LOAD MESSAGE HISTORY
        result = await db.execute(
            select(models.Messages)
            .where(models.Messages.chat_id == chat_id)
            .order_by(models.Messages.created_at)
            .options(joinedload(models.Messages.user))
        )

        messages = result.scalars().all()

        for message in messages:
            payload = {
                "type": "message",
                "chat_id": chat_id,
                "username": message.user.username,
                "content": message.content
                }
            
            # Sends message to this specific websocket
            await websocket.send_text(json.dumps(payload))
        

    # LISTEN FOR NEW MESSAGES
    try:
        while True:
            msg = await websocket.receive_json()

            # Join is always sent when opening websocket connection
            if msg["type"] == "join":
                
                # NOTIFICATIONS
                for chat_notify in msg.get("chatsNotify", []):
                    
                    # VERIFY SECONDARY CHAT MEMBERSHIP
                    # A user will never be able to be a member of a non-existent chat
                    if not await utils.user_in_chat(user.id, chat_notify["chat_id"], db):
                        continue

                    if websocket not in manager.active_connections[chat_notify["chat_id"]]:
                        await manager.connect(chat_notify["chat_id"], websocket)


            elif msg["type"] == "message" and chat_id is not None:
                
                # SAVE HISTORY
                message = models.Messages(
                    user_id=user.id,
                    chat_id=chat_id,
                    content=msg["content"]
                )

                db.add(message)
                await db.commit()

                # BROADCAST
                payload = {
                    "type": "message",
                    "chat_id": chat_id,
                    "username": user.username,
                    "content": msg['content']
                }

                await manager.broadcast(payload, chat_id)

    except WebSocketDisconnect:
        pass

    except Exception as e:
        print(f"Unexpected error: {e}")

    finally:
        # If the user loses connection, closes the browser, or has other issues,
        # we remove their websocket from the rooms.
        # Copy dict_items to avoid errors when deleting keys during disconnect
        for chat_id_key, connections in list(manager.active_connections.items()):
            if websocket in connections:
                manager.disconnect(chat_id_key, websocket)

        # UPDATE LAST_SEEN_AT (guarantees primary last seen is updated
        # regardless of how the user exits)
        # To later correctly calculate new messages
        if chat_id is not None:
            users_chats = await utils.user_in_chat(user.id, chat_id, db)
            if users_chats:
                users_chats.last_seen_at = datetime.now(timezone.utc)
                await db.commit()