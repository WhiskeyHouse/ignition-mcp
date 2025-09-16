#!/usr/bin/env python3
"""Minimal MCP server based on official examples."""

import asyncio

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

server = Server("minimal-ignition")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="test_connection",
            description="Test connection",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        types.Tool(
            name="get_projects",
            description="Get projects",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    if name == "test_connection":
        return [
            types.TextContent(type="text", text="Connection test successful from minimal server!")
        ]
    elif name == "get_projects":
        return [
            types.TextContent(
                type="text", text='{"projects": ["MinimalProject1", "MinimalProject2"]}'
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Main function."""
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="minimal-ignition",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
