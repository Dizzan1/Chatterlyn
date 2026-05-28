# Copyright (C) 2026 Donovan Torres
# Licensed under the GNU Affero General Public License v3.0
# https://www.gnu.org/licenses/agpl-3.0.html

# 1. Standard library imports
from typing import Annotated
from datetime import datetime, timezone, timedelta

# 2. Third-party imports
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload

# 3. Local application imports
from modules import models, schemas, utils
from modules.dependencies import templates, CurrentUser, DBSession
from modules.connection_manager import manager

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

# PRIVATE ROUTES
# After validating the user, we send the JS that starts the WebSocket.
# The cookie is later retrieved in the WebSocket handshake.
# Default public room 1
# Verifications needed for http and websockets (different connections)
# query param chat_id
@router.get("", response_class=HTMLResponse)
async def get_chat(request: Request, user: CurrentUser, db: DBSession, chat_id: int = 1):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)
    
    # VERIFY IF CHAT EXISTS
    chat = await utils.get_chat(chat_id, db)

    if not chat:
        utils.set_flash(request, "This chat does not exist")
        return RedirectResponse("/chat", status_code=303)

    # VERIFY IF USER ALREADY BELONGS TO CHAT
    users_chats = await utils.user_in_chat(user.id, chat_id, db)

    is_new_member = False

    # If not belonging to the chat
    if not users_chats:

        if chat.type == models.ChatType.public:

            # INSERT
            new_user_chat = models.UsersChats(
                user_id = user.id,
                chat_id = chat_id
            )

            db.add(new_user_chat)
            await db.commit()

            # Resolve None in users_chats
            users_chats = new_user_chat

            is_new_member = True

        # Private or direct
        else:
            utils.set_flash(request, "You do not belong to this chat")
            return RedirectResponse("/chat", status_code=303)

    # Get number of chat members
    num_members = await utils.total_members(chat_id, db)

    # Real-time update of member count for other users via websocket
    if is_new_member:

        payload = {
            "type": "member_update",
            "count": num_members
        }

        await manager.broadcast(payload, chat_id)

    # Get sidebar info
    chats_notify, unread_counts = await utils.get_sidebar_data(user.id, db, chat_id)

    # UPDATE LAST_SEEN_AT
    users_chats.last_seen_at = datetime.now(timezone.utc)
    await db.commit()

    # Template context
    context = {
                # Primary chat to connect to
                "chat": chat,
                # User info, only username is used
                "user": user,
                # Chat members
                "num_members": num_members,
                # Sidebar chats, only including those where they are already a member
                "chats_notify": chats_notify,
                # Unread message counter
                "unread_counts": unread_counts,
                "role": users_chats.role
            }

    # Important not to store cache (conflict with websockets)
    return templates.TemplateResponse(request=request, name="chat.html", context=context, headers={"Cache-Control": "no-store"})

# Create new chat room
@router.post("/create")
async def create_chat(request: Request, form: Annotated[schemas.ChatCreate, Form()], user: CurrentUser, db: DBSession):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)
    
    # If public, verify name isn't already in use (unique name in public chats)
    if form.type == models.ChatType.public:

        result = await db.execute(
            select(models.Chats)
            .where(models.Chats.name == form.name)
            .where(models.Chats.type == models.ChatType.public)
        )

        result = result.scalars().first()

        if result:

            utils.set_flash(request, "Public chat name already exists")
            return RedirectResponse("/chat", status_code=303)

    # Insert into Chats
    new_chat = models.Chats(name=form.name, type=form.type)

    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)

    # Insert into UsersChats, the creator as owner
    new_user_chat = models.UsersChats(
        user_id = user.id,
        chat_id = new_chat.id,
        role = models.UserRole.owner
        )
    
    db.add(new_user_chat)
    await db.commit()

    return RedirectResponse(url=f"/chat?chat_id={new_chat.id}", status_code=302)

# View available public chats
@router.get("/public", response_class=HTMLResponse)
async def get_public_chats(request: Request, user: CurrentUser, db: DBSession):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)


    # Get sidebar info
    chats_notify, unread_counts = await utils.get_sidebar_data(user.id, db)

    # Get public chats
    result = await db.execute(
        select(models.Chats)
        .where(models.Chats.type == models.ChatType.public)
    )

    chats = result.scalars().all()

    context = {
        "chats": chats,
        "user": user,
        "chats_notify": chats_notify,
        "unread_counts": unread_counts
    }

    # Important not to store cache (conflict with websockets)
    return templates.TemplateResponse(request=request, name="public_chats.html", context=context, headers={"Cache-Control": "no-store"})


# Generate invitation link
@router.post("/{chat_id}/invite", response_class=JSONResponse)
async def generate_invite_link(request: Request, chat_id: int, user: CurrentUser, db: DBSession):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)

    # Check chat type
    chat = await utils.get_chat(chat_id, db)

    if chat is None:
        utils.set_flash(request, "This chat does not exist")
        return RedirectResponse("/chat", status_code=303)

    elif chat.type != models.ChatType.private:
        utils.set_flash(request, "Invitations can only be generated for private chats")
        return RedirectResponse("/chat", status_code=303)

    # Check if owner
    users_chats = await utils.user_in_chat(user.id, chat_id, db)

    if not users_chats or users_chats.role != models.UserRole.owner:
        utils.set_flash(request, "You are not the owner or don't belong to this chat")
        return RedirectResponse("/chat", status_code=303)
    
    # Token generation, valid for 1 day
    data = {"chat_id": chat_id}

    token = utils.create_access_token(data, timedelta(minutes=10))

    # Return JSON with invite_link
    return {"invite_url": f"{request.base_url}chat/join?token={token}"}

# Allow joining private room, query param token
@router.get("/join")
async def join_priv_chat(token: str, request: Request, user: CurrentUser, db: DBSession):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)
    
    # Verify token validity
    chat_id = utils.validate_invite_token(token)

    if chat_id is None:
        utils.set_flash(request, "Invalid token")
        return RedirectResponse("/chat", status_code=303)

    # Verify if chat exists
    chat = await utils.get_chat(chat_id, db)

    if chat is None:
        utils.set_flash(request, "Chat does not exist")
        return RedirectResponse("/chat", status_code=303)
    
    # Verify if already a member
    users_chats = await utils.user_in_chat(user.id, chat_id, db)

    if not users_chats:

        # INSERT
        new_user_chat = models.UsersChats(
            user_id = user.id,
            chat_id = chat_id
        )

        db.add(new_user_chat)
        await db.commit()

        # Get chat member counts and update other users
        num_members = await utils.total_members(chat_id, db)

        payload = {
            "type": "member_update",
            "count": num_members
        }

        await manager.broadcast(payload, chat_id)

    return RedirectResponse(url=f"/chat?chat_id={chat_id}", status_code=302)

# Updates last_seen_at before the user loads another window
@router.post("/{chat_id}/seen")
async def update_seen(request: Request, chat_id: int, user: CurrentUser, db: DBSession):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)
    
    # Verify if user belongs to chat
    users_chats = await utils.user_in_chat(user.id, chat_id, db)
    if users_chats:
        users_chats.last_seen_at = datetime.now(timezone.utc)
        await db.commit()

    return Response(status_code=204)

# View primary chat members
@router.get("/{chat_id}/members")
async def get_members(request: Request, chat_id: int, user: CurrentUser, db: DBSession):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)
    
    # Verify if user belongs to chat
    users_chats = await utils.user_in_chat(user.id, chat_id, db)
    if users_chats is None:
        utils.set_flash(request, "You do not belong to this chat")
        return RedirectResponse("/chat", status_code=303)
    
    # Get chat members
    result = await db.execute(
        select(models.UsersChats)
        .where(models.UsersChats.chat_id == chat_id)
        .options(joinedload(models.UsersChats.user))
        .order_by(models.UsersChats.joined_at)
    )

    # Get the column of [(UserChats_obj),..] with joinload loaded
    rows = result.scalars().all()

    members = []

    # Create JSON for JS
    for row in rows:

        # Serialize datetime
        fecha = row.joined_at.strftime("%d/%m/%Y %H:%M:%S")

        members.append({
            "username": row.user.username,
            "role": row.role.value,
            "joined_at": fecha
        })

    return members

# Leave chat (removes user membership)
@router.post("/{chat_id}/leave")
async def leave_chat(request: Request, chat_id: int, user: CurrentUser, db: DBSession):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)

    # Verify chat_id is not 1 (general is mandatory)
    if chat_id == 1:
        utils.set_flash(request, "Leaving the general chat is prohibited")
        return RedirectResponse(url="/chat", status_code=302)

    # Verify user is joined to the chat
    result = await utils.user_in_chat(user.id, chat_id, db)

    if result is None:
        utils.set_flash(request, "You don't belong to this chat or it doesn't exist")
        return RedirectResponse(url="/chat", status_code=302)

    # Remove user from UsersChats
    await db.execute(
        delete(models.UsersChats)
        .where(models.UsersChats.chat_id == chat_id)
        .where(models.UsersChats.user_id == user.id)
    )

    await db.commit()

    # Check if users remain in the chat
    num_members = await utils.total_members(chat_id, db)

    # If no members left, delete the chat
    if num_members == 0:
        await db.execute(
            delete(models.Chats)
            .where(models.Chats.id == chat_id)
        )

        await db.commit()
    else:

        # Update new member count to connected users
        payload = {
            "type": "member_update",
            "count": num_members
        }

        await manager.broadcast(payload, chat_id)

    # Redirect user to general
    return RedirectResponse(url="/chat", status_code=303)