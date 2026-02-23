"""Gateway tools — info, module health, logs, and system diagnostics."""

from typing import Annotated, Any, Optional, cast

from fastmcp import Context, FastMCP
from pydantic import Field

from ..ignition_client import IgnitionClient


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


async def get_gateway_info(ctx: Context) -> Any:
    """Get Ignition Gateway version, edition, state, and uptime.

    Use this first to verify connectivity and confirm the gateway is running.
    No parameters required.
    """
    try:
        return await _client(ctx).get_gateway_info()
    except Exception as exc:
        return {"error": f"Failed to reach gateway: {exc}"}


async def get_module_health(ctx: Context) -> Any:
    """List all installed Ignition modules and their health status.

    Returns module name, version, state (LOADED/FAULTED), and any error messages.
    Useful for diagnosing why something isn't working before investigating further.
    """
    try:
        return await _client(ctx).get_module_health()
    except Exception as exc:
        return {"error": f"Failed to query module health: {exc}"}


async def get_gateway_logs(
    ctx: Context,
    level: Annotated[
        Optional[str],
        Field(
            description=(
                "Minimum log level to return: TRACE, DEBUG, INFO, WARN, ERROR. Default: INFO"
            )
        ),
    ] = None,
    logger_name: Annotated[
        Optional[str],
        Field(description="Filter by logger name, e.g. 'com.inductiveautomation.ignition'"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of log entries to return (1-1000)", ge=1, le=1000),
    ] = 100,
) -> Any:
    """Fetch recent gateway log entries.

    Returns log entries with timestamp, level, logger, and message.
    Use this to investigate errors, module faults, or unexpected gateway behaviour.

    Note: Uses the native Ignition REST API (/data/api/v1/logs).
    """
    params: dict[str, Any] = {"limit": limit}
    if level:
        params["level"] = level.upper()
    if logger_name:
        params["logger"] = logger_name
    try:
        return await _client(ctx).get_logs(params=params)
    except Exception as exc:
        return {"error": f"Failed to fetch gateway logs: {exc}"}


async def get_database_connections(ctx: Context) -> Any:
    """List all database connections and their current status.

    Returns connection name, driver, state (Valid/Faulted), and error info.
    Uses native REST API endpoint /data/api/v1/connections/database.
    """
    try:
        return await _client(ctx).get_database_connections()
    except Exception as exc:
        return {"error": f"Failed to get database connections: {exc}"}


async def get_opc_connections(ctx: Context) -> Any:
    """List all OPC-UA / OPC-COM connections and their current state.

    Returns connection name, type, connection status, and any fault details.
    Uses native REST API endpoint /data/api/v1/connections/opc.
    """
    try:
        return await _client(ctx).get_opc_connections()
    except Exception as exc:
        return {"error": f"Failed to get OPC connections: {exc}"}


async def get_system_metrics(ctx: Context) -> Any:
    """Get gateway system metrics: CPU, memory, thread counts, active sessions.

    Returns a snapshot of gateway resource usage. Useful for diagnosing
    performance issues or understanding current gateway load.
    Uses native REST API endpoint /data/api/v1/system/metrics.
    """
    try:
        return await _client(ctx).get_system_metrics()
    except Exception as exc:
        return {"error": f"Failed to get system metrics: {exc}"}


def register(mcp: FastMCP) -> None:
    """Register all gateway tools with the FastMCP instance."""
    mcp.tool()(get_gateway_info)
    mcp.tool()(get_module_health)
    mcp.tool()(get_gateway_logs)
    mcp.tool()(get_database_connections)
    mcp.tool()(get_opc_connections)
    mcp.tool()(get_system_metrics)
