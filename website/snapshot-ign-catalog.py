#!/usr/bin/env python3
"""Refresh docs/_generated/ign-catalog.json from the ign on PATH.

Maintainer tool, never run in CI: it needs fastmcp and a working `ign`.

    uv run python website/snapshot-ign-catalog.py
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

OUT = Path(__file__).resolve().parent.parent / "docs" / "_generated" / "ign-catalog.json"


def ign_version() -> str:
    out = subprocess.run(["ign", "--version"], capture_output=True, text=True, check=True).stdout
    match = re.search(r"\d+\.\d+\.\d+", out)
    return match.group(0) if match else out.strip()


async def main() -> None:
    async with Client(StdioTransport(command="ign", args=["mcp", "serve"])) as client:
        tools = await client.list_tools()
    payload = {
        "ign_version": ign_version(),
        "tools": sorted(
            ({"name": t.name, "description": t.description or ""} for t in tools),
            key=lambda t: t["name"],
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {len(payload['tools'])} tools to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
