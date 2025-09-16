# Claude Code MCP Setup Instructions

## 🔧 Configuration Complete

The MCP server has been automatically configured for Claude Code at:
```
/Users/pmannion/Documents/whiskeyhouse/ignition-mcp/.mcp.json
```

**Important**: The configuration file is `.mcp.json` in the project directory, not in the global config.

## 🚀 Usage in Claude Code

### 1. Restart Claude Code
After adding the configuration, restart Claude Code to load the MCP server.

### 2. Verify Connection
Use these commands to test the connection:

```
Can you list all available Ignition MCP tools?
```

### 3. Available Tools
You'll have access to **45 total tools**:

#### 🔐 **Base Tools**
- `test_connection` - Test gateway connectivity
- `get_gateway_status` - Get gateway status  
- `list_available_tools` - List all tools by category

#### 🏭 **Ignition Gateway API Tools** (42 tools)
- **Activation**: License management
- **Backup**: Gateway backup/restore
- **Logs**: Log retrieval and management
- **Modules**: Module management
- **Projects**: Project operations

## 💡 Example Usage

### Test Connection
```
Can you test the connection to my Ignition Gateway?
```

### Check Gateway Status
```
Is my Ignition Gateway online?
```

### Get Gateway Backup
```
Can you create a backup of my Ignition Gateway?
```

### View Recent Logs
```
Show me the recent ERROR level logs from my gateway.
```

### Activate License
```
Activate the license key: ABC-123-DEF-456
```

## 🛠️ Troubleshooting

### Server Not Starting
1. Check that the path exists: `/Users/pmannion/Documents/whiskeyhouse/ignition-mcp/`
2. Verify the script is executable: `ls -la run_server.sh`
3. Test manually: `./run_server.sh`

### Environment Issues
1. Check `.env` file has correct credentials
2. Verify API key is valid
3. Test connection: `python test_server.py`

### Claude Code Not Detecting Tools
1. Restart Claude Code completely
2. Check configuration file exists: `~/.config/claude-code/claude_code_config.json`
3. Verify no JSON syntax errors

## 📁 File Locations

- **MCP Server**: `/Users/pmannion/Documents/whiskeyhouse/ignition-mcp/`
- **Configuration**: `~/.config/claude-code/claude_code_config.json`
- **Launcher Script**: `run_server.sh`
- **Environment**: `.env`

## 🔍 Alternative Configurations

If the current setup doesn't work, try this alternative configuration:

```json
{
  "mcpServers": {
    "ignition-mcp": {
      "command": "python",
      "args": ["-m", "ignition_mcp.main"],
      "cwd": "/Users/pmannion/Documents/whiskeyhouse/ignition-mcp",
      "env": {
        "PYTHONPATH": "/Users/pmannion/Documents/whiskeyhouse/ignition-mcp/src",
        "PATH": "/Users/pmannion/Documents/whiskeyhouse/ignition-mcp/.venv/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```