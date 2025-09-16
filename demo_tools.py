#!/usr/bin/env python3
"""Demo script showing available Ignition MCP tools."""

import asyncio
import json

from src.ignition_mcp.ignition_tools import IgnitionTools


async def demo_available_tools():
    """Show all available tools organized by category."""
    print("🔧 Ignition Gateway MCP Tools Demo")
    print("=" * 50)

    tools = IgnitionTools()
    summary = tools.get_available_tools_summary()

    print(f"📊 Total Tools Available: {summary['total_tools']}")
    print("\n📂 Tools by Category:")
    print("-" * 30)

    for category, category_tools in summary["categories"].items():
        print(f"\n🏷️  {category.upper()} ({len(category_tools)} tools)")
        print("─" * 40)

        for tool in category_tools[:5]:  # Show first 5 tools per category
            method_color = {
                "GET": "🔍",
                "POST": "➕",
                "PUT": "✏️",
                "DELETE": "🗑️",
                "PATCH": "🔧",
            }.get(tool["method"], "📋")

            print(f"  {method_color} {tool['name']}")
            print(f"     {tool['description']}")
            print(f"     Path: {tool['path']}")
            print()

        if len(category_tools) > 5:
            print(f"     ... and {len(category_tools) - 5} more tools")
            print()


async def demo_specific_tools():
    """Demo some specific useful tools."""
    print("\n🎯 Testing Key Tools")
    print("=" * 30)

    tools = IgnitionTools()

    test_cases = [
        {
            "name": "get_activation_is_online",
            "args": {},
            "description": "Check if gateway is online",
        }
    ]

    for test in test_cases:
        print(f"\n🧪 Testing: {test['description']}")
        print(f"   Tool: {test['name']}")

        try:
            result = await tools.call_tool(test["name"], test["args"])

            if result.isError:
                print(f"   ❌ Error: {result.content[0].text}")
            else:
                response = json.loads(result.content[0].text)
                print("   ✅ Success!")
                print(f"   📋 Response: {json.dumps(response, indent=6)}")

        except Exception as e:
            print(f"   ❌ Exception: {e}")


async def show_tool_schemas():
    """Show input schemas for some tools."""
    print("\n📋 Sample Tool Schemas")
    print("=" * 30)

    tools = IgnitionTools()
    tool_list = tools.get_tools()

    # Show schemas for a few interesting tools
    interesting_tools = ["put_activation_activate_key", "get_backup", "get_logs"]

    for tool in tool_list:
        if tool.name in interesting_tools:
            print(f"\n🔧 {tool.name}")
            print(f"   Description: {tool.description}")
            print("   Input Schema:")
            schema = tool.inputSchema
            if schema.get("properties"):
                for prop, details in schema["properties"].items():
                    required = "✅" if prop in schema.get("required", []) else "⭕"
                    desc = details.get("description", "No description")
                    print(f"     {required} {prop}: {details.get('type', 'unknown')} - {desc}")
            else:
                print("     No parameters required")


async def main():
    """Run the demo."""
    await demo_available_tools()
    await demo_specific_tools()
    await show_tool_schemas()

    print("\n🚀 Ready to Use!")
    print("To start the MCP server run:")
    print("  python -m ignition_mcp.main")


if __name__ == "__main__":
    asyncio.run(main())
