# Ignition MCP Server Usage Guide

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:9088
IGNITION_MCP_IGNITION_API_KEY=your_api_key_here
```

### 2. Install Dependencies
```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 3. Test Connection
```bash
python test_server.py
```

### 4. Run MCP Server
```bash
python -m ignition_mcp.main
```

## 🔧 Available Tools

The server provides **45 total tools**:
- **3 base tools**: connection testing, tool listing
- **42 API tools** generated from Ignition's OpenAPI spec

### Tool Categories:

#### 🔐 **Activation (7 tools)**
- `put_activation_activate_key` - Activate license
- `get_activation_is_online` - Check gateway online status  
- `post_activation_offline_activate` - Submit offline activation
- And more...

#### 💾 **Backup (2 tools)**
- `get_backup` - Get gateway backup
- `post_backup` - Restore gateway backup

#### 📋 **Logs (11 tools)**
- `get_logs` - Retrieve gateway logs
- `get_logs_download` - Download log files
- `post_logs_levelreset` - Reset logger levels
- And more...

#### 📦 **Modules (10 tools)**
- `get_modules_healthy` - List healthy modules
- `post_modules_certificate` - Accept certificates
- `get_modules_eula` - View EULAs
- And more...

#### 🏗️ **Projects (12 tools)**
- `post_projects` - Create project
- `get_projects_export_name` - Export project
- `post_projects_import_name` - Import project
- And more...

## 💡 Usage Examples

### Test Connection
```python
# Use test_connection tool
{"tool": "test_connection", "arguments": {}}
```

### Check Gateway Status
```python
# Check if gateway is online
{"tool": "get_activation_is_online", "arguments": {}}
```

### Activate License
```python
# Activate a license key
{"tool": "put_activation_activate_key", "arguments": {"key": "YOUR-LICENSE-KEY"}}
```

### Get Gateway Backup
```python
# Download gateway backup
{"tool": "get_backup", "arguments": {"includePeerLocal": false}}
```

### View Gateway Logs
```python
# Get recent logs
{"tool": "get_logs", "arguments": {"limit": 100, "minLevel": "INFO"}}
```

## 🛠️ Development

### Run Tests
```bash
python test_server.py
```

### View Tool Demo
```bash
python demo_tools.py
```

### Regenerate Tools
If the OpenAPI spec changes:
```bash
python fetch_openapi.py  # Update spec
python demo_tools.py     # View new tools
```

## 🔍 Troubleshooting

### Connection Issues
- Verify API key in `.env` file
- Check gateway URL and port (default 9088)
- Ensure gateway is running and accessible

### Tool Errors
- Use `list_available_tools` to see all options
- Check tool schemas with demo script
- Verify required parameters are provided

### Authentication
- Server uses `X-Ignition-API-Token` header
- Falls back to basic auth if no API key
- Test with `test_connection` tool