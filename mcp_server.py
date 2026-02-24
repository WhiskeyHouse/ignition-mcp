#!/usr/bin/env python3
"""Ignition MCP Server — FastMCP server for the Ignition Gateway REST API.

Provides curated, well-described tools that give AI assistants a developer-oriented
interface to the Ignition Gateway. Supports streamable HTTP (default) and stdio transports.

Usage:
    uv run python mcp_server.py                     # HTTP on port 8007
    uv run python mcp_server.py --transport stdio    # stdio for Claude Desktop
"""

import argparse
import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastmcp import FastMCP

# Ensure src/ is importable when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ignition_mcp.config import settings
from ignition_mcp.ignition_client import IgnitionClient
from ignition_mcp.tools import register_all

logger = logging.getLogger("ignition-mcp")


# ---------------------------------------------------------------------------
# Lifespan — one shared IgnitionClient for the server's lifetime
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncGenerator[dict, None]:
    """Create and share a single IgnitionClient across all tool calls."""
    client = IgnitionClient()
    logger.info("IgnitionClient initialised — %s", client.gateway_url)
    try:
        yield {"client": client}
    finally:
        await client.close()
        logger.info("IgnitionClient closed")


mcp = FastMCP("ignition-mcp", lifespan=lifespan)
register_all(mcp)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Ignition MCP Server")
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "stdio"],
        default="streamable-http",
        help="MCP transport (default: streamable-http)",
    )
    parser.add_argument("--host", default=settings.server_host)
    parser.add_argument("--port", type=int, default=settings.server_port)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
