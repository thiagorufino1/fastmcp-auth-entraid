from fastmcp.server.auth.authorization import AuthCheck, AuthContext


def require_roles(*roles: str) -> AuthCheck:
    """AuthCheck que valida App Roles do Entra ID (claim 'roles').

    Passa se token tiver qualquer uma das roles especificadas (OR).
    Usado em auth= por tool para filtrar tools/list e bloquear execução.
    """
    required = set(roles)

    def check(ctx: AuthContext) -> bool:
        if ctx.token is None:
            return False
        token_roles = set(ctx.token.claims.get("roles", []))
        return bool(token_roles.intersection(required))

    return check
