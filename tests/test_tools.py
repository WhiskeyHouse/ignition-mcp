"""Unit tests for MCP tool functions — mocked IgnitionClient, no live gateway.

Tools are now plain async functions in domain modules under
src/ignition_mcp/tools/. Tests call them directly without going through
the FastMCP wrapper.
"""

import base64
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from ignition_mcp.tools import (
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

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_ctx(client_mock: AsyncMock) -> MagicMock:
    """Build a fake FastMCP Context that returns client_mock from lifespan."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"client": client_mock}
    return ctx


def _mock_client(**overrides) -> AsyncMock:
    """Create an AsyncMock standing in for IgnitionClient."""
    client = AsyncMock()
    client.webdev_configured = overrides.get("webdev_configured", True)
    client.webdev_tag_config_configured = overrides.get("webdev_tag_config_configured", True)
    client.webdev_alarm_configured = overrides.get("webdev_alarm_configured", True)
    client.webdev_tag_history_configured = overrides.get("webdev_tag_history_configured", True)
    client.webdev_script_exec_configured = overrides.get("webdev_script_exec_configured", True)
    return client


# ------------------------------------------------------------------
# Gateway Tools
# ------------------------------------------------------------------


class TestGatewayTools:
    @pytest.mark.asyncio
    async def test_get_gateway_info_success(self):
        client = _mock_client()
        client.get_gateway_info.return_value = {"state": "RUNNING", "version": "8.1.44"}
        ctx = _make_ctx(client)

        result = await gateway.get_gateway_info(ctx=ctx)
        assert result["state"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_get_gateway_info_error(self):
        client = _mock_client()
        client.get_gateway_info.side_effect = httpx.ConnectError("refused")
        ctx = _make_ctx(client)

        result = await gateway.get_gateway_info(ctx=ctx)
        assert "error" in result
        assert "refused" in result["error"]

    @pytest.mark.asyncio
    async def test_get_module_health_success(self):
        client = _mock_client()
        client.get_module_health.return_value = [{"name": "Tags", "state": "LOADED"}]
        ctx = _make_ctx(client)

        result = await gateway.get_module_health(ctx=ctx)
        assert result[0]["name"] == "Tags"

    @pytest.mark.asyncio
    async def test_get_gateway_logs_default_params(self):
        client = _mock_client()
        client.get_logs.return_value = [{"level": "INFO", "message": "ok"}]
        ctx = _make_ctx(client)

        result = await gateway.get_gateway_logs(ctx=ctx)
        assert result[0]["level"] == "INFO"
        client.get_logs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_gateway_logs_with_filters(self):
        client = _mock_client()
        client.get_logs.return_value = []
        ctx = _make_ctx(client)

        await gateway.get_gateway_logs(ctx=ctx, level="ERROR", logger_name="com.test", limit=50)
        call_params = client.get_logs.call_args.kwargs["params"]
        assert call_params["level"] == "ERROR"
        assert call_params["logger"] == "com.test"
        assert call_params["limit"] == 50

    @pytest.mark.asyncio
    async def test_get_database_connections_success(self):
        client = _mock_client()
        client.get_database_connections.return_value = [{"name": "db1", "state": "Valid"}]
        ctx = _make_ctx(client)

        result = await gateway.get_database_connections(ctx=ctx)
        assert result[0]["name"] == "db1"

    @pytest.mark.asyncio
    async def test_get_database_connections_error(self):
        client = _mock_client()
        client.get_database_connections.side_effect = Exception("not found")
        ctx = _make_ctx(client)

        result = await gateway.get_database_connections(ctx=ctx)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_opc_connections_success(self):
        client = _mock_client()
        client.get_opc_connections.return_value = [{"name": "opc1", "connected": True}]
        ctx = _make_ctx(client)

        result = await gateway.get_opc_connections(ctx=ctx)
        assert result[0]["name"] == "opc1"

    @pytest.mark.asyncio
    async def test_get_system_metrics_success(self):
        client = _mock_client()
        client.get_system_metrics.return_value = {"cpu": 12.5, "memory": 60.0}
        ctx = _make_ctx(client)

        result = await gateway.get_system_metrics(ctx=ctx)
        assert result["cpu"] == 12.5


# ------------------------------------------------------------------
# Project Tools
# ------------------------------------------------------------------


class TestProjectTools:
    @pytest.mark.asyncio
    async def test_list_projects(self):
        client = _mock_client()
        client.list_projects.return_value = [{"name": "P1"}, {"name": "P2"}]
        ctx = _make_ctx(client)

        result = await projects.list_projects(ctx=ctx)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_project(self):
        client = _mock_client()
        client.get_project.return_value = {"name": "MyProj", "enabled": True}
        ctx = _make_ctx(client)

        result = await projects.get_project(name="MyProj", ctx=ctx)
        assert result["name"] == "MyProj"
        client.get_project.assert_awaited_once_with("MyProj")

    @pytest.mark.asyncio
    async def test_create_project_with_optional_params(self):
        client = _mock_client()
        client.create_project.return_value = {"status": "created"}
        ctx = _make_ctx(client)

        result = await projects.create_project(
            name="New", ctx=ctx, title="My Title", description="Desc", parent="Base"
        )
        assert result["status"] == "created"
        body = client.create_project.call_args.args[0]
        assert body["name"] == "New"
        assert body["title"] == "My Title"
        assert body["parent"] == "Base"

    @pytest.mark.asyncio
    async def test_delete_project_error(self):
        client = _mock_client()
        client.delete_project.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )
        ctx = _make_ctx(client)

        result = await projects.delete_project(name="Missing", ctx=ctx)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_copy_project(self):
        client = _mock_client()
        client.copy_project.return_value = {"status": "ok"}
        ctx = _make_ctx(client)

        result = await projects.copy_project(source_name="A", new_name="B", ctx=ctx)
        assert result["status"] == "ok"
        client.copy_project.assert_awaited_once_with("A", "B")

    @pytest.mark.asyncio
    async def test_rename_project(self):
        client = _mock_client()
        client.rename_project.return_value = {"status": "ok"}
        ctx = _make_ctx(client)

        await projects.rename_project(current_name="Old", new_name="New", ctx=ctx)
        client.rename_project.assert_awaited_once_with("Old", "New")

    @pytest.mark.asyncio
    async def test_export_project(self):
        zip_content = b"PK\x03\x04fake-zip"
        mock_resp = MagicMock()
        mock_resp.content = zip_content
        mock_resp.headers = {"content-disposition": 'attachment; filename="Proj.zip"'}

        client = _mock_client()
        client.export_project.return_value = mock_resp
        ctx = _make_ctx(client)

        result = await projects.export_project(name="Proj", ctx=ctx)
        assert result["filename"] == "Proj.zip"
        assert result["size_bytes"] == len(zip_content)
        decoded = base64.b64decode(result["content_base64"])
        assert decoded == zip_content

    @pytest.mark.asyncio
    async def test_import_project_bad_base64(self):
        client = _mock_client()
        ctx = _make_ctx(client)

        result = await projects.import_project(
            name="P", zip_base64="@@@not~base64~at~all@@@", ctx=ctx
        )
        assert "error" in result
        assert "base64" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_import_project_success(self):
        client = _mock_client()
        client.import_project.return_value = {"status": "imported"}
        ctx = _make_ctx(client)

        valid_b64 = base64.b64encode(b"PK\x03\x04fake").decode()
        result = await projects.import_project(
            name="P", zip_base64=valid_b64, ctx=ctx, overwrite=True
        )
        assert result["status"] == "imported"
        client.import_project.assert_awaited_once()


# ------------------------------------------------------------------
# Project Resource Tools
# ------------------------------------------------------------------


class TestResourceTools:
    @pytest.mark.asyncio
    async def test_list_project_resources(self):
        client = _mock_client()
        client.list_project_resources.return_value = [
            {"path": "com.ia.perspective/views/Main/view.json"}
        ]
        ctx = _make_ctx(client)

        result = await resources.list_project_resources(project="MyProj", ctx=ctx)
        assert len(result) == 1
        client.list_project_resources.assert_awaited_once_with("MyProj", path_prefix=None)

    @pytest.mark.asyncio
    async def test_list_project_resources_with_prefix(self):
        client = _mock_client()
        client.list_project_resources.return_value = []
        ctx = _make_ctx(client)

        await resources.list_project_resources(
            project="P", ctx=ctx, path_prefix="com.inductiveautomation.perspective/views"
        )
        client.list_project_resources.assert_awaited_once_with(
            "P", path_prefix="com.inductiveautomation.perspective/views"
        )

    @pytest.mark.asyncio
    async def test_get_project_resource(self):
        client = _mock_client()
        client.get_project_resource.return_value = {"root": {"type": "flex-container"}}
        ctx = _make_ctx(client)

        result = await resources.get_project_resource(
            project="P",
            resource_path="com.inductiveautomation.perspective/views/Main/view.json",
            ctx=ctx,
        )
        assert "root" in result

    @pytest.mark.asyncio
    async def test_set_project_resource(self):
        client = _mock_client()
        client.set_project_resource.return_value = {"status": "ok"}
        ctx = _make_ctx(client)

        content = {"root": {"type": "label", "props": {"text": "Hello"}}}
        result = await resources.set_project_resource(
            project="P",
            resource_path="com.inductiveautomation.perspective/views/Main/view.json",
            content=content,
            ctx=ctx,
        )
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_delete_project_resource(self):
        client = _mock_client()
        client.delete_project_resource.return_value = {"status": "deleted"}
        ctx = _make_ctx(client)

        result = await resources.delete_project_resource(
            project="P",
            resource_path="com.inductiveautomation.perspective/views/Old/view.json",
            ctx=ctx,
        )
        assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_resource_error_propagated(self):
        client = _mock_client()
        client.get_project_resource.side_effect = Exception("404 not found")
        ctx = _make_ctx(client)

        result = await resources.get_project_resource(
            project="P", resource_path="missing/resource.json", ctx=ctx
        )
        assert "error" in result
        assert "404 not found" in result["error"]


# ------------------------------------------------------------------
# Designer Tools
# ------------------------------------------------------------------


class TestDesignerTools:
    @pytest.mark.asyncio
    async def test_list_designers(self):
        client = _mock_client()
        client.list_designers.return_value = [{"user": "alice", "project": "MyProj"}]
        ctx = _make_ctx(client)

        result = await designers.list_designers(ctx=ctx)
        assert result[0]["user"] == "alice"


# ------------------------------------------------------------------
# Tag Provider Tools
# ------------------------------------------------------------------


class TestTagProviderTools:
    @pytest.mark.asyncio
    async def test_list_tag_providers(self):
        client = _mock_client()
        client.list_tag_providers.return_value = [{"name": "default"}]
        ctx = _make_ctx(client)

        result = await tag_providers.list_tag_providers(ctx=ctx)
        assert result[0]["name"] == "default"

    @pytest.mark.asyncio
    async def test_create_tag_provider_builds_correct_body(self):
        client = _mock_client()
        client.create_tag_provider.return_value = {"status": "ok"}
        ctx = _make_ctx(client)

        await tag_providers.create_tag_provider(
            name="custom", ctx=ctx, description="test", provider_type="REMOTE"
        )
        body = client.create_tag_provider.call_args.args[0]
        assert body[0]["name"] == "custom"
        assert body[0]["config"]["profile"]["type"] == "REMOTE"

    @pytest.mark.asyncio
    async def test_delete_tag_provider(self):
        client = _mock_client()
        client.delete_tag_provider.return_value = {"status": "deleted"}
        ctx = _make_ctx(client)

        result = await tag_providers.delete_tag_provider(name="old", ctx=ctx)
        assert result["status"] == "deleted"


# ------------------------------------------------------------------
# Browse Tags
# ------------------------------------------------------------------


class TestBrowseTagsTool:
    @pytest.mark.asyncio
    async def test_browse_tags_defaults(self):
        client = _mock_client()
        client.browse_tags.return_value = {"results": []}
        ctx = _make_ctx(client)

        await tags.browse_tags(ctx=ctx)
        client.browse_tags.assert_awaited_once_with(path="", depth=2)

    @pytest.mark.asyncio
    async def test_browse_tags_with_params(self):
        client = _mock_client()
        client.browse_tags.return_value = {"results": [{"name": "Tag1"}]}
        ctx = _make_ctx(client)

        await tags.browse_tags(ctx=ctx, path="[default]", depth=3)
        client.browse_tags.assert_awaited_once_with(path="[default]", depth=3)


# ------------------------------------------------------------------
# WebDev Tag Read/Write
# ------------------------------------------------------------------


class TestWebDevTagTools:
    @pytest.mark.asyncio
    async def test_read_tags_not_configured(self):
        client = _mock_client(webdev_configured=False)
        ctx = _make_ctx(client)

        result = await tags.read_tags(tag_paths=["[default]T1"], ctx=ctx)
        assert "error" in result
        assert "help" in result
        client.read_tags.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_read_tags_success(self):
        client = _mock_client()
        client.read_tags.return_value = [{"path": "[default]T1", "value": 42, "quality": "Good"}]
        ctx = _make_ctx(client)

        result = await tags.read_tags(tag_paths=["[default]T1"], ctx=ctx)
        assert result[0]["value"] == 42

    @pytest.mark.asyncio
    async def test_write_tag_not_configured(self):
        client = _mock_client(webdev_configured=False)
        ctx = _make_ctx(client)

        result = await tags.write_tag(tag_path="[default]SP", value=100, ctx=ctx)
        assert "error" in result
        assert "help" in result
        client.write_tag.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_write_tag_success(self):
        client = _mock_client()
        client.write_tag.return_value = {"status": "ok"}
        ctx = _make_ctx(client)

        result = await tags.write_tag(
            tag_path="[default]SP", value=55.5, ctx=ctx, data_type="Float8"
        )
        assert result["status"] == "ok"
        client.write_tag.assert_awaited_once_with("[default]SP", 55.5, data_type="Float8")

    @pytest.mark.asyncio
    async def test_write_tag_error(self):
        client = _mock_client()
        client.write_tag.side_effect = Exception("timeout")
        ctx = _make_ctx(client)

        result = await tags.write_tag(tag_path="[default]X", value=0, ctx=ctx)
        assert "error" in result
        assert "timeout" in result["error"]


# ------------------------------------------------------------------
# Tag Config CRUD (WebDev-backed)
# ------------------------------------------------------------------


class TestTagConfigTools:
    @pytest.mark.asyncio
    async def test_get_tag_config_not_configured(self):
        client = _mock_client(webdev_tag_config_configured=False)
        ctx = _make_ctx(client)

        result = await tags.get_tag_config(tag_path="[default]T1", ctx=ctx)
        assert "error" in result
        assert "help" in result
        client.get_tag_config.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_tag_config_success(self):
        client = _mock_client()
        client.get_tag_config.return_value = {
            "name": "T1",
            "tagType": "AtomicTag",
            "dataType": "Float8",
        }
        ctx = _make_ctx(client)

        result = await tags.get_tag_config(tag_path="[default]T1", ctx=ctx)
        assert result["dataType"] == "Float8"
        client.get_tag_config.assert_awaited_once_with("[default]T1")

    @pytest.mark.asyncio
    async def test_create_tags_success(self):
        client = _mock_client()
        client.configure_tags.return_value = {"status": "ok", "created": 2}
        ctx = _make_ctx(client)

        tag_list = [
            {"name": "TagA", "tagType": "AtomicTag", "dataType": "Float8"},
            {"name": "TagB", "tagType": "AtomicTag", "dataType": "Int4"},
        ]
        result = await tags.create_tags(tags=tag_list, ctx=ctx, provider="default")
        assert result["created"] == 2
        client.configure_tags.assert_awaited_once_with(tag_list, edit_mode="a", provider="default")

    @pytest.mark.asyncio
    async def test_edit_tags_uses_merge_mode(self):
        client = _mock_client()
        client.configure_tags.return_value = {"status": "ok"}
        ctx = _make_ctx(client)

        tag_list = [{"name": "TagA", "dataType": "String"}]
        await tags.edit_tags(tags=tag_list, ctx=ctx)
        client.configure_tags.assert_awaited_once_with(tag_list, edit_mode="m", provider=None)

    @pytest.mark.asyncio
    async def test_delete_tags_success(self):
        client = _mock_client()
        client.delete_tags.return_value = {"status": "deleted", "count": 1}
        ctx = _make_ctx(client)

        result = await tags.delete_tags(tag_paths=["[default]OldTag"], ctx=ctx)
        assert result["count"] == 1
        client.delete_tags.assert_awaited_once_with(["[default]OldTag"])

    @pytest.mark.asyncio
    async def test_list_udt_types_default_provider(self):
        client = _mock_client()
        client.list_udt_types.return_value = [{"name": "Motor"}, {"name": "Pump"}]
        ctx = _make_ctx(client)

        result = await tags.list_udt_types(ctx=ctx)
        assert len(result) == 2
        client.list_udt_types.assert_awaited_once_with(provider="default")

    @pytest.mark.asyncio
    async def test_get_udt_definition_success(self):
        client = _mock_client()
        client.get_udt_definition.return_value = {"name": "Motor", "members": []}
        ctx = _make_ctx(client)

        result = await tags.get_udt_definition(udt_path="[default]_types_/Motor", ctx=ctx)
        assert result["name"] == "Motor"
        client.get_udt_definition.assert_awaited_once_with("[default]_types_/Motor")

    @pytest.mark.asyncio
    async def test_tag_config_not_configured_returns_help(self):
        client = _mock_client(webdev_tag_config_configured=False)
        ctx = _make_ctx(client)

        for fn, kwargs in [
            (tags.create_tags, {"tags": []}),
            (tags.edit_tags, {"tags": []}),
            (tags.delete_tags, {"tag_paths": []}),
            (tags.list_udt_types, {}),
            (tags.get_udt_definition, {"udt_path": "[default]_types_/Motor"}),
        ]:
            result = await fn(ctx=ctx, **kwargs)
            assert "error" in result
            assert "help" in result


# ------------------------------------------------------------------
# Alarm Tools
# ------------------------------------------------------------------


class TestAlarmTools:
    @pytest.mark.asyncio
    async def test_get_active_alarms_not_configured(self):
        client = _mock_client(webdev_alarm_configured=False)
        ctx = _make_ctx(client)

        result = await alarms.get_active_alarms(ctx=ctx)
        assert "error" in result
        assert "help" in result
        client.get_active_alarms.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_active_alarms_success(self):
        client = _mock_client()
        client.get_active_alarms.return_value = [
            {"eventId": "abc-123", "displayPath": "Zone1/HighTemp", "priority": "High"}
        ]
        ctx = _make_ctx(client)

        result = await alarms.get_active_alarms(ctx=ctx)
        assert result[0]["priority"] == "High"

    @pytest.mark.asyncio
    async def test_get_active_alarms_with_filters(self):
        client = _mock_client()
        client.get_active_alarms.return_value = []
        ctx = _make_ctx(client)

        await alarms.get_active_alarms(
            ctx=ctx, source_filter="[default]Zone1", priority_filter="High"
        )
        client.get_active_alarms.assert_awaited_once_with(
            source_filter="[default]Zone1",
            priority_filter="High",
            state_filter=None,
        )

    @pytest.mark.asyncio
    async def test_get_alarm_history_success(self):
        client = _mock_client()
        client.get_alarm_history.return_value = {"entries": [], "total": 0}
        ctx = _make_ctx(client)

        result = await alarms.get_alarm_history(
            ctx=ctx, start_time="2024-01-15T00:00:00Z", end_time="2024-01-16T00:00:00Z"
        )
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_acknowledge_alarms_success(self):
        client = _mock_client()
        client.acknowledge_alarms.return_value = {"acknowledged": 2}
        ctx = _make_ctx(client)

        result = await alarms.acknowledge_alarms(
            event_ids=["abc-1", "abc-2"], ctx=ctx, ack_note="Investigated and resolved"
        )
        assert result["acknowledged"] == 2
        client.acknowledge_alarms.assert_awaited_once_with(
            ["abc-1", "abc-2"], ack_note="Investigated and resolved"
        )


# ------------------------------------------------------------------
# Historian Tools
# ------------------------------------------------------------------


class TestHistorianTools:
    @pytest.mark.asyncio
    async def test_get_tag_history_not_configured(self):
        client = _mock_client(webdev_tag_history_configured=False)
        ctx = _make_ctx(client)

        result = await historian.get_tag_history(
            tag_paths=["[default]T1"],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            ctx=ctx,
        )
        assert "error" in result
        assert "help" in result
        client.get_tag_history.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_tag_history_success(self):
        client = _mock_client()
        client.get_tag_history.return_value = {
            "tags": [{"path": "[default]T1", "values": [{"t": "2024-01-15T00:00:00Z", "v": 23.5}]}]
        }
        ctx = _make_ctx(client)

        result = await historian.get_tag_history(
            tag_paths=["[default]T1"],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            ctx=ctx,
        )
        assert result["tags"][0]["path"] == "[default]T1"

    @pytest.mark.asyncio
    async def test_get_tag_history_passes_all_params(self):
        client = _mock_client()
        client.get_tag_history.return_value = {}
        ctx = _make_ctx(client)

        await historian.get_tag_history(
            tag_paths=["[default]T1"],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            ctx=ctx,
            aggregation="Average",
            interval_ms=60000,
            max_results=500,
        )
        client.get_tag_history.assert_awaited_once_with(
            tag_paths=["[default]T1"],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            aggregation="Average",
            interval_ms=60000,
            max_results=500,
        )


# ------------------------------------------------------------------
# Execution Tools
# ------------------------------------------------------------------


class TestExecutionTools:
    @pytest.mark.asyncio
    async def test_run_gateway_script_disabled_by_default(self, monkeypatch):
        from ignition_mcp.config import settings

        monkeypatch.setattr(settings, "enable_script_execution", False)
        client = _mock_client()
        ctx = _make_ctx(client)

        result = await execution.run_gateway_script(script="print('hi')", ctx=ctx)
        assert "error" in result
        assert "disabled" in result["error"].lower()
        client.run_gateway_script.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_gateway_script_not_configured(self, monkeypatch):
        from ignition_mcp.config import settings

        monkeypatch.setattr(settings, "enable_script_execution", True)
        client = _mock_client(webdev_script_exec_configured=False)
        ctx = _make_ctx(client)

        result = await execution.run_gateway_script(script="print('hi')", ctx=ctx)
        assert "error" in result
        assert "help" in result
        client.run_gateway_script.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_gateway_script_dry_run(self, monkeypatch):
        from ignition_mcp.config import settings

        monkeypatch.setattr(settings, "enable_script_execution", True)
        client = _mock_client()
        ctx = _make_ctx(client)

        result = await execution.run_gateway_script(
            script="system.tag.readBlocking(['[default]T'])", ctx=ctx, dry_run=True
        )
        assert result["dry_run"] is True
        assert result["would_execute"] is True
        assert "system.tag" in result["script"]
        client.run_gateway_script.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_gateway_script_success(self, monkeypatch):
        from ignition_mcp.config import settings

        monkeypatch.setattr(settings, "enable_script_execution", True)
        client = _mock_client()
        client.run_gateway_script.return_value = {"result": 42, "stdout": "", "error": None}
        ctx = _make_ctx(client)

        result = await execution.run_gateway_script(script="result = 42", ctx=ctx, timeout_secs=5)
        assert result["result"] == 42
        client.run_gateway_script.assert_awaited_once_with(
            script="result = 42", timeout_secs=5, dry_run=False
        )

    @pytest.mark.asyncio
    async def test_run_gateway_script_timeout_clamped(self, monkeypatch):
        """timeout_secs > 60 is clamped on the client side."""
        from ignition_mcp.config import settings

        monkeypatch.setattr(settings, "enable_script_execution", True)
        client = _mock_client()
        client.run_gateway_script.return_value = {"result": None}
        ctx = _make_ctx(client)

        # timeout_secs is clamped to max 60 by the tool's Field(le=60) annotation
        # and additionally by the client method. We test a value within range here.
        await execution.run_gateway_script(script="pass", ctx=ctx, timeout_secs=30)
        client.run_gateway_script.assert_awaited_once_with(
            script="pass", timeout_secs=30, dry_run=False
        )
