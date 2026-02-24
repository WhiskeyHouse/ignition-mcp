"""Ignition Gateway REST API client.

Owns an httpx.AsyncClient for the lifetime of the MCP server.
Constructed once in the FastMCP lifespan and shared across all tool calls.
"""

import base64
from typing import Any, Dict, List, Optional, cast
from urllib.parse import quote

import httpx

from .config import settings


class IgnitionClient:
    """Async HTTP client for the Ignition Gateway REST API and WebDev endpoints."""

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        ssl_verify: Optional[bool] = None,
    ):
        self.gateway_url = (gateway_url or settings.ignition_gateway_url).rstrip("/")
        self.username = username or settings.ignition_username
        self.password = password or settings.ignition_password
        self.api_key = api_key or settings.ignition_api_key
        self._verify = ssl_verify if ssl_verify is not None else settings.ssl_verify

        self._client = httpx.AsyncClient(
            base_url=self.gateway_url, timeout=30.0, verify=self._verify
        )

    async def __aenter__(self) -> "IgnitionClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _auth_headers(self) -> Dict[str, str]:
        """Build auth headers — prefer API key over basic auth."""
        if self.api_key:
            return {"X-Ignition-API-Token": self.api_key}
        creds = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return {"Authorization": f"Basic {creds}"}

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        raw_response: bool = False,
        timeout: Optional[float] = None,
    ) -> Any:
        """Make an authenticated request to the Ignition Gateway.

        Args:
            raw_response: If True, return the httpx.Response object instead
                          of parsing JSON. Used for binary endpoints (export).
        """
        merged_headers = self._auth_headers()
        merged_headers["Accept"] = "application/json"
        if json is not None:
            merged_headers["Content-Type"] = "application/json"
        if headers:
            merged_headers.update(headers)

        resp = await self._client.request(
            method=method,
            url=path,
            headers=merged_headers,
            json=json,
            params=params,
            timeout=timeout,
        )
        resp.raise_for_status()

        if raw_response:
            return resp

        ct = resp.headers.get("content-type", "")
        if "application/json" in ct:
            return resp.json()
        return {"status": "success", "content": resp.text}

    # ------------------------------------------------------------------
    # Gateway
    # ------------------------------------------------------------------

    async def get_gateway_info(self) -> Dict[str, Any]:
        """GET /data/api/v1/gateway-info — version, edition, state, uptime."""
        return cast(Dict[str, Any], await self._request("GET", "/data/api/v1/gateway-info"))

    async def get_module_health(self) -> Any:
        """GET /data/api/v1/modules/healthy — all modules and health status."""
        return await self._request("GET", "/data/api/v1/modules/healthy")

    async def get_logs(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET /data/api/v1/logs — gateway log entries."""
        return await self._request("GET", "/data/api/v1/logs", params=params)

    async def get_database_connections(self) -> Any:
        """GET /data/api/v1/connections/database — database connection status."""
        return await self._request("GET", "/data/api/v1/connections/database")

    async def get_opc_connections(self) -> Any:
        """GET /data/api/v1/connections/opc — OPC-UA/COM connection status."""
        return await self._request("GET", "/data/api/v1/connections/opc")

    async def get_system_metrics(self) -> Any:
        """GET /data/api/v1/system/metrics — CPU, memory, threads, sessions."""
        return await self._request("GET", "/data/api/v1/system/metrics")

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    async def list_projects(self) -> Any:
        """GET /data/api/v1/projects/list — all projects with metadata."""
        return await self._request("GET", "/data/api/v1/projects/list")

    async def get_project(self, name: str) -> Any:
        """GET /data/api/v1/projects/find/{name} — full project details."""
        return await self._request("GET", f"/data/api/v1/projects/find/{quote(name, safe='')}")

    async def create_project(self, body: Dict[str, Any]) -> Any:
        """POST /data/api/v1/projects — create a new project."""
        return await self._request("POST", "/data/api/v1/projects", json=body)

    async def delete_project(self, name: str, confirm: bool = True) -> Any:
        """DELETE /data/api/v1/projects/{name} — permanently delete a project."""
        return await self._request(
            "DELETE", f"/data/api/v1/projects/{quote(name, safe='')}", params={"confirm": confirm}
        )

    async def copy_project(self, from_name: str, to_name: str) -> Any:
        """POST /data/api/v1/projects/copy — clone an existing project."""
        return await self._request(
            "POST",
            "/data/api/v1/projects/copy",
            json={"fromName": from_name, "toName": to_name},
        )

    async def rename_project(self, name: str, new_name: str) -> Any:
        """POST /data/api/v1/projects/rename/{name}."""
        return await self._request(
            "POST",
            f"/data/api/v1/projects/rename/{quote(name, safe='')}",
            json={"name": new_name},
        )

    async def export_project(self, name: str) -> httpx.Response:
        """GET /data/api/v1/projects/export/{name} — returns raw response (ZIP bytes)."""
        return cast(
            httpx.Response,
            await self._request(
                "GET", f"/data/api/v1/projects/export/{quote(name, safe='')}", raw_response=True
            ),
        )

    async def import_project(self, name: str, zip_bytes: bytes, overwrite: bool = False) -> Any:
        """POST /data/api/v1/projects/import/{name} — upload ZIP archive."""
        headers = self._auth_headers()
        headers["Content-Type"] = "application/zip"
        resp = await self._client.request(
            method="POST",
            url=f"/data/api/v1/projects/import/{quote(name, safe='')}",
            headers=headers,
            content=zip_bytes,
            params={"overwrite": str(overwrite).lower()},
        )
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "application/json" in ct:
            return resp.json()
        return {"status": "success"}

    # ------------------------------------------------------------------
    # Project Resources (native REST, no WebDev needed)
    # Endpoint: /data/api/v1/projects/{project}/resources/{resourcePath}
    # ------------------------------------------------------------------

    async def list_project_resources(self, project: str, path_prefix: Optional[str] = None) -> Any:
        """GET /data/api/v1/projects/{project}/resources — list all project resources.

        Args:
            path_prefix: Optional filter, e.g. 'com.inductiveautomation.perspective/views'
        """
        params: Dict[str, Any] = {}
        if path_prefix:
            params["path"] = path_prefix
        return await self._request(
            "GET", f"/data/api/v1/projects/{quote(project, safe='')}/resources", params=params
        )

    def _resource_url(self, project: str, resource_path: str) -> str:
        p = quote(project, safe="")
        r = quote(resource_path, safe="/")
        return f"/data/api/v1/projects/{p}/resources/{r}"

    async def get_project_resource(self, project: str, resource_path: str) -> Any:
        """GET /data/api/v1/projects/{project}/resources/{resourcePath} — fetch resource content."""
        return await self._request("GET", self._resource_url(project, resource_path))

    async def set_project_resource(self, project: str, resource_path: str, content: Any) -> Any:
        """PUT /data/api/v1/projects/{project}/resources/{resourcePath} — create or overwrite."""
        return await self._request("PUT", self._resource_url(project, resource_path), json=content)

    async def delete_project_resource(self, project: str, resource_path: str) -> Any:
        """DELETE /data/api/v1/projects/{project}/resources/{resourcePath}."""
        return await self._request("DELETE", self._resource_url(project, resource_path))

    # ------------------------------------------------------------------
    # Designers
    # ------------------------------------------------------------------

    async def list_designers(self) -> Any:
        """GET /data/api/v1/designers — active Designer sessions."""
        return await self._request("GET", "/data/api/v1/designers")

    # ------------------------------------------------------------------
    # Tag Providers (configuration resources)
    # ------------------------------------------------------------------

    async def list_tag_providers(self) -> Any:
        """GET /data/api/v1/resources/list/ignition/tag-provider."""
        return await self._request("GET", "/data/api/v1/resources/list/ignition/tag-provider")

    async def get_tag_provider(self, name: str) -> Any:
        """GET /data/api/v1/resources/find/ignition/tag-provider/{name}."""
        return await self._request(
            "GET", f"/data/api/v1/resources/find/ignition/tag-provider/{quote(name, safe='')}"
        )

    async def create_tag_provider(self, body: Any) -> Any:
        """POST /data/api/v1/resources/ignition/tag-provider — create provider."""
        return await self._request(
            "POST", "/data/api/v1/resources/ignition/tag-provider", json=body
        )

    async def delete_tag_provider(self, name: str, confirm: bool = True) -> Any:
        """POST /data/api/v1/resources/delete/ignition/tag-provider."""
        return await self._request(
            "POST",
            "/data/api/v1/resources/delete/ignition/tag-provider",
            json={"name": name, "confirm": confirm},
        )

    # ------------------------------------------------------------------
    # Tag Browse (structure only, not values)
    # ------------------------------------------------------------------

    async def browse_tags(self, path: str = "", depth: int = 2) -> Any:
        """GET /data/api/v1/entity/browse — tag tree structure."""
        params: Dict[str, Any] = {}
        if path:
            params["path"] = path
        if depth:
            params["depth"] = min(depth, 4)  # enforce cap
        return await self._request("GET", "/data/api/v1/entity/browse", params=params)

    # ------------------------------------------------------------------
    # Tag Read/Write (WebDev-backed)
    # ------------------------------------------------------------------

    def _webdev_url(self, endpoint: Optional[str] = None) -> str:
        """Build WebDev URL from configured or override endpoint."""
        ep = (endpoint or settings.webdev_tag_endpoint).lstrip("/")
        if not ep:
            raise ValueError(
                "WebDev tag endpoint not configured. "
                "Set IGNITION_MCP_WEBDEV_TAG_ENDPOINT or provide an endpoint."
            )
        return f"/system/webdev/{ep}"

    @property
    def webdev_configured(self) -> bool:
        """Check if WebDev tag read/write endpoint is configured."""
        return bool(settings.webdev_tag_endpoint)

    @property
    def webdev_tag_config_configured(self) -> bool:
        """Check if WebDev tag config endpoint is configured."""
        return bool(settings.webdev_tag_config_endpoint)

    @property
    def webdev_alarm_configured(self) -> bool:
        """Check if WebDev alarm endpoint is configured."""
        return bool(settings.webdev_alarm_endpoint)

    @property
    def webdev_tag_history_configured(self) -> bool:
        """Check if WebDev tag history endpoint is configured."""
        return bool(settings.webdev_tag_history_endpoint)

    @property
    def webdev_script_exec_configured(self) -> bool:
        """Check if WebDev script execution endpoint is configured."""
        return bool(settings.webdev_script_exec_endpoint)

    async def read_tags(self, tag_paths: List[str]) -> Any:
        """POST to WebDev endpoint — read runtime tag values."""
        url = self._webdev_url()
        return await self._request("POST", url, json={"paths": tag_paths})

    async def write_tag(
        self,
        tag_path: str,
        value: Any,
        data_type: Optional[str] = None,
    ) -> Any:
        """POST to WebDev endpoint — write a single tag value."""
        url = self._webdev_url()
        payload: Dict[str, Any] = {"tagPath": tag_path, "value": value}
        if data_type:
            payload["dataType"] = data_type
        return await self._request("POST", url, json=payload)

    # ------------------------------------------------------------------
    # Tag Config CRUD (WebDev-backed, wraps system.tag.configure)
    # Endpoint: webdev_tag_config_endpoint (default: Global/GatewayAPI/tagConfig)
    # ------------------------------------------------------------------

    def _webdev_tag_config_url(self) -> str:
        """Build WebDev tag config URL."""
        ep = settings.webdev_tag_config_endpoint.lstrip("/")
        return f"/system/webdev/{ep}"

    async def get_tag_config(self, tag_path: str) -> Any:
        """POST to WebDev tagConfig endpoint — get configuration for a tag."""
        url = self._webdev_tag_config_url()
        return await self._request("POST", url, json={"action": "getConfig", "tagPath": tag_path})

    async def configure_tags(
        self,
        tags: List[Dict[str, Any]],
        edit_mode: str = "m",
        provider: Optional[str] = None,
    ) -> Any:
        """POST to WebDev tagConfig endpoint — create or modify tags via system.tag.configure.

        Args:
            tags: List of tag configuration objects.
            edit_mode: 'a' (add only), 'm' (merge/upsert), 'd' (delete).
            provider: Optional tag provider name. Defaults to 'default' on gateway.
        """
        url = self._webdev_tag_config_url()
        payload: Dict[str, Any] = {"action": "configure", "tags": tags, "editMode": edit_mode}
        if provider:
            payload["provider"] = provider
        return await self._request("POST", url, json=payload)

    async def delete_tags(self, tag_paths: List[str]) -> Any:
        """POST to WebDev tagConfig endpoint — delete tags by path list."""
        url = self._webdev_tag_config_url()
        return await self._request(
            "POST", url, json={"action": "deleteTags", "tagPaths": tag_paths}
        )

    async def list_udt_types(self, provider: str = "default") -> Any:
        """POST to WebDev tagConfig endpoint — list UDT type definitions."""
        url = self._webdev_tag_config_url()
        return await self._request(
            "POST", url, json={"action": "listUDTTypes", "provider": provider}
        )

    async def get_udt_definition(self, udt_path: str) -> Any:
        """POST to WebDev tagConfig endpoint — get full UDT type schema."""
        url = self._webdev_tag_config_url()
        return await self._request(
            "POST", url, json={"action": "getUDTDefinition", "udtPath": udt_path}
        )

    # ------------------------------------------------------------------
    # Alarms (WebDev-backed, wraps system.alarm.* functions)
    # Endpoint: webdev_alarm_endpoint (default: Global/GatewayAPI/alarms)
    # ------------------------------------------------------------------

    def _webdev_alarm_url(self) -> str:
        """Build WebDev alarm URL."""
        ep = settings.webdev_alarm_endpoint.lstrip("/")
        return f"/system/webdev/{ep}"

    async def get_active_alarms(
        self,
        source_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        state_filter: Optional[str] = None,
    ) -> Any:
        """POST to WebDev alarm endpoint — query active alarm status."""
        url = self._webdev_alarm_url()
        payload: Dict[str, Any] = {"action": "getActive"}
        if source_filter:
            payload["sourceFilter"] = source_filter
        if priority_filter:
            payload["priorityFilter"] = priority_filter
        if state_filter:
            payload["stateFilter"] = state_filter
        return await self._request("POST", url, json=payload)

    async def get_alarm_history(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        source_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        max_results: int = 100,
    ) -> Any:
        """POST to WebDev alarm endpoint — query alarm journal/history."""
        url = self._webdev_alarm_url()
        payload: Dict[str, Any] = {"action": "getHistory", "maxResults": max_results}
        if start_time:
            payload["startTime"] = start_time
        if end_time:
            payload["endTime"] = end_time
        if source_filter:
            payload["sourceFilter"] = source_filter
        if priority_filter:
            payload["priorityFilter"] = priority_filter
        return await self._request("POST", url, json=payload)

    async def acknowledge_alarms(self, event_ids: List[str], ack_note: Optional[str] = None) -> Any:
        """POST to WebDev alarm endpoint — acknowledge alarms by event ID."""
        url = self._webdev_alarm_url()
        payload: Dict[str, Any] = {"action": "acknowledge", "eventIds": event_ids}
        if ack_note:
            payload["ackNote"] = ack_note
        return await self._request("POST", url, json=payload)

    # ------------------------------------------------------------------
    # Tag History (WebDev-backed, wraps system.tag.queryTagHistory)
    # Endpoint: webdev_tag_history_endpoint (default: Global/GatewayAPI/tagHistory)
    # ------------------------------------------------------------------

    def _webdev_tag_history_url(self) -> str:
        """Build WebDev tag history URL."""
        ep = settings.webdev_tag_history_endpoint.lstrip("/")
        return f"/system/webdev/{ep}"

    async def get_tag_history(
        self,
        tag_paths: List[str],
        start_time: str,
        end_time: str,
        aggregation: str = "LastValue",
        interval_ms: Optional[int] = None,
        max_results: int = 1000,
    ) -> Any:
        """POST to WebDev tagHistory endpoint — query historical tag values."""
        url = self._webdev_tag_history_url()
        payload: Dict[str, Any] = {
            "tagPaths": tag_paths,
            "startTime": start_time,
            "endTime": end_time,
            "aggregation": aggregation,
            "maxResults": max_results,
        }
        if interval_ms is not None:
            payload["intervalMs"] = interval_ms
        return await self._request("POST", url, json=payload)

    # ------------------------------------------------------------------
    # Script Execution (WebDev-backed)
    # Endpoint: webdev_script_exec_endpoint (default: Global/GatewayAPI/scriptExec)
    # NOTE: Only usable when settings.enable_script_execution is True.
    # ------------------------------------------------------------------

    def _webdev_script_exec_url(self) -> str:
        """Build WebDev script execution URL."""
        ep = settings.webdev_script_exec_endpoint.lstrip("/")
        return f"/system/webdev/{ep}"

    async def run_gateway_script(
        self,
        script: str,
        timeout_secs: int = 10,
        dry_run: bool = False,
    ) -> Any:
        """POST to WebDev scriptExec endpoint — execute Python on the gateway."""
        url = self._webdev_script_exec_url()
        gateway_timeout = min(timeout_secs, 60)
        payload: Dict[str, Any] = {
            "script": script,
            "timeoutSecs": gateway_timeout,
            "dryRun": dry_run,
        }
        # Use a client timeout slightly longer than the gateway's own timeout so the
        # gateway can return a clean timeout error rather than the connection being cut.
        http_timeout = gateway_timeout + 5.0
        return await self._request("POST", url, json=payload, timeout=http_timeout)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()
