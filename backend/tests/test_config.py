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
