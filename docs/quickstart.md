# Connect a client

From the configured repository checkout, start the HTTP server:

```sh
uv run python mcp_server.py
```

The default MCP endpoint is `http://127.0.0.1:8007/mcp`. Configure your MCP client's HTTP connection to use that address.

For a client that launches a stdio subprocess, use `uv` as the executable with these arguments:

```json
["--directory", "/absolute/path/to/ignition-mcp", "run", "python", "mcp_server.py", "--transport", "stdio"]
```

Replace the absolute path with your checkout. The `--directory` option ensures the server loads the intended `.env` file.

Start with `get_gateway_info` or `get_module_health` and inspect the returned data. These requests read gateway information. The server also exposes tools that modify projects and tags; review the [tool reference](api-reference.md) when choosing operations.

## Optional runtime data

Tag values, alarms, history, and script execution need gateway-side WebDev resources. Leave those endpoints unconfigured until you need them. See [WebDev setup](webdev-setup.md). Gateway script execution additionally requires `IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true` and is disabled by default.
