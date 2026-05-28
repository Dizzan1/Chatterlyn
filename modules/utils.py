# Copyright (C) 2026 Donovan Torres
# Licensed under the GNU Affero General Public License v3.0
# https://www.gnu.org/licenses/agpl-3.0.html

# 1. Standard library imports
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
from collections import defaultdict
import uuid

# 2. Third-party imports
import jwt
from fastapi import Depends, Request
from fastapi.requests import HTTPConnection
from fastapi.responses import RedirectResponse
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

# 3. Local application imports
import config
from modules import database, models

# CONFIGURATION
ALGORITHM = "HS256"

CUSTOM_MESSAGES = {
    'int_parsing': 'This is not an integer',
    'url_scheme': 'Use the correct URL scheme, I expected {expected_schemes}.',
    'enum': 'Invalid type, expected: {expected}'
}

# AUTHENTICATION
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")

def get_password_hash(password: str):
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return password_hash.verify(plain_password, hashed_password)

# Verifies password and user
async def authenticate_user(db: AsyncSession, username: str, password: str):

    # Search for user by username
    result = await db.execute(select(models.Users).where(models.Users.username == username))
    user = result.scalars().first()

    # User does not exist, verify password anyway so response time
    # is always uniform (prevent attacks)
    if not user:
        verify_password(password, DUMMY_HASH)
        return None

    # User exists but password incorrect
    if not verify_password(password, user.password_hash):
        return None
    
    return user


# JWT TOKEN
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    payload = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta

    # If no timedelta is defined, set to 15min
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    payload.update({"exp": expire})
    
    # Encode token
    encoded_jwt = jwt.encode(payload, config.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Validates private chat invitation link token
def validate_invite_token(token: str) -> int | None:
    
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
        chat_id = payload.get("chat_id")
        return chat_id
    
    except InvalidTokenError:
        return None

# HTTP and WebSocket - extracts from cookie and verifies token sent automatically via http connection (occurs in handshake for websocket)
async def get_current_active_user(request: HTTPConnection, db: Annotated[AsyncSession, Depends(database.get_db)]) ->  models.Users | None:

    # Get token
    token = request.cookies.get("access_token", "valor_incorrecto")

    try:
        # Decode token
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("user_id")
        session_id: Optional[str] = payload.get("session_id")
        if user_id is None or session_id is None:
            return None
        
    except InvalidTokenError:
        return None
    
    # Returns user row
    result = await db.execute(select(models.Users).where(models.Users.id == user_id))
    user = result.scalars().first()

    # Check session_id
    if user is None or user.session_id != session_id:
        return None

    return user

# COOKIE
# Creates and assigns cookie (token -> user_id + session_id)
# Important: can only be used by POST /register and POST /login endpoints (after verifying credentials)
async def set_cookie(user: models.Users, db: AsyncSession) -> RedirectResponse:
    print("Generated new cookie, invalidated token")

    # Generate and save session_id
    user.session_id = str(uuid.uuid4())
    await db.commit()

    # Create token
    token = create_access_token(
        data={"user_id": user.id, "session_id": user.session_id},
        expires_delta=timedelta(days=1)
    )

    # Create response with cookie
    response = RedirectResponse("/chat", status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        path="/"
    )

    return response


# DATABASE QUERIES (VALIDATIONS + INFO)
# Verify if user belongs to chat (implicitly verifies chat and user exist)
async def user_in_chat(user_id: int, chat_id: int, db: AsyncSession) -> models.UsersChats | None:

    result = await db.execute(
        select(models.UsersChats)
        .where(models.UsersChats.user_id == user_id)
        .where(models.UsersChats.chat_id == chat_id)
    )

    users_chats = result.scalars().first()

    return users_chats

# Get chat
async def get_chat(chat_id: int, db: AsyncSession) -> models.Chats | None:
    
    result = await db.execute(
        select(models.Chats)
        .where(models.Chats.id == chat_id)
    )

    chat = result.scalars().first()

    return chat

# Get (userschats, unread) where unread is a calculated column
# chat_id can only be None when the user is not in chat.html
async def get_sidebar_data(user_id: int, db: AsyncSession, chat_id: Optional[int] = None):
    
    result = await db.execute(
        select(
            models.UsersChats,
            func.count(models.Messages.id).label("unread")
        )
        # Outer join returns all rows from the left table (userschats) even if no match
        # in the right (messages), NULL appears because filtering happens later
        .outerjoin(
            models.Messages,
            (models.Messages.chat_id == models.UsersChats.chat_id) &
            (models.Messages.created_at > models.UsersChats.last_seen_at)
        )
        .options(joinedload(models.UsersChats.chat))
        # Important: rows are filtered by user_id and grouped by chat;
        # without group by, it would only give the global message count
        .where(models.UsersChats.user_id == user_id)
        .group_by(models.UsersChats.chat_id)
    )


    chats_notify = []
    # defaultdict avoids KeyError by returning 0
    unread_counts = defaultdict(int)

    rows = result.all() 

    # We get -> Each row has a tuple (USERCHATS, UNREAD)
    # [
    #   (UsersChats(chat_id=1), 5),
    #   (UsersChats(chat_id=2), 0),
    #   (UsersChats(chat_id=3), 2),
    # ]

    # Separate tuple (USERCHATS, UNREAD)
    for row in rows:
        uc = row[0] # UsersChats
        unread = row[1] # unread count

        # Create these structures because they must be JSON serializable.
        # Jinja uses json.dumps, which only supports native Python types, necessary for JS to process them.
        chats_notify.append({"chat_id": uc.chat_id, "name": uc.chat.name, "notify_active": uc.notify_active, "type": uc.chat.type.value})
        unread_counts[uc.chat_id] = unread

    # Primary chat does not need unread_counts
    if chat_id is not None:
        unread_counts[chat_id] = 0

    return chats_notify, unread_counts

# Count total chat members
async def total_members(chat_id: int, db: AsyncSession) -> int:
    
    result = await db.execute(
        select(func.count(models.UsersChats.user_id).label("num_members"))
        .where(models.UsersChats.chat_id == chat_id)
    )

    num_members = result.scalar()

    return num_members or 0


# FLASH MESSAGES (DISPLAY ERRORS)
# Sets flash messages (cookie session)
def set_flash(request: Request, message: str, category: str = "danger"):

    # If flashes key doesn't exist, initialize as list
    request.session.setdefault("flashes", [])

    # Add new messages to the list
    # {"flashes": [{"message": message, "category": category}] }
    payload = {"message": message, "category": category}

    request.session["flashes"].append(payload)

    return

# Extracts session["flashes"] list and deletes it
# Used by jinja to generate alerts and delete the cookie in the process
def get_flashes(request: Request):

    # If flashes doesn't exist return []
    return request.session.pop("flashes", [])


if __name__ == "__main__":
    print("utils.py: useful functions")
