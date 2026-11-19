"""Entry point: python -m booking."""

import os

import uvicorn


def main() -> None:
    # Temporary: replaced by get_settings() once config.py exists (lab 3A, step 3).
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(
        "booking.app:create_app",
        factory=True,
        host="0.0.0.0",  # inside a container the server must accept any address
        port=port,
        log_config=None,  # logging will be configured by structlog; no second setup
    )


if __name__ == "__main__":
    main()
