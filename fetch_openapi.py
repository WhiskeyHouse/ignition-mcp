#!/usr/bin/env python3
"""Utility script to fetch and save the Ignition Gateway OpenAPI specification."""

import asyncio
import json

from src.ignition_mcp.ignition_client import IgnitionClient


async def fetch_openapi():
    """Fetch OpenAPI spec from Ignition Gateway."""
    try:
        async with IgnitionClient() as client:
            print("Fetching OpenAPI specification...")
            spec = await client.get_openapi_spec()

            # Save to file
            with open("ignition_openapi.json", "w") as f:
                json.dump(spec, f, indent=2)

            print("OpenAPI specification saved to ignition_openapi.json")
            print(f"Found {len(spec.get('paths', {}))} API endpoints")

            # Print some basic info
            info = spec.get("info", {})
            print(f"API Title: {info.get('title', 'Unknown')}")
            print(f"API Version: {info.get('version', 'Unknown')}")

            return spec

    except Exception as e:
        print(f"Error fetching OpenAPI spec: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(fetch_openapi())
