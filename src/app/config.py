import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_dir

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_AUTH_MODE = "jwt"
DEFAULT_OAUTH_STORAGE_DIR = str(Path(user_data_dir("fastmcp-auth-entraid")) / "oauth")
ALLOWED_ROLES = frozenset({"mcp-trc-read", "mcp-trc-admin"})


@dataclass(frozen=True, slots=True)
class Settings:
    tenant_id: str
    client_id: str
    client_secret: str = ""
    base_url: str = DEFAULT_BASE_URL
    auth_mode: str = DEFAULT_AUTH_MODE
    trust_proxy_headers: bool = False
    oauth_jwt_signing_key: str = ""
    oauth_storage_dir: str = DEFAULT_OAUTH_STORAGE_DIR
    oauth_storage_encryption_key: str = ""


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


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
        trust_proxy_headers=_env_bool("TRUST_PROXY_HEADERS", False),
        oauth_jwt_signing_key=os.getenv("FASTMCP_JWT_SIGNING_KEY", "").strip(),
        oauth_storage_dir=os.getenv("MCP_OAUTH_STORAGE_DIR", DEFAULT_OAUTH_STORAGE_DIR).strip()
        or DEFAULT_OAUTH_STORAGE_DIR,
        oauth_storage_encryption_key=os.getenv("MCP_OAUTH_STORAGE_ENCRYPTION_KEY", "").strip(),
    )
