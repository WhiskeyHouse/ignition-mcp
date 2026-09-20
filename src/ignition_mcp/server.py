"""Assemble the FastMCP app: ign proxy + composites + resources + prompts."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.providers.proxy import FastMCPProxy

from ignition_mcp import __version__
from ignition_mcp.config import Settings
from ignition_mcp.ign import IgnBackend
from ignition_mcp.prompts import register_prompts
from ignition_mcp.resources import register_resources
from ignition_mcp.workflows import register_workflows

INSTRUCTIONS = (
    "Every tool named like an `ign` verb (status, project_sync, tags_read, ...) is proxied "
    "unchanged from `ign mcp serve`; results are ign JSON envelopes "
    "({ok, profile, data} or {ok:false, profile, error:{code,message,endpoint,hint}}). "
    "Destructive verbs refuse until called with confirm: true. "
    "Composite tools (diagnose_gateway, deploy_project, rig_fresh, tag_snapshot, find_alarms) "
    "chain several ign calls and return {ok, steps, ...}. "
    "Resources under ign:// mirror the most-polled reads. Prompts are runbooks."
)


def build_server(settings: Settings, backend: IgnBackend) -> FastMCP:
    mcp = FastMCP(name="ignition-mcp", version=__version__, instructions=INSTRUCTIONS)

    proxy = FastMCPProxy(client_factory=lambda: backend.client, name="ign")
    mcp.mount(proxy)

    register_workflows(mcp, backend)
    register_resources(mcp, backend)
    register_prompts(mcp)
    return mcp
