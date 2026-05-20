import os

import uvicorn
from dotenv import find_dotenv, load_dotenv

from .logging_config import configure_logging
from .server import create_http_app


def _load_environment() -> None:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path, override=False, encoding="utf-8-sig")


if __name__ == "__main__":
    _load_environment()
    configure_logging()
    host = os.getenv("MCP_HOST", "0.0.0.0")  # noqa: S104
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run(create_http_app(), host=host, port=port)
