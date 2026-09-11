# Install ignition-mcp

Use Python 3.10+, uv, and an Ignition 8.3+ development gateway.

```sh
git clone https://github.com/WhiskeyHouse/ignition-mcp.git
cd ignition-mcp
uv sync --locked
cp .env.example .env
```

Set the gateway URL and API token in `.env`:

```dotenv
IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:8088
IGNITION_MCP_IGNITION_API_KEY=name:replace-with-your-token
```

Use the full token issued by the gateway. Keep `.env` local. The client sends the value as `X-Ignition-API-Token`.

Check the server entry point:

```sh
uv run python mcp_server.py --help
```

Continue with [connecting an MCP client](quickstart.md). No gateway access is needed to display command help.
