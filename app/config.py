from __future__ import annotations

import os
import sys
from getpass import getpass
from pathlib import Path

from app.services.config_service import ConfigService


def _default_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


BASE_DIR = Path(os.getenv("INTERN_ASSISTANT_ROOT", _default_base_dir()))
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", BASE_DIR / "vault"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "database" / "intern_assistant.db"))
LOCAL_ENV_PATH = Path(os.getenv("LOCAL_ENV_PATH", BASE_DIR / ".env.local"))

_config_service = ConfigService(LOCAL_ENV_PATH)

def get_google_api_key() -> str | None:
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return api_key
    stored = _config_service.load().get("GOOGLE_API_KEY")
    if stored:
        os.environ["GOOGLE_API_KEY"] = stored
        return stored
    if sys.stdin and sys.stdin.isatty():
        try:
            api_key = getpass("Enter GOOGLE_API_KEY (Gemini): ").strip()
        except EOFError:
            api_key = ""
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            _config_service.save({"GOOGLE_API_KEY": api_key})
            return api_key
    return None


def get_gemini_model() -> str:
    stored = _config_service.load().get("GEMINI_MODEL")
    return os.getenv("GEMINI_MODEL", stored or "gemini-2.5-flash")
