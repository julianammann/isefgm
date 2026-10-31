"""Notification table (F-13)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models.notification import Notification
from tests.notifications import make_notification, make_user


@pytest.mark.requirement("F-13")
async def test_notification_rows_go_with_the_account(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    session.add(make_notification(user, dedup_key="k1"))
    await session.flush()
    await session.delete(user)
    await session.flush()
    assert await session.scalar(select(func.count()).select_from(Notification)) == 0


@pytest.mark.requirement("F-13", "Q-02")
async def test_dedup_key_is_unique(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    session.add_all(
        [make_notification(user, dedup_key="k1"), make_notification(user, dedup_key="k1")]
    )
    with pytest.raises(IntegrityError):
        await session.flush()
