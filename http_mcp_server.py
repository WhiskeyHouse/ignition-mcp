#!/usr/bin/env python3
"""HTTP-based MCP server for Ignition Gateway."""

import asyncio
import json
from typing import Any, Dict
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, CallToolResult, ListToolsResult
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route


class IgnitionHTTPMCPServer:
    """HTTP-based MCP server for Ignition Gateway."""
    
    def __init__(self):
        self.server = Server("ignition-http-mcp")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools."""
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
                ),
                Tool(
                    name="get_activation_is_online",
                    description="Check if Ignition Gateway is online",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            
            if name == "test_connection":
                return CallToolResult(
                    content=[TextContent(
                        type="text", 
                        text='{"status": "success", "message": "HTTP MCP server is working!"}'
                    )]
                )
            elif name == "get_projects_list":
                return CallToolResult(
                    content=[TextContent(
                        type="text", 
                        text='{"projects": ["HTTPProject1", "HTTPProject2"], "count": 2, "source": "HTTP MCP"}'
                    )]
                )
            elif name == "get_activation_is_online":
                return CallToolResult(
                    content=[TextContent(
                        type="text", 
                        text='{"online": true, "status": "HTTP MCP connection successful"}'
                    )]
                )
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )

    async def handle_sse(self, request):
        """Handle SSE connection for MCP."""
        transport = SseServerTransport("/message")
        async with transport.connect_sse(request) as streams:
            await self.server.run(
                streams[0], streams[1], 
                self.server.create_initialization_options()
            )

    def create_app(self):
        """Create Starlette application."""
        routes = [
            Route("/sse", self.handle_sse),
        ]
        
        app = Starlette(routes=routes)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        return app


async def main():
    """Run the HTTP MCP server."""
    mcp_server = IgnitionHTTPMCPServer()
    app = mcp_server.create_app()
    
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    print("Starting HTTP MCP server on http://127.0.0.1:8001")
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())