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

    async def get_gateway_status(self) -> Dict[str, Any]:
        """Get gateway status information."""
        return await self._request("GET", "/system/gateway-network/remote-servers/status")

    async def get_openapi_spec(self) -> Dict[str, Any]:
        """Get OpenAPI specification."""
        return await self._request("GET", "/openapi.json")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
