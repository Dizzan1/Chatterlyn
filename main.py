# Copyright (C) 2026 Donovan Torres
# Licensed under the GNU Affero General Public License v3.0
# https://www.gnu.org/licenses/agpl-3.0.html

# 1. Standard library imports
from contextlib import asynccontextmanager

# 2. Third-party imports
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select
import uvicorn
from starlette.middleware.sessions import SessionMiddleware

# 3. Local application imports
import config
from modules import database, models, utils
from routers import auth, chat, websocket

# Create tables if they don't exist, on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    # Create default general public room
    async with database.SessionLocal() as db:
            result = await db.execute(select(models.Chats).where(models.Chats.id == 1))
            chat =  result.scalars().first()
            if not chat:
                db.add(models.Chats(name="General", type=models.ChatType.public))
                await db.commit()

    
    yield

# Create app object
app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, config.SESSION_SECRET_KEY)

# Serve static files in /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Override default Pydantic error messages
@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):

    print(exc.errors())

    for error in exc.errors():
        custom_message = utils.CUSTOM_MESSAGES.get(error['type'])

        if custom_message:
            ctx = error.get('ctx')

            # Get expected_schemes="values.." from **ctx (unpack dict) and format custom_message
            error['msg'] = (
                custom_message.format(**ctx) if ctx else custom_message
            )

        # Format correctly and each error has its flash alert
        message = f"{error['msg'].replace('Value error, ', '')}"
        utils.set_flash(request, message)

    # Redirect to / if referer is not found
    referer = request.headers.get("referer", "/")

    return RedirectResponse(referer, status_code=303)

# Load my endpoints
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(websocket.router)

# Uvicorn ASGI server specifications
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)