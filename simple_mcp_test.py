#!/usr/bin/env python3
"""Simple MCP server for testing."""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool


async def main():
    """Run a simple MCP server."""
    server = Server("test-mcp")

    @server.list_tools()
    async def list_tools() -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name="hello",
                    description="Say hello",
                    inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                )
            ]
        )

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> CallToolResult:
        if name == "hello":
            return CallToolResult(
                content=[TextContent(type="text", text="Hello from test MCP server!")]
            )

        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")], isError=True
        )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
