from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.azure import AzureJWTVerifier, AzureProvider
from pydantic import AnyHttpUrl

from ..config import ALLOWED_ROLES, AUTH_MODE, BASE_URL, CLIENT_ID, CLIENT_SECRET, TENANT_ID


class RoleEnforcedJWTVerifier(AzureJWTVerifier):
    """Rejeita na conexão (401) tokens sem nenhuma role válida do Entra ID."""

    async def verify_token(self, token: str):
        access_token = await super().verify_token(token)
        if access_token is None:
            return None
        roles = set(access_token.claims.get("roles", []))
        if not roles.intersection(ALLOWED_ROLES):
            return None
        return access_token


def build_auth_provider() -> RemoteAuthProvider | AzureProvider:
    if AUTH_MODE == "oauth":
        if not CLIENT_SECRET:
            raise ValueError("AUTH_MODE=oauth requer AZURE_CLIENT_SECRET no .env")
        return AzureProvider(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            tenant_id=TENANT_ID,
            base_url=BASE_URL,
            required_scopes=["access_as_user"],
            additional_authorize_scopes=["openid", "profile", "email"],
        )

    # Padrão: jwt
    verifier = RoleEnforcedJWTVerifier(
        client_id=CLIENT_ID,
        tenant_id=TENANT_ID,
        required_scopes=["access_as_user"],
    )
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[
            AnyHttpUrl(f"https://login.microsoftonline.com/{TENANT_ID}/v2.0")
        ],
        base_url=BASE_URL,
    )
