"""Ignition Gateway API tools for MCP server."""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.types import CallToolResult, TextContent, Tool

from .api_generator import IgnitionAPIGenerator
from .ignition_client import IgnitionClient


class IgnitionTools:
    """Handles Ignition Gateway API tools for MCP server."""

    def __init__(self) -> None:
        self.generator = IgnitionAPIGenerator()
        self.tools_cache: Optional[List[Dict[str, Any]]] = None
        self.custom_tool_defs = self._build_custom_tool_definitions()
        self.custom_tool_handlers = {
            "create_or_update_tag": self._tool_create_or_update_tag,
        }

    def _build_custom_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Define custom MCP tools that are not generated from OpenAPI."""
        input_schema = {
            "type": "object",
            "properties": {
                "tagPath": {
                    "type": "string",
                    "description": "Fully qualified Ignition tag path, e.g. `[default]Folder/TagName`.",
                },
                "value": {
                    "type": ["string", "number", "boolean", "object", "array", "null"],
                    "description": "Value to write when auto-generating the payload.",
                },
                "dataType": {
                    "type": "string",
                    "description": "Optional Ignition data type (String, Integer, Boolean, etc.).",
                },
                "attributes": {
                    "type": "object",
                    "description": "Optional tag attribute overrides such as EngUnit or Tooltip.",
                    "additionalProperties": True,
                },
                "resourcePath": {
                    "type": "string",
                    "description": "Override WebDev resource path relative to /system/webdev.",
                },
                "httpMethod": {
                    "type": "string",
                    "description": "HTTP method to use for the WebDev call (defaults to configuration).",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                },
                "payloadOverride": {
                    "description": "Send this JSON payload directly instead of using tagPath/value.",
                    "anyOf": [
                        {"type": "object", "additionalProperties": True},
                        {"type": "array"},
                    ],
                },
                "queryParams": {
                    "type": "object",
                    "description": "Optional query string parameters for the WebDev request.",
                    "additionalProperties": {"type": "string"},
                },
                "headers": {
                    "type": "object",
                    "description": "Optional additional headers to include in the request.",
                    "additionalProperties": {"type": "string"},
                },
                "valueTimestamp": {
                    "type": "string",
                    "description": "Optional ISO-8601 timestamp associated with the tag value.",
                },
                "quality": {
                    "type": "string",
                    "description": "Optional quality code for the tag write (e.g. 'Good').",
                },
            },
            "required": [],
            "additionalProperties": False,
        }

        return {
            "create_or_update_tag": {
                "name": "create_or_update_tag",
                "description": "Create or update an Ignition tag using a configured WebDev endpoint.",
                "inputSchema": input_schema,
            }
        }

    def _error_result(self, message: str) -> CallToolResult:
        """Return a standardized error result."""
        return CallToolResult(
            content=[TextContent(type="text", text=message)],
            isError=True,
        )

    async def _tool_create_or_update_tag(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handler for creating or updating tags via WebDev."""

        payload_override = arguments.get("payloadOverride")
        if payload_override is not None and not isinstance(payload_override, (dict, list)):
            return self._error_result("payloadOverride must be an object or array when provided")

        attributes = arguments.get("attributes")
        if attributes is not None and not isinstance(attributes, dict):
            return self._error_result("attributes must be an object when provided")

        headers = arguments.get("headers")
        if headers is not None and not isinstance(headers, dict):
            return self._error_result("headers must be an object of string values when provided")

        query_params = arguments.get("queryParams")
        if query_params is not None and not isinstance(query_params, dict):
            return self._error_result("queryParams must be an object when provided")

        method = arguments.get("httpMethod")
        if method is not None and not isinstance(method, str):
            return self._error_result("httpMethod must be a string when provided")

        tag_path = arguments.get("tagPath")
        if payload_override is None and not tag_path:
            return self._error_result("tagPath is required when payloadOverride is not provided")

        value_provided = "value" in arguments
        if payload_override is None and not value_provided:
            return self._error_result("value is required when payloadOverride is not provided")

        try:
            async with IgnitionClient() as client:
                result = await client.create_or_update_tag(
                    tag_path=tag_path,
                    value=arguments.get("value"),
                    data_type=arguments.get("dataType"),
                    attributes=attributes,
                    resource_path=arguments.get("resourcePath"),
                    method=method,
                    payload_override=payload_override,
                    query_params=query_params,
                    headers=headers,
                    value_timestamp=arguments.get("valueTimestamp"),
                    quality=arguments.get("quality"),
                )
        except ValueError as exc:
            return self._error_result(str(exc))
        except Exception:
            logging.exception("Error executing create_or_update_tag", exc_info=True)
            return self._error_result(
                "Error executing create_or_update_tag. Please verify the WebDev configuration."
            )

        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])

    def get_tools(self) -> List[Tool]:
        """Get list of MCP tools from OpenAPI spec."""
        if self.tools_cache is None:
            self._generate_tools_cache()

        tools = []
        for tool_def in self.custom_tool_defs.values():
            tools.append(
                Tool(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    inputSchema=tool_def["inputSchema"],
                )
            )

        if self.tools_cache:
            for tool_def in self.tools_cache:
                tools.append(
                    Tool(
                        name=tool_def["name"],
                        description=tool_def["description"],
                        inputSchema=tool_def["inputSchema"],
                    )
                )

        return tools

    def _generate_tools_cache(self) -> None:
        """Generate and cache tools from OpenAPI spec."""
        self.tools_cache = self.generator.generate_tools()

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute an Ignition Gateway API call or custom handler."""
        if name in self.custom_tool_defs:
            handler = self.custom_tool_handlers.get(name)
            if handler is None:
                return self._error_result(f"No handler registered for tool '{name}'")
            return await handler(arguments)

        if self.tools_cache is None:
            self._generate_tools_cache()

        # Find tool definition
        tool_def = None
        if self.tools_cache:
            for tool in self.tools_cache:
                if tool["name"] == name:
                    tool_def = tool
                    break

        if not tool_def:
            return self._error_result(f"Tool '{name}' not found")

        try:
            # Execute API call
            async with IgnitionClient() as client:
                result = await self._execute_api_call(client, tool_def, arguments)

                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
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

    async def _execute_api_call(
        self, client: IgnitionClient, tool_def: Dict[str, Any], arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the actual API call."""
        path = tool_def["_ignition_path"]
        method = tool_def["_ignition_method"]

        # Replace path parameters
        final_path = path
        path_params = {}
        body_params = {}
        query_params = {}

        for key, value in arguments.items():
            if key.startswith("body_"):
                body_params[key[5:]] = value
            elif "{" + key + "}" in path:
                final_path = final_path.replace("{" + key + "}", str(value))
                path_params[key] = value
            else:
                query_params[key] = value

        # Prepare request kwargs
        kwargs = {}
        if query_params:
            kwargs["params"] = query_params
        if body_params:
            kwargs["json"] = body_params

        # Make the API call
        return await client._request(method, final_path, **kwargs)

    def get_available_tools_summary(self) -> Dict[str, Any]:
        """Get a summary of available tools."""
        if self.tools_cache is None:
            self._generate_tools_cache()

        categories: Dict[str, List[Dict[str, Any]]] = {}
        total_tools = 0

        if self.tools_cache:
            for tool in self.tools_cache:
                path_parts = tool["_ignition_path"].split("/")
                category = path_parts[4] if len(path_parts) > 4 else "general"

                if category not in categories:
                    categories[category] = []

                categories[category].append(
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "method": tool["_ignition_method"],
                        "path": tool["_ignition_path"],
                    }
                )

            total_tools += len(self.tools_cache)

        if self.custom_tool_defs:
            custom_category = categories.setdefault("custom", [])
            for tool in self.custom_tool_defs.values():
                custom_category.append(
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "method": "CUSTOM",
                        "path": "webdev",
                    }
                )

            total_tools += len(self.custom_tool_defs)

        return {"total_tools": total_tools, "categories": categories}
