"""Project resource tools — read and write Perspective views, scripts, and other resources.

Uses the native Ignition REST API:
  GET/PUT/DELETE /data/api/v1/projects/{project}/resources/{resourcePath}

No WebDev dependency required.

Resource path examples:
  Perspective view : com.inductiveautomation.perspective/views/MainView/view.json
  Project script   : com.inductiveautomation.ignition/script-python/utils/code.py
  Named query      : com.inductiveautomation.ignition/named-query/MyQuery/query.json
"""

from typing import Annotated, Any, Optional, cast

from fastmcp import Context, FastMCP
from pydantic import Field

from ..ignition_client import IgnitionClient


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


async def list_project_resources(
    project: Annotated[str, Field(description="Project name, e.g. 'MyProject'")],
    ctx: Context,
    path_prefix: Annotated[
        Optional[str],
        Field(
            description=(
                "Optional path prefix to filter results. "
                "E.g. 'com.inductiveautomation.perspective/views' to list only Perspective views, "
                "or 'com.inductiveautomation.ignition/script-python' for scripts."
            )
        ),
    ] = None,
) -> Any:
    """List all resources in an Ignition project.

    Returns paths for all project resources: Perspective views, scripts, named queries,
    report templates, transaction groups, and more.

    Resource paths follow the pattern:
      {module-id}/{resource-type}/{name}/{filename}

    Common module IDs:
    - com.inductiveautomation.perspective — Perspective views and styles
    - com.inductiveautomation.ignition   — Scripts, named queries, tags, etc.
    - com.inductiveautomation.vision     — Vision windows and templates

    Use get_project_resource to fetch the content of a specific resource.
    """
    try:
        return await _client(ctx).list_project_resources(project, path_prefix=path_prefix)
    except Exception as exc:
        return {"error": f"Failed to list resources for project '{project}': {exc}"}


async def get_project_resource(
    project: Annotated[str, Field(description="Project name, e.g. 'MyProject'")],
    resource_path: Annotated[
        str,
        Field(
            description=(
                "Full resource path within the project. "
                "E.g. 'com.inductiveautomation.perspective/views/MainView/view.json'"
            )
        ),
    ],
    ctx: Context,
) -> Any:
    """Fetch the content of a specific project resource.

    Returns the raw resource content — usually JSON for views and queries,
    Python source for scripts. AI can read this to understand or modify the resource.

    Examples:
    - Perspective view: 'com.inductiveautomation.perspective/views/Dashboard/view.json'
    - Script module: 'com.inductiveautomation.ignition/script-python/utils/code.py'
    - Named query: 'com.inductiveautomation.ignition/named-query/GetSensorData/query.json'

    Use list_project_resources to discover available resource paths.
    """
    try:
        return await _client(ctx).get_project_resource(project, resource_path)
    except Exception as exc:
        return {
            "error": f"Failed to get resource '{resource_path}' from project '{project}': {exc}"
        }


async def set_project_resource(
    project: Annotated[str, Field(description="Project name, e.g. 'MyProject'")],
    resource_path: Annotated[
        str,
        Field(
            description=(
                "Full resource path within the project. "
                "E.g. 'com.inductiveautomation.perspective/views/MainView/view.json'. "
                "If the resource doesn't exist, it will be created."
            )
        ),
    ],
    content: Annotated[
        Any,
        Field(
            description=(
                "Resource content to write. For JSON resources (views, queries) this should "
                "be a dict/object. For Python scripts, this may be a string or structured object "
                "depending on the Ignition version."
            )
        ),
    ],
    ctx: Context,
) -> Any:
    """Create or overwrite a project resource (view, script, named query, etc.).

    Writes the provided content to the specified resource path. If the resource
    doesn't exist it is created; if it does, it is overwritten.

    WARNING: This directly overwrites the resource on the gateway. There is no
    undo — consider reading the existing resource with get_project_resource first
    if you want to preserve or merge content.

    Common use cases:
    - Modify a Perspective view's JSON to update component properties
    - Update a script module with new Python code
    - Create a new named query

    No WebDev required — uses native REST API.
    """
    try:
        return await _client(ctx).set_project_resource(project, resource_path, content)
    except Exception as exc:
        return {"error": f"Failed to set resource '{resource_path}' in project '{project}': {exc}"}


async def delete_project_resource(
    project: Annotated[str, Field(description="Project name, e.g. 'MyProject'")],
    resource_path: Annotated[
        str,
        Field(
            description=(
                "Full resource path within the project to delete. "
                "E.g. 'com.inductiveautomation.perspective/views/OldView/view.json'"
            )
        ),
    ],
    ctx: Context,
) -> Any:
    """Delete a specific project resource. THIS IS IRREVERSIBLE.

    Permanently removes the resource from the project. This cannot be undone.
    Consider listing project resources first (list_project_resources) to
    confirm the exact path before deleting.

    No WebDev required — uses native REST API.
    """
    try:
        return await _client(ctx).delete_project_resource(project, resource_path)
    except Exception as exc:
        return {
            "error": f"Failed to delete resource '{resource_path}' from project '{project}': {exc}"
        }


def register(mcp: FastMCP) -> None:
    """Register all project resource tools with the FastMCP instance."""
    mcp.tool()(list_project_resources)
    mcp.tool()(get_project_resource)
    mcp.tool()(set_project_resource)
    mcp.tool()(delete_project_resource)
