"""Tag tools — browse, read/write values, and full tag CRUD via WebDev.

Runtime tag reads/writes use the WebDev endpoint configured via
IGNITION_MCP_WEBDEV_TAG_ENDPOINT (default: Global/GatewayAPI/tags).

Tag configuration CRUD (create, edit, delete, UDT types) uses a separate
WebDev endpoint: IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT
(default: Global/GatewayAPI/tagConfig).

See docs/webdev-setup.md for gateway-side script setup instructions.
"""

from typing import Annotated, Any, Dict, List, Optional, cast

from fastmcp import Context, FastMCP
from pydantic import Field

from ..ignition_client import IgnitionClient

_WEBDEV_NOT_CONFIGURED = {
    "error": "WebDev tag endpoint not configured",
    "help": (
        "Runtime tag reads/writes require a WebDev script on the Ignition gateway. "
        "Set IGNITION_MCP_WEBDEV_TAG_ENDPOINT to the WebDev resource path "
        "(e.g. 'Global/GatewayAPI/tags'). See docs/webdev-setup.md for setup instructions."
    ),
}

_WEBDEV_TAG_CONFIG_NOT_CONFIGURED = {
    "error": "WebDev tag config endpoint not configured",
    "help": (
        "Tag CRUD operations require a WebDev script on the Ignition gateway. "
        "Set IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT to the WebDev resource path "
        "(e.g. 'Global/GatewayAPI/tagConfig'). See docs/webdev-setup.md for setup instructions."
    ),
}


def _client(ctx: Context) -> IgnitionClient:
    if ctx.request_context is None:
        raise RuntimeError("Tool called outside of a request context")
    return cast(IgnitionClient, ctx.request_context.lifespan_context["client"])


# ─── Browse ──────────────────────────────────────────────────────────────────


async def browse_tags(
    ctx: Context,
    path: Annotated[
        str,
        Field(
            description=(
                "Tag path to browse from. Use '[default]' for the default provider root, "
                "'[default]Folder/Subfolder' for deeper paths. Empty string browses all providers."
            )
        ),
    ] = "",
    depth: Annotated[
        int,
        Field(
            description="How deep to recurse (1-4). Default 2. Max 4 to prevent huge responses.",
            ge=1,
            le=4,
        ),
    ] = 2,
) -> Any:
    """Browse the tag tree structure (names, types, paths) — NOT runtime values.

    Returns the hierarchical tag structure up to the requested depth. Tags may be
    AtomicTag (leaf), Folder, or UDT instances. Large tag databases can have
    thousands of tags, so depth is capped at 4.

    Path syntax: [provider]Folder/Subfolder/TagName
    - Provider name in square brackets, e.g. [default]
    - Forward-slash hierarchy after the provider
    - Empty path returns all providers as top-level entries

    For runtime tag VALUES (current reading, quality, timestamp), use read_tags instead.
    """
    try:
        return await _client(ctx).browse_tags(path=path, depth=depth)
    except Exception as exc:
        return {"error": f"Failed to browse tags at '{path}': {exc}"}


# ─── Read / Write (WebDev-backed) ────────────────────────────────────────────


async def read_tags(
    tag_paths: Annotated[
        List[str],
        Field(
            description=(
                "List of fully qualified tag paths to read, e.g. "
                "['[default]Folder/Temperature', '[default]Folder/Pressure']. Max 100."
            ),
            max_length=100,
        ),
    ],
    ctx: Context,
) -> Any:
    """Read runtime values of one or more Ignition tags.

    Returns a list of {path, value, quality, timestamp} for each tag.

    IMPORTANT: Requires a WebDev script on the Ignition gateway.
    Set IGNITION_MCP_WEBDEV_TAG_ENDPOINT (default: Global/GatewayAPI/tags).
    See docs/webdev-setup.md for setup instructions.
    """
    client = _client(ctx)
    if not client.webdev_configured:
        return _WEBDEV_NOT_CONFIGURED
    try:
        return await client.read_tags(tag_paths)
    except Exception as exc:
        return {"error": f"Failed to read tags: {exc}"}


async def write_tag(
    tag_path: Annotated[
        str,
        Field(description="Fully qualified tag path, e.g. '[default]Folder/SetPoint'"),
    ],
    value: Annotated[Any, Field(description="Value to write to the tag")],
    ctx: Context,
    data_type: Annotated[
        Optional[str],
        Field(description="Ignition data type hint (Int4, Float8, String, Boolean, etc.)"),
    ] = None,
) -> Any:
    """Write a value to a single Ignition tag.

    IMPORTANT: Requires a WebDev script on the Ignition gateway.
    Set IGNITION_MCP_WEBDEV_TAG_ENDPOINT (default: Global/GatewayAPI/tags).
    See docs/webdev-setup.md for setup instructions.
    """
    client = _client(ctx)
    if not client.webdev_configured:
        return _WEBDEV_NOT_CONFIGURED
    try:
        return await client.write_tag(tag_path, value, data_type=data_type)
    except Exception as exc:
        return {"error": f"Failed to write tag '{tag_path}': {exc}"}


# ─── Tag Config CRUD (WebDev-backed) ─────────────────────────────────────────


async def get_tag_config(
    tag_path: Annotated[
        str,
        Field(
            description=(
                "Fully qualified tag path, e.g. '[default]Folder/MyTag'. "
                "Returns full configuration JSON, not the runtime value."
            )
        ),
    ],
    ctx: Context,
) -> Any:
    """Get the full configuration object for a tag (not its runtime value).

    Returns the tag definition: data type, tag type, alarming config, history
    settings, scaling, etc. This is equivalent to right-clicking a tag in the
    Designer and viewing its properties.

    Requires the WebDev tagConfig endpoint (IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT).
    See docs/webdev-setup.md for gateway setup instructions.
    """
    client = _client(ctx)
    if not client.webdev_tag_config_configured:
        return _WEBDEV_TAG_CONFIG_NOT_CONFIGURED
    try:
        return await client.get_tag_config(tag_path)
    except Exception as exc:
        return {"error": f"Failed to get tag config for '{tag_path}': {exc}"}


async def create_tags(
    tags: Annotated[
        List[Dict[str, Any]],
        Field(
            description=(
                "List of tag configuration objects to create. Each must have at minimum "
                "'name' and 'tagType' (e.g. 'AtomicTag'). Include 'path' to specify "
                "the folder. Example: [{'name': 'MyTag', 'tagType': 'AtomicTag', "
                "'dataType': 'Float8', 'path': '[default]Folder'}]"
            )
        ),
    ],
    ctx: Context,
    provider: Annotated[
        Optional[str],
        Field(description="Tag provider name. Defaults to 'default' on the gateway."),
    ] = None,
) -> Any:
    """Create one or more tags from configuration objects.

    Uses Ignition's system.tag.configure() with editMode='a' (add only).
    Tags that already exist will not be overwritten — use edit_tags for updates.

    Each tag object should follow Ignition's tag configuration schema. Minimum:
    - name: tag name
    - tagType: 'AtomicTag', 'Folder', 'UdtInstance', etc.
    - dataType: 'Boolean', 'Int4', 'Float8', 'String', etc.

    Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_tag_config_configured:
        return _WEBDEV_TAG_CONFIG_NOT_CONFIGURED
    try:
        return await client.configure_tags(tags, edit_mode="a", provider=provider)
    except Exception as exc:
        return {"error": f"Failed to create tags: {exc}"}


async def edit_tags(
    tags: Annotated[
        List[Dict[str, Any]],
        Field(
            description=(
                "List of tag configuration objects to create or update. "
                "Uses merge/upsert semantics — existing tags are updated, new ones created. "
                "Each object must include 'name' and any fields to modify."
            )
        ),
    ],
    ctx: Context,
    provider: Annotated[
        Optional[str],
        Field(description="Tag provider name. Defaults to 'default' on the gateway."),
    ] = None,
) -> Any:
    """Create or modify tags using merge/upsert semantics.

    Uses Ignition's system.tag.configure() with editMode='m' (merge).
    Existing tags have specified properties updated; non-specified properties
    are left unchanged. New tags are created if they don't exist.

    Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_tag_config_configured:
        return _WEBDEV_TAG_CONFIG_NOT_CONFIGURED
    try:
        return await client.configure_tags(tags, edit_mode="m", provider=provider)
    except Exception as exc:
        return {"error": f"Failed to edit tags: {exc}"}


async def delete_tags(
    tag_paths: Annotated[
        List[str],
        Field(
            description=(
                "List of fully qualified tag paths to delete, e.g. "
                "['[default]Folder/MyTag', '[default]OtherFolder']. "
                "Deleting a folder removes all tags within it."
            )
        ),
    ],
    ctx: Context,
) -> Any:
    """Delete tags by path. THIS IS IRREVERSIBLE.

    Deleting a folder removes all tags within it recursively.
    The tag paths must be fully qualified (e.g. '[default]Folder/TagName').

    Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_tag_config_configured:
        return _WEBDEV_TAG_CONFIG_NOT_CONFIGURED
    try:
        return await client.delete_tags(tag_paths)
    except Exception as exc:
        return {"error": f"Failed to delete tags: {exc}"}


async def list_udt_types(
    ctx: Context,
    provider: Annotated[
        str,
        Field(description="Tag provider name to list UDT types from, e.g. 'default'"),
    ] = "default",
) -> Any:
    """List all UDT (User Defined Type) type definitions in a tag provider.

    Returns the names and paths of all UDT type definitions. Use get_udt_definition
    to fetch the full schema for a specific UDT type.

    UDT types live under the _types_ folder in the tag browser.

    Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_tag_config_configured:
        return _WEBDEV_TAG_CONFIG_NOT_CONFIGURED
    try:
        return await client.list_udt_types(provider=provider)
    except Exception as exc:
        return {"error": f"Failed to list UDT types for provider '{provider}': {exc}"}


async def get_udt_definition(
    udt_path: Annotated[
        str,
        Field(
            description=(
                "Path to the UDT type definition, e.g. '[default]_types_/Motor'. "
                "Use list_udt_types to discover available types."
            )
        ),
    ],
    ctx: Context,
) -> Any:
    """Fetch the full schema definition of a UDT (User Defined Type).

    Returns the complete UDT structure: all member tags, their types, alarming
    config, parameters, and overridable properties. Useful for understanding
    what an instance will contain before creating one.

    Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.
    """
    client = _client(ctx)
    if not client.webdev_tag_config_configured:
        return _WEBDEV_TAG_CONFIG_NOT_CONFIGURED
    try:
        return await client.get_udt_definition(udt_path)
    except Exception as exc:
        return {"error": f"Failed to get UDT definition for '{udt_path}': {exc}"}


def register(mcp: FastMCP) -> None:
    """Register all tag tools with the FastMCP instance."""
    mcp.tool()(browse_tags)
    mcp.tool()(read_tags)
    mcp.tool()(write_tag)
    mcp.tool()(get_tag_config)
    mcp.tool()(create_tags)
    mcp.tool()(edit_tags)
    mcp.tool()(delete_tags)
    mcp.tool()(list_udt_types)
    mcp.tool()(get_udt_definition)
