from .logging_config import configure_logging
from .server import create_mcp

if __name__ == "__main__":
    configure_logging()
    create_mcp().run(
        transport="streamable-http",
        host="0.0.0.0",  # noqa: S104 — container binds all interfaces; ingress restricts exposure
        port=8000,
    )
