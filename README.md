# ignition-mcp

A **Model Context Protocol (MCP)** server that gives AI assistants a curated,
developer-oriented interface to the **Ignition Gateway REST API**.

Built on [FastMCP](https://github.com/jlowin/fastmcp) with 37 hand-crafted tools
covering gateway management, projects, resources, tag providers, tags, alarms,
tag history, and script execution.

## Tools

| Category | Tools | Backend |
|----------|-------|---------|
| Gateway (6) | `get_gateway_info`, `get_module_health`, `get_gateway_logs`, `get_database_connections`, `get_opc_connections`, `get_system_metrics` | Native REST |
| Projects (8) | `list_projects`, `get_project`, `create_project`, `delete_project`, `copy_project`, `rename_project`, `export_project`, `import_project` | Native REST |
| Project Resources (4) | `list_project_resources`, `get_project_resource`, `set_project_resource`, `delete_project_resource` | Native REST |
| Designers (1) | `list_designers` | Native REST |
| Tag Providers (4) | `list_tag_providers`, `get_tag_provider`, `create_tag_provider`, `delete_tag_provider` | Native REST |
| Tag Browse (1) | `browse_tags` | Native REST |
| Tag Values (2) | `read_tags`, `write_tag` | WebDev |
| Tag Config (6) | `get_tag_config`, `create_tags`, `edit_tags`, `delete_tags`, `list_udt_types`, `get_udt_definition` | WebDev |
| Alarms (3) | `get_active_alarms`, `get_alarm_history`, `acknowledge_alarms` | WebDev |
| Historian (1) | `get_tag_history` | WebDev |
| Script Execution (1) | `run_gateway_script` (disabled by default) | WebDev |

## Requirements

- Python 3.10+
- Ignition Gateway 8.3+ with REST API enabled
- Gateway credentials (API key preferred) or basic auth

## Setup

```bash
# Install
uv sync

# Configure
cp .env.example .env
# Edit .env with your gateway URL and credentials
```

### Environment Variables

All environment variables are prefixed with `IGNITION_MCP_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `IGNITION_MCP_IGNITION_GATEWAY_URL` | `http://localhost:8088` | Gateway base URL |
| `IGNITION_MCP_IGNITION_API_KEY` | *(empty)* | API key auth (preferred over basic auth) |
| `IGNITION_MCP_IGNITION_USERNAME` | `admin` | Basic auth username |
| `IGNITION_MCP_IGNITION_PASSWORD` | `password` | Basic auth password |
| `IGNITION_MCP_SSL_VERIFY` | `true` | Set `false` for self-signed certs |
| `IGNITION_MCP_WEBDEV_TAG_ENDPOINT` | *(empty)* | WebDev path for `read_tags`/`write_tag` |
| `IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT` | *(empty)* | WebDev path for tag CRUD |
| `IGNITION_MCP_WEBDEV_ALARM_ENDPOINT` | *(empty)* | WebDev path for alarm tools |
| `IGNITION_MCP_WEBDEV_TAG_HISTORY_ENDPOINT` | *(empty)* | WebDev path for `get_tag_history` |
| `IGNITION_MCP_WEBDEV_SCRIPT_EXEC_ENDPOINT` | *(empty)* | WebDev path for `run_gateway_script` |
| `IGNITION_MCP_ENABLE_SCRIPT_EXECUTION` | `false` | Set `true` to enable `run_gateway_script` |
| `IGNITION_MCP_SERVER_HOST` | `127.0.0.1` | MCP server bind host |
| `IGNITION_MCP_SERVER_PORT` | `8007` | MCP server port |

## Running

```bash
# Streamable HTTP (default) — http://localhost:8007/mcp
uv run python mcp_server.py

# stdio transport (for Claude Desktop subprocess mode)
uv run python mcp_server.py --transport stdio
```

## Client Configuration

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "ignition-mcp": {
      "type": "streamable-http",
      "url": "http://localhost:8007/mcp"
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "ignition-mcp": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py", "--transport", "stdio"],
      "cwd": "/path/to/ignition-mcp",
      "env": {
        "IGNITION_MCP_IGNITION_GATEWAY_URL": "https://your-gateway:8043",
        "IGNITION_MCP_IGNITION_API_KEY": "your-api-key"
      }
    }
  }
}
```

## WebDev Prerequisite (tag values, alarms, history, script execution)

Several tools require **WebDev module scripts** deployed on the target Ignition gateway.
The native REST API (`/data/api/v1/`) only covers configuration — it does not support
runtime tag reads/writes, alarm queries, historian, or script execution.

Tools that require WebDev endpoints:
- **Tag values**: `read_tags`, `write_tag` → `IGNITION_MCP_WEBDEV_TAG_ENDPOINT`
- **Tag CRUD**: `get_tag_config`, `create_tags`, `edit_tags`, `delete_tags`, `list_udt_types`, `get_udt_definition` → `IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT`
- **Alarms**: `get_active_alarms`, `get_alarm_history`, `acknowledge_alarms` → `IGNITION_MCP_WEBDEV_ALARM_ENDPOINT`
- **Historian**: `get_tag_history` → `IGNITION_MCP_WEBDEV_TAG_HISTORY_ENDPOINT`
- **Script execution**: `run_gateway_script` → `IGNITION_MCP_WEBDEV_SCRIPT_EXEC_ENDPOINT` + `IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true`

If a WebDev endpoint is not configured, the relevant tools return a clear error with setup instructions.
See [docs/webdev-setup.md](docs/webdev-setup.md) for gateway-side deployment scripts.

## Testing

```bash
# Unit tests (no live gateway needed)
uv run pytest tests/ -v

# Integration tests (requires running Ignition gateway)
RUN_LIVE_GATEWAY_TESTS=1 uv run pytest tests/test_integration.py -v
```

## Architecture

```text
mcp_server.py                      # FastMCP entry point, lifespan, arg parsing
src/ignition_mcp/
    config.py                      # Pydantic Settings (IGNITION_MCP_ prefix)
    ignition_client.py             # Async HTTP client (httpx) for Gateway REST + WebDev
    tools/
        __init__.py                # register_all(mcp) — calls each module
        gateway.py                 # info, health, logs, connections, metrics
        projects.py                # project CRUD + export/import
        resources.py               # project resource CRUD (native REST)
        designers.py               # list_designers
        tag_providers.py           # tag provider CRUD
        tags.py                    # browse + read/write + CRUD via WebDev
        alarms.py                  # alarm query + ack (WebDev)
        historian.py               # tag history (WebDev)
        execution.py               # run_gateway_script (off by default)
tests/
    conftest.py                    # Shared fixtures
    test_client.py                 # IgnitionClient unit tests (mocked httpx)
    test_tools.py                  # Tool logic unit tests (mocked client)
    test_integration.py            # Live gateway tests (skipped by default)
docs/
    webdev-setup.md                # WebDev script deployment guide
    api-reference.md               # Full tool reference
```

## License

MIT
