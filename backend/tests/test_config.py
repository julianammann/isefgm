import pytest

from giftmanager.core.config import Settings


@pytest.mark.requirement("Q-03")
def test_app_env_defaults_to_production() -> None:
    # Fail closed: a deployment that forgets APP_ENV gets Secure cookies and no /docs.
    # model_construct() applies the declared defaults without reading env or .env.
    settings = Settings.model_construct()
    assert settings.app_env == "production"
    assert not settings.is_dev
