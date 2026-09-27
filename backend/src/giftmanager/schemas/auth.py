"""Request and response bodies of the auth endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# `description` and `examples` end up in openapi.json, in the generated TypeScript
# client and in docs/generated/api.md (MS 4).


class RegisterIn(BaseModel):
    """Data for a new account."""

    email: EmailStr = Field(
        description="Login name. Case is ignored.",
        examples=["anna@example.org"],
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="At least 8 characters. Only stored as an Argon2id hash (Q-03).",
        examples=["correct-horse-battery"],
    )
    display_name: str = Field(
        min_length=1,
        max_length=100,
        description="Display name in the UI and in notifications.",
        examples=["Anna"],
    )


class LoginIn(BaseModel):
    """Login credentials."""

    email: EmailStr = Field(description="Login name.", examples=["anna@example.org"])
    password: str = Field(
        min_length=1, max_length=128, description="Password.", examples=["correct-horse-battery"]
    )


class UserOut(BaseModel):
    """Account as the frontend sees it, without the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Account ID (UUIDv7).")
    email: str = Field(description="Login name, lowercased.")
    display_name: str = Field(description="Display name.")
    created_at: datetime = Field(description="Account creation time (UTC).")
