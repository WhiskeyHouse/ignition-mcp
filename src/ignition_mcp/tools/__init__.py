"""Ignition MCP tool modules.

Each module exposes a register(mcp) function that registers its tools
with the FastMCP instance. Call register_all(mcp) from mcp_server.py
to register everything at once.

Tool inventory (37 total):

Gateway (6):
  get_gateway_info, get_module_health, get_gateway_logs,
  get_database_connections, get_opc_connections, get_system_metrics

Projects (8):
  list_projects, get_project, create_project, delete_project,
  copy_project, rename_project, export_project, import_project

Project Resources (4):
  list_project_resources, get_project_resource,
  set_project_resource, delete_project_resource

Designers (1):
  list_designers

Tag Providers (4):
  list_tag_providers, get_tag_provider, create_tag_provider, delete_tag_provider

Tags (9):
  browse_tags, read_tags, write_tag,
  get_tag_config, create_tags, edit_tags, delete_tags,
  list_udt_types, get_udt_definition

Alarms (3):
  get_active_alarms, get_alarm_history, acknowledge_alarms

Historian (1):
  get_tag_history

Execution (1, off by default):
  run_gateway_script
"""

from fastmcp import FastMCP

from . import (
    alarms,
    designers,
    execution,
    gateway,
    historian,
    projects,
    resources,
    tag_providers,
    tags,
)

__all__ = [
    "alarms",
    "designers",
    "execution",
    "gateway",
    "historian",
    "projects",
    "resources",
    "tag_providers",
    "tags",
    "register_all",
]


def register_all(mcp: FastMCP) -> None:
    """Register all tool modules with the FastMCP instance."""
    gateway.register(mcp)
    projects.register(mcp)
    resources.register(mcp)
    designers.register(mcp)
    tag_providers.register(mcp)
    tags.register(mcp)
    alarms.register(mcp)
    historian.register(mcp)
    execution.register(mcp)
