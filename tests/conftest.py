import stat
import sys
from pathlib import Path

import pytest
from fastmcp import Client

from ignition_mcp.config import Settings

FAKE = Path(__file__).with_name("fake_ign.py")


@pytest.fixture
def ign_bin(tmp_path: Path) -> str:
    shim = tmp_path / "ign"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n')
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    return str(shim)


@pytest.fixture
def scenario(monkeypatch, tmp_path):
    def _set(name: str, version: str = "1.2.0"):
        monkeypatch.setenv("FAKE_IGN_SCENARIO", name)
        monkeypatch.setenv("FAKE_IGN_VERSION", version)
        monkeypatch.setenv("FAKE_IGN_CRASH_MARK", str(tmp_path / "crashed"))

    _set("healthy")
    return _set


@pytest.fixture
def settings(ign_bin, scenario) -> Settings:
    return Settings(ign_bin=ign_bin, profile="uat")


@pytest.fixture
async def backend(settings):
    from ignition_mcp.ign import IgnBackend

    b = IgnBackend(settings)
    await b.start()
    try:
        yield b
    finally:
        await b.stop()


@pytest.fixture
async def client(settings, backend):
    from ignition_mcp.server import build_server

    server = build_server(settings, backend)
    async with Client(server) as c:
        yield c


def envelope_of(result) -> dict:
    """Parse the single text block ign returns into its envelope dict."""
    import json

    return json.loads(result.content[0].text)
