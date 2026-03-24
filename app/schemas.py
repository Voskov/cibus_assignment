from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, username: str) -> str:
        username = username.strip()
        if not username:
            raise ValueError("username must not be empty")
        return username

    @field_validator("password")
    @classmethod
    def password_constraints(cls, password: str) -> str:
        if not password:
            raise ValueError("password must not be empty")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if not any(c.isupper() for c in password):
            raise ValueError("password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("password must contain at least one digit")
        return password


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content must not be empty")
        return v


class MessageOut(BaseModel):
    id: int
    content: str
    author_username: str
    vote_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Votes ─────────────────────────────────────────────────────────────────────

class VoteRequest(BaseModel):
    value: int

    @field_validator("value")
    @classmethod
    def value_must_be_valid(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError("value must be 1 or -1")
        return v


class VoteResponse(BaseModel):
    vote_count: int
