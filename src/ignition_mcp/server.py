"""MCP server implementation for Ignition Gateway automation."""

from typing import Any, Dict, List
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
)
import json
from .ignition_client import IgnitionClient
from .ignition_tools import IgnitionTools
from .config import settings


class IgnitionMCPServer:
    """MCP server for Ignition Gateway automation."""
    
    def __init__(self):
        self.server = Server("ignition-mcp")
        self.ignition_client = None
        self.ignition_tools = None
        self._setup_handlers()
    
    def _get_ignition_tools(self):
        """Lazy initialization of IgnitionTools."""
        if self.ignition_tools is None:
            self.ignition_tools = IgnitionTools()
        return self.ignition_tools
    
    def _setup_handlers(self):
        """Setup MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools."""
            base_tools = [
                Tool(
                    name="get_gateway_status",
                    description="Get Ignition Gateway status information",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                ),
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
                    name="list_available_tools",
                    description="List all available Ignition Gateway API tools by category",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]
            
            # Add generated API tools
            try:
                ignition_tools = self._get_ignition_tools()
                api_tools = ignition_tools.get_tools()
                all_tools = base_tools + api_tools
            except Exception as e:
                # If tool loading fails, just return base tools
                all_tools = base_tools
            
            return ListToolsResult(tools=all_tools)
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            
            if not self.ignition_client:
                self.ignition_client = IgnitionClient()
            
            try:
                # Handle base tools
                if name == "get_gateway_status":
                    async with self.ignition_client as client:
                        result = await client.get_gateway_status()
                        return CallToolResult(
                            content=[
                                TextContent(
                                    type="text",
                                    text=json.dumps(result, indent=2)
                                )
                            ]
                        )
                
                elif name == "test_connection":
                    async with self.ignition_client as client:
                        try:
                            await client.get_openapi_spec()
                            result = {"status": "success", "message": "Connection successful"}
                        except Exception as e:
                            result = {"status": "error", "message": str(e)}
                        
                        return CallToolResult(
                            content=[
                                TextContent(
                                    type="text",
                                    text=json.dumps(result, indent=2)
                                )
                            ]
                        )
                
                elif name == "list_available_tools":
                    try:
                        ignition_tools = self._get_ignition_tools()
                        summary = ignition_tools.get_available_tools_summary()
                    except Exception as e:
                        summary = {"error": f"Failed to load tools: {str(e)}", "total_tools": 0, "categories": {}}
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=json.dumps(summary, indent=2)
                            )
                        ]
                    )
                
                else:
                    # Try to handle as generated API tool
                    try:
                        ignition_tools = self._get_ignition_tools()
                        return await ignition_tools.call_tool(name, arguments)
                    except Exception as e:
                        return CallToolResult(
                            content=[TextContent(type="text", text=f"Tool not available: {name}. Error: {str(e)}")],
                            isError=True
                        )
            
            except Exception as e:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error executing {name}: {str(e)}"
                        )
                    ],
                    isError=True
                )
    
    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )