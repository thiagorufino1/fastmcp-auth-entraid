from fastmcp import FastMCP

from .auth import build_auth_provider
from .tools import register_tools

mcp = FastMCP("mcp-lab", auth=build_auth_provider())

register_tools(mcp)

