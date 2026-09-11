# Contributing

Clone your fork of [WhiskeyHouse/ignition-mcp](https://github.com/WhiskeyHouse/ignition-mcp), then install the locked development environment:

```sh
uv sync --locked
uv run pytest tests/ -v
uv run ruff check .
```

The server entry point is `mcp_server.py`. Tools live under `src/ignition_mcp/tools/`, share `IgnitionClient`, and register through `register_all`. Keep a tool's docstring and tests aligned with the behavior a client sees.

Unit tests do not need a live gateway. Gateway integration tests are opt-in:

```sh
RUN_LIVE_GATEWAY_TESTS=1 uv run pytest tests/test_integration.py -v
```

Use a configured development gateway for that command. Include the gateway version and the checks you ran in your pull request.

## Documentation

Edit user guides under `docs/`. Configuration and tool references are regenerated from source by `python3 website/sync-reference.py`. Update the source descriptions rather than editing generated reference text.

From `website/`, run `npm ci`, `npm run typecheck`, and `npm run build`. The build checks internal links. Use `npm start` for a local preview.
