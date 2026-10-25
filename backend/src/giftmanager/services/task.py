"""Tasks of giftings (F-08). No HTTP in here.

A task has no owner_id; it belongs to the account of its gifting's gift idea. Like
services/note.py, this module scopes its own queries through gift.owner_id; `paginate()`
still applies.
"""

import uuid
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import NotFoundError
from giftmanager.models import Gift, Gifting, Task, TaskStatus
from giftmanager.services.gifting import get_gifting
from giftmanager.services.ownership import paginate


def _owned_tasks(owner_id: uuid.UUID) -> Select[tuple[Task]]:
    """Select tasks whose gifting's gift idea belongs to the given account."""
    return (
        select(Task)
        .join(Gifting, Gifting.id == Task.gifting_id)
        .join(Gift, Gift.id == Gifting.gift_id)
        .where(Gift.owner_id == owner_id)
    )


async def list_tasks(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    gifting_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Task], int]:
    """Return one page of the owner's tasks and the total count.

    Earliest due date first, tasks without one last; the same due date keeps creation order.
    With `gifting_id`, only the tasks of that gifting. A gifting of another account yields an
    empty page, not 404: the filter only narrows the owner's tasks.
    """
    statement = _owned_tasks(owner_id)
    if gifting_id is not None:
        statement = statement.where(Task.gifting_id == gifting_id)
    statement = statement.order_by(Task.due_on.asc().nulls_last(), Task.id)
    return await paginate(session, statement, limit=limit, offset=offset)


async def get_task(session: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    """Return the owner's task.

    Raises:
        NotFoundError: The task does not exist or belongs to another account.
    """
    task = await session.scalar(_owned_tasks(owner_id).where(Task.id == task_id))
    if task is None:
        raise NotFoundError("Task not found")
    return task


async def create_task(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    gifting_id: uuid.UUID,
    title: str,
    status: TaskStatus,
    due_on: date | None,
) -> Task:
    """Add a task to one of the owner's giftings, whatever its status.

    Raises:
        NotFoundError: The gifting does not exist or belongs to another account.
    """
    await get_gifting(session, owner_id, gifting_id)
    task = Task(gifting_id=gifting_id, title=title, status=status, due_on=due_on)
    session.add(task)
    await session.flush()
    return task


async def update_task(
    session: AsyncSession,
    owner_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    gifting_id: uuid.UUID,
    title: str,
    status: TaskStatus,
    due_on: date | None,
) -> Task:
    """Replace all editable fields of the owner's task.

    Raises:
        NotFoundError: The task or the gifting does not exist or belongs to another account.
    """
    task = await get_task(session, owner_id, task_id)
    await get_gifting(session, owner_id, gifting_id)
    task.gifting_id = gifting_id
    task.title = title
    task.status = status
    task.due_on = due_on
    await session.flush()
    return task


async def delete_task(session: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID) -> None:
    """Delete the owner's task; the gifting stays."""
    task = await get_task(session, owner_id, task_id)
    await session.delete(task)
    await session.flush()
