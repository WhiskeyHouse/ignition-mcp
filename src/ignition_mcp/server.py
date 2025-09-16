"""MCP server implementation for Ignition Gateway automation."""

import json
import logging
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

from .ignition_client import IgnitionClient
from .ignition_tools import IgnitionTools


class IgnitionMCPServer:
    """MCP server for Ignition Gateway automation."""

    def __init__(self) -> None:
        self.server = Server("ignition-mcp")
        self.ignition_client: Optional[IgnitionClient] = None
        self.ignition_tools: Optional[IgnitionTools] = None
        self._setup_handlers()

    def _get_ignition_tools(self) -> IgnitionTools:
        """Lazy initialization of IgnitionTools."""
        if self.ignition_tools is None:
            self.ignition_tools = IgnitionTools()
        return self.ignition_tools

    def _setup_handlers(self) -> None:
        """Setup MCP server handlers."""

        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools."""
            base_tools = [
                Tool(
                    name="get_gateway_status",
                    description="Get Ignition Gateway status information",
                    inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                ),
                Tool(
                    name="test_connection",
                    description="Test connection to Ignition Gateway",
                    inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                ),
                Tool(
                    name="list_available_tools",
                    description="List all available Ignition Gateway API tools by category",
                    inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                ),
            ]

            # Add generated API tools
            try:
                ignition_tools = self._get_ignition_tools()
                api_tools = ignition_tools.get_tools()
                all_tools = base_tools + api_tools
            except Exception:
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
                            content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                        )

                elif name == "test_connection":
                    async with self.ignition_client as client:
                        try:
                            await client.get_openapi_spec()
                            result = {"status": "success", "message": "Connection successful"}
                        except Exception:
                            logging.exception(
                                "Error testing connection to Ignition Gateway", exc_info=True
                            )
                            result = {
                                "status": "error",
                                "message": "Connection failed. Please check configuration.",
                            }

                        return CallToolResult(
                            content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                        )

                elif name == "list_available_tools":
                    try:
                        ignition_tools = self._get_ignition_tools()
                        summary = ignition_tools.get_available_tools_summary()
                    except Exception:
                        logging.exception("Error loading available tools", exc_info=True)
                        summary = {
                            "error": "Failed to load tools. Please contact support.",
                            "total_tools": 0,
                            "categories": {},
                        }
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(summary, indent=2))]
                    )

                else:
                    # Try to handle as generated API tool
                    try:
                        ignition_tools = self._get_ignition_tools()
                        return await ignition_tools.call_tool(name, arguments)
                    except Exception:
                        logging.exception(f"Error loading tool '{name}'", exc_info=True)
                        return CallToolResult(
                            content=[
                                TextContent(
                                    type="text",
                                    text=f"Tool not available: {name}. Please contact support.",
                                )
                            ],
                            isError=True,
                        )

            except Exception:
                logging.exception(
                    f"Error executing tool '{name}' with arguments {arguments}", exc_info=True
                )
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=f"Error executing {name}. Please contact support."
                        )
                    ],
                    isError=True,
                )

    async def run(self) -> None:
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )
