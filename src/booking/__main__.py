"""Entry point: python -m booking."""

import uvicorn

from booking.config import ConfigurationError, get_settings
from booking.logging import configure_logging


def main() -> None:
    try:
        settings = get_settings()
    except ConfigurationError as error:
        raise SystemExit(str(error)) from None
    # Before uvicorn starts: its own startup lines must already be JSON (NFR-03).
    configure_logging(settings.log_level)
    uvicorn.run(
        "booking.app:create_app",
        factory=True,
        host="0.0.0.0",  # inside a container the server must accept any address
        port=settings.port,
        log_config=None,  # logging is configured above; uvicorn must not add its own
    )


if __name__ == "__main__":
    main()
