#!/usr/bin/env python3
"""
Simple FastMCP server for Cursor integration
Runs on port 8007 alongside the FastAPI server on port 8006
"""

import os
import sys
from fastmcp import FastMCP

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from ignition_mcp.ignition_client import IgnitionClient
    from ignition_mcp.ignition_tools import IgnitionTools
except ImportError as e:
    print(f"Warning: Could not import Ignition modules: {e}")
    IgnitionClient = None
    IgnitionTools = None

# Create FastMCP server
mcp = FastMCP("Ignition FastMCP Server")


# Dynamic tool creation from Ignition Tools
async def create_ignition_tools():
    """Create FastMCP tools dynamically from available Ignition tools"""
    if not IgnitionTools:
        print("⚠️  Ignition tools not available, creating mock tools only")
        create_mock_tools()
        return

    try:
        tools = IgnitionTools()
        tool_list = tools.get_tools()

        print(f"🔧 Creating {len(tool_list)} Ignition tools for FastMCP...")

        for tool in tool_list:
            create_dynamic_tool(tool.name, tool.description, tool.inputSchema)

        print("✅ All Ignition tools created successfully!")

    except Exception as e:
        print(f"❌ Failed to create Ignition tools: {e}")
        import traceback

        traceback.print_exc()
        print("🔄 Falling back to mock tools...")
        create_mock_tools()


def create_dynamic_tool(tool_name: str, description: str, input_schema: dict):
    """Create a dynamic FastMCP tool for an Ignition tool"""
    from typing import Any, Optional, Union

    # Extract parameters from input schema
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    # Build parameter string for function definition
    param_strs = []
    param_annotations = {}

    # Keep track of original parameter names for mapping
    param_mapping = {}

    for param_name, param_def in properties.items():
        param_type = param_def.get("type", "string")

        # Sanitize parameter name to make it a valid Python identifier
        sanitized_name = param_name.replace("-", "_").replace(".", "_")
        # Ensure it doesn't start with a number and isn't empty
        if not sanitized_name or sanitized_name[0].isdigit():
            sanitized_name = f"param_{sanitized_name}"
        # Remove any other invalid characters
        sanitized_name = "".join(c if c.isalnum() or c == "_" else "_" for c in sanitized_name)

        param_mapping[sanitized_name] = param_name

        # Convert JSON schema types to Python types
        if param_type == "string":
            annotation = str
        elif param_type == "integer":
            annotation = int
        elif param_type == "number":
            annotation = Union[int, float]
        elif param_type == "boolean":
            annotation = bool
        elif isinstance(param_type, list):
            # Handle multiple types like ["string", "number", "boolean", "object", "array", "null"]
            annotation = Any
        else:
            annotation = Any

        # Make parameter optional if not required
        if param_name not in required:
            annotation = Optional[annotation]
            param_strs.append(f"{sanitized_name}=None")
        else:
            param_strs.append(sanitized_name)

        param_annotations[sanitized_name] = annotation

    # Create function dynamically using exec
    param_list = ", ".join(param_strs)

    # Build the function code
    func_code = f'''
async def {tool_name}({param_list}) -> dict:
    """Dynamic tool function that calls the corresponding Ignition tool"""
    if not IgnitionTools:
        return {{"error": "Ignition tools not available", "source": "fastmcp"}}

    # Build call arguments from parameters, mapping sanitized names back to originals
    call_args = {{}}
    locals_dict = locals()
    param_mapping = {param_mapping}
    for sanitized_name, original_name in param_mapping.items():
        if sanitized_name in locals_dict and locals_dict[sanitized_name] is not None:
            call_args[original_name] = locals_dict[sanitized_name]

    try:
        tools = IgnitionTools()
        result = await tools.call_tool("{tool_name}", call_args)

        if result.isError:
            return {{
                "error": f"Ignition tool '{tool_name}' failed",
                "details": result.content[0].text if result.content else "No details",
                "source": "fastmcp_ignition",
            }}

        # Try to parse JSON response, fallback to raw text
        try:
            import json

            data = json.loads(result.content[0].text)
            return {{
                "success": True,
                "data": data,
                "source": "fastmcp_ignition",
                "tool": "{tool_name}",
            }}
        except (json.JSONDecodeError, AttributeError):
            return {{
                "success": True,
                "data": result.content[0].text if result.content else "No response",
                "source": "fastmcp_ignition",
                "tool": "{tool_name}",
            }}

    except Exception as e:
        return {{
            "error": f"Failed to call Ignition tool '{tool_name}': {{str(e)}}",
            "source": "fastmcp",
        }}
'''

    # Create the function in a local namespace
    namespace = {
        "IgnitionTools": IgnitionTools,
        "Optional": Optional,
        "Union": Union,
        "Any": Any,
    }

    exec(func_code, namespace)
    tool_function = namespace[tool_name]

    # Set annotations
    tool_function.__annotations__ = param_annotations.copy()
    tool_function.__annotations__["return"] = dict
    tool_function.__doc__ = description

    # Use the @mcp.tool() decorator approach by calling it manually
    decorated_tool = mcp.tool()(tool_function)

    return decorated_tool


def create_mock_tools():
    """Create mock tools when Ignition tools are not available"""

    @mcp.tool()
    def test_connection() -> dict:
        """Test connection to Ignition Gateway"""
        return {
            "status": "success",
            "message": "FastMCP mock connection test",
            "source": "fastmcp_mock",
        }

    @mcp.tool()
    def get_projects_list() -> dict:
        """List all projects in Ignition Gateway"""
        return {
            "projects": ["MockProject1", "MockProject2", "MockProject3"],
            "count": 3,
            "source": "fastmcp_mock",
        }

    @mcp.tool()
    def get_activation_is_online() -> dict:
        """Check if Ignition Gateway is online"""
        return {"online": True, "status": "FastMCP mock connection", "source": "fastmcp_mock"}


# Enhanced tag provider creation tool
@mcp.tool()
async def create_tag_provider(
    name: str, description: str = "Tag provider created via MCP", enabled: bool = True
) -> dict:
    """Create a new tag provider in Ignition Gateway"""
    if not IgnitionTools:
        return {
            "success": True,
            "message": f"Mock tag provider created: {name}",
            "source": "fastmcp_mock",
        }

    try:
        # Use direct HTTP call since this isn't in the standard Ignition tools
        import httpx
        from src.ignition_mcp.config import settings

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ignition_gateway_url}/data/api/v1/resources/ignition/tag-provider",
                headers={
                    "X-Ignition-API-Token": settings.ignition_api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=[
                    {
                        "name": name,
                        "collection": "core",
                        "enabled": enabled,
                        "description": description,
                        "config": {
                            "profile": {
                                "type": "STANDARD",
                                "allowBackfill": False,
                                "enableTagReferenceStore": True,
                            },
                            "settings": {"nonUseCount": 0},
                        },
                        "backupConfig": {
                            "profile": {
                                "type": "STANDARD",
                                "allowBackfill": False,
                                "enableTagReferenceStore": True,
                            },
                            "settings": {"nonUseCount": 0},
                        },
                    }
                ],
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Tag provider '{name}' created successfully",
                    "data": response.json(),
                    "source": "fastmcp_ignition",
                }
            else:
                return {
                    "error": f"Failed to create tag provider '{name}'",
                    "status_code": response.status_code,
                    "details": response.text,
                    "source": "fastmcp_ignition",
                }

    except Exception as e:
        return {"error": f"Failed to create tag provider '{name}': {str(e)}", "source": "fastmcp"}


# Enhanced tag creation tool with parameters
@mcp.tool()
async def create_tag(tag_path: str, value: str = "0", data_type: str = "Int4") -> dict:
    """Create or update an Ignition tag with specified parameters"""
    if not IgnitionTools:
        return {
            "success": True,
            "message": f"Mock tag created: {tag_path} = {value} ({data_type})",
            "source": "fastmcp_mock",
        }

    try:
        tools = IgnitionTools()
        # Call the create_or_update_tag tool with proper parameters
        result = await tools.call_tool(
            "create_or_update_tag", {"tagPath": tag_path, "value": value, "dataType": data_type}
        )

        if result.isError:
            return {
                "error": f"Failed to create tag '{tag_path}'",
                "details": result.content[0].text if result.content else "No details",
                "source": "fastmcp_ignition",
            }

        # Parse the response
        try:
            import json

            data = json.loads(result.content[0].text)
            return {
                "success": True,
                "message": f"Tag '{tag_path}' created/updated successfully",
                "data": data,
                "source": "fastmcp_ignition",
            }
        except (json.JSONDecodeError, AttributeError):
            return {
                "success": True,
                "message": f"Tag '{tag_path}' created/updated",
                "data": result.content[0].text if result.content else "Success",
                "source": "fastmcp_ignition",
            }

    except Exception as e:
        return {"error": f"Failed to create tag '{tag_path}': {str(e)}", "source": "fastmcp"}


# Enhanced tag update tool
@mcp.tool()
async def update_tag(tag_path: str, value: str, data_type: str = "Int4") -> dict:
    """Update an existing Ignition tag with new value and/or data type"""
    if not IgnitionTools:
        return {
            "success": True,
            "message": f"Mock tag updated: {tag_path} = {value} ({data_type})",
            "source": "fastmcp_mock",
        }

    try:
        tools = IgnitionTools()
        # Call the create_or_update_tag tool (it handles both create and update)
        result = await tools.call_tool(
            "create_or_update_tag", {"tagPath": tag_path, "value": value, "dataType": data_type}
        )

        if result.isError:
            return {
                "error": f"Failed to update tag '{tag_path}'",
                "details": result.content[0].text if result.content else "No details",
                "source": "fastmcp_ignition",
            }

        # Parse the response
        try:
            import json

            data = json.loads(result.content[0].text)
            return {
                "success": True,
                "message": f"Tag '{tag_path}' updated successfully",
                "data": data,
                "source": "fastmcp_ignition",
            }
        except (json.JSONDecodeError, AttributeError):
            return {
                "success": True,
                "message": f"Tag '{tag_path}' updated",
                "data": result.content[0].text if result.content else "Success",
                "source": "fastmcp_ignition",
            }

    except Exception as e:
        return {"error": f"Failed to update tag '{tag_path}': {str(e)}", "source": "fastmcp"}


# Enhanced tag delete tool
@mcp.tool()
async def delete_tag(tag_path: str) -> dict:
    """Delete an Ignition tag"""
    if not IgnitionTools:
        return {
            "success": True,
            "message": f"Mock tag deleted: {tag_path}",
            "source": "fastmcp_mock",
        }

    try:
        # Use direct HTTP call for tag deletion
        import httpx
        from src.ignition_mcp.config import settings

        async with httpx.AsyncClient() as client:
            # Delete tag using WebDev endpoint (assuming it supports DELETE)
            response = await client.delete(
                f"{settings.ignition_gateway_url}/system/webdev/tags",
                headers={
                    "X-Ignition-API-Token": settings.ignition_api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"tagPath": tag_path},
            )

            if response.status_code in [200, 204]:
                return {
                    "success": True,
                    "message": f"Tag '{tag_path}' deleted successfully",
                    "source": "fastmcp_ignition",
                }
            else:
                return {
                    "error": f"Failed to delete tag '{tag_path}'",
                    "status_code": response.status_code,
                    "details": response.text,
                    "source": "fastmcp_ignition",
                }

    except Exception as e:
        return {"error": f"Failed to delete tag '{tag_path}': {str(e)}", "source": "fastmcp"}


# Enhanced tag read tool
@mcp.tool()
async def read_tag(tag_path: str) -> dict:
    """Read the current value of an Ignition tag"""
    if not IgnitionTools:
        return {
            "success": True,
            "value": "42",
            "quality": "Good",
            "timestamp": "2025-09-17T04:30:00Z",
            "message": f"Mock tag read: {tag_path}",
            "source": "fastmcp_mock",
        }

    try:
        # Use direct HTTP call for tag reading
        import httpx
        from src.ignition_mcp.config import settings

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.ignition_gateway_url}/system/webdev/tags",
                headers={
                    "X-Ignition-API-Token": settings.ignition_api_key,
                    "Accept": "application/json",
                },
                params={"tagPath": tag_path},
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "tag_path": tag_path,
                    "data": data,
                    "source": "fastmcp_ignition",
                }
            else:
                return {
                    "error": f"Failed to read tag '{tag_path}'",
                    "status_code": response.status_code,
                    "details": response.text,
                    "source": "fastmcp_ignition",
                }

    except Exception as e:
        return {"error": f"Failed to read tag '{tag_path}': {str(e)}", "source": "fastmcp"}


async def main():
    """Main function to set up tools and run the server"""
    print("🚀 Starting comprehensive FastMCP server for Cursor...")
    print("🔧 MCP Client Config: http://localhost:8007/mcp")
    print("🔗 This server runs alongside FastAPI on port 8006")

    # Create all Ignition tools dynamically
    await create_ignition_tools()

    # Run in HTTP mode on port 8007
    await mcp.run_async(host="0.0.0.0", port=8007, transport="http")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
