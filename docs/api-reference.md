# API Reference

Complete reference for all 37 tools provided by Ignition MCP Server.

## Tool Summary

| Category | Tool | Transport | Description |
|----------|------|-----------|-------------|
| **Gateway** | `get_gateway_info` | Native REST | Version, edition, state, uptime |
| | `get_module_health` | Native REST | All modules and health status |
| | `get_gateway_logs` | Native REST | Recent gateway log entries |
| | `get_database_connections` | Native REST | Database connection status |
| | `get_opc_connections` | Native REST | OPC-UA/COM connection state |
| | `get_system_metrics` | Native REST | CPU, memory, threads, sessions |
| **Projects** | `list_projects` | Native REST | All projects with metadata |
| | `get_project` | Native REST | Single project details |
| | `create_project` | Native REST | Create new project |
| | `delete_project` | Native REST | Delete project (irreversible) |
| | `copy_project` | Native REST | Clone project |
| | `rename_project` | Native REST | Rename project |
| | `export_project` | Native REST | Export as base64 ZIP |
| | `import_project` | Native REST | Import from base64 ZIP |
| **Resources** | `list_project_resources` | Native REST | List views, scripts, etc. |
| | `get_project_resource` | Native REST | Fetch resource content |
| | `set_project_resource` | Native REST | Create or overwrite resource |
| | `delete_project_resource` | Native REST | Delete resource |
| **Designers** | `list_designers` | Native REST | Active Designer sessions |
| **Tag Providers** | `list_tag_providers` | Native REST | All configured providers |
| | `get_tag_provider` | Native REST | Provider configuration |
| | `create_tag_provider` | Native REST | Create provider |
| | `delete_tag_provider` | Native REST | Delete provider + all tags |
| **Tags** | `browse_tags` | Native REST | Tag tree structure (not values) |
| | `read_tags` | WebDev | Runtime tag values |
| | `write_tag` | WebDev | Write tag value |
| | `get_tag_config` | WebDev | Tag configuration object |
| | `create_tags` | WebDev | Create tags from config |
| | `edit_tags` | WebDev | Merge-update tag config |
| | `delete_tags` | WebDev | Delete tags by path |
| | `list_udt_types` | WebDev | List UDT type definitions |
| | `get_udt_definition` | WebDev | Full UDT schema |
| **Alarms** | `get_active_alarms` | WebDev | Current active alarms |
| | `get_alarm_history` | WebDev | Alarm journal entries |
| | `acknowledge_alarms` | WebDev | Acknowledge by event ID |
| **Historian** | `get_tag_history` | WebDev | Historical tag values |
| **Execution** | `run_gateway_script` | WebDev | Execute Python on gateway (disabled by default) |

**Native REST** = uses Ignition's built-in REST API, no WebDev setup needed.
**WebDev** = requires a gateway-side WebDev script. See [webdev-setup.md](webdev-setup.md).

---

## Gateway Tools

### `get_gateway_info`
Get Ignition Gateway version, edition, state, and uptime. No parameters required.

**Returns:** `{version, edition, state, uptime, ...}`

### `get_module_health`
List all installed Ignition modules and their health status.

**Returns:** `[{name, version, state, error?}, ...]`

### `get_gateway_logs`
Fetch recent gateway log entries.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | string | `"INFO"` | Min log level: TRACE, DEBUG, INFO, WARN, ERROR |
| `logger_name` | string | `null` | Filter by logger name |
| `limit` | int | `100` | Max entries (1-1000) |

**Returns:** `[{timestamp, level, logger, message}, ...]`

### `get_database_connections`
List all database connections and their current status. No parameters.

**Returns:** `[{name, driver, state, error?}, ...]`

### `get_opc_connections`
List all OPC-UA/COM connections and their state. No parameters.

**Returns:** `[{name, type, connected, state}, ...]`

### `get_system_metrics`
Get gateway system metrics: CPU, memory, threads, active sessions. No parameters.

**Returns:** `{cpu, memory, threads, sessions, ...}`

---

## Project Tools

### `list_projects`
List all Ignition projects. No parameters.

**Returns:** `[{name, title, description, enabled, parent}, ...]`

### `get_project`
Get full details of a specific project.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Exact project name |

### `create_project`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Unique project name |
| `title` | string | no | Display title |
| `description` | string | no | Description |
| `parent` | string | no | Parent project for inheritance |
| `enabled` | bool | no | Default: `true` |

### `delete_project`
**Irreversible.** Consider `export_project` first.

| Parameter | Type | Required |
|-----------|------|----------|
| `name` | string | yes |

### `copy_project`

| Parameter | Type | Required |
|-----------|------|----------|
| `source_name` | string | yes |
| `new_name` | string | yes |

### `rename_project`

| Parameter | Type | Required |
|-----------|------|----------|
| `current_name` | string | yes |
| `new_name` | string | yes |

### `export_project`
Export project as a base64-encoded ZIP archive.

| Parameter | Type | Required |
|-----------|------|----------|
| `name` | string | yes |

**Returns:** `{filename, content_base64, size_bytes}`

### `import_project`
Import from a base64-encoded ZIP archive.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Target project name |
| `zip_base64` | string | yes | Base64 ZIP content from `export_project` |
| `overwrite` | bool | no | Overwrite existing project. Default: `false` |

---

## Project Resource Tools

Project resources are files within a project: Perspective views, scripts, named
queries, Vision windows, etc.

Resource path format: `{module-id}/{resource-type}/{name}/{filename}`

Common prefixes:
- `com.inductiveautomation.perspective/views/` — Perspective views
- `com.inductiveautomation.ignition/script-python/` — Project scripts
- `com.inductiveautomation.ignition/named-query/` — Named queries

### `list_project_resources`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project` | string | yes | Project name |
| `path_prefix` | string | no | Filter prefix, e.g. `com.inductiveautomation.perspective/views` |

### `get_project_resource`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project` | string | yes | Project name |
| `resource_path` | string | yes | Full resource path |

### `set_project_resource`
Create or overwrite a resource. **Overwrites without confirmation.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project` | string | yes | Project name |
| `resource_path` | string | yes | Full resource path |
| `content` | any | yes | Resource content (dict for JSON, string for scripts) |

### `delete_project_resource`
**Irreversible.**

| Parameter | Type | Required |
|-----------|------|----------|
| `project` | string | yes |
| `resource_path` | string | yes |

---

## Designer Tools

### `list_designers`
List active Designer sessions. No parameters.

**Returns:** `[{user, project, since, address}, ...]`

---

## Tag Provider Tools

### `list_tag_providers`
No parameters. Returns all configured providers.

### `get_tag_provider`

| Parameter | Type | Required |
|-----------|------|----------|
| `name` | string | yes |

### `create_tag_provider`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | required | Provider name |
| `description` | string | `""` | Description |
| `provider_type` | string | `"STANDARD"` | STANDARD, REMOTE, or DERIVED |

### `delete_tag_provider`
**Irreversible. Deletes all tags in the provider.**

| Parameter | Type | Required |
|-----------|------|----------|
| `name` | string | yes |

---

## Tag Tools

### `browse_tags`
Browse tag tree structure (names, paths, types) — **not runtime values**.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | `""` | Tag path, e.g. `[default]Folder`. Empty = all providers |
| `depth` | int | `2` | Recursion depth (1-4) |

### `read_tags`
Read runtime values. Requires WebDev tag endpoint.

| Parameter | Type | Description |
|-----------|------|-------------|
| `tag_paths` | list[str] | Fully qualified paths, e.g. `["[default]T1"]`. Max 100 |

**Returns:** `[{path, value, quality, timestamp}, ...]`

### `write_tag`
Write a value. Requires WebDev tag endpoint.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_path` | string | yes | Fully qualified path |
| `value` | any | yes | Value to write |
| `data_type` | string | no | Type hint: Int4, Float8, String, Boolean, etc. |

### `get_tag_config`
Get full tag configuration object (not runtime value). Requires WebDev tagConfig endpoint.

| Parameter | Type | Required |
|-----------|------|----------|
| `tag_path` | string | yes |

### `create_tags`
Create tags (add-only, no overwrite). Requires WebDev tagConfig endpoint.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tags` | list[dict] | yes | Tag config objects with `name`, `tagType`, `dataType` |
| `provider` | string | no | Tag provider name. Default: `"default"` |

### `edit_tags`
Create or update tags with merge semantics. Requires WebDev tagConfig endpoint.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tags` | list[dict] | yes | Tag config objects to merge |
| `provider` | string | no | Tag provider name |

### `delete_tags`
Delete tags by path. **Irreversible.** Requires WebDev tagConfig endpoint.

| Parameter | Type | Required |
|-----------|------|----------|
| `tag_paths` | list[str] | yes |

### `list_udt_types`
List UDT type definitions. Requires WebDev tagConfig endpoint.

| Parameter | Type | Default |
|-----------|------|---------|
| `provider` | string | `"default"` |

### `get_udt_definition`
Get full UDT schema. Requires WebDev tagConfig endpoint.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `udt_path` | string | yes | E.g. `[default]_types_/Motor` |

---

## Alarm Tools

All alarm tools require the WebDev alarm endpoint. See [webdev-setup.md](webdev-setup.md).

### `get_active_alarms`

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_filter` | string | Filter by source path prefix |
| `priority_filter` | string | Min priority: Diagnostic, Low, Medium, High, Critical |
| `state_filter` | string | ActiveUnacked, ActiveAcked, ClearUnacked |

### `get_alarm_history`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_time` | string | 24h ago | ISO 8601, e.g. `2024-01-15T08:00:00Z` |
| `end_time` | string | now | ISO 8601 |
| `source_filter` | string | — | Filter by source prefix |
| `priority_filter` | string | — | Min priority |
| `max_results` | int | `100` | Max entries (1-1000) |

### `acknowledge_alarms`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_ids` | list[str] | yes | Alarm event UUIDs from `get_active_alarms` |
| `ack_note` | string | no | Optional acknowledgement comment |

---

## Historian Tools

### `get_tag_history`
Query historical tag values. Requires WebDev tagHistory endpoint.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_paths` | list[str] | yes | Fully qualified paths (history must be enabled) |
| `start_time` | string | yes | ISO 8601 start |
| `end_time` | string | yes | ISO 8601 end |
| `aggregation` | string | no | LastValue, Average, Minimum, Maximum, Range, Count, etc. Default: `LastValue` |
| `interval_ms` | int | no | Aggregation interval in ms (≥1000). Omit for natural resolution |
| `max_results` | int | no | Max data points per tag (1-10000). Default: `1000` |

**Returns:** `{tags: [{path, values: [{t, v}, ...]}, ...], rowCount}`

---

## Execution Tools

### `run_gateway_script`

**Disabled by default.** Must set `IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true`.

Requires WebDev scriptExec endpoint and careful security setup. See [webdev-setup.md](webdev-setup.md).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `script` | string | required | Python script to execute |
| `timeout_secs` | int | `10` | Timeout (1-60 seconds) |
| `dry_run` | bool | `false` | Preview without executing |

**Returns:** `{result, stdout, error, scriptHash}`

---

## Configuration Reference

All settings use the `IGNITION_MCP_` prefix. See also `src/ignition_mcp/config.py`.

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `IGNITION_MCP_IGNITION_GATEWAY_URL` | `http://localhost:8088` | Gateway base URL |
| `IGNITION_MCP_IGNITION_USERNAME` | `admin` | Basic auth username |
| `IGNITION_MCP_IGNITION_PASSWORD` | `password` | Basic auth password |
| `IGNITION_MCP_IGNITION_API_KEY` | `""` | API key (preferred over basic auth) |
| `IGNITION_MCP_WEBDEV_TAG_ENDPOINT` | `""` (disabled) | Tag read/write WebDev path (recommended: `Global/GatewayAPI/tags`) |
| `IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT` | `""` (disabled) | Tag CRUD WebDev path (recommended: `Global/GatewayAPI/tagConfig`) |
| `IGNITION_MCP_WEBDEV_ALARM_ENDPOINT` | `""` (disabled) | Alarm WebDev path (recommended: `Global/GatewayAPI/alarms`) |
| `IGNITION_MCP_WEBDEV_TAG_HISTORY_ENDPOINT` | `""` (disabled) | Tag history WebDev path (recommended: `Global/GatewayAPI/tagHistory`) |
| `IGNITION_MCP_WEBDEV_SCRIPT_EXEC_ENDPOINT` | `""` (disabled) | Script exec WebDev path (recommended: `Global/GatewayAPI/scriptExec`) |
| `IGNITION_MCP_ENABLE_SCRIPT_EXECUTION` | `false` | Enable `run_gateway_script` |
| `IGNITION_MCP_SSL_VERIFY` | `true` | Verify SSL certificates |
| `IGNITION_MCP_SERVER_HOST` | `127.0.0.1` | MCP server bind host |
| `IGNITION_MCP_SERVER_PORT` | `8007` | MCP server port |
