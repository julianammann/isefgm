"""Response body of the health endpoints."""

from typing import Literal

from pydantic import BaseModel


class HealthOut(BaseModel):
    """State of the service and its database connection."""

    status: Literal["ok", "degraded"]
    database: bool
