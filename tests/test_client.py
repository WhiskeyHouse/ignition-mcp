"""Unit tests for IgnitionClient — mocked httpx, no live gateway required."""

import base64

import pytest

from ignition_mcp.ignition_client import IgnitionClient

# ------------------------------------------------------------------
# Construction & Auth
# ------------------------------------------------------------------


class TestClientAuth:
    def test_api_key_auth_headers(self):
        client = IgnitionClient(gateway_url="http://gw:8088", api_key="my-key", ssl_verify=False)
        headers = client._auth_headers()
        assert headers == {"X-Ignition-API-Token": "my-key"}

    def test_basic_auth_headers_when_no_api_key(self, monkeypatch):
        # Patch settings so the fallback doesn't pick up a real .env key
        from ignition_mcp.config import settings

        monkeypatch.setattr(settings, "ignition_api_key", "")
        client = IgnitionClient(
            gateway_url="http://gw:8088",
            api_key="",
            username="admin",
            password="secret",
            ssl_verify=False,
        )
        headers = client._auth_headers()
        expected = base64.b64encode(b"admin:secret").decode()
        assert headers == {"Authorization": f"Basic {expected}"}

    def test_gateway_url_trailing_slash_stripped(self):
        client = IgnitionClient(gateway_url="http://gw:8088/", api_key="k", ssl_verify=False)
        assert client.gateway_url == "http://gw:8088"


# ------------------------------------------------------------------
# _request internals
# ------------------------------------------------------------------


class TestRequest:
    @pytest.mark.asyncio
    async def test_request_json_response(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"version": "8.1.44"})
        mock_client._client.request.return_value = resp

        result = await mock_client._request("GET", "/data/api/v1/gateway-info")
        assert result == {"version": "8.1.44"}
        mock_client._client.request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_request_text_response(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(text="OK", headers={"content-type": "text/plain"})
        mock_client._client.request.return_value = resp

        result = await mock_client._request("GET", "/health")
        assert result == {"status": "success", "content": "OK"}

    @pytest.mark.asyncio
    async def test_request_raw_response(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(content=b"\x50\x4b\x03\x04")
        mock_client._client.request.return_value = resp

        result = await mock_client._request("GET", "/export", raw_response=True)
        assert result is resp

    @pytest.mark.asyncio
    async def test_request_includes_auth_headers(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={})
        mock_client._client.request.return_value = resp

        await mock_client._request("GET", "/test")
        call_kwargs = mock_client._client.request.call_args
        headers = call_kwargs.kwargs["headers"]
        assert "X-Ignition-API-Token" in headers


# ------------------------------------------------------------------
# Gateway methods
# ------------------------------------------------------------------


class TestGatewayMethods:
    @pytest.mark.asyncio
    async def test_get_gateway_info(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"edition": "standard", "state": "RUNNING"})
        mock_client._client.request.return_value = resp

        result = await mock_client.get_gateway_info()
        assert result["state"] == "RUNNING"
        call_args = mock_client._client.request.call_args
        assert call_args.kwargs["url"] == "/data/api/v1/gateway-info"

    @pytest.mark.asyncio
    async def test_get_module_health(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data=[{"name": "Tags", "state": "LOADED"}])
        mock_client._client.request.return_value = resp

        result = await mock_client.get_module_health()
        assert result[0]["name"] == "Tags"

    @pytest.mark.asyncio
    async def test_get_logs(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data=[{"level": "INFO", "message": "started"}])
        mock_client._client.request.return_value = resp

        result = await mock_client.get_logs(params={"limit": 10})
        assert result[0]["level"] == "INFO"
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["params"] == {"limit": 10}

    @pytest.mark.asyncio
    async def test_get_database_connections(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data=[{"name": "mydb", "status": "Valid"}])
        mock_client._client.request.return_value = resp

        result = await mock_client.get_database_connections()
        assert result[0]["name"] == "mydb"
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "/connections/database" in call_kwargs["url"]

    @pytest.mark.asyncio
    async def test_get_opc_connections(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data=[{"name": "opc1", "connected": True}])
        mock_client._client.request.return_value = resp

        result = await mock_client.get_opc_connections()
        assert result[0]["connected"] is True
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "/connections/opc" in call_kwargs["url"]

    @pytest.mark.asyncio
    async def test_get_system_metrics(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"cpu": 5.2, "memoryMB": 1024})
        mock_client._client.request.return_value = resp

        result = await mock_client.get_system_metrics()
        assert result["cpu"] == 5.2
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "/system/metrics" in call_kwargs["url"]


# ------------------------------------------------------------------
# Project methods
# ------------------------------------------------------------------


class TestProjectMethods:
    @pytest.mark.asyncio
    async def test_list_projects(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data=[{"name": "Proj1"}, {"name": "Proj2"}])
        mock_client._client.request.return_value = resp

        result = await mock_client.list_projects()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_project(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"name": "MyProject", "enabled": True})
        mock_client._client.request.return_value = resp

        result = await mock_client.get_project("MyProject")
        assert result["name"] == "MyProject"
        assert "/data/api/v1/projects/find/MyProject" in str(mock_client._client.request.call_args)

    @pytest.mark.asyncio
    async def test_create_project(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"status": "created"})
        mock_client._client.request.return_value = resp

        body = {"name": "NewProj", "enabled": True}
        result = await mock_client.create_project(body)
        assert result["status"] == "created"
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"] == body

    @pytest.mark.asyncio
    async def test_delete_project(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"status": "deleted"})
        mock_client._client.request.return_value = resp

        await mock_client.delete_project("OldProj")
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "OldProj" in call_kwargs["url"]
        assert call_kwargs["params"] == {"confirm": True}

    @pytest.mark.asyncio
    async def test_copy_project(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"status": "ok"})
        mock_client._client.request.return_value = resp

        await mock_client.copy_project("Src", "Dest")
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"] == {"fromName": "Src", "toName": "Dest"}

    @pytest.mark.asyncio
    async def test_rename_project(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"status": "ok"})
        mock_client._client.request.return_value = resp

        await mock_client.rename_project("Old", "New")
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "Old" in call_kwargs["url"]
        assert call_kwargs["json"] == {"name": "New"}

    @pytest.mark.asyncio
    async def test_export_project_returns_raw_response(self, mock_client, mock_httpx_response):
        zip_bytes = b"PK\x03\x04fake-zip-data"
        resp = mock_httpx_response(content=zip_bytes)
        mock_client._client.request.return_value = resp

        result = await mock_client.export_project("MyProject")
        assert result.content == zip_bytes

    @pytest.mark.asyncio
    async def test_import_project(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"status": "imported"})
        mock_client._client.request.return_value = resp

        zip_bytes = b"PK\x03\x04fake"
        result = await mock_client.import_project("Proj", zip_bytes, overwrite=True)
        assert result["status"] == "imported"
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["content"] == zip_bytes
        assert call_kwargs["params"] == {"overwrite": "true"}


# ------------------------------------------------------------------
# Project Resource methods
# ------------------------------------------------------------------


class TestProjectResourceMethods:
    @pytest.mark.asyncio
    async def test_list_project_resources(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data=[{"path": "com.ia.perspective/views/Main/view.json"}])
        mock_client._client.request.return_value = resp

        result = await mock_client.list_project_resources("MyProject")
        assert len(result) == 1
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "MyProject" in call_kwargs["url"]

    @pytest.mark.asyncio
    async def test_list_project_resources_with_prefix(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data=[])
        mock_client._client.request.return_value = resp

        await mock_client.list_project_resources(
            "MyProject", path_prefix="com.inductiveautomation.perspective/views"
        )
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["params"]["path"] == "com.inductiveautomation.perspective/views"

    @pytest.mark.asyncio
    async def test_get_project_resource(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"root": {"type": "label"}})
        mock_client._client.request.return_value = resp

        result = await mock_client.get_project_resource(
            "MyProject", "com.inductiveautomation.perspective/views/Main/view.json"
        )
        assert result["root"]["type"] == "label"

    @pytest.mark.asyncio
    async def test_set_project_resource(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"status": "ok"})
        mock_client._client.request.return_value = resp

        content = {"root": {"type": "label"}}
        result = await mock_client.set_project_resource(
            "MyProject",
            "com.inductiveautomation.perspective/views/Main/view.json",
            content,
        )
        assert result["status"] == "ok"
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["method"] == "PUT"
        assert call_kwargs["json"] == content

    @pytest.mark.asyncio
    async def test_delete_project_resource(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"status": "deleted"})
        mock_client._client.request.return_value = resp

        await mock_client.delete_project_resource(
            "MyProject", "com.inductiveautomation.perspective/views/Old/view.json"
        )
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["method"] == "DELETE"


# ------------------------------------------------------------------
# Tag Provider methods
# ------------------------------------------------------------------


class TestTagProviderMethods:
    @pytest.mark.asyncio
    async def test_list_tag_providers(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data=[{"name": "default"}])
        mock_client._client.request.return_value = resp

        result = await mock_client.list_tag_providers()
        assert result[0]["name"] == "default"

    @pytest.mark.asyncio
    async def test_get_tag_provider(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"name": "default", "type": "STANDARD"})
        mock_client._client.request.return_value = resp

        result = await mock_client.get_tag_provider("default")
        assert result["type"] == "STANDARD"

    @pytest.mark.asyncio
    async def test_delete_tag_provider(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"status": "deleted"})
        mock_client._client.request.return_value = resp

        await mock_client.delete_tag_provider("test-provider")
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"]["name"] == "test-provider"


# ------------------------------------------------------------------
# Tag Browse
# ------------------------------------------------------------------


class TestBrowseTags:
    @pytest.mark.asyncio
    async def test_browse_tags_default_params(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"results": []})
        mock_client._client.request.return_value = resp

        await mock_client.browse_tags()
        call_kwargs = mock_client._client.request.call_args.kwargs
        # No path param when empty, but depth should be set
        assert call_kwargs["params"]["depth"] == 2

    @pytest.mark.asyncio
    async def test_browse_tags_with_path(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"results": []})
        mock_client._client.request.return_value = resp

        await mock_client.browse_tags(path="[default]Folder", depth=3)
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["params"]["path"] == "[default]Folder"
        assert call_kwargs["params"]["depth"] == 3

    @pytest.mark.asyncio
    async def test_browse_tags_depth_capped_at_4(self, mock_client, mock_httpx_response):
        resp = mock_httpx_response(json_data={"results": []})
        mock_client._client.request.return_value = resp

        await mock_client.browse_tags(depth=10)
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["params"]["depth"] == 4


# ------------------------------------------------------------------
# WebDev Tag Read/Write
# ------------------------------------------------------------------


class TestWebDevTags:
    def test_webdev_not_configured_by_default(self, mock_client):
        assert mock_client.webdev_configured is False

    def test_webdev_configured_when_set(self, mock_client, webdev_settings):
        assert mock_client.webdev_configured is True

    def test_webdev_url_construction(self, mock_client, webdev_settings):
        url = mock_client._webdev_url()
        assert url == "/system/webdev/Global/GatewayAPI/tags"

    def test_webdev_url_with_override(self, mock_client):
        url = mock_client._webdev_url("Custom/Endpoint")
        assert url == "/system/webdev/Custom/Endpoint"

    @pytest.mark.asyncio
    async def test_read_tags(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(
            json_data=[{"path": "[default]T1", "value": 42, "quality": "Good"}]
        )
        mock_client._client.request.return_value = resp

        result = await mock_client.read_tags(["[default]T1"])
        assert result[0]["value"] == 42
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"] == {"paths": ["[default]T1"]}

    @pytest.mark.asyncio
    async def test_write_tag(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"status": "ok"})
        mock_client._client.request.return_value = resp

        await mock_client.write_tag("[default]SetPoint", 100.5, data_type="Float8")
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"] == {
            "tagPath": "[default]SetPoint",
            "value": 100.5,
            "dataType": "Float8",
        }

    @pytest.mark.asyncio
    async def test_write_tag_without_data_type(
        self, mock_client, mock_httpx_response, webdev_settings
    ):
        resp = mock_httpx_response(json_data={"status": "ok"})
        mock_client._client.request.return_value = resp

        await mock_client.write_tag("[default]Counter", 7)
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "dataType" not in call_kwargs["json"]


# ------------------------------------------------------------------
# Tag Config CRUD (WebDev-backed)
# ------------------------------------------------------------------


class TestTagConfigMethods:
    def test_webdev_tag_config_not_configured_by_default(self, mock_client):
        assert mock_client.webdev_tag_config_configured is False

    def test_webdev_tag_config_configured_when_set(self, mock_client, webdev_settings):
        assert mock_client.webdev_tag_config_configured is True

    def test_webdev_tag_config_url(self, mock_client, webdev_settings):
        url = mock_client._webdev_tag_config_url()
        assert url == "/system/webdev/Global/GatewayAPI/tagConfig"

    @pytest.mark.asyncio
    async def test_get_tag_config(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"name": "MyTag", "dataType": "Float8"})
        mock_client._client.request.return_value = resp

        result = await mock_client.get_tag_config("[default]MyTag")
        assert result["dataType"] == "Float8"
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"] == {"action": "getConfig", "tagPath": "[default]MyTag"}

    @pytest.mark.asyncio
    async def test_configure_tags_add_mode(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"status": "ok"})
        mock_client._client.request.return_value = resp

        tags_to_add = [{"name": "NewTag", "tagType": "AtomicTag", "dataType": "Int4"}]
        await mock_client.configure_tags(tags_to_add, edit_mode="a", provider="default")
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"]["action"] == "configure"
        assert call_kwargs["json"]["editMode"] == "a"
        assert call_kwargs["json"]["provider"] == "default"

    @pytest.mark.asyncio
    async def test_configure_tags_merge_no_provider(
        self, mock_client, mock_httpx_response, webdev_settings
    ):
        resp = mock_httpx_response(json_data={"status": "ok"})
        mock_client._client.request.return_value = resp

        await mock_client.configure_tags([{"name": "T"}], edit_mode="m")
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "provider" not in call_kwargs["json"]

    @pytest.mark.asyncio
    async def test_delete_tags(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"deleted": 1})
        mock_client._client.request.return_value = resp

        await mock_client.delete_tags(["[default]OldTag"])
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"] == {
            "action": "deleteTags",
            "tagPaths": ["[default]OldTag"],
        }

    @pytest.mark.asyncio
    async def test_list_udt_types(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data=[{"name": "Motor"}, {"name": "Pump"}])
        mock_client._client.request.return_value = resp

        result = await mock_client.list_udt_types(provider="default")
        assert len(result) == 2
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"] == {"action": "listUDTTypes", "provider": "default"}

    @pytest.mark.asyncio
    async def test_get_udt_definition(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"name": "Motor", "members": []})
        mock_client._client.request.return_value = resp

        result = await mock_client.get_udt_definition("[default]_types_/Motor")
        assert result["name"] == "Motor"
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"] == {
            "action": "getUDTDefinition",
            "udtPath": "[default]_types_/Motor",
        }


# ------------------------------------------------------------------
# Alarm methods (WebDev-backed)
# ------------------------------------------------------------------


class TestAlarmMethods:
    def test_webdev_alarm_not_configured_by_default(self, mock_client):
        assert mock_client.webdev_alarm_configured is False

    def test_webdev_alarm_configured_when_set(self, mock_client, webdev_settings):
        assert mock_client.webdev_alarm_configured is True

    def test_webdev_alarm_url(self, mock_client, webdev_settings):
        url = mock_client._webdev_alarm_url()
        assert url == "/system/webdev/Global/GatewayAPI/alarms"

    @pytest.mark.asyncio
    async def test_get_active_alarms_no_filters(
        self, mock_client, mock_httpx_response, webdev_settings
    ):
        resp = mock_httpx_response(json_data=[])
        mock_client._client.request.return_value = resp

        await mock_client.get_active_alarms()
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"]["action"] == "getActive"
        assert "sourceFilter" not in call_kwargs["json"]

    @pytest.mark.asyncio
    async def test_get_active_alarms_with_filters(
        self, mock_client, mock_httpx_response, webdev_settings
    ):
        resp = mock_httpx_response(json_data=[])
        mock_client._client.request.return_value = resp

        await mock_client.get_active_alarms(source_filter="[default]Zone1", priority_filter="High")
        call_kwargs = mock_client._client.request.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["sourceFilter"] == "[default]Zone1"
        assert payload["priorityFilter"] == "High"

    @pytest.mark.asyncio
    async def test_get_alarm_history(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"entries": []})
        mock_client._client.request.return_value = resp

        await mock_client.get_alarm_history(
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            max_results=50,
        )
        call_kwargs = mock_client._client.request.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["action"] == "getHistory"
        assert payload["startTime"] == "2024-01-15T00:00:00Z"
        assert payload["maxResults"] == 50

    @pytest.mark.asyncio
    async def test_acknowledge_alarms(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"acknowledged": 2})
        mock_client._client.request.return_value = resp

        await mock_client.acknowledge_alarms(["id1", "id2"], ack_note="Resolved")
        call_kwargs = mock_client._client.request.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["action"] == "acknowledge"
        assert payload["eventIds"] == ["id1", "id2"]
        assert payload["ackNote"] == "Resolved"


# ------------------------------------------------------------------
# Tag History methods (WebDev-backed)
# ------------------------------------------------------------------


class TestTagHistoryMethods:
    def test_webdev_tag_history_not_configured_by_default(self, mock_client):
        assert mock_client.webdev_tag_history_configured is False

    def test_webdev_tag_history_configured_when_set(self, mock_client, webdev_settings):
        assert mock_client.webdev_tag_history_configured is True

    def test_webdev_tag_history_url(self, mock_client, webdev_settings):
        url = mock_client._webdev_tag_history_url()
        assert url == "/system/webdev/Global/GatewayAPI/tagHistory"

    @pytest.mark.asyncio
    async def test_get_tag_history(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"tags": []})
        mock_client._client.request.return_value = resp

        await mock_client.get_tag_history(
            tag_paths=["[default]T1"],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
            aggregation="Average",
            interval_ms=60000,
            max_results=500,
        )
        call_kwargs = mock_client._client.request.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["tagPaths"] == ["[default]T1"]
        assert payload["aggregation"] == "Average"
        assert payload["intervalMs"] == 60000
        assert payload["maxResults"] == 500

    @pytest.mark.asyncio
    async def test_get_tag_history_no_interval(
        self, mock_client, mock_httpx_response, webdev_settings
    ):
        resp = mock_httpx_response(json_data={"tags": []})
        mock_client._client.request.return_value = resp

        await mock_client.get_tag_history(
            tag_paths=["[default]T1"],
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T01:00:00Z",
        )
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert "intervalMs" not in call_kwargs["json"]


# ------------------------------------------------------------------
# Script Execution methods (WebDev-backed)
# ------------------------------------------------------------------


class TestScriptExecMethods:
    def test_webdev_script_exec_not_configured_by_default(self, mock_client):
        assert mock_client.webdev_script_exec_configured is False

    def test_webdev_script_exec_configured_when_set(self, mock_client, webdev_settings):
        assert mock_client.webdev_script_exec_configured is True

    def test_webdev_script_exec_url(self, mock_client, webdev_settings):
        url = mock_client._webdev_script_exec_url()
        assert url == "/system/webdev/Global/GatewayAPI/scriptExec"

    @pytest.mark.asyncio
    async def test_run_gateway_script(self, mock_client, mock_httpx_response, webdev_settings):
        resp = mock_httpx_response(json_data={"result": 42, "stdout": "", "error": None})
        mock_client._client.request.return_value = resp

        result = await mock_client.run_gateway_script("result = 42", timeout_secs=10)
        assert result["result"] == 42
        call_kwargs = mock_client._client.request.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["script"] == "result = 42"
        assert payload["timeoutSecs"] == 10
        assert payload["dryRun"] is False

    @pytest.mark.asyncio
    async def test_run_gateway_script_timeout_clamped(
        self, mock_client, mock_httpx_response, webdev_settings
    ):
        resp = mock_httpx_response(json_data={"result": None})
        mock_client._client.request.return_value = resp

        # timeout_secs > 60 is clamped to 60
        await mock_client.run_gateway_script("pass", timeout_secs=999)
        call_kwargs = mock_client._client.request.call_args.kwargs
        assert call_kwargs["json"]["timeoutSecs"] == 60


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_close(self, mock_client):
        await mock_client.close()
        mock_client._client.aclose.assert_awaited_once()
