from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.azure import AzureJWTVerifier, AzureProvider
from pydantic import AnyHttpUrl

from ..config import ALLOWED_ROLES, Settings
from ..logging_config import get_logger
from .oauth_storage import build_oauth_client_storage

_logger = get_logger("app.auth.verifier")


class RoleEnforcedJWTVerifier(AzureJWTVerifier):
    """Reject tokens that do not carry an allowed Entra ID role."""

    def __init__(self, *, allowed_roles: frozenset[str], **kwargs):
        super().__init__(**kwargs)
        self._allowed_roles = allowed_roles

    async def verify_token(self, token: str):
        access_token = await super().verify_token(token)
        if access_token is None:
            _logger.warning("auth.token.invalid")
            return None

        claims = access_token.claims or {}
        token_roles = set(claims.get("roles", []))
        granted = token_roles.intersection(self._allowed_roles)
        subject = claims.get("sub") or claims.get("oid")

        if not granted:
            _logger.warning(
                "auth.token.rejected",
                reason="no_allowed_role",
                subject=subject,
                token_roles=sorted(token_roles),
            )
            return None

        _logger.info(
            "auth.token.accepted",
            subject=subject,
            granted_roles=sorted(granted),
        )
        return access_token


def build_auth_provider(settings: Settings) -> RemoteAuthProvider | AzureProvider:
    if settings.auth_mode == "oauth":
        if not settings.client_secret:
            raise ValueError("AUTH_MODE=oauth requires AZURE_CLIENT_SECRET")
        if not settings.oauth_jwt_signing_key:
            raise ValueError("AUTH_MODE=oauth requires FASTMCP_JWT_SIGNING_KEY")
        if not settings.oauth_storage_encryption_key:
            raise ValueError("AUTH_MODE=oauth requires MCP_OAUTH_STORAGE_ENCRYPTION_KEY")
        return AzureProvider(
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            tenant_id=settings.tenant_id,
            base_url=settings.base_url,
            required_scopes=["access_as_user"],
            additional_authorize_scopes=["openid", "profile", "email"],
            jwt_signing_key=settings.oauth_jwt_signing_key,
            client_storage=build_oauth_client_storage(
                storage_dir=settings.oauth_storage_dir,
                encryption_key=settings.oauth_storage_encryption_key,
            ),
        )

    verifier = RoleEnforcedJWTVerifier(
        allowed_roles=ALLOWED_ROLES,
        client_id=settings.client_id,
        tenant_id=settings.tenant_id,
        required_scopes=["access_as_user"],
    )
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[
            AnyHttpUrl(f"https://login.microsoftonline.com/{settings.tenant_id}/v2.0")
        ],
        base_url=settings.base_url,
    )
