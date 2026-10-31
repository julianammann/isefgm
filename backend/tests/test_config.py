import pytest

from giftmanager.core.config import Settings


@pytest.mark.requirement("Q-03")
def test_app_env_defaults_to_production() -> None:
    # Fail closed: a deployment that forgets APP_ENV gets Secure cookies and no /docs.
    # model_construct() applies the declared defaults without reading env or .env.
    settings = Settings.model_construct()
    assert settings.app_env == "production"
    assert not settings.is_dev


@pytest.mark.requirement("F-01", "Q-03")
def test_registration_is_closed_by_default() -> None:
    # Fail closed: a deployment that forgets REGISTRATION_ENABLED accepts no sign-ups.
    assert Settings.model_construct().registration_enabled is False


@pytest.mark.requirement("F-13")
def test_smtp_defaults_point_at_local_mailpit(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_SECURITY",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM",
    ):
        monkeypatch.delenv(var, raising=False)
    # pyright hides BaseSettings' `_env_file` kwarg behind the synthesized pydantic __init__.
    s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert (s.smtp_host, s.smtp_port, s.smtp_security) == ("localhost", 1025, "none")
    assert s.smtp_username is None and s.smtp_password is None
    assert s.smtp_from == "Geschenke-Manager <noreply@isefgm.localhost>"


@pytest.mark.requirement("F-13")
def test_smtp_password_is_not_shown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_PASSWORD", "re_secret")
    s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert "re_secret" not in repr(s)
    assert s.smtp_password is not None and s.smtp_password.get_secret_value() == "re_secret"
