"""Tag provider configuration tools — list, get, create, delete."""

from typing import Annotated, Any, cast

from fastmcp import Context, FastMCP
from pydantic import Field

from ..ignition_client import IgnitionClient


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


async def list_tag_providers(ctx: Context) -> Any:
    """List all configured tag providers on the gateway.

    Tag providers are containers for tags. Most installations have a 'default'
    provider of type STANDARD. This returns provider names, types, and config.
    These are *configuration* resources — for runtime tag values, use read_tags.
    """
    try:
        return await _client(ctx).list_tag_providers()
    except Exception as exc:
        return {"error": f"Failed to list tag providers: {exc}"}


async def get_tag_provider(
    name: Annotated[str, Field(description="Tag provider name, e.g. 'default'")],
    ctx: Context,
) -> Any:
    """Get the full configuration of a specific tag provider.

    Returns the provider type (STANDARD, REMOTE, DERIVED), settings, and
    metadata. Use list_tag_providers first to see available names.
    """
    try:
        return await _client(ctx).get_tag_provider(name)
    except Exception as exc:
        return {"error": f"Failed to get tag provider '{name}': {exc}"}


async def create_tag_provider(
    name: Annotated[str, Field(description="New tag provider name")],
    ctx: Context,
    description: Annotated[str, Field(description="Provider description")] = "",
    provider_type: Annotated[
        str,
        Field(description="Provider type: STANDARD (local tags), REMOTE, or DERIVED"),
    ] = "STANDARD",
) -> Any:
    """Create a new tag provider on the gateway.

    Most use cases need a STANDARD provider, which stores tags locally.
    REMOTE providers connect to another gateway's tags over the gateway network.
    """
    body = [
        {
            "name": name,
            "collection": "core",
            "enabled": True,
            "description": description,
            "config": {
                "profile": {
                    "type": provider_type,
                    "allowBackfill": False,
                    "enableTagReferenceStore": True,
                },
                "settings": {"nonUseCount": 0},
            },
        }
    ]
    try:
        return await _client(ctx).create_tag_provider(body)
    except Exception as exc:
        return {"error": f"Failed to create tag provider '{name}': {exc}"}


async def delete_tag_provider(
    name: Annotated[str, Field(description="Tag provider name to delete")],
    ctx: Context,
) -> Any:
    """Delete a tag provider and ALL of its tags. THIS IS IRREVERSIBLE.

    All tags within this provider will be permanently deleted. This cannot
    be undone. Make sure you have a backup if the tags are important.
    """
    try:
        return await _client(ctx).delete_tag_provider(name)
    except Exception as exc:
        return {"error": f"Failed to delete tag provider '{name}': {exc}"}


def register(mcp: FastMCP) -> None:
    """Register all tag provider tools with the FastMCP instance."""
    mcp.tool()(list_tag_providers)
    mcp.tool()(get_tag_provider)
    mcp.tool()(create_tag_provider)
    mcp.tool()(delete_tag_provider)
