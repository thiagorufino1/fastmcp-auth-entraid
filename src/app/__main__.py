import os

import uvicorn

from .logging_config import configure_logging
from .server import create_http_app

if __name__ == "__main__":
    configure_logging()
    host = os.getenv("MCP_HOST", "0.0.0.0")  # noqa: S104
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run(create_http_app(), host=host, port=port)
