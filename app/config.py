import os

TENANT_ID     = os.environ["AZURE_TENANT_ID"]
CLIENT_ID     = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
BASE_URL      = os.environ.get("MCP_BASE_URL", "http://localhost:8000")
AUTH_MODE     = os.environ.get("AUTH_MODE", "jwt").lower()  # "jwt" | "oauth"

ALLOWED_ROLES = {"mcp-trc-read", "mcp-trc-admin"}
