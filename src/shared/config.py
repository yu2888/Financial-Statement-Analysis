"""Load configuration from .env file."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    model: str
    base_url: str
    api_key: str


def load_config(env_path: Path | None = None) -> Config:
    """Load config from .env file, falling back to defaults."""
    values: dict[str, str] = {}

    # Find .env: explicit path > project root > cwd
    if env_path is None:
        candidates = [
            Path(__file__).resolve().parents[2] / ".env",  # src/../.env
            Path.cwd() / ".env",
        ]
        for c in candidates:
            if c.exists():
                env_path = c
                break

    if env_path and env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()

    # Env vars override .env file
    for key in ["MODEL", "BASE_URL", "API_KEY"]:
        env_val = os.environ.get(key)
        if env_val:
            values[key] = env_val

    return Config(
        model=values["MODEL"],
        base_url=values["BASE_URL"],
        api_key=values["API_KEY"],
    )
