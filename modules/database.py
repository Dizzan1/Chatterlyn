# 2. Third-party imports
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# 3. Local application imports
import config

# Relative to main.py where the app is executed
engine = create_async_engine(config.DATABASE_URL)

# Session factory
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# Base class for table models, stores table metadata
class Base(DeclarativeBase):
    pass

# Creates and closes sessions
async def get_db():
    async with SessionLocal() as db:
        yield db

if __name__ == "__main__":
    print("database.py: creates the engine and sessions to work with the DB")
