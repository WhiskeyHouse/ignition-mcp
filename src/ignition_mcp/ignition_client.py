"""Ignition Gateway REST API client."""

import base64
from typing import Any, Dict, Optional

import httpx

from .config import settings


class IgnitionClient:
    """Client for interacting with Ignition Gateway REST API."""

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.gateway_url = gateway_url or settings.ignition_gateway_url
        self.username = username or settings.ignition_username
        self.password = password or settings.ignition_password
        self.api_key = api_key or settings.ignition_api_key

        self.gateway_url = self.gateway_url.rstrip("/")

        self._client = httpx.AsyncClient(base_url=self.gateway_url, timeout=30.0)

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get fresh authentication headers for each request."""
        return self._create_auth_headers()

    def _create_auth_headers(self) -> Dict[str, str]:
        """Create auth headers - prefer API key if available."""
        if self.api_key:
            return {"X-Ignition-API-Token": self.api_key}
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded_credentials}"}

    async def __aenter__(self) -> "IgnitionClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Make authenticated request to Ignition Gateway API."""
        headers = kwargs.pop("headers", {})

        # Get fresh auth headers for each request
        auth_headers = self._get_auth_headers()
        headers.update(auth_headers)
        headers["Content-Type"] = "application/json"

        response = await self._client.request(
            method=method, url=endpoint, headers=headers, **kwargs
        )
        response.raise_for_status()

        if response.headers.get("content-type", "").startswith("application/json"):
            result: Dict[str, Any] = response.json()
            return result
        return {"status": "success", "content": response.text}

    def _build_webdev_path(self, resource_path: Optional[str] = None) -> str:
        """Construct the fully qualified WebDev path."""
        resource = (resource_path or settings.webdev_tag_endpoint).lstrip("/")
        if not resource:
            raise ValueError(
                "WebDev tag endpoint not configured. Set IGNITION_MCP_WEBDEV_TAG_ENDPOINT or"
                " provide resourcePath."
            )
        return f"/system/webdev/{resource}"

    async def call_webdev(
        self,
        resource_path: Optional[str] = None,
        method: str = "POST",
        *,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Call a WebDev endpoint on the Ignition Gateway."""
        path = self._build_webdev_path(resource_path)
        request_headers: Dict[str, str] = headers.copy() if headers else {}
        return await self._request(method.upper(), path, json=json, params=params, headers=request_headers)

    async def create_or_update_tag(
        self,
        tag_path: Optional[str],
        value: Any = None,
        *,
        data_type: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        resource_path: Optional[str] = None,
        method: Optional[str] = None,
        payload_override: Optional[Any] = None,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        value_timestamp: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a tag via the configured WebDev endpoint."""

        if payload_override is not None:
            payload = payload_override
        else:
            if not tag_path:
                raise ValueError("tag_path is required when payloadOverride is not provided")
            payload = {"path": tag_path, "value": value}
            if data_type:
                payload["dataType"] = data_type
            if attributes:
                payload["attributes"] = attributes
            if value_timestamp:
                payload["valueTimestamp"] = value_timestamp
            if quality:
                payload["quality"] = quality

        http_method = (method or settings.webdev_tag_method or "POST").upper()
        return await self.call_webdev(
            resource_path=resource_path,
            method=http_method,
            json=payload,
            params=query_params,
            headers=headers,
        )

    async def get_gateway_status(self) -> Dict[str, Any]:
        """Get gateway status information."""
        return await self._request("GET", "/system/gateway-network/remote-servers/status")

    async def get_openapi_spec(self) -> Dict[str, Any]:
        """Get OpenAPI specification."""
        try:
            return await self._request("GET", "/openapi.json")
        except Exception as e:
            # If OpenAPI spec is not accessible (403 Forbidden), return empty spec
            # This allows the client to continue working with direct endpoint calls
            print(f"Warning: OpenAPI spec not accessible: {e}")
            return {"openapi": "3.0.0", "info": {"title": "Ignition Gateway API", "version": "1.0.0"}, "paths": {}}

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
