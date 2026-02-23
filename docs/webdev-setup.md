# WebDev Endpoint Setup Guide

This guide explains how to deploy the gateway-side WebDev scripts that back
several Ignition MCP tools. These scripts expose Ignition scripting functions
(system.tag.*, system.alarm.*, etc.) over HTTP so the MCP server can reach them.

## Overview

The following tools require WebDev endpoints on the gateway:

| Endpoint path (default)          | Used by tools                                      |
|----------------------------------|----------------------------------------------------|
| `Global/GatewayAPI/tags`         | `read_tags`, `write_tag`                           |
| `Global/GatewayAPI/tagConfig`    | `get_tag_config`, `create_tags`, `edit_tags`, `delete_tags`, `list_udt_types`, `get_udt_definition` |
| `Global/GatewayAPI/alarms`       | `get_active_alarms`, `get_alarm_history`, `acknowledge_alarms` |
| `Global/GatewayAPI/tagHistory`   | `get_tag_history`                                  |
| `Global/GatewayAPI/scriptExec`   | `run_gateway_script` (off by default)              |

Tools that use the **native REST API only** (no WebDev needed):
`get_gateway_info`, `get_module_health`, `get_gateway_logs`, `get_database_connections`,
`get_opc_connections`, `get_system_metrics`, all project tools, `list_project_resources`,
`get_project_resource`, `set_project_resource`, `delete_project_resource`, and all tag
provider tools.

---

## Prerequisites

- Ignition 8.x with the **WebDev module** installed and licensed
- A project on the gateway to host the WebDev resources (e.g. `Global`)
- Appropriate user permissions to create WebDev resources in the Designer

## How to Deploy a WebDev Script

1. Open the Ignition Designer and connect to your gateway
2. In the Project Browser, expand **WebDev**
3. Right-click to create a **New Resource** at the desired path
4. Paste the script from this guide into the resource's `doPost` handler
5. Save and publish the project

Each WebDev resource handles `POST` requests with a JSON body.

---

## 1. Tag Read / Write — `Global/GatewayAPI/tags`

This endpoint backs `read_tags` and `write_tag`.

```python
# doPost handler
import json

def doPost(request, session):
    data = json.loads(request['data'])

    if 'paths' in data:
        # Read multiple tags
        paths = data['paths']
        results = []
        readings = system.tag.readBlocking(paths)
        for i, path in enumerate(paths):
            qv = readings[i]
            results.append({
                'path': path,
                'value': qv.value,
                'quality': str(qv.quality),
                'timestamp': str(qv.timestamp),
            })
        return {'json': results}

    elif 'tagPath' in data:
        # Write a single tag
        path = data['tagPath']
        value = data['value']
        data_type = data.get('dataType')
        if data_type:
            value = system.tag.DataType.valueOf(data_type).coerce(value)
        system.tag.writeBlocking([path], [value])
        return {'json': {'status': 'ok', 'tagPath': path, 'value': value}}

    else:
        return {'json': {'error': 'Invalid request body'}, 'response': {'code': 400}}
```

**Configuration:**
```ini
IGNITION_MCP_WEBDEV_TAG_ENDPOINT=Global/GatewayAPI/tags
```

---

## 2. Tag Configuration CRUD — `Global/GatewayAPI/tagConfig`

This endpoint backs `get_tag_config`, `create_tags`, `edit_tags`, `delete_tags`,
`list_udt_types`, and `get_udt_definition`.

```python
# doPost handler
import json

def doPost(request, session):
    data = json.loads(request['data'])
    action = data.get('action')

    if action == 'getConfig':
        tag_path = data['tagPath']
        tags = system.tag.getConfiguration([tag_path], False)
        if tags:
            return {'json': tags[0]}
        return {'json': {'error': 'Tag not found: ' + tag_path}, 'response': {'code': 404}}

    elif action == 'configure':
        tags_config = data['tags']
        edit_mode = data.get('editMode', 'm')
        provider = data.get('provider', 'default')
        result = system.tag.configure(provider, tags_config, edit_mode)
        return {'json': {'status': 'ok', 'results': result}}

    elif action == 'deleteTags':
        tag_paths = data['tagPaths']
        system.tag.deleteTags(tag_paths)
        return {'json': {'status': 'deleted', 'count': len(tag_paths)}}

    elif action == 'listUDTTypes':
        provider = data.get('provider', 'default')
        # Browse the _types_ folder to list UDT definitions
        results = system.tag.browse('[' + provider + ']_types_', {'tagType': 'UdtType'})
        types = [{'name': r.name, 'path': str(r.fullPath)} for r in results.getResults()]
        return {'json': types}

    elif action == 'getUDTDefinition':
        udt_path = data['udtPath']
        tags = system.tag.getConfiguration([udt_path], True)
        if tags:
            return {'json': tags[0]}
        return {'json': {'error': 'UDT not found: ' + udt_path}, 'response': {'code': 404}}

    else:
        return {'json': {'error': 'Unknown action: ' + str(action)}, 'response': {'code': 400}}
```

**Configuration:**
```ini
IGNITION_MCP_WEBDEV_TAG_CONFIG_ENDPOINT=Global/GatewayAPI/tagConfig
```

---

## 3. Alarms — `Global/GatewayAPI/alarms`

This endpoint backs `get_active_alarms`, `get_alarm_history`, and `acknowledge_alarms`.

```python
# doPost handler
import json
from java.util import Date
from java.text import SimpleDateFormat

def _parse_iso(iso_str):
    """Parse ISO 8601 string to Java Date."""
    if iso_str is None:
        return None
    fmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssX")
    return fmt.parse(iso_str)

def doPost(request, session):
    data = json.loads(request['data'])
    action = data.get('action')

    if action == 'getActive':
        source_filter = data.get('sourceFilter', '')
        priority_filter = data.get('priorityFilter', '')
        state_filter = data.get('stateFilter', '')
        alarms = system.alarm.queryStatus(
            source=source_filter,
            priority=priority_filter,
            state=state_filter,
        )
        results = []
        for alarm in alarms:
            results.append({
                'eventId': str(alarm.eventId),
                'displayPath': str(alarm.displayPath),
                'source': str(alarm.source),
                'priority': str(alarm.priority),
                'state': str(alarm.state),
                'activeTime': str(alarm.activeTime),
                'ackTime': str(alarm.ackTime) if alarm.ackTime else None,
            })
        return {'json': results}

    elif action == 'getHistory':
        start_time = _parse_iso(data.get('startTime'))
        end_time = _parse_iso(data.get('endTime'))
        source_filter = data.get('sourceFilter', '')
        priority_filter = data.get('priorityFilter', '')
        max_results = data.get('maxResults', 100)
        results_ds = system.alarm.queryJournal(
            startDate=start_time,
            endDate=end_time,
            source=source_filter,
            priority=priority_filter,
        )
        entries = []
        for i in range(min(results_ds.rowCount, max_results)):
            row = {}
            for col in range(results_ds.columnCount):
                row[results_ds.getColumnName(col)] = str(results_ds.getValueAt(i, col))
            entries.append(row)
        return {'json': {'entries': entries, 'total': results_ds.rowCount}}

    elif action == 'acknowledge':
        event_ids = data['eventIds']
        ack_note = data.get('ackNote', '')
        from java.util import UUID
        uuid_list = [UUID.fromString(eid) for eid in event_ids]
        system.alarm.acknowledge(uuid_list, ack_note)
        return {'json': {'acknowledged': len(event_ids)}}

    else:
        return {'json': {'error': 'Unknown action: ' + str(action)}, 'response': {'code': 400}}
```

**Configuration:**
```ini
IGNITION_MCP_WEBDEV_ALARM_ENDPOINT=Global/GatewayAPI/alarms
```

---

## 4. Tag History — `Global/GatewayAPI/tagHistory`

This endpoint backs `get_tag_history`.

```python
# doPost handler
import json
from java.text import SimpleDateFormat

def _parse_iso(iso_str):
    if iso_str is None:
        return None
    fmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssX")
    return fmt.parse(iso_str)

def doPost(request, session):
    data = json.loads(request['data'])
    tag_paths = data['tagPaths']
    start_time = _parse_iso(data['startTime'])
    end_time = _parse_iso(data['endTime'])
    aggregation = data.get('aggregation', 'LastValue')
    interval_ms = data.get('intervalMs')
    max_results = data.get('maxResults', 1000)

    kwargs = {
        'paths': tag_paths,
        'startDate': start_time,
        'endDate': end_time,
        'aggregationMode': aggregation,
        'returnSize': max_results,
    }
    if interval_ms:
        kwargs['columnTimestampMode'] = 'Interpolated'
        kwargs['intervalHours'] = interval_ms / 3600000.0

    results_ds = system.tag.queryTagHistory(**kwargs)

    # Convert dataset to JSON-serialisable structure
    tags_out = []
    for col_idx in range(results_ds.columnCount):
        col_name = results_ds.getColumnName(col_idx)
        if col_name == 'Timestamp':
            continue
        values = []
        for row_idx in range(min(results_ds.rowCount, max_results)):
            ts = results_ds.getValueAt(row_idx, 0)  # column 0 is timestamp
            v = results_ds.getValueAt(row_idx, col_idx)
            values.append({'t': str(ts), 'v': v})
        tags_out.append({'path': col_name, 'values': values})

    return {'json': {'tags': tags_out, 'rowCount': results_ds.rowCount}}
```

**Configuration:**
```ini
IGNITION_MCP_WEBDEV_TAG_HISTORY_ENDPOINT=Global/GatewayAPI/tagHistory
```

---

## 5. Script Execution — `Global/GatewayAPI/scriptExec`

> **SECURITY WARNING**: This endpoint executes arbitrary Python on the gateway.
> Deploy with extreme care. Restrict access using WebDev security zones and
> Ignition role-based security. Only enable when explicitly needed.

This endpoint backs `run_gateway_script`. It is **disabled by default** on the MCP
server side — you must also set `IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true`.

```python
# doPost handler
import json
import hashlib
import time
import traceback

logger = system.util.getLogger('GatewayAPI.scriptExec')

def doPost(request, session):
    data = json.loads(request['data'])
    script = data.get('script', '')
    timeout_secs = min(data.get('timeoutSecs', 10), 60)
    dry_run = data.get('dryRun', False)

    # Audit log: record every execution attempt
    script_hash = hashlib.sha256(script.encode()).hexdigest()[:12]
    logger.info('Script execution request | hash=%s | timeout=%ds | dryRun=%s'
                % (script_hash, timeout_secs, dry_run))

    if dry_run:
        return {'json': {'dry_run': True, 'script': script, 'would_execute': True}}

    # Execute with timeout enforcement
    stdout_lines = []
    result_holder = [None]
    error_holder = [None]

    class OutputCapture:
        def write(self, text):
            stdout_lines.append(text)
        def flush(self):
            pass

    try:
        import sys as _sys
        _old_stdout = _sys.stdout
        _sys.stdout = OutputCapture()
        exec_globals = {'__builtins__': __builtins__, 'system': system, 'result': None}
        start = time.time()
        exec(script, exec_globals)
        elapsed = time.time() - start
        result_holder[0] = exec_globals.get('result')
        logger.info('Script completed | hash=%s | elapsed=%.2fs' % (script_hash, elapsed))
    except Exception as e:
        error_holder[0] = traceback.format_exc()
        logger.warn('Script error | hash=%s | error=%s' % (script_hash, str(e)))
    finally:
        try:
            _sys.stdout = _old_stdout
        except:
            pass

    return {'json': {
        'result': result_holder[0],
        'stdout': ''.join(stdout_lines),
        'error': error_holder[0],
        'scriptHash': script_hash,
    }}
```

**Required configuration on the MCP server:**
```ini
IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true
IGNITION_MCP_WEBDEV_SCRIPT_EXEC_ENDPOINT=Global/GatewayAPI/scriptExec
```

**Security checklist before enabling:**
- [ ] Restrict the WebDev resource to specific security zones (e.g. internal network only)
- [ ] Set the WebDev resource to require authentication
- [ ] Add a role check in the script (e.g. `if 'Administrators' not in session.get('roles', []): ...`)
- [ ] Review what `system.*` functions are available in your gateway scope
- [ ] Enable audit logging in Ignition to capture all gateway script events
- [ ] Never expose this endpoint to the public internet

---

## Security Considerations

All WebDev endpoints should be protected by Ignition's built-in security:

1. **Authentication**: The MCP server authenticates using the `IGNITION_MCP_USERNAME`/
   `IGNITION_MCP_PASSWORD` or `IGNITION_MCP_API_KEY` credentials. Ensure these have
   the minimum required permissions.

2. **Role-based access**: Restrict WebDev resources to specific user roles in the
   Ignition security settings.

3. **Network access**: Use Ignition's WebDev security zone configuration to limit
   which IP addresses can reach these endpoints.

4. **TLS**: Use HTTPS (`IGNITION_MCP_SSL_VERIFY=true`) in production environments.

5. **Audit trail**: Enable Ignition's audit logging to record all gateway operations.

---

## Testing Your Endpoints

After deploying, you can test with curl:

```bash
# Test tag read endpoint
curl -X POST \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"paths": ["[default]YourTag"]}' \
  http://localhost:8088/system/webdev/Global/GatewayAPI/tags

# Test tag config endpoint
curl -X POST \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"action": "getConfig", "tagPath": "[default]YourTag"}' \
  http://localhost:8088/system/webdev/Global/GatewayAPI/tagConfig
```

Or via the MCP server:
```bash
# Start server
uv run python mcp_server.py

# Test with MCP inspector or Claude Desktop
```
