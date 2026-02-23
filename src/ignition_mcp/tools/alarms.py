"""Alarm tools — query active alarms, alarm history, and acknowledge alarms.

These tools are backed by a WebDev endpoint on the Ignition gateway that wraps
Ignition's system.alarm.* scripting functions.

Required WebDev endpoint: IGNITION_MCP_WEBDEV_ALARM_ENDPOINT
(default: Global/GatewayAPI/alarms)

See docs/webdev-setup.md for gateway-side script setup instructions.
"""

from typing import Annotated, Any, List, Optional, cast

from fastmcp import Context, FastMCP
from pydantic import Field

from ..ignition_client import IgnitionClient

_WEBDEV_NOT_CONFIGURED = {
    "error": "WebDev alarm endpoint not configured",
    "help": (
        "Alarm tools require a WebDev script on the Ignition gateway. "
        "Set IGNITION_MCP_WEBDEV_ALARM_ENDPOINT to the WebDev resource path "
        "(e.g. 'Global/GatewayAPI/alarms'). See docs/webdev-setup.md for setup instructions."
    ),
}


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


async def get_active_alarms(
    ctx: Context,
    source_filter: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter alarms by source path prefix. "
                "E.g. '[default]Pumps' to see only alarms from that folder."
            )
        ),
    ] = None,
    priority_filter: Annotated[
        Optional[str],
        Field(
            description=(
                "Minimum alarm priority: Diagnostic, Low, Medium, High, Critical. "
                "E.g. 'High' returns High and Critical alarms only."
            )
        ),
    ] = None,
    state_filter: Annotated[
        Optional[str],
        Field(
            description=(
                "Alarm state filter: ActiveUnacked, ActiveAcked, ClearUnacked. "
                "Omit to return all active alarms regardless of state."
            )
        ),
    ] = None,
) -> Any:
    """Get currently active alarms from the gateway.

    Returns active alarm events with source path, display name, priority,
    state (active/acked), and timestamps for activation and acknowledgement.

    Requires the WebDev alarm endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_alarm_configured:
        return _WEBDEV_NOT_CONFIGURED
    try:
        return await client.get_active_alarms(
            source_filter=source_filter,
            priority_filter=priority_filter,
            state_filter=state_filter,
        )
    except Exception as exc:
        return {"error": f"Failed to get active alarms: {exc}"}


async def get_alarm_history(
    ctx: Context,
    start_time: Annotated[
        Optional[str],
        Field(
            description=(
                "Start of the query time range in ISO 8601 format, "
                "e.g. '2024-01-15T08:00:00Z'. Defaults to 24 hours ago if omitted."
            )
        ),
    ] = None,
    end_time: Annotated[
        Optional[str],
        Field(
            description=(
                "End of the query time range in ISO 8601 format, "
                "e.g. '2024-01-15T16:00:00Z'. Defaults to now if omitted."
            )
        ),
    ] = None,
    source_filter: Annotated[
        Optional[str],
        Field(description="Filter by alarm source path prefix, e.g. '[default]Zone1'"),
    ] = None,
    priority_filter: Annotated[
        Optional[str],
        Field(description="Minimum priority: Diagnostic, Low, Medium, High, Critical"),
    ] = None,
    max_results: Annotated[
        int,
        Field(
            description="Maximum number of alarm journal entries to return (1-1000)", ge=1, le=1000
        ),
    ] = 100,
) -> Any:
    """Query historical alarm journal entries.

    Returns alarm events (activations, acknowledgements, clears) within the
    specified time range. Use this to investigate past alarm activity or build
    audit trails.

    Requires the WebDev alarm endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_alarm_configured:
        return _WEBDEV_NOT_CONFIGURED
    try:
        return await client.get_alarm_history(
            start_time=start_time,
            end_time=end_time,
            source_filter=source_filter,
            priority_filter=priority_filter,
            max_results=max_results,
        )
    except Exception as exc:
        return {"error": f"Failed to get alarm history: {exc}"}


async def acknowledge_alarms(
    event_ids: Annotated[
        List[str],
        Field(
            description=(
                "List of alarm event UUIDs to acknowledge. "
                "Get these from get_active_alarms (the eventId field)."
            )
        ),
    ],
    ctx: Context,
    ack_note: Annotated[
        Optional[str],
        Field(description="Optional acknowledgement note or comment (logged with the ack)"),
    ] = None,
) -> Any:
    """Acknowledge one or more active alarms.

    Requires alarm event IDs, which you can get from get_active_alarms.
    The acknowledgement is logged in the alarm journal with the current user
    (as configured on the WebDev endpoint) and the optional note.

    Requires the WebDev alarm endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_alarm_configured:
        return _WEBDEV_NOT_CONFIGURED
    try:
        return await client.acknowledge_alarms(event_ids, ack_note=ack_note)
    except Exception as exc:
        return {"error": f"Failed to acknowledge alarms: {exc}"}


def register(mcp: FastMCP) -> None:
    """Register all alarm tools with the FastMCP instance."""
    mcp.tool()(get_active_alarms)
    mcp.tool()(get_alarm_history)
    mcp.tool()(acknowledge_alarms)
