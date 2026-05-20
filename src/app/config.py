from dataclasses import dataclass
from functools import lru_cache
import os

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_AUTH_MODE = "jwt"
ALLOWED_ROLES = frozenset({"mcp-trc-read", "mcp-trc-admin"})


@dataclass(frozen=True, slots=True)
class Settings:
    tenant_id: str
    client_id: str
    client_secret: str = ""
    base_url: str = DEFAULT_BASE_URL
    auth_mode: str = DEFAULT_AUTH_MODE


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    auth_mode = os.getenv("AUTH_MODE", DEFAULT_AUTH_MODE).strip().lower()
    if auth_mode not in {"jwt", "oauth"}:
        raise ValueError("AUTH_MODE must be either 'jwt' or 'oauth'")

    base_url = os.getenv("MCP_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL

    return Settings(
        tenant_id=_env("AZURE_TENANT_ID"),
        client_id=_env("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET", "").strip(),
        base_url=base_url,
        auth_mode=auth_mode,
    )
