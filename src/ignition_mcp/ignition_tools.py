"""Ignition Gateway API tools for MCP server."""

import json
from typing import Dict, Any, List
from mcp.types import Tool, TextContent, CallToolResult
from .ignition_client import IgnitionClient
from .api_generator import IgnitionAPIGenerator


class IgnitionTools:
    """Handles Ignition Gateway API tools for MCP server."""
    
    def __init__(self):
        self.generator = IgnitionAPIGenerator()
        self.tools_cache = None
        
    def get_tools(self) -> List[Tool]:
        """Get list of MCP tools from OpenAPI spec."""
        if self.tools_cache is None:
            self._generate_tools_cache()
        
        tools = []
        for tool_def in self.tools_cache:
            tools.append(Tool(
                name=tool_def['name'],
                description=tool_def['description'],
                inputSchema=tool_def['inputSchema']
            ))
        
        return tools
    
    def _generate_tools_cache(self):
        """Generate and cache tools from OpenAPI spec."""
        self.tools_cache = self.generator.generate_tools()
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute an Ignition Gateway API call."""
        if self.tools_cache is None:
            self._generate_tools_cache()
        
        # Find tool definition
        tool_def = None
        for tool in self.tools_cache:
            if tool['name'] == name:
                tool_def = tool
                break
        
        if not tool_def:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Tool '{name}' not found")],
                isError=True
            )
        
        try:
            # Execute API call
            async with IgnitionClient() as client:
                result = await self._execute_api_call(client, tool_def, arguments)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
                
        except Exception as e:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )],
                isError=True
            )
    
    async def _execute_api_call(
        self, 
        client: IgnitionClient, 
        tool_def: Dict[str, Any], 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the actual API call."""
        path = tool_def['_ignition_path']
        method = tool_def['_ignition_method']
        
        # Replace path parameters
        final_path = path
        path_params = {}
        body_params = {}
        query_params = {}
        
        for key, value in arguments.items():
            if key.startswith('body_'):
                body_params[key[5:]] = value
            elif '{' + key + '}' in path:
                final_path = final_path.replace('{' + key + '}', str(value))
                path_params[key] = value
            else:
                query_params[key] = value
        
        # Prepare request kwargs
        kwargs = {}
        if query_params:
            kwargs['params'] = query_params
        if body_params:
            kwargs['json'] = body_params
        
        # Make the API call
        return await client._request(method, final_path, **kwargs)
    
    def get_available_tools_summary(self) -> Dict[str, Any]:
        """Get a summary of available tools."""
        if self.tools_cache is None:
            self._generate_tools_cache()
        
        categories = {}
        for tool in self.tools_cache:
            path_parts = tool['_ignition_path'].split('/')
            category = path_parts[4] if len(path_parts) > 4 else 'general'
            
            if category not in categories:
                categories[category] = []
            
            categories[category].append({
                'name': tool['name'],
                'description': tool['description'],
                'method': tool['_ignition_method'],
                'path': tool['_ignition_path']
            })
        
        return {
            'total_tools': len(self.tools_cache),
            'categories': categories
        }