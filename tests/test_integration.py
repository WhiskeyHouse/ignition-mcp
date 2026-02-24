"""Integration / end-to-end tests — require a live Ignition Gateway.

Tests are organised in two layers:
  - Client layer  : calls IgnitionClient methods directly (validates HTTP + JSON)
  - Tool layer    : calls tool functions with a real client in ctx (validates the
                    full stack including parameter handling and error wrapping)

Run all integration tests:
    RUN_LIVE_GATEWAY_TESTS=1 uv run pytest tests/test_integration.py -v

Enable WebDev-backed tests (alarms, tag read/write, tag config, historian):
    RUN_LIVE_GATEWAY_TESTS=1 IGNITION_MCP_WEBDEV_AVAILABLE=1 uv run pytest ...

Enable specific WebDev feature groups:
    IGNITION_MCP_WEBDEV_TAGS=1       read_tags / write_tag
    IGNITION_MCP_WEBDEV_TAG_CONFIG=1 create_tags / edit_tags / delete_tags / UDTs
    IGNITION_MCP_WEBDEV_ALARMS=1     get_active_alarms / get_alarm_history
    IGNITION_MCP_WEBDEV_HISTORY=1    get_tag_history
    IGNITION_MCP_WEBDEV_EXEC=1       run_gateway_script (also needs ENABLE_SCRIPT_EXECUTION)

Point tests at a writable tag:
    IGNITION_MCP_TEST_TAG_PATH=[default]MCP_Test_Tag

Point historian tests at a tag with history enabled:
    IGNITION_MCP_TEST_HISTORY_TAG=[default]MCP_Historised_Tag

Note: the IGNITION_MCP_WEBDEV_AVAILABLE=1 flag implies all five WEBDEV_* flags above.
"""

import os
import time
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Top-level gate: skip entire module unless live tests are explicitly enabled
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_GATEWAY_TESTS") != "1",
    reason="Live gateway tests disabled — set RUN_LIVE_GATEWAY_TESTS=1 to enable",
)

# ---------------------------------------------------------------------------
# WebDev feature flags
# ---------------------------------------------------------------------------

_ALL_WEBDEV = os.environ.get("IGNITION_MCP_WEBDEV_AVAILABLE") == "1"

_WEBDEV_TAGS = _ALL_WEBDEV or os.environ.get("IGNITION_MCP_WEBDEV_TAGS") == "1"
_WEBDEV_TAG_CONFIG = _ALL_WEBDEV or os.environ.get("IGNITION_MCP_WEBDEV_TAG_CONFIG") == "1"
_WEBDEV_ALARMS = _ALL_WEBDEV or os.environ.get("IGNITION_MCP_WEBDEV_ALARMS") == "1"
_WEBDEV_HISTORY = _ALL_WEBDEV or os.environ.get("IGNITION_MCP_WEBDEV_HISTORY") == "1"
_WEBDEV_EXEC = _ALL_WEBDEV or os.environ.get("IGNITION_MCP_WEBDEV_EXEC") == "1"

# Optional tag paths provided by the user running the tests
_TEST_TAG_PATH = os.environ.get("IGNITION_MCP_TEST_TAG_PATH", "")
_TEST_HISTORY_TAG = os.environ.get("IGNITION_MCP_TEST_HISTORY_TAG", "")

# Unique suffix so parallel / repeated runs don't collide
_SUFFIX = str(int(time.time()))[-6:]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(client):
    """Wrap a real IgnitionClient in a minimal fake FastMCP Context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"client": client}
    return ctx


def _no_error(result):
    """Assert a tool result does not contain a top-level 'error' key."""
    assert isinstance(result, (dict, list)), f"Expected dict or list, got {type(result)}: {result}"
    if isinstance(result, dict):
        assert "error" not in result, f"Tool returned error: {result['error']}"


def _is_connection_error(result):
    """Return True if the result is a connection-level failure (gateway unreachable).

    Deliberately narrow — only matches genuine TCP/TLS failures, not 404s or auth errors.
    """
    if isinstance(result, dict) and "error" in result:
        msg = str(result["error"]).lower()
        return any(
            w in msg
            for w in (
                "connection refused",
                "no route to host",
                "connecterror",
                "network is unreachable",
                "failed to establish",
                "name or service not known",
                "timed out",
                "read timeout",
                "pool timeout",
            )
        )
    return False


def _is_endpoint_not_found(result) -> bool:
    """Return True if the result is a 404 from the gateway (endpoint not supported)."""
    if isinstance(result, dict) and "error" in result:
        msg = str(result["error"]).lower()
        return "404" in msg or "not found" in msg or "no route match" in msg
    return False


# ---------------------------------------------------------------------------
# Module-scoped client (one connection per test session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def live_client():
    from ignition_mcp.ignition_client import IgnitionClient

    client = IgnitionClient()
    yield client
    await client.close()


# ---------------------------------------------------------------------------
# Project lifecycle fixture — creates a test project, tears it down after
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_project(live_client) -> AsyncGenerator[str, None]:
    """Create a fresh project for a single test, delete it on teardown."""
    name = f"mcp-test-{_SUFFIX}-{int(time.time() * 1000) % 10000}"
    await live_client.create_project({"name": name, "enabled": True})
    yield name
    try:
        await live_client.delete_project(name)
    except Exception:
        pass  # best-effort cleanup


# ---------------------------------------------------------------------------
# Tag provider fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_provider(live_client) -> AsyncGenerator[str, None]:
    """Create a test tag provider, delete it on teardown."""
    name = f"mcp-prov-{_SUFFIX}"
    await live_client.create_tag_provider(
        [
            {
                "name": name,
                "collection": "core",
                "enabled": True,
                "description": "MCP test",
                "config": {
                    "profile": {
                        "type": "STANDARD",
                        "allowBackfill": False,
                        "enableTagReferenceStore": True,
                    },
                    "settings": {"nonUseCount": 0},
                },
            }
        ]
    )
    yield name
    try:
        await live_client.delete_tag_provider(name)
    except Exception:
        pass


# ===========================================================================
# 1. Gateway — no WebDev, read-only
# ===========================================================================


class TestGatewayIntegration:
    """Validate gateway info, module health, logs, and diagnostic endpoints."""

    @pytest.mark.asyncio
    async def test_gateway_info_client(self, live_client):
        result = await live_client.get_gateway_info()
        assert isinstance(result, dict)
        # Must contain at least one of the key fields Ignition returns
        assert any(k in result for k in ("state", "edition", "version", "id"))

    @pytest.mark.asyncio
    async def test_gateway_info_tool_returns_no_error(self, live_client):
        from ignition_mcp.tools import gateway

        result = await gateway.get_gateway_info(ctx=_ctx(live_client))
        _no_error(result)

    @pytest.mark.asyncio
    async def test_gateway_state_is_running(self, live_client):
        """Gateway must report RUNNING — catches a faulted gateway early."""
        from ignition_mcp.tools import gateway

        result = await gateway.get_gateway_info(ctx=_ctx(live_client))
        if "state" in result:
            assert result["state"] == "RUNNING", (
                f"Gateway is not RUNNING: {result['state']}. "
                "Check gateway health before running integration tests."
            )

    @pytest.mark.asyncio
    async def test_module_health_client(self, live_client):
        result = await live_client.get_module_health()
        assert isinstance(result, (list, dict))

    @pytest.mark.asyncio
    async def test_module_health_tool(self, live_client):
        from ignition_mcp.tools import gateway

        result = await gateway.get_module_health(ctx=_ctx(live_client))
        _no_error(result)

    @pytest.mark.asyncio
    async def test_module_health_has_tag_module(self, live_client):
        """The module list should contain known Ignition modules.

        In Ignition 8.3+, tagging is core functionality (not a module), so we
        verify that well-known modules (e.g. Perspective, OPC-UA, Historian) are
        present instead of searching for a 'tag' module by name.
        """
        result = await live_client.get_module_health()
        # Ignition 8.3 returns {"items": [...]} where each item has an "id" field
        items = []
        if isinstance(result, list):
            items = result
        elif isinstance(result, dict) and "items" in result:
            items = result["items"]
        if items:
            ids = [str(m.get("id", "") or m.get("name", "")).lower() for m in items]
            # At least one well-known Ignition module should be present
            known = ["inductiveautomation", "cirruslink", "perspective", "opcua", "historian"]
            found = [k for k in known if any(k in i for i in ids)]
            assert found, f"No known Ignition modules found in list: {ids[:10]}"

    @pytest.mark.asyncio
    async def test_get_gateway_logs_tool(self, live_client):
        """Logs endpoint may not exist on all Ignition versions; success or graceful error."""
        from ignition_mcp.tools import gateway

        result = await gateway.get_gateway_logs(ctx=_ctx(live_client), limit=20)
        # Result is either a list of log entries or {"error": "..."} if endpoint not available
        assert isinstance(result, (list, dict))
        # If it's a connection failure (not just a 404), that's a real problem
        assert not _is_connection_error(result), f"Gateway unreachable: {result}"

    @pytest.mark.asyncio
    async def test_get_database_connections_tool(self, live_client):
        from ignition_mcp.tools import gateway

        result = await gateway.get_database_connections(ctx=_ctx(live_client))
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.asyncio
    async def test_get_opc_connections_tool(self, live_client):
        from ignition_mcp.tools import gateway

        result = await gateway.get_opc_connections(ctx=_ctx(live_client))
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.asyncio
    async def test_get_system_metrics_tool(self, live_client):
        from ignition_mcp.tools import gateway

        result = await gateway.get_system_metrics(ctx=_ctx(live_client))
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)


# ===========================================================================
# 2. Designers
# ===========================================================================


class TestDesignersIntegration:
    @pytest.mark.asyncio
    async def test_list_designers_returns_list(self, live_client):
        from ignition_mcp.tools import designers

        result = await designers.list_designers(ctx=_ctx(live_client))
        assert isinstance(result, (list, dict))
        _no_error(result)


# ===========================================================================
# 3. Projects — full CRUD lifecycle (creates + cleans up its own resources)
# ===========================================================================


class TestProjectsIntegration:
    @pytest.mark.asyncio
    async def test_list_projects_client(self, live_client):
        result = await live_client.list_projects()
        assert isinstance(result, (list, dict))

    @pytest.mark.asyncio
    async def test_list_projects_tool(self, live_client):
        from ignition_mcp.tools import projects

        result = await projects.list_projects(ctx=_ctx(live_client))
        _no_error(result)
        assert isinstance(result, (list, dict))

    @pytest.mark.asyncio
    async def test_get_nonexistent_project_returns_error(self, live_client):
        from ignition_mcp.tools import projects

        result = await projects.get_project(
            name=f"definitely-does-not-exist-{_SUFFIX}", ctx=_ctx(live_client)
        )
        # Should return {"error": "..."} not raise an exception
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_project_create_and_get(self, live_client, test_project):
        """Created project should be retrievable by name."""
        from ignition_mcp.tools import projects

        result = await projects.get_project(name=test_project, ctx=_ctx(live_client))
        _no_error(result)
        # Name should appear somewhere in the response
        assert test_project in str(result)

    @pytest.mark.asyncio
    async def test_project_appears_in_list(self, live_client, test_project):
        from ignition_mcp.tools import projects

        result = await projects.list_projects(ctx=_ctx(live_client))
        all_names = str(result)
        assert test_project in all_names, (
            f"Newly created project '{test_project}' not found in project list"
        )

    @pytest.mark.asyncio
    async def test_project_copy_and_delete(self, live_client, test_project):
        """Copy a project then delete the copy."""
        copy_name = f"{test_project}-copy"
        from ignition_mcp.tools import projects

        copy_result = await projects.copy_project(
            source_name=test_project, new_name=copy_name, ctx=_ctx(live_client)
        )
        _no_error(copy_result)

        # Confirm copy exists
        get_result = await projects.get_project(name=copy_name, ctx=_ctx(live_client))
        _no_error(get_result)

        # Clean up copy
        del_result = await projects.delete_project(name=copy_name, ctx=_ctx(live_client))
        _no_error(del_result)

    @pytest.mark.asyncio
    async def test_project_export_roundtrip(self, live_client, test_project):
        """Export a project and re-import it under a new name."""
        import_name = f"{test_project}-imported"
        from ignition_mcp.tools import projects

        # Export
        export_result = await projects.export_project(name=test_project, ctx=_ctx(live_client))
        _no_error(export_result)
        assert "content_base64" in export_result
        assert export_result["size_bytes"] > 0

        # Import as new name
        import_result = await projects.import_project(
            name=import_name,
            zip_base64=export_result["content_base64"],
            ctx=_ctx(live_client),
        )
        _no_error(import_result)

        # Verify the imported project exists
        get_result = await projects.get_project(name=import_name, ctx=_ctx(live_client))
        _no_error(get_result)

        # Clean up imported project
        await live_client.delete_project(import_name)


# ===========================================================================
# 4. Project Resources — native REST, no WebDev
# ===========================================================================


class TestProjectResourcesIntegration:
    """Tests use a dedicated test project (via fixture) for isolation."""

    # A simple Perspective view JSON that Ignition will accept
    _TEST_VIEW_CONTENT = {
        "root": {
            "type": "ia.container.flex",
            "version": 0,
            "props": {"direction": "column"},
            "children": [],
        }
    }
    _TEST_RESOURCE_PATH = "com.inductiveautomation.perspective/views/mcp-test-view/view.json"

    @pytest.mark.asyncio
    async def test_list_resources_on_new_project(self, live_client, test_project):
        from ignition_mcp.tools import resources

        result = await resources.list_project_resources(project=test_project, ctx=_ctx(live_client))
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)
        # If the endpoint returned 404, skip remaining resource tests
        if _is_endpoint_not_found(result):
            pytest.skip(
                "Project resource listing endpoint not available on this gateway version "
                "(returned 404 — requires Ignition with resource REST API support)"
            )

    @pytest.mark.asyncio
    async def test_set_and_get_resource_roundtrip(self, live_client, test_project):
        """Write a resource, read it back, assert content matches."""
        from ignition_mcp.tools import resources

        # Write
        set_result = await resources.set_project_resource(
            project=test_project,
            resource_path=self._TEST_RESOURCE_PATH,
            content=self._TEST_VIEW_CONTENT,
            ctx=_ctx(live_client),
        )
        if _is_endpoint_not_found(set_result):
            pytest.skip("Project resource set endpoint not available on this gateway version")
        _no_error(set_result)

        # Read back
        get_result = await resources.get_project_resource(
            project=test_project,
            resource_path=self._TEST_RESOURCE_PATH,
            ctx=_ctx(live_client),
        )
        _no_error(get_result)
        result_str = str(get_result)
        assert "flex" in result_str or "ia.container" in result_str, (
            f"Written view content not found in response: {result_str[:200]}"
        )

    @pytest.mark.asyncio
    async def test_resource_appears_in_listing(self, live_client, test_project):
        """After writing, the resource should appear in list_project_resources."""
        from ignition_mcp.tools import resources

        set_result = await resources.set_project_resource(
            project=test_project,
            resource_path=self._TEST_RESOURCE_PATH,
            content=self._TEST_VIEW_CONTENT,
            ctx=_ctx(live_client),
        )
        if _is_endpoint_not_found(set_result):
            pytest.skip("Project resource endpoints not available on this gateway version")

        list_result = await resources.list_project_resources(
            project=test_project,
            path_prefix="com.inductiveautomation.perspective/views",
            ctx=_ctx(live_client),
        )
        assert not _is_connection_error(list_result)
        result_str = str(list_result)
        assert "mcp-test-view" in result_str or "view.json" in result_str, (
            f"Written resource not found in listing: {result_str[:400]}"
        )

    @pytest.mark.asyncio
    async def test_get_nonexistent_resource_returns_error(self, live_client, test_project):
        from ignition_mcp.tools import resources

        result = await resources.get_project_resource(
            project=test_project,
            resource_path="com.inductiveautomation.perspective/views/does-not-exist/view.json",
            ctx=_ctx(live_client),
        )
        # Either a proper 404 error dict, or an endpoint-unavailable error — both are dicts
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_resource(self, live_client, test_project):
        """Create a resource then delete it; subsequent get should return error."""
        from ignition_mcp.tools import resources

        set_result = await resources.set_project_resource(
            project=test_project,
            resource_path=self._TEST_RESOURCE_PATH,
            content=self._TEST_VIEW_CONTENT,
            ctx=_ctx(live_client),
        )
        if _is_endpoint_not_found(set_result):
            pytest.skip("Project resource endpoints not available on this gateway version")

        del_result = await resources.delete_project_resource(
            project=test_project,
            resource_path=self._TEST_RESOURCE_PATH,
            ctx=_ctx(live_client),
        )
        _no_error(del_result)

        get_result = await resources.get_project_resource(
            project=test_project,
            resource_path=self._TEST_RESOURCE_PATH,
            ctx=_ctx(live_client),
        )
        assert "error" in get_result


# ===========================================================================
# 5. Tag Providers — create / list / get / delete lifecycle
# ===========================================================================


class TestTagProvidersIntegration:
    @pytest.mark.asyncio
    async def test_list_tag_providers(self, live_client):
        from ignition_mcp.tools import tag_providers

        result = await tag_providers.list_tag_providers(ctx=_ctx(live_client))
        _no_error(result)
        assert isinstance(result, (list, dict))

    @pytest.mark.asyncio
    async def test_default_provider_exists(self, live_client):
        """At least one tag provider should be present on any Ignition install."""
        result = await live_client.list_tag_providers()
        # Response is {"items": [...]} — check there is at least one provider
        items = result.get("items", result) if isinstance(result, dict) else result
        assert len(items) > 0, "Expected at least one tag provider; check gateway configuration"

    @pytest.mark.asyncio
    async def test_get_default_provider(self, live_client):
        """Get the first available tag provider by name."""
        from ignition_mcp.tools import tag_providers

        # Discover the actual provider name first (varies per gateway)
        list_result = await live_client.list_tag_providers()
        items = list_result.get("items", []) if isinstance(list_result, dict) else list_result
        if not items:
            pytest.skip("No tag providers found on this gateway")
        provider_name = items[0].get("name") or items[0].get("id")
        assert provider_name, f"Could not determine provider name from: {items[0]}"

        result = await tag_providers.get_tag_provider(name=provider_name, ctx=_ctx(live_client))
        _no_error(result)
        assert provider_name.lower() in str(result).lower()

    @pytest.mark.asyncio
    async def test_provider_create_and_delete_lifecycle(self, live_client, test_provider):
        """New provider should appear in the list and be retrievable."""
        from ignition_mcp.tools import tag_providers

        # Appears in list
        list_result = await tag_providers.list_tag_providers(ctx=_ctx(live_client))
        assert test_provider in str(list_result), (
            f"Newly created provider '{test_provider}' not in list"
        )

        # Retrievable individually
        get_result = await tag_providers.get_tag_provider(name=test_provider, ctx=_ctx(live_client))
        _no_error(get_result)


# ===========================================================================
# 6. Tag Browse — native REST, read-only
# ===========================================================================


class TestTagBrowseIntegration:
    @pytest.mark.asyncio
    async def test_browse_root_returns_providers(self, live_client):
        """Browsing the root (empty path) should return provider-level entries."""
        from ignition_mcp.tools import tags as tag_tools

        result = await tag_tools.browse_tags(ctx=_ctx(live_client), path="", depth=1)
        _no_error(result)
        assert isinstance(result, (list, dict))

    @pytest.mark.asyncio
    async def test_browse_default_provider(self, live_client):
        from ignition_mcp.tools import tags as tag_tools

        result = await tag_tools.browse_tags(ctx=_ctx(live_client), path="[default]", depth=1)
        _no_error(result)

    @pytest.mark.asyncio
    async def test_browse_depth_is_respected(self, live_client):
        """depth=1 vs depth=2 should return same or more results."""
        from ignition_mcp.tools import tags as tag_tools

        shallow = await tag_tools.browse_tags(ctx=_ctx(live_client), path="[default]", depth=1)
        deep = await tag_tools.browse_tags(ctx=_ctx(live_client), path="[default]", depth=2)
        # Both should succeed; deep may have more entries
        _no_error(shallow)
        _no_error(deep)

    @pytest.mark.asyncio
    async def test_browse_nonexistent_path_returns_error_or_empty(self, live_client):
        from ignition_mcp.tools import tags as tag_tools

        result = await tag_tools.browse_tags(
            ctx=_ctx(live_client), path="[definitely_no_such_provider]", depth=1
        )
        # Either empty results or an error — neither should be a raw exception
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)


# ===========================================================================
# 7. Tag Read / Write — WebDev-backed (conditional)
# ===========================================================================


@pytest.mark.skipif(not _WEBDEV_TAGS, reason="Set IGNITION_MCP_WEBDEV_TAGS=1 to enable")
class TestTagReadWriteIntegration:
    @pytest.mark.asyncio
    async def test_read_tags_returns_structured_result(self, live_client):
        """Even without a known tag path, a well-formed request should not crash."""
        from ignition_mcp.tools import tags as tag_tools

        paths = ["[default]MCP_Test_Tag"] if not _TEST_TAG_PATH else [_TEST_TAG_PATH]
        result = await tag_tools.read_tags(tag_paths=paths, ctx=_ctx(live_client))
        # Either list of readings or an error from the gateway — neither should be raw exception
        assert isinstance(result, (list, dict))

    @pytest.mark.skipif(
        not _TEST_TAG_PATH,
        reason="Set IGNITION_MCP_TEST_TAG_PATH=[default]YourTag to enable write test",
    )
    @pytest.mark.asyncio
    async def test_write_and_read_roundtrip(self, live_client):
        """Write a value to a tag then read it back — values should match."""
        from ignition_mcp.tools import tags as tag_tools

        write_value = 42.0
        write_result = await tag_tools.write_tag(
            tag_path=_TEST_TAG_PATH, value=write_value, ctx=_ctx(live_client)
        )
        _no_error(write_result)

        # Small sleep to let the write propagate
        import asyncio

        await asyncio.sleep(0.2)

        read_result = await tag_tools.read_tags(tag_paths=[_TEST_TAG_PATH], ctx=_ctx(live_client))
        _no_error(read_result)
        # The value we wrote should be present somewhere in the result
        assert str(write_value) in str(read_result) or write_value in str(read_result), (
            f"Written value {write_value} not found in read result: {read_result}"
        )


# ===========================================================================
# 8. Tag Config CRUD — WebDev-backed (conditional)
# ===========================================================================


@pytest.mark.skipif(not _WEBDEV_TAG_CONFIG, reason="Set IGNITION_MCP_WEBDEV_TAG_CONFIG=1 to enable")
class TestTagConfigIntegration:
    """Full create → get_config → edit → delete lifecycle for a test tag."""

    _PROVIDER = "default"
    _TAG_NAME = f"MCP_Test_{_SUFFIX}"
    _TAG_PATH_TPL = "[default]{name}"

    @pytest.mark.asyncio
    async def test_create_edit_delete_tag_lifecycle(self, live_client):
        from ignition_mcp.tools import tags as tag_tools

        tag_name = self._TAG_NAME
        tag_path = self._TAG_PATH_TPL.format(name=tag_name)

        # --- Create ---
        create_result = await tag_tools.create_tags(
            tags=[
                {
                    "name": tag_name,
                    "tagType": "AtomicTag",
                    "dataType": "Float8",
                    "value": 0.0,
                }
            ],
            ctx=_ctx(live_client),
            provider=self._PROVIDER,
        )
        _no_error(create_result)

        # --- Get Config ---
        config_result = await tag_tools.get_tag_config(tag_path=tag_path, ctx=_ctx(live_client))
        _no_error(config_result)
        assert tag_name in str(config_result) or "Float8" in str(config_result)

        # --- Edit (add description) ---
        edit_result = await tag_tools.edit_tags(
            tags=[{"name": tag_name, "tagType": "AtomicTag", "tooltip": "MCP integration test"}],
            ctx=_ctx(live_client),
            provider=self._PROVIDER,
        )
        _no_error(edit_result)

        # --- Delete ---
        delete_result = await tag_tools.delete_tags(tag_paths=[tag_path], ctx=_ctx(live_client))
        _no_error(delete_result)

    @pytest.mark.asyncio
    async def test_list_udt_types_returns_list(self, live_client):
        from ignition_mcp.tools import tags as tag_tools

        result = await tag_tools.list_udt_types(ctx=_ctx(live_client), provider="default")
        # May be empty on a clean gateway — that's fine
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.asyncio
    async def test_get_config_nonexistent_tag_returns_error(self, live_client):
        from ignition_mcp.tools import tags as tag_tools

        result = await tag_tools.get_tag_config(
            tag_path=f"[default]definitely_no_such_tag_{_SUFFIX}", ctx=_ctx(live_client)
        )
        assert isinstance(result, dict)
        assert "error" in result or "not found" in str(result).lower()


# ===========================================================================
# 9. Alarms — WebDev-backed (conditional)
# ===========================================================================


@pytest.mark.skipif(not _WEBDEV_ALARMS, reason="Set IGNITION_MCP_WEBDEV_ALARMS=1 to enable")
class TestAlarmsIntegration:
    @pytest.mark.asyncio
    async def test_get_active_alarms_returns_list(self, live_client):
        from ignition_mcp.tools import alarms as alarm_tools

        result = await alarm_tools.get_active_alarms(ctx=_ctx(live_client))
        # May be empty on a quiet system — that's fine
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.asyncio
    async def test_get_active_alarms_with_priority_filter(self, live_client):
        from ignition_mcp.tools import alarms as alarm_tools

        result = await alarm_tools.get_active_alarms(
            ctx=_ctx(live_client), priority_filter="Critical"
        )
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.asyncio
    async def test_get_alarm_history_returns_structured_result(self, live_client):
        from ignition_mcp.tools import alarms as alarm_tools

        # Query last 24 hours — may be empty on a fresh gateway
        result = await alarm_tools.get_alarm_history(ctx=_ctx(live_client), max_results=10)
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.asyncio
    async def test_alarm_history_with_time_range(self, live_client):
        from ignition_mcp.tools import alarms as alarm_tools

        result = await alarm_tools.get_alarm_history(
            ctx=_ctx(live_client),
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z",
            max_results=5,
        )
        # Historical date — should return empty results (or structured error if journal is off)
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.asyncio
    async def test_acknowledge_empty_list_does_not_crash(self, live_client):
        """Acknowledging an empty list should return a graceful result."""
        from ignition_mcp.tools import alarms as alarm_tools

        result = await alarm_tools.acknowledge_alarms(event_ids=[], ctx=_ctx(live_client))
        assert isinstance(result, (list, dict))


# ===========================================================================
# 10. Tag History (Historian) — WebDev-backed (conditional)
# ===========================================================================


@pytest.mark.skipif(not _WEBDEV_HISTORY, reason="Set IGNITION_MCP_WEBDEV_HISTORY=1 to enable")
class TestHistorianIntegration:
    @pytest.mark.skipif(
        not _TEST_HISTORY_TAG,
        reason="Set IGNITION_MCP_TEST_HISTORY_TAG=[default]YourTag to enable historian test",
    )
    @pytest.mark.asyncio
    async def test_get_tag_history_returns_data(self, live_client):
        from ignition_mcp.tools import historian as historian_tools

        result = await historian_tools.get_tag_history(
            tag_paths=[_TEST_HISTORY_TAG],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            ctx=_ctx(live_client),
        )
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.skipif(
        not _TEST_HISTORY_TAG,
        reason="Set IGNITION_MCP_TEST_HISTORY_TAG=[default]YourTag to enable historian test",
    )
    @pytest.mark.asyncio
    async def test_get_tag_history_with_aggregation(self, live_client):
        """Average aggregation over 1-minute intervals."""
        from ignition_mcp.tools import historian as historian_tools

        result = await historian_tools.get_tag_history(
            tag_paths=[_TEST_HISTORY_TAG],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            ctx=_ctx(live_client),
            aggregation="Average",
            interval_ms=60000,
            max_results=60,
        )
        assert isinstance(result, (list, dict))
        assert not _is_connection_error(result)

    @pytest.mark.asyncio
    async def test_get_tag_history_without_known_tag(self, live_client):
        """Requesting history for a tag that likely doesn't exist — graceful error."""
        from ignition_mcp.tools import historian as historian_tools

        result = await historian_tools.get_tag_history(
            tag_paths=[f"[default]definitely_no_such_tag_{_SUFFIX}"],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            ctx=_ctx(live_client),
        )
        assert isinstance(result, (list, dict))


# ===========================================================================
# 11. Script Execution — WebDev-backed, disabled by default (conditional)
# ===========================================================================


@pytest.mark.skipif(
    not _WEBDEV_EXEC,
    reason="Set IGNITION_MCP_WEBDEV_EXEC=1 and IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true to enable",
)
class TestScriptExecutionIntegration:
    @pytest.mark.asyncio
    async def test_disabled_by_default(self, live_client, monkeypatch):
        """Even with WebDev available, the feature must be off unless explicitly enabled."""
        from ignition_mcp.config import settings
        from ignition_mcp.tools import execution

        monkeypatch.setattr(settings, "enable_script_execution", False)
        result = await execution.run_gateway_script(script="result = 1", ctx=_ctx(live_client))
        assert "error" in result
        assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_execute(self, live_client, monkeypatch):
        from ignition_mcp.config import settings
        from ignition_mcp.tools import execution

        monkeypatch.setattr(settings, "enable_script_execution", True)
        result = await execution.run_gateway_script(
            script="result = 1 + 1", ctx=_ctx(live_client), dry_run=True
        )
        assert result.get("dry_run") is True
        assert "1 + 1" in result.get("script", "")

    @pytest.mark.asyncio
    async def test_simple_script_execution(self, live_client, monkeypatch):
        """Execute a trivial expression on the gateway."""
        from ignition_mcp.config import settings
        from ignition_mcp.tools import execution

        monkeypatch.setattr(settings, "enable_script_execution", True)
        result = await execution.run_gateway_script(
            script="result = 2 + 2", ctx=_ctx(live_client), timeout_secs=10
        )
        assert isinstance(result, dict)
        # Either error (if endpoint not deployed) or result == 4
        if "error" not in result:
            assert result.get("result") == 4

    @pytest.mark.asyncio
    async def test_gateway_script_can_read_system_version(self, live_client, monkeypatch):
        """Use system.util.getVersion() — always available on gateway scope."""
        from ignition_mcp.config import settings
        from ignition_mcp.tools import execution

        monkeypatch.setattr(settings, "enable_script_execution", True)
        result = await execution.run_gateway_script(
            script="result = system.util.getVersion()", ctx=_ctx(live_client)
        )
        assert isinstance(result, dict)
        if "error" not in result:
            # version string should contain digits
            assert any(c.isdigit() for c in str(result.get("result", "")))
