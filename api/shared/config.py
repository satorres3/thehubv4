import os
from typing import Dict


REQUIRED_VARS = [
    "MSAL_CLIENT_ID",
    "MSAL_CLIENT_SECRET",
    "MSAL_TENANT_ID",
    "SESSION_SECRET",
]


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value


# Expose configuration values
MSAL_CLIENT_ID: str = _require_env("MSAL_CLIENT_ID")
MSAL_CLIENT_SECRET: str = _require_env("MSAL_CLIENT_SECRET")
MSAL_TENANT_ID: str = _require_env("MSAL_TENANT_ID")
SESSION_SECRET: str = _require_env("SESSION_SECRET")
APP_URI: str = os.getenv("APP_URI", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

