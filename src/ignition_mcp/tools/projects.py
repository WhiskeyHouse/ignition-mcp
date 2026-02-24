"""Project lifecycle tools — list, get, create, delete, copy, rename, export, import."""

import base64
from typing import Annotated, Any, Dict, Optional, cast

from fastmcp import Context, FastMCP
from pydantic import Field

from ..ignition_client import IgnitionClient


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


async def list_projects(ctx: Context) -> Any:
    """List all Ignition projects with their metadata.

    Returns project names, titles, descriptions, enabled state, parent project,
    and other configuration. No parameters needed.
    """
    try:
        return await _client(ctx).list_projects()
    except Exception as exc:
        return {"error": f"Failed to list projects: {exc}"}


async def get_project(
    name: Annotated[str, Field(description="Exact project name, e.g. 'MyProject'")],
    ctx: Context,
) -> Any:
    """Get full details of a specific Ignition project by name.

    Returns the project's configuration including title, description, parent,
    default database, tag provider, user source, and enabled state.
    """
    try:
        return await _client(ctx).get_project(name)
    except Exception as exc:
        return {"error": f"Failed to get project '{name}': {exc}"}


async def create_project(
    name: Annotated[str, Field(description="Project name (must be unique)")],
    ctx: Context,
    title: Annotated[Optional[str], Field(description="Display title")] = None,
    description: Annotated[Optional[str], Field(description="Project description")] = None,
    parent: Annotated[
        Optional[str],
        Field(description="Parent project name for inheritance. Omit for standalone."),
    ] = None,
    enabled: Annotated[bool, Field(description="Whether the project is enabled")] = True,
) -> Any:
    """Create a new empty Ignition project.

    The project name must be unique on the gateway. Optionally set a parent
    project for resource inheritance.
    """
    body: Dict[str, Any] = {"name": name, "enabled": enabled}
    if title:
        body["title"] = title
    if description:
        body["description"] = description
    if parent:
        body["parent"] = parent
    try:
        return await _client(ctx).create_project(body)
    except Exception as exc:
        return {"error": f"Failed to create project '{name}': {exc}"}


async def delete_project(
    name: Annotated[str, Field(description="Project name to delete")],
    ctx: Context,
) -> Any:
    """Permanently delete an Ignition project. THIS IS IRREVERSIBLE.

    All project resources (views, scripts, named queries, etc.) will be lost.
    Consider exporting the project first with export_project.
    """
    try:
        return await _client(ctx).delete_project(name)
    except Exception as exc:
        return {"error": f"Failed to delete project '{name}': {exc}"}


async def copy_project(
    source_name: Annotated[str, Field(description="Name of the existing project to copy")],
    new_name: Annotated[str, Field(description="Name for the new copy")],
    ctx: Context,
) -> Any:
    """Clone an existing Ignition project to a new name.

    Creates an exact copy of all project resources. The new name must not
    already exist on the gateway.
    """
    try:
        return await _client(ctx).copy_project(source_name, new_name)
    except Exception as exc:
        return {"error": f"Failed to copy '{source_name}' to '{new_name}': {exc}"}


async def rename_project(
    current_name: Annotated[str, Field(description="Current project name")],
    new_name: Annotated[str, Field(description="New project name")],
    ctx: Context,
) -> Any:
    """Rename an Ignition project.

    This changes the project's identifier. Any references to the old name
    (e.g. in gateway scripts) will need to be updated manually.
    """
    try:
        return await _client(ctx).rename_project(current_name, new_name)
    except Exception as exc:
        return {"error": f"Failed to rename '{current_name}': {exc}"}


async def export_project(
    name: Annotated[str, Field(description="Project name to export")],
    ctx: Context,
) -> Any:
    """Export an Ignition project as a ZIP archive (base64-encoded).

    Returns {filename, content_base64, size_bytes}. The content is the standard
    Ignition project export format — you can save it as a .zip file and re-import
    it with import_project. Useful for backups or migration between gateways.
    """
    try:
        resp = await _client(ctx).export_project(name)
        content_b64 = base64.b64encode(resp.content).decode("ascii")
        cd = resp.headers.get("content-disposition", "")
        filename = f"{name}.zip"
        if "filename=" in cd:
            filename = cd.split("filename=")[-1].strip('"')
        return {
            "filename": filename,
            "content_base64": content_b64,
            "size_bytes": len(resp.content),
        }
    except Exception as exc:
        return {"error": f"Failed to export project '{name}': {exc}"}


async def import_project(
    name: Annotated[str, Field(description="Project name for the import")],
    zip_base64: Annotated[
        str,
        Field(description="Base64-encoded ZIP content from export_project"),
    ],
    ctx: Context,
    overwrite: Annotated[
        bool,
        Field(description="Overwrite if a project with this name already exists"),
    ] = False,
) -> Any:
    """Import an Ignition project from a base64-encoded ZIP archive.

    The ZIP should be in Ignition's standard project export format (as returned
    by export_project). WARNING: if overwrite=true, any existing project with
    the same name will be replaced.
    """
    try:
        zip_bytes = base64.b64decode(zip_base64, validate=True)
    except Exception:
        return {"error": "Invalid base64 content — could not decode ZIP data"}
    try:
        return await _client(ctx).import_project(name, zip_bytes, overwrite=overwrite)
    except Exception as exc:
        return {"error": f"Failed to import project '{name}': {exc}"}


def register(mcp: FastMCP) -> None:
    """Register all project tools with the FastMCP instance."""
    mcp.tool()(list_projects)
    mcp.tool()(get_project)
    mcp.tool()(create_project)
    mcp.tool()(delete_project)
    mcp.tool()(copy_project)
    mcp.tool()(rename_project)
    mcp.tool()(export_project)
    mcp.tool()(import_project)
