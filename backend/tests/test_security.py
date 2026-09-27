import asyncio
import threading
import time

import pytest

from giftmanager.core import security


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
