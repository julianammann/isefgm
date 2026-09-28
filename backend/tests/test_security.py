import asyncio
import threading
import time

import pytest

from giftmanager.core import security
from giftmanager.core.errors import ServiceUnavailableError


class _SlowHasher:
    """Stands in for pwdlib and records how many calls run at the same time."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0
        self.peak = 0

    def _work(self) -> None:
        with self._lock:
            self._active += 1
            self.peak = max(self.peak, self._active)
        time.sleep(0.05)
        with self._lock:
            self._active -= 1

    def hash(self, password: str) -> str:
        self._work()
        return "hash"

    def verify(self, password: str, password_hash: str) -> bool:
        self._work()
        return True


@pytest.mark.requirement("Q-03")
async def test_argon2_calls_are_bounded_to_fit_the_memory_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hasher = _SlowHasher()
    monkeypatch.setattr(security, "_password_hash", hasher)

    # Logins and registrations draw from the same budget.
    await asyncio.gather(
        *(security.verify_password("pw", "hash") for _ in range(7)),
        *(security.hash_password("pw") for _ in range(3)),
    )

    # 3 x 64 MiB fits the api container's 512 MiB; the default thread pool allows 40.
    assert hasher.peak == 3


async def _password_check() -> None:
    """What a login does: take an admission slot, then verify."""
    async with security.admit_password_check():
        await security.verify_password("pw", "hash")


@pytest.mark.requirement("Q-03")
async def test_password_checks_beyond_the_queue_are_turned_away_at_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hasher = _SlowHasher()
    monkeypatch.setattr(security, "_password_hash", hasher)

    admitted = [asyncio.create_task(_password_check()) for _ in range(11)]
    await asyncio.sleep(0)  # each task runs up to its first await, i.e. is admitted

    # 3 hash and 8 wait; the 12th does not queue behind them, it fails before any wait.
    with pytest.raises(ServiceUnavailableError):
        await _password_check()
    assert not any(task.done() for task in admitted)

    await asyncio.gather(*admitted)
    assert hasher.peak == 3
    # The slots are free again.
    await _password_check()
