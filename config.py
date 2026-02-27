"""
Application configuration loaded from environment variables.

Imports validate that all required keys are present and raise a clear
error message naming whichever key is missing, so the developer knows
exactly what to add to their .env file.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def _require(key: str) -> str:
    """
    Return the value of an environment variable or raise with a clear message.
    """

    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is missing or empty. "
            f"Please add it to your .env file."
        )
    return value


OPENAI_API_KEY: str = _require("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()  # optional — bot skipped if absent
DATABASE_URL: str = _require("DATABASE_URL")
