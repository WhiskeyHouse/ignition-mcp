#!/usr/bin/env python3
"""
Enhanced MCP FastAPI Server with Jython Script Validation
Provides REST endpoints for Ignition Gateway automation and script validation
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from ignition_mcp.ignition_client import IgnitionClient
    from ignition_mcp.ignition_tools import IgnitionTools
except ImportError as e:
    print(f"Warning: Could not import Ignition modules: {e}")
    IgnitionClient = None
    IgnitionTools = None


app = FastAPI(
    title="Enhanced Ignition MCP Server",
    description="REST API for Ignition Gateway automation with Jython script validation",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
RULES_ENGINE_URL = "http://localhost:8087"
RAG_SERVICE_URL = "http://localhost:8086"

# In-memory storage for validation sessions (in production, use Redis/DB)
validation_sessions = {}


# Models
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
    rules_engine_available: bool
    rag_service_available: bool


class JythonScriptRequest(BaseModel):
    """Request model for Jython script validation."""
    script: str = Field(..., description="The Jython script to validate")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for validation")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Script metadata (name, type, etc.)")


class JythonScriptPatch(BaseModel):
    """Request model for partial Jython script updates."""
    script_updates: Optional[str] = Field(None, description="Updated script content")
    context: Optional[Dict[str, Any]] = Field(None, description="Updated context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class ValidationSession(BaseModel):
    """Model for validation session."""
    session_id: str
    script: str
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ComponentRequest(BaseModel):
    """Request model for Perspective component validation."""
    component: Dict[str, Any] = Field(..., description="The Perspective component to validate")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for validation")


# Helper functions
async def check_service_health(url: str, timeout: int = 2) -> bool:
    """Check if a service is healthy."""
    try:
        response = requests.get(f"{url}/health", timeout=timeout)
        return response.status_code == 200
    except:
        return False


async def validate_script_with_rules_engine(script: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """Validate script using the rules engine."""
    try:
        response = requests.post(
            f"{RULES_ENGINE_URL}/validate/script",
            json={"script": script, "context": context},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Rules engine error: {response.text}"}
    except Exception as e:
        return {"error": f"Failed to connect to rules engine: {str(e)}"}


async def validate_component_with_rules_engine(component: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    """Validate component using the rules engine."""
    try:
        response = requests.post(
            f"{RULES_ENGINE_URL}/validate/component",
            json={"component": component, "context": context},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Rules engine error: {response.text}"}
    except Exception as e:
        return {"error": f"Failed to connect to rules engine: {str(e)}"}


# Original MCP endpoints
@app.get("/", response_model=HealthResponse)
async def health_check():
    """Enhanced health check endpoint."""
    rules_engine_healthy = await check_service_health(RULES_ENGINE_URL)
    rag_service_healthy = await check_service_health(RAG_SERVICE_URL)
    
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        ignition_available=IgnitionClient is not None,
        rules_engine_available=rules_engine_healthy,
        rag_service_available=rag_service_healthy
    )


@app.get("/tools")
async def list_tools():
    """List all available tools including new validation endpoints."""
    base_tools = []
    
    if not IgnitionTools:
        base_tools = [
            {"name": "test_connection", "description": "Test connection (mock)"},
            {"name": "get_projects_list", "description": "List projects (mock)"},
        ]
    else:
        try:
            tools = IgnitionTools()
            tool_list = tools.get_tools()
            base_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
                for tool in tool_list
            ]
        except Exception as e:
            base_tools = [
                {"name": "test_connection", "description": "Test connection (fallback)"},
                {"name": "get_projects_list", "description": "List projects (fallback)"},
            ]
    
    # Add validation tools
    validation_tools = [
        {
            "name": "validate_jython_script",
            "description": "Validate Jython scripts using WHK rules engine",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "Jython script content"},
                    "context": {"type": "object", "description": "Optional context"},
                    "metadata": {"type": "object", "description": "Optional metadata"}
                },
                "required": ["script"]
            }
        },
        {
            "name": "validate_perspective_component",
            "description": "Validate Perspective components using WHK rules engine",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "component": {"type": "object", "description": "Component definition"},
                    "context": {"type": "object", "description": "Optional context"}
                },
                "required": ["component"]
            }
        }
    ]
    
    return {
        "tools": base_tools + validation_tools,
        "count": len(base_tools) + len(validation_tools),
        "source": "enhanced_mcp",
        "validation_endpoints": [
            "GET /validation/scripts - List validation sessions",
            "POST /validation/scripts - Validate new script",
            "GET /validation/scripts/{session_id} - Get validation session",
            "PATCH /validation/scripts/{session_id} - Update validation session",
            "POST /validation/components - Validate Perspective component"
        ]
    }


# New Jython Script Validation Endpoints

@app.get("/validation/scripts")
async def list_validation_sessions():
    """GET - List all validation sessions."""
    sessions = []
    for session_id, session_data in validation_sessions.items():
        sessions.append({
            "session_id": session_id,
            "metadata": session_data.get("metadata", {}),
            "has_validation": session_data.get("validation_result") is not None,
            "created_at": session_data.get("created_at"),
            "updated_at": session_data.get("updated_at")
        })
    
    return {
        "sessions": sessions,
        "total": len(sessions)
    }


@app.post("/validation/scripts")
async def validate_jython_script(request: JythonScriptRequest):
    """POST - Create new validation session and validate Jython script."""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Validate the script
    validation_result = await validate_script_with_rules_engine(
        request.script, 
        request.context
    )
    
    # Store the session
    validation_sessions[session_id] = {
        "session_id": session_id,
        "script": request.script,
        "context": request.context,
        "metadata": request.metadata or {},
        "validation_result": validation_result,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    return {
        "session_id": session_id,
        "validation_result": validation_result,
        "created_at": now.isoformat()
    }


@app.get("/validation/scripts/{session_id}")
async def get_validation_session(session_id: str):
    """GET - Retrieve specific validation session."""
    if session_id not in validation_sessions:
        raise HTTPException(status_code=404, detail="Validation session not found")
    
    return validation_sessions[session_id]


@app.patch("/validation/scripts/{session_id}")
async def update_validation_session(session_id: str, request: JythonScriptPatch):
    """PATCH - Update validation session with new script content."""
    if session_id not in validation_sessions:
        raise HTTPException(status_code=404, detail="Validation session not found")
    
    session = validation_sessions[session_id]
    now = datetime.utcnow()
    
    # Update fields if provided
    if request.script_updates is not None:
        session["script"] = request.script_updates
    if request.context is not None:
        session["context"] = request.context
    if request.metadata is not None:
        session["metadata"].update(request.metadata)
    
    session["updated_at"] = now.isoformat()
    
    # Re-validate if script was updated
    if request.script_updates is not None:
        validation_result = await validate_script_with_rules_engine(
            session["script"],
            session["context"]
        )
        session["validation_result"] = validation_result
    
    return {
        "session_id": session_id,
        "updated_at": now.isoformat(),
        "validation_result": session.get("validation_result")
    }


@app.delete("/validation/scripts/{session_id}")
async def delete_validation_session(session_id: str):
    """DELETE - Remove validation session."""
    if session_id not in validation_sessions:
        raise HTTPException(status_code=404, detail="Validation session not found")
    
    del validation_sessions[session_id]
    return {"message": "Validation session deleted", "session_id": session_id}


# Component Validation Endpoint
@app.post("/validation/components")
async def validate_perspective_component(request: ComponentRequest):
    """POST - Validate Perspective component."""
    validation_result = await validate_component_with_rules_engine(
        request.component,
        request.context
    )
    
    return {
        "component_type": request.component.get("type", "unknown"),
        "validation_result": validation_result,
        "timestamp": datetime.utcnow().isoformat()
    }


# Enhanced tool endpoints with validation integration
@app.post("/tools/validate_jython_script", response_model=ToolResponse)
async def tool_validate_jython_script(request: ToolRequest):
    """Tool endpoint for script validation."""
    script = request.arguments.get("script")
    if not script:
        return ToolResponse(success=False, error="Script content is required")
    
    context = request.arguments.get("context")
    validation_result = await validate_script_with_rules_engine(script, context)
    
    return ToolResponse(success=True, data=validation_result)


@app.post("/tools/validate_perspective_component", response_model=ToolResponse)
async def tool_validate_perspective_component(request: ToolRequest):
    """Tool endpoint for component validation."""
    component = request.arguments.get("component")
    if not component:
        return ToolResponse(success=False, error="Component definition is required")
    
    context = request.arguments.get("context")
    validation_result = await validate_component_with_rules_engine(component, context)
    
    return ToolResponse(success=True, data=validation_result)


# Original tool endpoints (preserved)
@app.post("/tools/test_connection", response_model=ToolResponse)
async def test_connection(request: ToolRequest = ToolRequest()):
    """Test connection to Ignition Gateway."""
    if not IgnitionClient:
        return ToolResponse(
            success=True,
            data={"status": "success", "message": "Mock connection test", "source": "enhanced_mcp"},
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
        return ToolResponse(success=False, data={"error": str(e)}, error=str(e))


@app.post("/tools/get_projects_list", response_model=ToolResponse)
async def get_projects_list(request: ToolRequest = ToolRequest()):
    """Get list of Ignition projects."""
    if not IgnitionClient:
        return ToolResponse(
            success=True,
            data={
                "projects": [{"name": "MockProject", "description": "Mock project"}],
                "source": "enhanced_mcp",
            },
        )

    try:
        async with IgnitionClient() as client:
            result = await client.call_tool("get_projects_list", {})
            return ToolResponse(success=True, data=result.content[0].text)
    except Exception as e:
        return ToolResponse(success=False, data={"error": str(e)}, error=str(e))


# Dynamic tool routing (preserved from original)
@app.post("/tools/{tool_name}", response_model=ToolResponse)
async def call_tool(tool_name: str, request: ToolRequest):
    """Call any available Ignition tool."""
    if not IgnitionTools:
        return ToolResponse(
            success=False,
            data={"error": "Ignition tools not available"},
            error="Tools unavailable",
        )

    try:
        tools = IgnitionTools()
        result = await tools.call_tool(tool_name, request.arguments)
        
        if hasattr(result, 'content') and result.content:
            return ToolResponse(success=True, data=result.content[0].text)
        else:
            return ToolResponse(
                success=False, data=result.content[0].text, error="Tool execution failed"
            )

        return ToolResponse(success=True, data=result.content[0].text)
    except Exception as e:
        return ToolResponse(success=False, data={"error": str(e)}, error=str(e))


if __name__ == "__main__":
    print("🚀 Starting Enhanced Ignition MCP Server with Validation...")
    print("📋 Available endpoints:")
    print("  GET  /                              - Health check")
    print("  GET  /tools                         - List all tools")
    print("  POST /tools/{tool_name}             - Call any Ignition tool")
    print("")
    print("🔍 Validation endpoints:")
    print("  GET  /validation/scripts            - List validation sessions")
    print("  POST /validation/scripts            - Validate Jython script")
    print("  GET  /validation/scripts/{id}       - Get validation session")
    print("  PATCH /validation/scripts/{id}      - Update validation session")
    print("  DELETE /validation/scripts/{id}     - Delete validation session")
    print("  POST /validation/components         - Validate Perspective component")
    print("")
    print("🛠️  Tool endpoints:")
    print("  POST /tools/validate_jython_script     - Validate script via tool interface")
    print("  POST /tools/validate_perspective_component - Validate component via tool interface")
    print("")
    print("  📖 Docs: http://localhost:8089/docs")
    print("  🔧 Rules Engine: http://localhost:8087")
    print("  🤖 RAG Service: http://localhost:8086")

    uvicorn.run(app, host="0.0.0.0", port=8089, log_level="info")