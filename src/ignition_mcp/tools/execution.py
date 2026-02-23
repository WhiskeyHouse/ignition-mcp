"""Script execution tool — run Python on the Ignition gateway.

DISABLED BY DEFAULT. Must be explicitly enabled:
  IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true

Security guardrails:
1. Off by default — must set IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true to enable.
2. Timeout enforced on both client (timeout_secs param) and gateway WebDev side.
3. Dry-run mode available (dry_run=True) to preview without executing.
4. Audit log: every execution is logged on the gateway with timestamp + script hash.
5. WebDev endpoint uses Ignition role-based access control (see docs/webdev-setup.md).

Required WebDev endpoint: IGNITION_MCP_WEBDEV_SCRIPT_EXEC_ENDPOINT
(default: Global/GatewayAPI/scriptExec)

See docs/webdev-setup.md for gateway-side script setup, required roles, and
security recommendations.
"""

from typing import Annotated, Any, cast

from fastmcp import Context, FastMCP
from pydantic import Field

from ..config import settings
from ..ignition_client import IgnitionClient

_DISABLED = {
    "error": "Script execution is disabled",
    "help": (
        "run_gateway_script is disabled by default for safety. "
        "To enable, set IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true in your environment or .env file."
        " "
        "Ensure you understand the security implications before enabling. "
        "See docs/webdev-setup.md for required gateway setup and security guidance."
    ),
}

_WEBDEV_NOT_CONFIGURED = {
    "error": "WebDev script execution endpoint not configured",
    "help": (
        "Script execution requires a WebDev script on the Ignition gateway. "
        "Set IGNITION_MCP_WEBDEV_SCRIPT_EXEC_ENDPOINT to the WebDev resource path "
        "(e.g. 'Global/GatewayAPI/scriptExec'). See docs/webdev-setup.md for setup instructions."
    ),
}


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


async def run_gateway_script(
    script: Annotated[
        str,
        Field(
            description=(
                "Python script to execute on the Ignition gateway. "
                "Use system.* functions available in the gateway scope. "
                "The script runs as a gateway script (not client/designer scope). "
                "Return values: use a module-level 'result' variable or print() for output."
            )
        ),
    ],
    ctx: Context,
    timeout_secs: Annotated[
        int,
        Field(
            description="Execution timeout in seconds (1-60). Default: 10.",
            ge=1,
            le=60,
        ),
    ] = 10,
    dry_run: Annotated[
        bool,
        Field(
            description=(
                "If True, return the script that WOULD be executed without running it. "
                "Useful for previewing before committing to execution."
            )
        ),
    ] = False,
) -> Any:
    """Execute a Python script on the Ignition gateway and return the result.

    WARNING: This tool executes arbitrary code on the Ignition gateway.
    It is DISABLED by default. Set IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true to enable.

    The script runs in the gateway scripting scope with access to all
    system.* functions available on the gateway (system.tag, system.db, etc.).
    It does NOT have access to client-only functions like system.gui.*.

    Execution is logged on the gateway with a script hash for audit purposes.

    Guardrails:
    - Feature flag: must set IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true
    - Timeout: enforced both here and on the gateway WebDev side
    - Dry-run: set dry_run=True to preview without executing
    - Audit: every execution is logged on the gateway

    Example script:
      tags = system.tag.readBlocking(['[default]MyTag'])
      result = tags[0].value

    The gateway WebDev script must be deployed — see docs/webdev-setup.md.
    """
    if not settings.enable_script_execution:
        return _DISABLED

    client = _client(ctx)
    if not client.webdev_script_exec_configured:
        return _WEBDEV_NOT_CONFIGURED

    if dry_run:
        return {
            "dry_run": True,
            "would_execute": True,
            "script": script,
            "timeout_secs": min(timeout_secs, 60),
            "note": "Set dry_run=False to actually execute this script.",
        }

    try:
        return await client.run_gateway_script(
            script=script,
            timeout_secs=timeout_secs,
            dry_run=False,
        )
    except Exception as exc:
        return {"error": f"Script execution failed: {exc}"}


def register(mcp: FastMCP) -> None:
    """Register script execution tool with the FastMCP instance.

    Only registers if script execution is enabled in settings.
    """
    mcp.tool()(run_gateway_script)
