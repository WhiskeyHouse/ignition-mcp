"""Main entry point for Ignition MCP server."""

import asyncio

from .server import IgnitionMCPServer


async def main() -> None:
    """Run the Ignition MCP server."""
    server = IgnitionMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
