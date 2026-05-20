from fastmcp import FastMCP

from .auth import build_auth_provider
from .config import load_settings
from .middleware import AuditMiddleware
from .tools import register_tools


def create_mcp() -> FastMCP:
    settings = load_settings()
    mcp = FastMCP("mcp-lab", auth=build_auth_provider(settings))
    mcp.add_middleware(AuditMiddleware())
    register_tools(mcp)
    return mcp
