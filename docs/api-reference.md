# API Reference

This document provides comprehensive API documentation for all modules in the Ignition MCP Server.

## Module Overview

The Ignition MCP Server consists of several key modules:

- **[`ignition_mcp.main`](#ignition_mcpmain)** - Main entry point
- **[`ignition_mcp.server`](#ignition_mcpserver)** - MCP server implementation  
- **[`ignition_mcp.ignition_client`](#ignition_mcpignition_client)** - Gateway REST API client
- **[`ignition_mcp.ignition_tools`](#ignition_mcpignition_tools)** - MCP tools implementation
- **[`ignition_mcp.api_generator`](#ignition_mcpapi_generator)** - OpenAPI to MCP tool generator
- **[`ignition_mcp.config`](#ignition_mcpconfig)** - Configuration management

---

## `ignition_mcp.main`

Main entry point for the Ignition MCP server.

### Functions

#### `main()`
```python
async def main() -> None
```

**Description**: Run the Ignition MCP server.

**Returns**: None

**Usage**:
```bash
python -m ignition_mcp.main
```

---

## `ignition_mcp.server`

MCP server implementation for Ignition Gateway automation.

### Classes

#### `IgnitionMCPServer`
```python
class IgnitionMCPServer:
    """MCP server for Ignition Gateway automation."""
```

**Attributes**:
- `server: Server` - MCP server instance
- `ignition_client: IgnitionClient | None` - Gateway client instance  
- `ignition_tools: IgnitionTools | None` - Tools manager instance

##### `__init__()`
```python
def __init__(self) -> None
```

**Description**: Initialize the MCP server with handlers.

##### `run()`
```python
async def run(self) -> None
```

**Description**: Run the MCP server with stdio transport.

**Usage**:
```python
server = IgnitionMCPServer()
await server.run()
```

### Available Tools

The server provides the following base tools:

#### `get_gateway_status`
- **Description**: Get Ignition Gateway status information
- **Parameters**: None
- **Returns**: Gateway status JSON

#### `test_connection`  
- **Description**: Test connection to Ignition Gateway
- **Parameters**: None
- **Returns**: Connection test result

#### `list_available_tools`
- **Description**: List all available Ignition Gateway API tools by category
- **Parameters**: None
- **Returns**: Categorized tool summary

---

## `ignition_mcp.ignition_client`

Client for interacting with Ignition Gateway REST API.

### Classes

#### `IgnitionClient`
```python
class IgnitionClient:
    """Client for interacting with Ignition Gateway REST API."""
```

**Attributes**:
- `gateway_url: str` - Base gateway URL
- `username: str` - Gateway username
- `password: str` - Gateway password
- `api_key: str` - Gateway API key

##### `__init__()`
```python
def __init__(
    self,
    gateway_url: str = None,
    username: str = None,
    password: str = None,
    api_key: str = None
) -> None
```

**Parameters**:
- `gateway_url` (optional): Gateway base URL, defaults to settings
- `username` (optional): Gateway username, defaults to settings
- `password` (optional): Gateway password, defaults to settings  
- `api_key` (optional): Gateway API key, defaults to settings

**Usage**:
```python
# Use default settings
client = IgnitionClient()

# Override specific settings
client = IgnitionClient(
    gateway_url="http://custom-gateway:8088",
    api_key="custom_api_key"
)
```

##### Context Manager Support
```python
async def __aenter__(self) -> "IgnitionClient"
async def __aexit__(self, exc_type, exc_val, exc_tb) -> None
```

**Usage**:
```python
async with IgnitionClient() as client:
    result = await client.get_gateway_status()
```

##### `call_webdev()`
```python
async def call_webdev(
    self,
    resource_path: str | None = None,
    method: str = "POST",
    *,
    json: Any | None = None,
    params: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
) -> Dict[str, Any]
```

**Description**: Invoke a WebDev resource on the Ignition Gateway using the configured authentication.

**Parameters**:
- `resource_path` (optional): Overrides the configured WebDev resource path
- `method` (optional): HTTP verb to use. Defaults to the configured method or `POST`
- `json` (optional): JSON payload to send in the request body
- `params` (optional): Query string parameters
- `headers` (optional): Additional headers to merge with authentication headers

**Returns**: Parsed JSON response or a status dictionary

##### `create_or_update_tag()`
```python
async def create_or_update_tag(
    self,
    tag_path: str | None,
    value: Any = None,
    *,
    data_type: str | None = None,
    attributes: Dict[str, Any] | None = None,
    resource_path: str | None = None,
    method: str | None = None,
    payload_override: Dict[str, Any] | list[Any] | None = None,
    query_params: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
    value_timestamp: str | None = None,
    quality: str | None = None,
) -> Dict[str, Any]
```

**Description**: Helper that constructs a tag definition payload and forwards it to the configured WebDev endpoint.

**Parameters**:
- `tag_path`: Fully qualified tag path, required unless `payload_override` is provided
- `value`: Desired tag value (can be `None`)
- `data_type` (optional): Ignition data type string
- `attributes` (optional): Additional tag attributes
- `resource_path` (optional): Override WebDev resource path for this call
- `method` (optional): Override HTTP method
- `payload_override` (optional): Custom payload to send verbatim instead of building one automatically
- `query_params` (optional): Query parameters for the request
- `headers` (optional): Additional request headers
- `value_timestamp` (optional): ISO timestamp to associate with the value
- `quality` (optional): Quality code string

**Returns**: Parsed JSON response or status dictionary from the WebDev endpoint

##### `get_gateway_status()`
```python
async def get_gateway_status(self) -> Dict[str, Any]
```

**Description**: Get gateway status information.

**Returns**: Gateway status data

**Raises**: `httpx.HTTPStatusError` on API errors

##### `get_openapi_spec()`
```python
async def get_openapi_spec(self) -> Dict[str, Any]
```

**Description**: Get OpenAPI specification from gateway.

**Returns**: OpenAPI specification JSON

**Raises**: `httpx.HTTPStatusError` on API errors

##### `close()`
```python
async def close(self) -> None
```

**Description**: Close the HTTP client connection.

### Private Methods

#### `_create_auth_header()`
```python
def _create_auth_header(self) -> str
```

**Description**: Create authentication header, preferring API key.

**Returns**: Authorization header string

#### `_request()`
```python
async def _request(
    self,
    method: str,
    endpoint: str,
    **kwargs
) -> Dict[str, Any]
```

**Description**: Make authenticated request to Ignition Gateway API.

**Parameters**:
- `method`: HTTP method (GET, POST, etc.)
- `endpoint`: API endpoint path
- `**kwargs`: Additional request parameters

**Returns**: Response JSON data

**Raises**: `httpx.HTTPStatusError` on API errors

---

## `ignition_mcp.ignition_tools`

Handles Ignition Gateway API tools for MCP server.

### Classes

#### `IgnitionTools`
```python
class IgnitionTools:
    """Handles Ignition Gateway API tools for MCP server."""
```

**Attributes**:
- `generator: IgnitionAPIGenerator` - API tool generator
- `tools_cache: List[Dict[str, Any]] | None` - Cached tool definitions
- `custom_tool_defs: Dict[str, Dict[str, Any]]` - Definitions for handcrafted tools
- `custom_tool_handlers: Dict[str, Callable[..., Awaitable[CallToolResult]]]` - Handler mapping for custom tools

##### `__init__()`
```python
def __init__(self) -> None
```

**Description**: Initialize tools manager.

##### `get_tools()`
```python
def get_tools(self) -> List[Tool]
```

**Description**: Get list of MCP tools from the OpenAPI spec and handcrafted additions.

**Returns**: List of MCP Tool objects

**Usage**:
```python
tools_manager = IgnitionTools()
tools = tools_manager.get_tools()
print(f"Available tools: {len(tools)}")
```

##### `call_tool()`
```python
async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult
```

**Description**: Execute an Ignition Gateway API call or dispatch to a custom handler.

**Parameters**:
- `name`: Tool name to execute
- `arguments`: Tool arguments dictionary

**Returns**: Tool execution result

**Usage**:
```python
tools_manager = IgnitionTools()
result = await tools_manager.call_tool(
    "test_connection", 
    {}
)
```

##### `get_available_tools_summary()`
```python
def get_available_tools_summary(self) -> Dict[str, Any]
```

**Description**: Get a summary of generated and custom tools organized by category.

**Returns**: Dictionary with tool categories and counts

**Example Return**:
```python
{
    "total_tools": 45,
    "categories": {
        "activation": [
            {
                "name": "put_activation_activate_key",
                "description": "Activate license key",
                "method": "PUT",
                "path": "/data/api/v1/activation/activate/{key}"
            }
        ]
    }
}
```

### Private Methods

#### `_generate_tools_cache()`
```python
def _generate_tools_cache(self) -> None
```

**Description**: Generate and cache tools from OpenAPI spec.

#### `_execute_api_call()`
```python
async def _execute_api_call(
    self, 
    client: IgnitionClient, 
    tool_def: Dict[str, Any], 
    arguments: Dict[str, Any]
) -> Dict[str, Any]
```

**Description**: Execute the actual API call with parameter processing.

**Parameters**:
- `client`: Ignition client instance
- `tool_def`: Tool definition dictionary
- `arguments`: Call arguments

**Returns**: API response data

---

## `ignition_mcp.api_generator`

Generate MCP tools from OpenAPI specification.

### Classes

#### `IgnitionAPIGenerator`
```python
class IgnitionAPIGenerator:
    """Generate MCP tools from Ignition OpenAPI spec."""
```

**Attributes**:
- `spec_path: str` - Path to OpenAPI specification file
- `spec: Dict[str, Any]` - Loaded OpenAPI specification
- `tools: List[Dict[str, Any]]` - Generated tools list

##### `__init__()`
```python
def __init__(self, openapi_spec_path: str = None) -> None
```

**Parameters**:
- `openapi_spec_path` (optional): Path to OpenAPI spec file, defaults to `ignition_openapi.json`

##### `generate_tools()`
```python
def generate_tools(self) -> List[Dict[str, Any]]
```

**Description**: Generate MCP tools from the OpenAPI spec.

**Returns**: List of tool definition dictionaries

**Tool Definition Structure**:
```python
{
    "name": "tool_name",
    "description": "Tool description",
    "inputSchema": {
        "type": "object",
        "properties": {...},
        "required": [...]
    },
    "_ignition_path": "/api/path",
    "_ignition_method": "GET",
    "_ignition_operation": {...}
}
```

##### `save_tools_summary()`
```python
def save_tools_summary(self, output_path: str = "ignition_tools_summary.json") -> Dict[str, Any]
```

**Description**: Save a summary of generated tools to file.

**Parameters**:
- `output_path`: Output file path

**Returns**: Summary dictionary

### Private Methods

#### `_load_spec()`
```python
def _load_spec(self) -> Dict[str, Any]
```

**Description**: Load the OpenAPI specification from file.

#### `_sanitize_tool_name()`
```python
def _sanitize_tool_name(self, path: str, method: str, operation_id: str = None) -> str
```

**Description**: Create a valid tool name from path and method.

#### `_extract_parameters()`
```python
def _extract_parameters(self, operation: Dict[str, Any]) -> Dict[str, Any]
```

**Description**: Extract parameters schema from OpenAPI operation.

#### `_should_include_endpoint()`
```python
def _should_include_endpoint(self, path: str, method: str, operation: Dict[str, Any]) -> bool
```

**Description**: Determine if endpoint should be included as MCP tool.

**Included Patterns**:
- `/data/api/v1/projects/*` - Project management
- `/data/api/v1/tags/*` - Tag operations  
- `/data/api/v1/devices/*` - Device management
- `/data/api/v1/modules/*` - Module operations
- `/data/api/v1/activation/*` - License activation
- `/data/api/v1/backup/*` - Backup operations
- `/data/api/v1/logs/*` - Log management
- `/system/gateway/*` - Gateway status

---

## `ignition_mcp.config`

Configuration management for Ignition MCP server.

### Classes

#### `Settings`
```python
class Settings(BaseSettings):
    """Application settings using Pydantic."""
```

**Configuration**:
- `env_file = ".env"` - Environment file location
- `env_prefix = "IGNITION_MCP_"` - Environment variable prefix

##### Settings Fields

**Gateway Settings**:
- `ignition_gateway_url: str` - Gateway URL (default: `"http://localhost:8088"`)
- `ignition_username: str` - Gateway username (default: `"admin"`)
- `ignition_password: str` - Gateway password (default: `"password"`)
- `ignition_api_key: str` - Gateway API key (default: `""`)

**Server Settings**:
- `server_host: str` - Server host (default: `"127.0.0.1"`)
- `server_port: int` - Server port (default: `8000`)

### Module Variables

#### `settings`
```python
settings = Settings()
```

**Description**: Global settings instance used throughout the application.

**Usage**:
```python
from ignition_mcp.config import settings

print(f"Gateway URL: {settings.ignition_gateway_url}")
print(f"Server Port: {settings.server_port}")
```

## Error Handling

### Common Exceptions

#### HTTP Errors
```python
import httpx

try:
    async with IgnitionClient() as client:
        result = await client.get_gateway_status()
except httpx.HTTPStatusError as e:
    print(f"HTTP {e.response.status_code}: {e.response.text}")
except httpx.ConnectError:
    print("Failed to connect to gateway")
```

#### Tool Execution Errors
```python
result = await tools.call_tool("invalid_tool", {})
if result.isError:
    print(f"Tool error: {result.content[0].text}")
```

#### Configuration Errors
```python
from pydantic import ValidationError

try:
    settings = Settings()
except ValidationError as e:
    print(f"Configuration error: {e}")
```

## Usage Examples

### Basic Client Usage
```python
from ignition_mcp.ignition_client import IgnitionClient

async def main():
    async with IgnitionClient() as client:
        # Test connection
        spec = await client.get_openapi_spec()
        print(f"API version: {spec.get('info', {}).get('version')}")
        
        # Get status
        status = await client.get_gateway_status()
        print(f"Gateway status: {status}")
```

### Tool Generation
```python
from ignition_mcp.api_generator import IgnitionAPIGenerator

generator = IgnitionAPIGenerator()
tools = generator.generate_tools()
print(f"Generated {len(tools)} tools")

# Save summary
summary = generator.save_tools_summary()
print(f"Categories: {list(summary['tools_by_category'].keys())}")
```

### MCP Server Integration
```python
from ignition_mcp.server import IgnitionMCPServer

async def main():
    server = IgnitionMCPServer()
    await server.run()  # Runs until interrupted
```

## Type Definitions

### Common Types
```python
from typing import Dict, Any, List, Optional
from mcp.types import Tool, CallToolResult, TextContent
```

### Tool Definition Type
```python
ToolDefinition = Dict[str, Any]  # Generated tool definition
APIResponse = Dict[str, Any]     # Gateway API response
ToolArguments = Dict[str, Any]   # Tool input arguments
```
