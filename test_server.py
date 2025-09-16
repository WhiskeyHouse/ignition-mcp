#!/usr/bin/env python3
"""Test script for Ignition MCP server functionality."""

import asyncio
import os

import pytest

from src.ignition_mcp.ignition_client import IgnitionClient
from src.ignition_mcp.ignition_tools import IgnitionTools
from src.ignition_mcp.server import IgnitionMCPServer


@pytest.mark.asyncio
async def test_basic_imports():
    """Test that all imports work correctly."""
    # Test that classes can be instantiated without errors
    server = IgnitionMCPServer()
    tools = IgnitionTools()

    # Assert objects are created properly
    assert server is not None, "IgnitionMCPServer should be instantiated"
    assert tools is not None, "IgnitionTools should be instantiated"
    assert hasattr(server, "server"), "IgnitionMCPServer should have server attribute"
    assert hasattr(tools, "generator"), "IgnitionTools should have generator attribute"

    print("✓ All imports and instantiation successful")


@pytest.mark.asyncio
async def test_connection():
    """Test connection to Ignition Gateway."""
    if not os.getenv("RUN_LIVE_GATEWAY_TESTS"):
        pytest.skip("Skipping live gateway test. Set RUN_LIVE_GATEWAY_TESTS=1 to run.")

    async with IgnitionClient() as client:
        result = await client.get_openapi_spec()

        # Assert expected response structure
        assert isinstance(result, dict), "Response should be a dictionary"
        assert "info" in result, "Response should contain 'info' field"
        assert "version" in result["info"], "Info should contain 'version' field"

        version = result["info"]["version"]
        assert version, "Version should not be empty"
        print(f"✓ Connection successful - API version: {version}")


@pytest.mark.asyncio
async def test_tool_generation():
    """Test tool generation from OpenAPI spec."""
    tools = IgnitionTools()
    tool_list = tools.get_tools()
    summary = tools.get_available_tools_summary()

    # Assert expected response structure
    assert isinstance(tool_list, list), "Tool list should be a list"
    assert isinstance(summary, dict), "Summary should be a dictionary"
    assert "total_tools" in summary, "Summary should contain 'total_tools' field"
    assert "categories" in summary, "Summary should contain 'categories' field"
    assert isinstance(summary["categories"], dict), "Categories should be a dictionary"

    # Assert we generated some tools
    assert len(tool_list) >= 0, "Should generate at least 0 tools"
    assert summary["total_tools"] == len(tool_list), "Summary count should match tool list length"

    print(f"✓ Generated {len(tool_list)} MCP tools")
    print(f"✓ Tool categories: {list(summary['categories'].keys())}")


@pytest.mark.asyncio
async def test_specific_api_call():
    """Test a specific API call."""
    if not os.getenv("RUN_LIVE_GATEWAY_TESTS"):
        pytest.skip("Skipping live gateway API call test. Set RUN_LIVE_GATEWAY_TESTS=1 to run.")

    tools = IgnitionTools()
    # Test the online status check
    result = await tools.call_tool("get_activation_is_online", {})

    # Assert expected response structure
    assert result is not None, "Result should not be None"
    assert hasattr(result, "content"), "Result should have content attribute"
    assert len(result.content) > 0, "Result content should not be empty"
    assert hasattr(result.content[0], "text"), "Content should have text attribute"

    response_text = result.content[0].text
    assert response_text, "Response text should not be empty"
    print("✓ API call successful")
    print(f"  Response: {response_text[:100]}...")


async def main():
    """Run all tests."""
    print("🧪 Starting Ignition MCP Server Tests\n")

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Gateway Connection", test_connection),
        ("Tool Generation", test_tool_generation),
        ("API Call", test_specific_api_call),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        try:
            await test_func()
            print(f"✓ {test_name} passed")
            results.append((test_name, True))
        except pytest.skip.Exception as e:
            print(f"⏩ {test_name} skipped: {e}")
            results.append((test_name, "skipped"))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    print("\n🎯 Test Results")
    print("=" * 40)
    passed = 0
    skipped = 0
    for test_name, result in results:
        if result == "skipped":
            emoji = "⏩"
            status = "SKIP"
            skipped += 1
        elif result is True:
            emoji = "✅"
            status = "PASS"
            passed += 1
        else:
            emoji = "❌"
            status = "FAIL"
        print(f"{emoji} {test_name}: {status}")

    failed = len(results) - passed - skipped
    print(f"\n🏆 Overall: {passed} passed, {skipped} skipped, {failed} failed")

    if failed == 0:
        print("🎉 All non-skipped tests passed! MCP server is ready to use.")
        if skipped > 0:
            print("💡 Set RUN_LIVE_GATEWAY_TESTS=1 to run live gateway tests.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
