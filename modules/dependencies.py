# 1. Standard library imports
from typing import Annotated

# 2. Third-party imports
from fastapi import Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local application imports
from modules import database, models, utils


# Object to work with templates
templates = Jinja2Templates(directory="templates")
# Set global variables accessible from templates
templates.env.globals["get_flashes"] = utils.get_flashes # Pass function to make it accessible


# REUSABLE TYPE HINTS
# Gets current user
CurrentUser = Annotated[models.Users, Depends(utils.get_current_active_user)]
# Gets session to work with database
DBSession = Annotated[AsyncSession, Depends(database.get_db)]

if __name__ == "__main__":
    print("dependencies.py: Centralizes shared dependencies" \
    "that need to be imported by different routes")