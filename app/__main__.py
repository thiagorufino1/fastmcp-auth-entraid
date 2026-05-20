from .main import create_mcp


if __name__ == "__main__":
    create_mcp().run(transport="streamable-http", host="0.0.0.0", port=8000)
