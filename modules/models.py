# 1. Standard library imports
from datetime import datetime, timezone
import enum
import uuid

# 2. Third-party imports
from sqlalchemy import Index, Boolean, String, Text, ForeignKey, DateTime, Enum, text # Type affinities sqlite
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 3. Local application imports
from modules.database import Base # Base class inherited by models


# Define chat types
class ChatType(enum.Enum):
    public = "public"
    private = "private"
    direct = "direct"

# Define user roles
class UserRole(enum.Enum):
    owner = "owner"
    member = "member"

# Table models
class Users(Base):
    __tablename__ = "users"

    # Auto-increment and not null by default
    id: Mapped[int] = mapped_column(primary_key=True)
    # unique creates an index by default
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    # set_cookie overrides default, but it's good to keep it for extra security
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, default=lambda: str(uuid.uuid4()))

    # Relationship performs automatic join
    chats: Mapped[list["UsersChats"]] = relationship(back_populates="user")
    messages: Mapped[list["Messages"]] = relationship(back_populates="user")

class Chats(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[ChatType] = mapped_column(Enum(ChatType), default=ChatType.public)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Only public chats have unique names
    __table_args__ = (
        Index(
            # Index name
            "uq_public_chat_name",
            # Column where it applies
            "name",
            unique=True,
            # Only when
            sqlite_where=text("type = 'public'")
        ),
    )

    messages: Mapped[list["Messages"]] = relationship(back_populates="chat")
    users: Mapped[list["UsersChats"]] = relationship(back_populates="chat")

# Intermediate table
class UsersChats(Base):
    __tablename__ = "users_chats"

    # Unique, cannot have two equal users in the same chat
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.member)
    notify_active: Mapped[bool] = mapped_column(Boolean, default=False)

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        # Lambda so when a record is created, it executes the
        # function at the exact moment (updated time)
        default=lambda: datetime.now(timezone.utc),
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["Users"] = relationship(back_populates="chats")
    chat: Mapped["Chats"] = relationship(back_populates="users")

# Intermediate table
class Messages(Base):
    __tablename__ = "messages"

    # Needs id because a user can send many messages in a chat
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    chat: Mapped["Chats"] = relationship(back_populates="messages")
    user: Mapped["Users"] = relationship(back_populates="messages")


if __name__ == "__main__":
    print("models: define model classes that represent database tables")


