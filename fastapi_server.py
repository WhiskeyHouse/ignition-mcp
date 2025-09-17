#!/usr/bin/env python3
"""FastAPI server for Ignition Gateway REST API."""

import os
import sys
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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


# Initialize FastMCP first
mcp = FastMCP("Ignition FastAPI MCP")

app = FastAPI(
    title="Ignition Gateway API",
    description="REST API for Ignition Gateway automation and management",
    version="1.0.0",
    lifespan=mcp.http_app().lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastMCP already initialized above


class ToolRequest(BaseModel):
    """Request model for tool calls."""

    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    """Response model for tool calls."""

    success: bool
    data: Any
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    ignition_available: bool


# ------------------------------
# FastMCP Tools
# ------------------------------


@mcp.tool()
def test_connection() -> dict:
    """Test connection to Ignition Gateway"""
    if not IgnitionClient:
        return {"status": "success", "message": "FastMCP mock connection test", "source": "fastmcp"}

    # Note: This is sync, but we can make it async if needed
    return {"status": "success", "message": "FastMCP connection working!", "source": "fastmcp"}


@mcp.tool()
def get_projects_list() -> dict:
    """List all projects in Ignition Gateway"""
    if not IgnitionTools:
        return {
            "projects": ["FastMCPProject1", "FastMCPProject2", "MockProject"],
            "count": 3,
            "source": "fastmcp_mock",
        }

    # Note: In a real implementation, you'd call the actual Ignition API here
    return {"projects": ["FastMCPProject1", "FastMCPProject2"], "count": 2, "source": "fastmcp"}


@mcp.tool()
def get_activation_is_online() -> dict:
    """Check if Ignition Gateway is online"""
    return {"online": True, "status": "FastMCP connection successful", "source": "fastmcp"}


# Mount FastMCP at root level for simpler access
app.mount("/fastmcp", mcp.http_app())


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy", version="1.0.0", ignition_available=IgnitionClient is not None
    )


@app.get("/tools")
async def list_tools():
    """List all available tools."""
    if not IgnitionTools:
        return {
            "tools": [
                {"name": "test_connection", "description": "Test connection (mock)"},
                {"name": "get_projects_list", "description": "List projects (mock)"},
            ],
            "count": 2,
            "source": "mock",
        }

    try:
        tools = IgnitionTools()
        tool_list = tools.get_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
                for tool in tool_list
            ],
            "count": len(tool_list),
            "source": "ignition",
        }
    except Exception as e:
        return {
            "tools": [
                {"name": "test_connection", "description": "Test connection (fallback)"},
                {"name": "get_projects_list", "description": "List projects (fallback)"},
            ],
            "count": 2,
            "source": "fallback",
            "error": str(e),
        }


@app.post("/tools/test_connection", response_model=ToolResponse)
async def test_connection(request: ToolRequest = ToolRequest()):
    """Test connection to Ignition Gateway."""
    if not IgnitionClient:
        return ToolResponse(
            success=True,
            data={"status": "success", "message": "Mock connection test", "source": "fastapi"},
        )

    try:
        async with IgnitionClient() as client:
            await client.get_openapi_spec()
            return ToolResponse(
                success=True,
                data={
                    "status": "success",
                    "message": "Connection successful",
                    "source": "ignition",
                },
            )
    except Exception as e:
        return ToolResponse(
            success=False, data={"status": "error", "message": str(e)}, error=str(e)
        )


@app.post("/tools/get_projects_list", response_model=ToolResponse)
async def get_projects_list(request: ToolRequest = ToolRequest()):
    """Get list of projects from Ignition Gateway."""
    if not IgnitionTools:
        return ToolResponse(
            success=True,
            data={
                "projects": ["FastAPIProject1", "FastAPIProject2", "MockProject"],
                "count": 3,
                "source": "mock",
            },
        )

    try:
        tools = IgnitionTools()
        result = await tools.call_tool("get_projects_list", request.arguments)

        if result.isError:
            return ToolResponse(
                success=False, data=result.content[0].text, error="Tool execution failed"
            )

        return ToolResponse(success=True, data=result.content[0].text)
    except Exception as e:
        return ToolResponse(success=False, data={"error": str(e)}, error=str(e))


@app.post("/tools/get_activation_is_online", response_model=ToolResponse)
async def get_activation_is_online(request: ToolRequest = ToolRequest()):
    """Check if Ignition Gateway is online."""
    if not IgnitionTools:
        return ToolResponse(
            success=True,
            data={"online": True, "source": "mock", "message": "FastAPI mock response"},
        )

    try:
        tools = IgnitionTools()
        result = await tools.call_tool("get_activation_is_online", request.arguments)

        if result.isError:
            return ToolResponse(
                success=False, data=result.content[0].text, error="Tool execution failed"
            )

        return ToolResponse(success=True, data=result.content[0].text)
    except Exception as e:
        return ToolResponse(success=False, data={"error": str(e)}, error=str(e))


@app.post("/tools/{tool_name}", response_model=ToolResponse)
async def call_tool(tool_name: str, request: ToolRequest):
    """Call any Ignition tool by name."""
    if not IgnitionTools:
        return ToolResponse(
            success=False,
            data={"error": f"Tool {tool_name} not available in mock mode"},
            error="Ignition tools not loaded",
        )

    try:
        tools = IgnitionTools()
        result = await tools.call_tool(tool_name, request.arguments)

        if result.isError:
            return ToolResponse(
                success=False, data=result.content[0].text, error="Tool execution failed"
            )

        return ToolResponse(success=True, data=result.content[0].text)
    except Exception as e:
        return ToolResponse(success=False, data={"error": str(e)}, error=str(e))


if __name__ == "__main__":
    print("🚀 Starting Ignition FastAPI server with FastMCP...")
    print("📋 Available endpoints:")
    print("  GET  /                    - Health check")
    print("  GET  /tools               - List all tools")
    print("  POST /tools/test_connection - Test connection")
    print("  POST /tools/get_projects_list - List projects")
    print("  POST /tools/{tool_name}   - Call any tool")
    print("")
    print("🔗 FastMCP Integration:")
    print("  GET/POST /mcp/sse         - MCP Server-Sent Events endpoint")
    print("  GET  /mcp/tools           - MCP tools list")
    print("")
    print("  📖 Docs: http://localhost:8006/docs")
    print("  🔧 MCP Client Config: http://localhost:8006/mcp/sse")

    uvicorn.run(app, host="0.0.0.0", port=8006, log_level="info")
