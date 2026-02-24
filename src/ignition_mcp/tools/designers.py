"""Designer session tools."""

from typing import Any, cast

from fastmcp import Context, FastMCP

from ..ignition_client import IgnitionClient


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


async def list_designers(ctx: Context) -> Any:
    """List active Ignition Designer sessions.

    Shows who is connected to the Designer, which project they have open, and
    since when. Useful to check if anyone is actively editing before making
    programmatic changes to a project.
    """
    try:
        return await _client(ctx).list_designers()
    except Exception as exc:
        return {"error": f"Failed to list designers: {exc}"}


def register(mcp: FastMCP) -> None:
    """Register all designer tools with the FastMCP instance."""
    mcp.tool()(list_designers)
