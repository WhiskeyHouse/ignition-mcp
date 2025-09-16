"""Generate MCP tools from OpenAPI specification."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class IgnitionAPIGenerator:
    """Generate MCP tools from Ignition OpenAPI spec."""

    def __init__(self, openapi_spec_path: Optional[str] = None):
        if openapi_spec_path is None:
            # Use path relative to this module's location
            module_dir = Path(__file__).parent.parent.parent
            self.spec_path = str(module_dir / "ignition_openapi.json")
        else:
            self.spec_path = openapi_spec_path
        self.spec = self._load_spec()
        self.tools: List[Dict[str, Any]] = []

    def _load_spec(self) -> Dict[str, Any]:
        """Load the OpenAPI specification."""
        with open(self.spec_path, "r") as f:
            result: Dict[str, Any] = json.load(f)
            return result

    def _sanitize_tool_name(
        self, path: str, method: str, operation_id: Optional[str] = None
    ) -> str:
        """Create a valid tool name from path and method."""
        if operation_id:
            return operation_id.replace("-", "_").replace(" ", "_").lower()

        # Convert path to tool name
        parts = path.strip("/").split("/")
        # Remove common prefixes and make more readable
        parts = [p for p in parts if p not in ["data", "api", "v1"]]
        # Replace path parameters
        parts = [p.replace("{", "").replace("}", "") for p in parts]

        tool_name = f"{method.lower()}_{('_'.join(parts)).replace('-', '_')}"
        return tool_name[:50]  # Limit length

    def _extract_parameters(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters schema from operation."""
        properties = {}
        required = []

        # Handle path parameters
        for param in operation.get("parameters", []):
            param_name = param["name"]
            param_schema = param.get("schema", {"type": "string"})

            properties[param_name] = {
                "type": param_schema.get("type", "string"),
                "description": param.get("description", f"{param_name} parameter"),
            }

            if param.get("required", False):
                required.append(param_name)

        # Handle request body
        request_body = operation.get("requestBody")
        if request_body:
            content = request_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                if schema.get("type") == "object":
                    body_props = schema.get("properties", {})
                    for prop_name, prop_schema in body_props.items():
                        properties[f"body_{prop_name}"] = {
                            "type": prop_schema.get("type", "string"),
                            "description": prop_schema.get(
                                "description", f"{prop_name} in request body"
                            ),
                        }

        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    def _should_include_endpoint(self, path: str, method: str, operation: Dict[str, Any]) -> bool:
        """Determine if endpoint should be included as MCP tool."""
        # Skip deprecated endpoints
        if operation.get("deprecated", False):
            return False

        # Focus on common management operations
        management_patterns = [
            "/data/api/v1/projects",
            "/data/api/v1/tags",
            "/data/api/v1/devices",
            "/data/api/v1/connections",
            "/data/api/v1/modules",
            "/data/api/v1/certificates",
            "/data/api/v1/users",
            "/data/api/v1/roles",
            "/system/gateway",
            "/data/api/v1/activation",
            "/data/api/v1/backup",
            "/data/api/v1/logs",
        ]

        # Include if path matches management patterns
        for pattern in management_patterns:
            if path.startswith(pattern):
                return True

        return False

    def generate_tools(self) -> List[Dict[str, Any]]:
        """Generate MCP tools from the OpenAPI spec."""
        tools = []
        paths = self.spec.get("paths", {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                    continue

                if not self._should_include_endpoint(path, method, operation):
                    continue

                tool_name = self._sanitize_tool_name(path, method, operation.get("operationId"))

                input_schema = self._extract_parameters(operation)

                tool = {
                    "name": tool_name,
                    "description": operation.get("summary", f"{method.upper()} {path}"),
                    "inputSchema": input_schema,
                    "_ignition_path": path,
                    "_ignition_method": method.upper(),
                    "_ignition_operation": operation,
                }

                tools.append(tool)

        # Sort by path for better organization
        tools.sort(key=lambda x: x["_ignition_path"])
        return tools

    def save_tools_summary(
        self, output_path: str = "ignition_tools_summary.json"
    ) -> Dict[str, Any]:
        """Save a summary of generated tools."""
        tools = self.generate_tools()

        summary: Dict[str, Any] = {"total_tools": len(tools), "tools_by_category": {}, "tools": []}

        for tool in tools:
            path = tool["_ignition_path"]
            category = path.split("/")[3] if len(path.split("/")) > 3 else "other"

            if category not in summary["tools_by_category"]:
                summary["tools_by_category"][category] = 0
            summary["tools_by_category"][category] += 1

            summary["tools"].append(
                {
                    "name": tool["name"],
                    "path": tool["_ignition_path"],
                    "method": tool["_ignition_method"],
                    "description": tool["description"],
                }
            )

        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

        return summary


if __name__ == "__main__":
    generator = IgnitionAPIGenerator()
    summary = generator.save_tools_summary()
    print(f"Generated {summary['total_tools']} MCP tools")
    print("Categories:", summary["tools_by_category"])
