import pytest
from pydantic import ValidationError

from app.config import Settings


def test_debug_accepts_legacy_mode_strings():
    settings = Settings(_env_file=None, debug="release", env="development")

    assert settings.debug is False
    assert settings.runtime_env == "dev"
    assert settings.is_dev is True
    assert settings.allow_test_controls is True


def test_env_aliases_normalize_to_prod():
    settings = Settings(_env_file=None, env="release", debug="false")

    assert settings.runtime_env == "prod"
    assert settings.is_prod is True
    assert settings.is_dev is False
    assert settings.allow_test_controls is False


def test_invalid_debug_value_fails_clearly():
    with pytest.raises(ValidationError, match="DEBUG must be a boolean-like value"):
        Settings(_env_file=None, debug="banana")


def test_invalid_env_value_fails_clearly():
    with pytest.raises(ValidationError, match="ENV must be one of"):
        Settings(_env_file=None, env="staging")
