"""Main entry point for Ignition MCP server (module invocation)."""

import os
import sys

# Ensure the project root is importable so mcp_server.py can find src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def main() -> None:
    from mcp_server import main as _main

    _main()


if __name__ == "__main__":
    main()
