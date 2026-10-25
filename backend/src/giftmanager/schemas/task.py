"""Request and response bodies of the task endpoints (F-08)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from giftmanager.models import TaskStatus
from giftmanager.schemas.common import PageParams
from giftmanager.schemas.gift import Title


class TaskListParams(PageParams):
    """Pagination for the task list, optionally narrowed to one gifting."""

    gifting_id: uuid.UUID | None = Field(
        default=None, description="Only the tasks of this gifting."
    )


class TaskIn(BaseModel):
    """Data of a task; used for create and for full update (PUT)."""

    gifting_id: uuid.UUID = Field(
        description="ID of the account's gifting the task belongs to. Any status of the "
        "gifting will do, from `idea` on.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a73"],
    )
    title: Title = Field(
        description="What to do, 1 to 200 characters.", examples=["Karte schreiben"]
    )
    status: TaskStatus = Field(
        default=TaskStatus.OPEN,
        description="`open`, `in_progress`, `done` or `discarded`; `open` when left out. Any "
        "status may follow any other.",
        examples=["in_progress"],
    )
    due_on: date | None = Field(
        default=None,
        description="Day the task should be done by, as a plain date (YYYY-MM-DD). Left out "
        "or null means no due date.",
        examples=["2026-12-20"],
    )


class TaskOut(BaseModel):
    """A task as the frontend sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Task ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a75"]
    )
    gifting_id: uuid.UUID = Field(
        description="ID of the gifting the task belongs to.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a73"],
    )
    title: str = Field(description="What to do.", examples=["Karte schreiben"])
    status: TaskStatus = Field(description="Progress of the task.", examples=["in_progress"])
    due_on: date | None = Field(
        description="Day the task should be done by as a plain date, or null.",
        examples=["2026-12-20"],
    )
    created_at: datetime = Field(
        description="Creation time (UTC), set by the server.", examples=["2026-10-04T09:30:00Z"]
    )
