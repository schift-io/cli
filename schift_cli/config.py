from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".schift"
CONFIG_FILE = CONFIG_DIR / "config.json"

ENV_API_KEY = "SCHIFT_API_KEY"
ENV_API_URL = "SCHIFT_API_URL"

DEFAULT_API_URL = "https://api.schift.io/v1"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict[str, Any]) -> None:
    _ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")
    # Restrict permissions — API key lives here
    CONFIG_FILE.chmod(0o600)


def get_api_key() -> str | None:
    """Return API key from env var (highest priority) or config file."""
    env_key = os.environ.get(ENV_API_KEY)
    if env_key:
        return env_key
    return load_config().get("api_key")


def set_api_key(api_key: str) -> None:
    config = load_config()
    config["api_key"] = api_key
    save_config(config)


def clear_api_key() -> None:
    config = load_config()
    config.pop("api_key", None)
    save_config(config)


def get_api_url() -> str:
    return os.environ.get(ENV_API_URL, DEFAULT_API_URL)
