# Configuration

Settings load from environment variables and the checkout’s `.env` file. The variables below match `src/ignition_mcp/config.py`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `IGNITION_MCP_IGNITION_GATEWAY_URL` | `http://localhost:8088` | Base URL for the Ignition Gateway (e.g. https://gateway:8043) |
| `IGNITION_MCP_IGNITION_USERNAME` | `admin` | Username for basic auth (used when api_key is empty) |
| `IGNITION_MCP_IGNITION_PASSWORD` | `password` | Password for basic auth |
| `IGNITION_MCP_IGNITION_API_KEY` | `` | API key for Ignition Gateway REST API auth (preferred over basic auth) |
| `IGNITION_MCP_WEBDEV_TAG_ENDPOINT` | `` | WebDev resource path for tag read/write (e.g. Global/GatewayAPI/tags). Leave empty to disable — tools will return a setup-guidance error. |
| `IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT` | `` | WebDev resource path for tag CRUD (e.g. Global/GatewayAPI/tagConfig). Leave empty to disable — tools will return a setup-guidance error. |
| `IGNITION_MCP_WEBDEV_ALARM_ENDPOINT` | `` | WebDev resource path for alarm queries (e.g. Global/GatewayAPI/alarms). Leave empty to disable — tools will return a setup-guidance error. |
| `IGNITION_MCP_WEBDEV_TAG_HISTORY_ENDPOINT` | `` | WebDev resource path for tag history (e.g. Global/GatewayAPI/tagHistory). Leave empty to disable — tools will return a setup-guidance error. |
| `IGNITION_MCP_WEBDEV_SCRIPT_EXEC_ENDPOINT` | `` | WebDev resource path for script execution (e.g. Global/GatewayAPI/scriptExec). Leave empty to disable — tools will return a setup-guidance error. |
| `IGNITION_MCP_ENABLE_SCRIPT_EXECUTION` | `False` | Enable the run_gateway_script tool. OFF by default for safety. Set IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true to enable. |
| `IGNITION_MCP_SSL_VERIFY` | `True` | Verify TLS certificates. For a private CA, configure SSL_CERT_FILE or SSL_CERT_DIR with the trusted CA certificates. Use false only for isolated local development. |
| `IGNITION_MCP_SERVER_HOST` | `127.0.0.1` | Host to bind the MCP server to |
| `IGNITION_MCP_SERVER_PORT` | `8007` | Port to bind the MCP server to |

Use an API token for native gateway REST access. Leave optional WebDev paths empty until their gateway resources are deployed. Keep TLS verification enabled for normal use.

See [installation](installation.md) and [WebDev setup](webdev-setup.md).
