"""Historian tools — query historical tag values via WebDev.

Backed by a WebDev endpoint that wraps system.tag.queryTagHistory().

Required WebDev endpoint: IGNITION_MCP_WEBDEV_TAG_HISTORY_ENDPOINT
(default: Global/GatewayAPI/tagHistory)

See docs/webdev-setup.md for gateway-side script setup instructions.
"""

from typing import Annotated, Any, List, Optional, cast

from fastmcp import Context, FastMCP
from pydantic import Field

from ..ignition_client import IgnitionClient

_WEBDEV_NOT_CONFIGURED = {
    "error": "WebDev tag history endpoint not configured",
    "help": (
        "Tag history queries require a WebDev script on the Ignition gateway. "
        "Set IGNITION_MCP_WEBDEV_TAG_HISTORY_ENDPOINT to the WebDev resource path "
        "(e.g. 'Global/GatewayAPI/tagHistory'). See docs/webdev-setup.md for setup instructions."
    ),
}


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


async def get_tag_history(
    tag_paths: Annotated[
        List[str],
        Field(
            description=(
                "List of fully qualified tag paths with history enabled, e.g. "
                "['[default]Sensors/Temperature', '[default]Sensors/Pressure']. "
                "Tags must have historian enabled in their configuration."
            )
        ),
    ],
    start_time: Annotated[
        str,
        Field(
            description=(
                "Start of the query time range in ISO 8601 format. "
                "E.g. '2024-01-15T08:00:00Z' or '2024-01-15T08:00:00-05:00'."
            )
        ),
    ],
    end_time: Annotated[
        str,
        Field(
            description=(
                "End of the query time range in ISO 8601 format. E.g. '2024-01-15T16:00:00Z'."
            )
        ),
    ],
    ctx: Context,
    aggregation: Annotated[
        str,
        Field(
            description=(
                "Aggregation mode for the returned values. Common options: "
                "LastValue (raw/last value in window), Average, Minimum, Maximum, "
                "Range, Count, StdDev, Sum, MinMax. Default: LastValue."
            )
        ),
    ] = "LastValue",
    interval_ms: Annotated[
        Optional[int],
        Field(
            description=(
                "Aggregation interval in milliseconds. "
                "E.g. 60000 for 1-minute intervals. "
                "If omitted, Ignition uses the natural storage resolution."
            ),
            ge=1000,
        ),
    ] = None,
    max_results: Annotated[
        int,
        Field(
            description="Maximum number of data points to return per tag (1-10000)",
            ge=1,
            le=10000,
        ),
    ] = 1000,
) -> Any:
    """Query historical tag values from the Ignition historian.

    Returns time-series data for the specified tags over the given time range.
    Results include timestamp and value for each data point.

    Tag history must be enabled on each tag (History tab in tag properties).
    Use browse_tags to find tag paths and get_tag_config to verify history is enabled.

    Aggregation modes:
    - LastValue: raw stored values (default)
    - Average: average value over each interval
    - Minimum / Maximum / Range: statistical aggregations
    - Count: number of values stored per interval

    Requires the WebDev tagHistory endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_tag_history_configured:
        return _WEBDEV_NOT_CONFIGURED
    try:
        return await client.get_tag_history(
            tag_paths=tag_paths,
            start_time=start_time,
            end_time=end_time,
            aggregation=aggregation,
            interval_ms=interval_ms,
            max_results=max_results,
        )
    except Exception as exc:
        return {"error": f"Failed to query tag history: {exc}"}


def register(mcp: FastMCP) -> None:
    """Register all historian tools with the FastMCP instance."""
    mcp.tool()(get_tag_history)
