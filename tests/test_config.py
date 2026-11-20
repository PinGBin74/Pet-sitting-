"""Settings: defaults, validation, secrets kept out of messages."""

from pathlib import Path

import pytest

from booking.config import ConfigurationError, Settings, get_settings
from tests.conftest import TEST_DATABASE_URL


def make_settings(**values: object) -> Settings:
    """Settings from explicit values only: the developer's .env must not leak in."""
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_defaults_match_env_example() -> None:
    settings = make_settings()

    assert settings.port == 8080
    assert settings.log_level == "info"
    assert settings.environment == "development"
    assert settings.app_version == "0.0.0-dev"
    assert str(settings.database_url) == TEST_DATABASE_URL


def test_values_are_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_VERSION", "1.2.3")

    settings = make_settings()

    assert settings.port == 9000
    assert settings.log_level == "warning"
    assert settings.environment == "production"
    assert settings.app_version == "1.2.3"


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.chdir(tmp_path)  # no .env in the working directory

    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        get_settings()


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("PORT", "0"),
        ("PORT", "70000"),
        ("PORT", "eighty"),
        ("LOG_LEVEL", "verbose"),
        ("ENVIRONMENT", "staging"),
        ("DATABASE_URL", "not a url"),
    ],
)
def test_invalid_value_names_the_variable(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    monkeypatch.setenv(variable, value)

    with pytest.raises(ConfigurationError, match=variable):
        get_settings()


def test_error_message_does_not_contain_the_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "mysql://user:s3cret@db/app")

    with pytest.raises(ConfigurationError) as error:
        get_settings()

    assert "s3cret" not in str(error.value)
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


def test_repr_does_not_contain_the_database_url() -> None:
    settings = make_settings(database_url="postgresql://user:s3cret@db/app")

    assert "s3cret" not in repr(settings)


def test_settings_are_read_once_per_process() -> None:
    assert get_settings() is get_settings()


def test_settings_cannot_be_changed_after_start() -> None:
    settings = make_settings()

    with pytest.raises(ValueError, match="frozen"):
        settings.port = 1


def test_unknown_key_in_env_file_is_rejected(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"DATABASE_URL={TEST_DATABASE_URL}\nLOG_LEVL=info\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="LOG_LEVL"):
        Settings(_env_file=env_file)  # type: ignore[call-arg]
