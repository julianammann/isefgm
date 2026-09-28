import getpass
from collections.abc import Iterator

import pytest

from giftmanager import create_user
from giftmanager.core.config import get_settings
from giftmanager.core.db import get_engine, get_sessionmaker


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture
def cli_database(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point the command's own engine at the test database.

    Unlike the `session` fixture, what the command writes is committed, so every test
    here uses an address no other test registers.
    """
    monkeypatch.setenv("DATABASE_URL", database_url)
    _clear_caches()
    yield
    _clear_caches()


def _passwords(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    prompts = iter(answers)
    monkeypatch.setattr(getpass, "getpass", lambda _prompt="": next(prompts))


@pytest.mark.requirement("F-01")
@pytest.mark.usefixtures("cli_database")
def test_creates_the_account_once_while_registration_is_closed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not get_settings().registration_enabled
    argv = ["--email", "Cli@Example.org", "--display-name", "Cli"]

    _passwords(monkeypatch, "correct-horse-battery", "correct-horse-battery")
    assert create_user.main(argv) == 0
    assert "cli@example.org" in capsys.readouterr().out

    # The second run only conflicts if the first one was committed.
    _passwords(monkeypatch, "correct-horse-battery", "correct-horse-battery")
    assert create_user.main(argv) == 1
    assert "already registered" in capsys.readouterr().err


@pytest.mark.requirement("F-01")
@pytest.mark.usefixtures("cli_database")
def test_rejects_mismatched_passwords(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _passwords(monkeypatch, "correct-horse-battery", "correct-horse-battery!")
    argv = ["--email", "mismatch@example.org", "--display-name", "Mismatch"]
    assert create_user.main(argv) == 1
    assert "do not match" in capsys.readouterr().err


@pytest.mark.requirement("F-01", "Q-03")
@pytest.mark.usefixtures("cli_database")
def test_validates_like_the_registration_endpoint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _passwords(monkeypatch, "short", "short")
    argv = ["--email", "short@example.org", "--display-name", "Short"]
    assert create_user.main(argv) == 1
    assert "password" in capsys.readouterr().err
