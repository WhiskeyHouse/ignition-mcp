#!/usr/bin/env python3
"""Test MCP protocol communication with the Ignition server."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_mcp_communication():
    """Test MCP server communication via stdin/stdout."""
    print("🧪 Testing MCP Protocol Communication")
    print("=" * 40)

    # Start the MCP server
    server_path = Path(__file__).parent / "run_server.sh"

    process = subprocess.Popen(
        [str(server_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Send initialization message
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        print("📤 Sending initialization...")
        process.stdin.write(json.dumps(init_message) + "\n")
        process.stdin.flush()

        # Read response
        response = process.stdout.readline()
        if response:
            print("✅ Server responded to initialization")
            print(f"   Response: {response.strip()[:100]}...")
        else:
            print("❌ No response from server")
            return False

        # Test list tools
        list_tools_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

        print("\n📤 Requesting tools list...")
        process.stdin.write(json.dumps(list_tools_message) + "\n")
        process.stdin.flush()

        # Read tools response
        tools_response = process.stdout.readline()
        if tools_response:
            try:
                tools_data = json.loads(tools_response)
                if "result" in tools_data and "tools" in tools_data["result"]:
                    tools_count = len(tools_data["result"]["tools"])
                    print(f"✅ Server returned {tools_count} tools")

                    # Show first few tools
                    for i, tool in enumerate(tools_data["result"]["tools"][:3]):
                        print(f"   📋 {tool['name']}: {tool['description']}")

                    if tools_count > 3:
                        print(f"   ... and {tools_count - 3} more tools")

                    return True
                else:
                    print("❌ Invalid tools response format")
                    print(f"   Response: {tools_response.strip()}")
                    return False
            except json.JSONDecodeError:
                print("❌ Invalid JSON in tools response")
                print(f"   Response: {tools_response.strip()}")
                return False
        else:
            print("❌ No tools response from server")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

    finally:
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


async def main():
    """Run the MCP protocol test."""
    success = await test_mcp_communication()

    print("\n🎯 Test Result")
    print("=" * 20)
    if success:
        print("✅ MCP Protocol Test PASSED")
        print("🚀 Server is ready for Claude Code!")
        print("\nNext steps:")
        print("1. Restart Claude Code")
        print("2. Try: 'Can you list available Ignition tools?'")
    else:
        print("❌ MCP Protocol Test FAILED")
        print("🔧 Check server configuration and try again")

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
