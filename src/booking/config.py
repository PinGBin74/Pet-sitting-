"""Service settings read from environment variables and the optional .env file.

Every variable is validated at startup: a wrong value stops the service with a
message that names the variable, instead of failing later on the first request.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

type LogLevel = Literal["debug", "info", "warning", "error"]
type Environment = Literal["development", "test", "production"]


class ConfigurationError(Exception):
    """Settings are missing or invalid. The message never contains the values."""


class Settings(BaseSettings):
    """Variables are documented in .env.example; names are case-insensitive."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        frozen=True,
    )

    port: int = Field(default=8080, ge=1, le=65535)
    log_level: LogLevel = "info"
    environment: Environment = "development"
    app_version: str = Field(default="0.0.0-dev", min_length=1)
    database_url: PostgresDsn = Field(repr=False)

    @field_validator("log_level", "environment", mode="before")
    @classmethod
    def _lowercase(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


def describe_errors(error: ValidationError) -> str:
    """List invalid variables without their values: a value may be a secret."""
    lines = []
    for item in error.errors():
        variable = ".".join(str(part) for part in item["loc"]).upper()
        lines.append(f"  {variable}: {item['msg']}")
    return "Invalid configuration:\n" + "\n".join(lines)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read and validate settings once per process."""
    try:
        return Settings()  # type: ignore[call-arg]  # values come from the environment
    except ValidationError as error:
        # `from None`: the original error text includes the rejected values.
        raise ConfigurationError(describe_errors(error)) from None
