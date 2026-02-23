"""Shared test fixtures for ignition-mcp."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_httpx_response():
    """Factory for creating mock httpx.Response objects."""

    def _make(
        status_code: int = 200,
        json_data: dict | list | None = None,
        text: str = "",
        content: bytes = b"",
        headers: dict | None = None,
    ):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        resp.content = content
        resp.headers = headers or {}
        if json_data is not None:
            resp.json.return_value = json_data
            resp.headers.setdefault("content-type", "application/json")
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            from httpx import HTTPStatusError, Request, Response

            real_resp = Response(status_code)
            resp.raise_for_status.side_effect = HTTPStatusError(
                f"{status_code}", request=Request("GET", "http://test"), response=real_resp
            )
        return resp

    return _make


@pytest.fixture
def mock_client(mock_httpx_response):
    """Create an IgnitionClient with a mocked httpx.AsyncClient."""
    from ignition_mcp.ignition_client import IgnitionClient

    client = IgnitionClient(
        gateway_url="http://test-gateway:8088",
        api_key="test-api-key",
        ssl_verify=False,
    )
    # Replace the real httpx client with an AsyncMock
    client._client = AsyncMock()
    return client


@pytest.fixture
def webdev_settings(monkeypatch):
    """Patch settings to enable all WebDev endpoints with their conventional paths."""
    from ignition_mcp import config

    monkeypatch.setattr(config.settings, "webdev_tag_endpoint", "Global/GatewayAPI/tags")
    monkeypatch.setattr(
        config.settings, "webdev_tag_config_endpoint", "Global/GatewayAPI/tagConfig"
    )
    monkeypatch.setattr(config.settings, "webdev_alarm_endpoint", "Global/GatewayAPI/alarms")
    monkeypatch.setattr(
        config.settings, "webdev_tag_history_endpoint", "Global/GatewayAPI/tagHistory"
    )
    monkeypatch.setattr(
        config.settings, "webdev_script_exec_endpoint", "Global/GatewayAPI/scriptExec"
    )
