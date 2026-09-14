# Tool reference

Function signatures and descriptions from `src/ignition_mcp/tools/`. The `ctx` parameter is supplied by the MCP server and is omitted below. Registration is defined in each module.

## get_active_alarms

```python
get_active_alarms(source_filter: Annotated[Optional[str], Field(description="Filter alarms by source path prefix. E.g. '[default]Pumps' to see only alarms from that folder.")] = None, priority_filter: Annotated[Optional[str], Field(description="Minimum alarm priority: Diagnostic, Low, Medium, High, Critical. E.g. 'High' returns High and Critical alarms only.")] = None, state_filter: Annotated[Optional[str], Field(description='Alarm state filter: ActiveUnacked, ActiveAcked, ClearUnacked. Omit to return all active alarms regardless of state.')] = None)
```

Get currently active alarms from the gateway.

Returns active alarm events with source path, display name, priority,
state (active/acked), and timestamps for activation and acknowledgement.

Requires the WebDev alarm endpoint. See docs/webdev-setup.md.

## get_alarm_history

```python
get_alarm_history(start_time: Annotated[Optional[str], Field(description="Start of the query time range in ISO 8601 format, e.g. '2024-01-15T08:00:00Z'. Defaults to 24 hours ago if omitted.")] = None, end_time: Annotated[Optional[str], Field(description="End of the query time range in ISO 8601 format, e.g. '2024-01-15T16:00:00Z'. Defaults to now if omitted.")] = None, source_filter: Annotated[Optional[str], Field(description="Filter by alarm source path prefix, e.g. '[default]Zone1'")] = None, priority_filter: Annotated[Optional[str], Field(description='Minimum priority: Diagnostic, Low, Medium, High, Critical')] = None, max_results: Annotated[int, Field(description='Maximum number of alarm journal entries to return (1-1000)', ge=1, le=1000)] = 100)
```

Query historical alarm journal entries.

Returns alarm events (activations, acknowledgements, clears) within the
specified time range. Use this to investigate past alarm activity or build
audit trails.

Requires the WebDev alarm endpoint. See docs/webdev-setup.md.

## acknowledge_alarms

```python
acknowledge_alarms(event_ids: Annotated[List[str], Field(description='List of alarm event UUIDs to acknowledge. Get these from get_active_alarms (the eventId field).')], ack_note: Annotated[Optional[str], Field(description='Optional acknowledgement note or comment (logged with the ack)')] = None)
```

Acknowledge one or more active alarms.

Requires alarm event IDs, which you can get from get_active_alarms.
The acknowledgement is logged in the alarm journal with the current user
(as configured on the WebDev endpoint) and the optional note.

Requires the WebDev alarm endpoint. See docs/webdev-setup.md.

## list_designers

```python
list_designers()
```

List active Ignition Designer sessions.

Shows who is connected to the Designer, which project they have open, and
since when. Useful to check if anyone is actively editing before making
programmatic changes to a project.

## run_gateway_script

```python
run_gateway_script(script: Annotated[str, Field(description="Python script to execute on the Ignition gateway. Use system.* functions available in the gateway scope. The script runs as a gateway script (not client/designer scope). Return values: use a module-level 'result' variable or print() for output.")], timeout_secs: Annotated[int, Field(description='Execution timeout in seconds (1-60). Default: 10.', ge=1, le=60)] = 10, dry_run: Annotated[bool, Field(description='If True, return the script that WOULD be executed without running it. Useful for previewing before committing to execution.')] = False)
```

Execute a Python script on the Ignition gateway and return the result.

WARNING: This tool executes arbitrary code on the Ignition gateway.
It is DISABLED by default. Set IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true to enable.

The script runs in the gateway scripting scope with access to all
system.* functions available on the gateway (system.tag, system.db, etc.).
It does NOT have access to client-only functions like system.gui.*.

Execution is logged on the gateway with a script hash for audit purposes.

Guardrails:
- Feature flag: must set IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true
- Timeout: enforced both here and on the gateway WebDev side
- Dry-run: set dry_run=True to preview without executing
- Audit: every execution is logged on the gateway

Example script:
  tags = system.tag.readBlocking(['[default]MyTag'])
  result = tags[0].value

The gateway WebDev script must be deployed — see docs/webdev-setup.md.

## get_gateway_info

```python
get_gateway_info()
```

Get Ignition Gateway version, edition, state, and uptime.

Use this first to verify connectivity and confirm the gateway is running.
No parameters required.

## get_module_health

```python
get_module_health()
```

List all installed Ignition modules and their health status.

Returns module name, version, state (LOADED/FAULTED), and any error messages.
Useful for diagnosing why something isn't working before investigating further.

## get_gateway_logs

```python
get_gateway_logs(level: Annotated[Optional[str], Field(description='Minimum log level to return: TRACE, DEBUG, INFO, WARN, ERROR. Default: INFO')] = None, logger_name: Annotated[Optional[str], Field(description="Filter by logger name, e.g. 'com.inductiveautomation.ignition'")] = None, limit: Annotated[int, Field(description='Maximum number of log entries to return (1-1000)', ge=1, le=1000)] = 100)
```

Fetch recent gateway log entries.

Returns log entries with timestamp, level, logger, and message.
Use this to investigate errors, module faults, or unexpected gateway behaviour.

Note: Uses the native Ignition REST API (/data/api/v1/logs).

## get_database_connections

```python
get_database_connections()
```

List all database connections and their current status.

Returns connection name, driver, state (Valid/Faulted), and error info.
Uses native REST API endpoint /data/api/v1/connections/database.

## get_opc_connections

```python
get_opc_connections()
```

List all OPC-UA / OPC-COM connections and their current state.

Returns connection name, type, connection status, and any fault details.
Uses native REST API endpoint /data/api/v1/connections/opc.

## get_system_metrics

```python
get_system_metrics()
```

Get gateway system metrics: CPU, memory, thread counts, active sessions.

Returns a snapshot of gateway resource usage. Useful for diagnosing
performance issues or understanding current gateway load.
Uses native REST API endpoint /data/api/v1/system/metrics.

## get_tag_history

```python
get_tag_history(tag_paths: Annotated[List[str], Field(description="List of fully qualified tag paths with history enabled, e.g. ['[default]Sensors/Temperature', '[default]Sensors/Pressure']. Tags must have historian enabled in their configuration.")], start_time: Annotated[str, Field(description="Start of the query time range in ISO 8601 format. E.g. '2024-01-15T08:00:00Z' or '2024-01-15T08:00:00-05:00'.")], end_time: Annotated[str, Field(description="End of the query time range in ISO 8601 format. E.g. '2024-01-15T16:00:00Z'.")], aggregation: Annotated[str, Field(description='Aggregation mode for the returned values. Common options: LastValue (raw/last value in window), Average, Minimum, Maximum, Range, Count, StdDev, Sum, MinMax. Default: LastValue.')] = 'LastValue', interval_ms: Annotated[Optional[int], Field(description='Aggregation interval in milliseconds. E.g. 60000 for 1-minute intervals. If omitted, Ignition uses the natural storage resolution.', ge=1000)] = None, max_results: Annotated[int, Field(description='Maximum number of data points to return per tag (1-10000)', ge=1, le=10000)] = 1000)
```

Query historical tag values from the Ignition historian.

Returns time-series data for the specified tags over the given time range.
Results include timestamp and value for each data point.

Tag history must be enabled on each tag (History tab in tag properties).
Use browse_tags to find tag paths and get_tag_config to verify history is enabled.

Aggregation modes:
- LastValue: raw stored values (default)
- Average: average value over each interval
- Minimum / Maximum / Range: statistical aggregations
- Count: number of values stored per interval

Requires the WebDev tagHistory endpoint. See docs/webdev-setup.md.

## list_projects

```python
list_projects()
```

List all Ignition projects with their metadata.

Returns project names, titles, descriptions, enabled state, parent project,
and other configuration. No parameters needed.

## get_project

```python
get_project(name: Annotated[str, Field(description="Exact project name, e.g. 'MyProject'")])
```

Get full details of a specific Ignition project by name.

Returns the project's configuration including title, description, parent,
default database, tag provider, user source, and enabled state.

## create_project

```python
create_project(name: Annotated[str, Field(description='Project name (must be unique)')], title: Annotated[Optional[str], Field(description='Display title')] = None, description: Annotated[Optional[str], Field(description='Project description')] = None, parent: Annotated[Optional[str], Field(description='Parent project name for inheritance. Omit for standalone.')] = None, enabled: Annotated[bool, Field(description='Whether the project is enabled')] = True)
```

Create a new empty Ignition project.

The project name must be unique on the gateway. Optionally set a parent
project for resource inheritance.

## delete_project

```python
delete_project(name: Annotated[str, Field(description='Project name to delete')])
```

Permanently delete an Ignition project. THIS IS IRREVERSIBLE.

All project resources (views, scripts, named queries, etc.) will be lost.
Consider exporting the project first with export_project.

## copy_project

```python
copy_project(source_name: Annotated[str, Field(description='Name of the existing project to copy')], new_name: Annotated[str, Field(description='Name for the new copy')])
```

Clone an existing Ignition project to a new name.

Creates an exact copy of all project resources. The new name must not
already exist on the gateway.

## rename_project

```python
rename_project(current_name: Annotated[str, Field(description='Current project name')], new_name: Annotated[str, Field(description='New project name')])
```

Rename an Ignition project.

This changes the project's identifier. Any references to the old name
(e.g. in gateway scripts) will need to be updated manually.

## export_project

```python
export_project(name: Annotated[str, Field(description='Project name to export')])
```

Export an Ignition project as a ZIP archive (base64-encoded).

Returns {filename, content_base64, size_bytes}. The content is the standard
Ignition project export format — you can save it as a .zip file and re-import
it with import_project. Useful for backups or migration between gateways.

## import_project

```python
import_project(name: Annotated[str, Field(description='Project name for the import')], zip_base64: Annotated[str, Field(description='Base64-encoded ZIP content from export_project')], overwrite: Annotated[bool, Field(description='Overwrite if a project with this name already exists')] = False)
```

Import an Ignition project from a base64-encoded ZIP archive.

The ZIP should be in Ignition's standard project export format (as returned
by export_project). WARNING: if overwrite=true, any existing project with
the same name will be replaced.

## list_project_resources

```python
list_project_resources(project: Annotated[str, Field(description="Project name, e.g. 'MyProject'")], path_prefix: Annotated[Optional[str], Field(description="Optional path prefix to filter results. E.g. 'com.inductiveautomation.perspective/views' to list only Perspective views, or 'com.inductiveautomation.ignition/script-python' for scripts.")] = None)
```

List all resources in an Ignition project.

Returns paths for all project resources: Perspective views, scripts, named queries,
report templates, transaction groups, and more.

Resource paths follow the pattern:
  {module-id}/{resource-type}/{name}/{filename}

Common module IDs:
- com.inductiveautomation.perspective — Perspective views and styles
- com.inductiveautomation.ignition   — Scripts, named queries, tags, etc.
- com.inductiveautomation.vision     — Vision windows and templates

Use get_project_resource to fetch the content of a specific resource.

## get_project_resource

```python
get_project_resource(project: Annotated[str, Field(description="Project name, e.g. 'MyProject'")], resource_path: Annotated[str, Field(description="Full resource path within the project. E.g. 'com.inductiveautomation.perspective/views/MainView/view.json'")])
```

Fetch the content of a specific project resource.

Returns the raw resource content — usually JSON for views and queries,
Python source for scripts. AI can read this to understand or modify the resource.

Examples:
- Perspective view: 'com.inductiveautomation.perspective/views/Dashboard/view.json'
- Script module: 'com.inductiveautomation.ignition/script-python/utils/code.py'
- Named query: 'com.inductiveautomation.ignition/named-query/GetSensorData/query.json'

Use list_project_resources to discover available resource paths.

## set_project_resource

```python
set_project_resource(project: Annotated[str, Field(description="Project name, e.g. 'MyProject'")], resource_path: Annotated[str, Field(description="Full resource path within the project. E.g. 'com.inductiveautomation.perspective/views/MainView/view.json'. If the resource doesn't exist, it will be created.")], content: Annotated[Any, Field(description='Resource content to write. For JSON resources (views, queries) this should be a dict/object. For Python scripts, this may be a string or structured object depending on the Ignition version.')])
```

Create or overwrite a project resource (view, script, named query, etc.).

Writes the provided content to the specified resource path. If the resource
doesn't exist it is created; if it does, it is overwritten.

WARNING: This directly overwrites the resource on the gateway. There is no
undo — consider reading the existing resource with get_project_resource first
if you want to preserve or merge content.

Common use cases:
- Modify a Perspective view's JSON to update component properties
- Update a script module with new Python code
- Create a new named query

No WebDev required — uses native REST API.

## delete_project_resource

```python
delete_project_resource(project: Annotated[str, Field(description="Project name, e.g. 'MyProject'")], resource_path: Annotated[str, Field(description="Full resource path within the project to delete. E.g. 'com.inductiveautomation.perspective/views/OldView/view.json'")])
```

Delete a specific project resource. THIS IS IRREVERSIBLE.

Permanently removes the resource from the project. This cannot be undone.
Consider listing project resources first (list_project_resources) to
confirm the exact path before deleting.

No WebDev required — uses native REST API.

## list_tag_providers

```python
list_tag_providers()
```

List all configured tag providers on the gateway.

Tag providers are containers for tags. Most installations have a 'default'
provider of type STANDARD. This returns provider names, types, and config.
These are *configuration* resources — for runtime tag values, use read_tags.

## get_tag_provider

```python
get_tag_provider(name: Annotated[str, Field(description="Tag provider name, e.g. 'default'")])
```

Get the full configuration of a specific tag provider.

Returns the provider type (STANDARD, REMOTE, DERIVED), settings, and
metadata. Use list_tag_providers first to see available names.

## create_tag_provider

```python
create_tag_provider(name: Annotated[str, Field(description='New tag provider name')], description: Annotated[str, Field(description='Provider description')] = '', provider_type: Annotated[str, Field(description='Provider type: STANDARD (local tags), REMOTE, or DERIVED')] = 'STANDARD')
```

Create a new tag provider on the gateway.

Most use cases need a STANDARD provider, which stores tags locally.
REMOTE providers connect to another gateway's tags over the gateway network.

## delete_tag_provider

```python
delete_tag_provider(name: Annotated[str, Field(description='Tag provider name to delete')])
```

Delete a tag provider and ALL of its tags. THIS IS IRREVERSIBLE.

All tags within this provider will be permanently deleted. This cannot
be undone. Make sure you have a backup if the tags are important.

## browse_tags

```python
browse_tags(path: Annotated[str, Field(description="Tag path to browse from. Use '[default]' for the default provider root, '[default]Folder/Subfolder' for deeper paths. Empty string browses all providers.")] = '', depth: Annotated[int, Field(description='How deep to recurse (1-4). Default 2. Max 4 to prevent huge responses.', ge=1, le=4)] = 2)
```

Browse the tag tree structure (names, types, paths) — NOT runtime values.

Returns the hierarchical tag structure up to the requested depth. Tags may be
AtomicTag (leaf), Folder, or UDT instances. Large tag databases can have
thousands of tags, so depth is capped at 4.

Path syntax: [provider]Folder/Subfolder/TagName
- Provider name in square brackets, e.g. [default]
- Forward-slash hierarchy after the provider
- Empty path returns all providers as top-level entries

For runtime tag VALUES (current reading, quality, timestamp), use read_tags instead.

## read_tags

```python
read_tags(tag_paths: Annotated[List[str], Field(description="List of fully qualified tag paths to read, e.g. ['[default]Folder/Temperature', '[default]Folder/Pressure']. Max 100.", max_length=100)])
```

Read runtime values of one or more Ignition tags.

Returns a list of {path, value, quality, timestamp} for each tag.

IMPORTANT: Requires a WebDev script on the Ignition gateway.
Set IGNITION_MCP_WEBDEV_TAG_ENDPOINT (default: Global/GatewayAPI/tags).
See docs/webdev-setup.md for setup instructions.

## write_tag

```python
write_tag(tag_path: Annotated[str, Field(description="Fully qualified tag path, e.g. '[default]Folder/SetPoint'")], value: Annotated[Any, Field(description='Value to write to the tag')], data_type: Annotated[Optional[str], Field(description='Ignition data type hint (Int4, Float8, String, Boolean, etc.)')] = None)
```

Write a value to a single Ignition tag.

IMPORTANT: Requires a WebDev script on the Ignition gateway.
Set IGNITION_MCP_WEBDEV_TAG_ENDPOINT (default: Global/GatewayAPI/tags).
See docs/webdev-setup.md for setup instructions.

## get_tag_config

```python
get_tag_config(tag_path: Annotated[str, Field(description="Fully qualified tag path, e.g. '[default]Folder/MyTag'. Returns full configuration JSON, not the runtime value.")])
```

Get the full configuration object for a tag (not its runtime value).

Returns the tag definition: data type, tag type, alarming config, history
settings, scaling, etc. This is equivalent to right-clicking a tag in the
Designer and viewing its properties.

Requires the WebDev tagConfig endpoint (IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT).
See docs/webdev-setup.md for gateway setup instructions.

## create_tags

```python
create_tags(tags: Annotated[List[Dict[str, Any]], Field(description="List of tag configuration objects to create. Each must have at minimum 'name' and 'tagType' (e.g. 'AtomicTag'). Include 'path' to specify the folder. Example: [{'name': 'MyTag', 'tagType': 'AtomicTag', 'dataType': 'Float8', 'path': '[default]Folder'}]")], provider: Annotated[Optional[str], Field(description="Tag provider name. Defaults to 'default' on the gateway.")] = None)
```

Create one or more tags from configuration objects.

Uses Ignition's system.tag.configure() with editMode='a' (add only).
Tags that already exist will not be overwritten — use edit_tags for updates.

Each tag object should follow Ignition's tag configuration schema. Minimum:
- name: tag name
- tagType: 'AtomicTag', 'Folder', 'UdtInstance', etc.
- dataType: 'Boolean', 'Int4', 'Float8', 'String', etc.

Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.

## edit_tags

```python
edit_tags(tags: Annotated[List[Dict[str, Any]], Field(description="List of tag configuration objects to create or update. Uses merge/upsert semantics — existing tags are updated, new ones created. Each object must include 'name' and any fields to modify.")], provider: Annotated[Optional[str], Field(description="Tag provider name. Defaults to 'default' on the gateway.")] = None)
```

Create or modify tags using merge/upsert semantics.

Uses Ignition's system.tag.configure() with editMode='m' (merge).
Existing tags have specified properties updated; non-specified properties
are left unchanged. New tags are created if they don't exist.

Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.

## delete_tags

```python
delete_tags(tag_paths: Annotated[List[str], Field(description="List of fully qualified tag paths to delete, e.g. ['[default]Folder/MyTag', '[default]OtherFolder']. Deleting a folder removes all tags within it.")])
```

Delete tags by path. THIS IS IRREVERSIBLE.

Deleting a folder removes all tags within it recursively.
The tag paths must be fully qualified (e.g. '[default]Folder/TagName').

Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.

## list_udt_types

```python
list_udt_types(provider: Annotated[str, Field(description="Tag provider name to list UDT types from, e.g. 'default'")] = 'default')
```

List all UDT (User Defined Type) type definitions in a tag provider.

Returns the names and paths of all UDT type definitions. Use get_udt_definition
to fetch the full schema for a specific UDT type.

UDT types live under the _types_ folder in the tag browser.

Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.

## get_udt_definition

```python
get_udt_definition(udt_path: Annotated[str, Field(description="Path to the UDT type definition, e.g. '[default]_types_/Motor'. Use list_udt_types to discover available types.")])
```

Fetch the full schema definition of a UDT (User Defined Type).

Returns the complete UDT structure: all member tags, their types, alarming
config, parameters, and overridable properties. Useful for understanding
what an instance will contain before creating one.

Requires the WebDev tagConfig endpoint. See docs/webdev-setup.md.
