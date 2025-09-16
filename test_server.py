#!/usr/bin/env python3
"""Test script for Ignition MCP server functionality."""

import asyncio
import json
from src.ignition_mcp.server import IgnitionMCPServer
from src.ignition_mcp.ignition_tools import IgnitionTools
from src.ignition_mcp.ignition_client import IgnitionClient


async def test_basic_imports():
    """Test that all imports work correctly."""
    print("✓ Testing imports...")
    try:
        server = IgnitionMCPServer()
        tools = IgnitionTools()
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


async def test_connection():
    """Test connection to Ignition Gateway."""
    print("✓ Testing connection to Ignition Gateway...")
    try:
        async with IgnitionClient() as client:
            result = await client.get_openapi_spec()
            print(f"✓ Connection successful - API version: {result.get('info', {}).get('version', 'Unknown')}")
            return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


async def test_tool_generation():
    """Test tool generation from OpenAPI spec."""
    print("✓ Testing tool generation...")
    try:
        tools = IgnitionTools()
        tool_list = tools.get_tools()
        summary = tools.get_available_tools_summary()
        
        print(f"✓ Generated {len(tool_list)} MCP tools")
        print(f"✓ Tool categories: {list(summary['categories'].keys())}")
        return True
    except Exception as e:
        print(f"✗ Tool generation failed: {e}")
        return False


async def test_specific_api_call():
    """Test a specific API call."""
    print("✓ Testing specific API call...")
    try:
        tools = IgnitionTools()
        # Test the online status check
        result = await tools.call_tool("get_activation_is_online", {})
        print(f"✓ API call successful")
        print(f"  Response: {result.content[0].text[:100]}...")
        return True
    except Exception as e:
        print(f"✗ API call failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Starting Ignition MCP Server Tests\n")
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Gateway Connection", test_connection), 
        ("Tool Generation", test_tool_generation),
        ("API Call", test_specific_api_call)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print(f"\n🎯 Test Results")
    print("=" * 40)
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        emoji = "✅" if success else "❌"
        print(f"{emoji} {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n🏆 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! MCP server is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())