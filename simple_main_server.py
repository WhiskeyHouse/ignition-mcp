#!/usr/bin/env python3
"""Simplified main server for testing."""

import asyncio
import json
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult, ListToolsResult


async def main():
    """Run simplified MCP server."""
    server = Server("ignition-mcp")
    
    @server.list_tools()
    async def list_tools() -> ListToolsResult:
        print("DEBUG: Simplified list_tools called", file=sys.stderr)
        
        tools = [
            Tool(
                name="test_connection",
                description="Test connection to Ignition Gateway",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            Tool(
                name="get_projects_list",
                description="List all projects in Ignition Gateway",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            )
        ]
        
        print(f"DEBUG: Returning {len(tools)} tools", file=sys.stderr)
        return ListToolsResult(tools=tools)
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> CallToolResult:
        print(f"DEBUG: call_tool called with name={name}", file=sys.stderr)
        
        if name == "test_connection":
            return CallToolResult(
                content=[TextContent(type="text", text='{"status": "success", "message": "Simplified server working!"}')]
            )
        elif name == "get_projects_list":
            return CallToolResult(
                content=[TextContent(type="text", text='{"projects": ["TestProject1", "TestProject2"], "count": 2}')]
            )
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True
        )
    
    print("DEBUG: Starting simplified MCP server...", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())