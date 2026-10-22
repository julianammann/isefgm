"""Task endpoints (F-08): list, create, show, update, delete tasks of giftings."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import Page, problem_responses
from giftmanager.schemas.task import TaskIn, TaskListParams, TaskOut
from giftmanager.services import task as task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

_NOT_FOUND_NOTE = " A task of another account returns 404, like a missing one."
_GIFTING_NOTE = (
    " `gifting_id` must be a gifting of the account, in any status from `idea` on; a gifting"
    " of another account returns 404, like a missing one, and nothing is saved."
)


@router.get(
    "",
    operation_id="listTasks",
    summary="List tasks",
    description="Returns the tasks of the current account, one page at a time: earliest due "
    "date first, tasks without one last, the same due date in creation order. `gifting_id` "
    "narrows the list to one gifting; a gifting of another account gives an empty page.",
    responses=problem_responses(401),
)
async def list_tasks(
    user: CurrentUser,
    session: SessionDep,
    page: Annotated[TaskListParams, Query()],
) -> Page[TaskOut]:
    """Return one page of the current account's tasks."""
    tasks, total = await task_service.list_tasks(
        session, user.id, gifting_id=page.gifting_id, limit=page.limit, offset=page.offset
    )
    return Page[TaskOut](
        items=[TaskOut.model_validate(t) for t in tasks],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createTask",
    summary="Create task",
    description="Adds a task to a gifting of the current account." + _GIFTING_NOTE,
    responses=problem_responses(401, 404),
)
async def create_task(body: TaskIn, user: CurrentUser, session: SessionDep) -> TaskOut:
    """Add a task to a gifting of the current account."""
    task = await task_service.create_task(session, user.id, **body.model_dump())
    return TaskOut.model_validate(task)


@router.get(
    "/{task_id}",
    operation_id="getTask",
    summary="Show task",
    description="Returns one task of the current account." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_task(task_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> TaskOut:
    """Return one task of the current account."""
    task = await task_service.get_task(session, user.id, task_id)
    return TaskOut.model_validate(task)


@router.put(
    "/{task_id}",
    operation_id="updateTask",
    summary="Update task",
    description="Replaces all fields of the task; a left-out `due_on` removes the due date."
    + _GIFTING_NOTE
    + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def update_task(
    task_id: uuid.UUID, body: TaskIn, user: CurrentUser, session: SessionDep
) -> TaskOut:
    """Replace all editable fields of a task of the current account."""
    task = await task_service.update_task(session, user.id, task_id, **body.model_dump())
    return TaskOut.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteTask",
    summary="Delete task",
    description="Deletes the task. Cannot be undone." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def delete_task(task_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete a task of the current account."""
    await task_service.delete_task(session, user.id, task_id)
