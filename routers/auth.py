# Copyright (C) 2026 Donovan Torres
# Licensed under the GNU Affero General Public License v3.0
# https://www.gnu.org/licenses/agpl-3.0.html

# 1. Standard library imports
from typing import Annotated
import uuid

# 2. Third-party imports
from fastapi import APIRouter
from fastapi import Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

# 3. Local application imports
import config
from modules import models, schemas, utils
from modules.dependencies import templates, CurrentUser, DBSession


router = APIRouter()

# PUBLIC ROUTES
@router.get("/", tags=["Home"])
async def index(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse(url="/chat", status_code=302)
    
    return templates.TemplateResponse(request=request, name="index.html")

@router.get("/register", response_class=HTMLResponse, tags=["Sign up"])
async def get_register(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse(url="/chat", status_code=302)
    
    return templates.TemplateResponse(request=request, name="register.html")

# Create new user
@router.post("/register", tags=["Sign up"])
async def new_user(raw_request: Request, request: Annotated[schemas.Login, Form()], db: DBSession):
    # Check if username already exists
    result = await db.execute(select(models.Users).where(models.Users.username ==  request.username))
    user = result.scalars().first()

    # If username is already in use
    if user:
        utils.set_flash(raw_request, "Username already exists")
        return RedirectResponse("/register", status_code=303)

    # If it doesn't exist, create it
    password_hash = utils.get_password_hash(request.password)
    new_user = models.Users(username=request.username, password_hash=password_hash)

    # Add object to session
    db.add(new_user)

    # Confirm changes
    await db.commit()

    # Create and assign cookie (token -> user_id + session_id)
    response = await utils.set_cookie(new_user, db)

    return response


@router.get("/login", response_class=HTMLResponse, tags=["Login"])
async def get_login(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse(url="/chat", status_code=302)
    
    return templates.TemplateResponse(request=request, name="login.html")

# Log in, authenticate user
@router.post("/login", tags=["Login"])
async def authenticate_user(request: Request, form: Annotated[schemas.Login, Form()], db: DBSession):
    
    # Authenticate username and password
    user = await utils.authenticate_user(db, form.username, form.password)

    # Incorrect authentication
    if not user:
        utils.set_flash(request, "Username or password incorrect")
        return RedirectResponse("/login", status_code=303)
    
    # Create and assign cookie (token -> user_id + session_id)
    response = await utils.set_cookie(user, db)

    return response

# PRIVATE ROUTE
@router.post("/logout", tags=["Logout"])
async def logout(request: Request, user: CurrentUser, db: DBSession):
    if not user:
        utils.set_flash(request, "You must log in")
        return RedirectResponse(url="/login", status_code=302)
    
    # If valid user, overwrite session_id for security
    # to invalidate their token
    user.session_id = str(uuid.uuid4())
    await db.commit()

    # Redirect to index and delete cookie
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax"
    )

    return response