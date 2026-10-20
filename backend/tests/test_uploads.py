"""Image files on the uploads volume (F-07): written at once, deleted only after the commit.

The `client` fixture never commits, so these tests drive the session directly.
"""

import re
import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core import uploads

OWNER = uuid.UUID("0192f6a0-0000-7000-8000-00000000000a")
OTHER = uuid.UUID("0192f6a0-0000-7000-8000-00000000000b")


@pytest.mark.requirement("F-07", "Q-03")
def test_storage_path_is_random_per_account() -> None:
    first, second = uploads.new_storage_path(OWNER), uploads.new_storage_path(OWNER)

    assert first != second
    for path in (first, second):
        directory, name = path.split("/")
        assert directory == "0192f6a0-0000-7000-8000-00000000000a"
        assert re.fullmatch(r"[0-9a-f]{32}\.webp", name)


@pytest.mark.requirement("F-07")
async def test_written_file_survives_commit(session: AsyncSession, uploads_dir: Path) -> None:
    path = uploads.new_storage_path(OWNER)

    await uploads.write(session, path, b"webp bytes")
    await session.commit()

    assert uploads.resolve(path) == uploads_dir / path
    assert (uploads_dir / path).read_bytes() == b"webp bytes"
    # Written via a temporary file and renamed: nothing else is left in the directory.
    assert [p.name for p in (uploads_dir / str(OWNER)).iterdir()] == [path.split("/")[1]]


@pytest.mark.requirement("F-07")
async def test_written_file_is_removed_on_rollback(
    session: AsyncSession, uploads_dir: Path
) -> None:
    # Like a request (core/db.py: get_session), the work runs inside an open transaction.
    await session.begin()
    path = uploads.new_storage_path(OWNER)
    await uploads.write(session, path, b"webp bytes")
    assert (uploads_dir / path).exists()

    await session.rollback()

    assert not (uploads_dir / path).exists()


@pytest.mark.requirement("F-07")
async def test_delete_waits_for_commit(session: AsyncSession, uploads_dir: Path) -> None:
    path = uploads.new_storage_path(OWNER)
    await uploads.write(session, path, b"webp bytes")
    await session.commit()

    uploads.delete_after_commit(session, path)
    assert (uploads_dir / path).exists()
    await session.commit()

    assert not (uploads_dir / path).exists()


@pytest.mark.requirement("F-07")
async def test_delete_is_dropped_on_rollback(session: AsyncSession, uploads_dir: Path) -> None:
    path = uploads.new_storage_path(OWNER)
    await uploads.write(session, path, b"webp bytes")
    await session.commit()

    await session.begin()
    uploads.delete_after_commit(session, path)
    await session.rollback()
    await session.commit()

    assert (uploads_dir / path).exists()


@pytest.mark.requirement("F-07", "F-17")
async def test_account_files_are_removed_after_commit(
    session: AsyncSession, uploads_dir: Path
) -> None:
    own = [uploads.new_storage_path(OWNER) for _ in range(2)]
    other = uploads.new_storage_path(OTHER)
    for path in [*own, other]:
        await uploads.write(session, path, b"webp bytes")
    await session.commit()

    uploads.delete_account_files_after_commit(session, OWNER)
    assert all((uploads_dir / path).exists() for path in own)
    await session.commit()

    assert not (uploads_dir / str(OWNER)).exists()
    assert (uploads_dir / other).exists()


# A SAVEPOINT inside the transaction is not the commit or rollback of the transaction.


@pytest.mark.requirement("F-07")
async def test_released_savepoint_does_not_delete_yet(
    session: AsyncSession, uploads_dir: Path
) -> None:
    path = uploads.new_storage_path(OWNER)
    await uploads.write(session, path, b"webp bytes")
    await session.commit()

    await session.begin()
    async with session.begin_nested():
        uploads.delete_after_commit(session, path)
    assert (uploads_dir / path).exists()
    await session.rollback()

    assert (uploads_dir / path).exists()


@pytest.mark.requirement("F-07")
async def test_released_savepoint_keeps_new_files_tracked(
    session: AsyncSession, uploads_dir: Path
) -> None:
    path = uploads.new_storage_path(OWNER)
    await session.begin()
    async with session.begin_nested():
        await uploads.write(session, path, b"webp bytes")

    await session.rollback()

    assert not (uploads_dir / path).exists()


@pytest.mark.requirement("F-07")
async def test_savepoint_rollback_keeps_files_of_the_transaction(
    session: AsyncSession, uploads_dir: Path
) -> None:
    path = uploads.new_storage_path(OWNER)
    await session.begin()
    await uploads.write(session, path, b"webp bytes")
    with pytest.raises(RuntimeError):
        async with session.begin_nested():
            raise RuntimeError("inner work failed")

    await session.commit()

    assert (uploads_dir / path).exists()


@pytest.mark.requirement("F-07")
async def test_rollback_with_an_open_savepoint_removes_new_files(
    session: AsyncSession, uploads_dir: Path
) -> None:
    path = uploads.new_storage_path(OWNER)
    await session.begin()
    await uploads.write(session, path, b"webp bytes")
    await session.begin_nested()

    await session.rollback()

    assert not (uploads_dir / path).exists()
