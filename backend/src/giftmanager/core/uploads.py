"""Image files on the uploads volume (F-07). The database holds only their storage paths.

A new file is written at once and removed again if the transaction rolls back. Files of
deleted rows are removed only after the commit, so a failed deletion keeps them (F-17).
"""

import secrets
import shutil
import uuid
from pathlib import Path
from typing import Any

from anyio import to_thread
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from giftmanager.core.config import get_settings

# Keys in Session.info: absolute paths to remove after a rollback or after a commit.
_ON_ROLLBACK = "uploads_remove_on_rollback"
_AFTER_COMMIT = "uploads_remove_after_commit"


def new_storage_path(owner_id: uuid.UUID) -> str:
    """Return a fresh path relative to UPLOADS_DIR: `<owner_id>/<128 random bits>.webp`."""
    return f"{owner_id}/{secrets.token_hex(16)}.webp"


def resolve(storage_path: str) -> Path:
    """Return the absolute path of the file behind a storage path."""
    return get_settings().uploads_dir / storage_path


def _write_atomically(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    # The target name is random, so this temporary name cannot clash either.
    partial = target.with_name(f"{target.name}.part")
    try:
        partial.write_bytes(data)
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


async def write(session: AsyncSession, storage_path: str, data: bytes) -> None:
    """Write a new file now; it is removed again if the session's transaction rolls back."""
    target = resolve(storage_path)
    _pending(session.info, _ON_ROLLBACK).append(target)
    await to_thread.run_sync(_write_atomically, target, data)


def delete_after_commit(session: AsyncSession, storage_path: str) -> None:
    """Remove the file once the session's transaction has committed; a rollback keeps it."""
    _pending(session.info, _AFTER_COMMIT).append(resolve(storage_path))


def delete_account_files_after_commit(session: AsyncSession, owner_id: uuid.UUID) -> None:
    """Remove the account's whole upload directory once its deletion has committed (F-17)."""
    _pending(session.info, _AFTER_COMMIT).append(get_settings().uploads_dir / str(owner_id))


def _pending(info: dict[Any, Any], key: str) -> list[Path]:
    return info.setdefault(key, [])


def _remove(paths: list[Path]) -> None:
    for path in paths:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


# SQLAlchemy fires both events for a SAVEPOINT too; only the outer transaction decides.
def _after_commit(session: Session) -> None:
    if session.in_nested_transaction():
        return
    session.info.pop(_ON_ROLLBACK, None)
    _remove(session.info.pop(_AFTER_COMMIT, []))


def _after_rollback(session: Session) -> None:
    if session.in_nested_transaction():
        return
    session.info.pop(_AFTER_COMMIT, None)
    _remove(session.info.pop(_ON_ROLLBACK, []))


# On the sync Session class: every AsyncSession runs on one, in the app and in tests.
event.listen(Session, "after_commit", _after_commit)
event.listen(Session, "after_rollback", _after_rollback)
