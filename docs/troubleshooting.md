# Troubleshooting

## The client cannot connect

Confirm the server process is running and the client uses `http://127.0.0.1:8007/mcp`, unless you changed its host or port. For stdio, use an absolute checkout path as shown in the [quickstart](quickstart.md).

## Gateway authentication fails

Check the configured gateway URL and use the full gateway API token in `name:key` form. The client prefers an API token and falls back to basic authentication only when no token is configured. That fallback in the client does not establish that a gateway endpoint accepts basic authentication.

Check the gateway's token permissions and HTTPS requirements. Share redacted errors when reporting a problem; do not dump the settings object because it contains credentials.

## A runtime tool asks for WebDev setup

Configure the matching endpoint from the [WebDev guide](webdev-setup.md). Native REST access alone does not provide all runtime operations. Script execution also needs its explicit enable flag.

## Old instructions mention port 8000 or generated tool names

Use `mcp_server.py`, port 8007, and the named tools in the [current reference](api-reference.md). Older installation examples described a different server interface.

Include the checkout commit, Python version, transport, tool name, and redacted error in an [issue](https://github.com/WhiskeyHouse/ignition-mcp/issues).
