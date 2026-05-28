# 2. Third-party imports
from pydantic import BaseModel, field_validator
import regex

# 3. Local application imports
from . import models

# Validates user input in login and register
class Login(BaseModel):
    # Form -> application/x-www-form-urlencoded
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        value = value.strip()

        if not 3 < len(value) < 20:
            raise ValueError("Username must be between 3 and 20 characters long")
        
        # \p{L} -> all letters from any language, UNICODE
        if not regex.fullmatch(r"[\p{L}0-9_.-]+", value):
            raise ValueError("Username can only contain alphanumeric characters, '_', '.' and '-'")
        
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):

        if not 4 <= len(value) <= 20:
            raise ValueError("Password must be between 4 and 20 characters long")
        
        if not regex.search(r"[A-Za-z]", value):
            raise ValueError("Password must contain at least one letter")
        
        if not regex.search(r"[\d]", value):
            raise ValueError("Password must contain at least one digit")
        
        return value

# Validates user input in chat creation
class ChatCreate(BaseModel):
    name: str
    type: models.ChatType = models.ChatType.public

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        value = value.strip()

        if not 2 <= len(value) <= 50:
            raise ValueError("Chat name must be between 2 and 50 characters long")

        if not regex.fullmatch(r"[\p{Emoji}\p{L}0-9_.\- ]+", value):
            raise ValueError("Name can only contain alphanumeric characters, emojis, '_', '.' and '-'")
        
        return value


if __name__ == "__main__":
    print("schemas.py: defines Pydantic models for data validation and serialization")