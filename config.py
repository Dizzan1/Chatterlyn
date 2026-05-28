import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is required")

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", SECRET_KEY)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db/chatterlyn.db")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "False").lower() in ("true", "1", "yes")