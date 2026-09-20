"""Read-only mirrors of the most-polled ign reads, as ign:// resources."""

from __future__ import annotations

import json

from fastmcp import FastMCP

from ignition_mcp.ign import IgnBackend


def register_resources(mcp: FastMCP, backend: IgnBackend) -> None:
    def static(uri: str, tool: str, description: str) -> None:
        async def read() -> str:
            return json.dumps(await backend.call(tool))

        read.__name__ = tool
        read.__doc__ = description
        mcp.resource(uri, mime_type="application/json")(read)

    static("ign://status", "status", "Gateway status envelope (ign status).")
    static("ign://profiles", "profile_list", "Configured ign profiles and the active one.")
    static("ign://projects", "project_list", "Projects on the active gateway.")
    static("ign://rig/status", "rig_status", "Docker rig container status.")

    @mcp.resource("ign://logs/tail{?n}", mime_type="application/json")
    async def logs_tail(n: int = 200) -> str:
        """Last n gateway log lines (ign logs)."""
        return json.dumps(await backend.call("logs", {"limit": str(n)}))
