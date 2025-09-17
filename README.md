# Ignition MCP Server

A powerful **Model Context Protocol (MCP)** server that provides seamless integration with **Inductiveautomation's Ignition SCADA/MES platform** through its REST API. This enables AI assistants to interact with Ignition Gateway operations for automation, monitoring, and management tasks.

## 🚀 Features

- **🔌 Automatic API Integration**: Dynamically generates 45+ tools from Ignition's OpenAPI specification
- **🛡️ Flexible Authentication**: Supports both API keys and basic authentication
- **📊 Real-time Gateway Management**: Monitor status, manage projects, handle backups, and more
- **🎯 MCP Protocol**: Full compatibility with Claude Desktop and other MCP clients
- **⚡ Async Operations**: Built on modern async/await patterns for optimal performance
- **🔧 Comprehensive Toolset**: Pre-built tools for activation, backups, logs, modules, and projects

## 📋 Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| **🔐 Activation** | 7 tools | License management and gateway activation |
| **💾 Backup** | 2 tools | Gateway backup creation and restoration |
| **📋 Logs** | 11 tools | Log retrieval, management, and analysis |
| **📦 Modules** | 10 tools | Module health checks and certificate management |
| **🏗️ Projects** | 12 tools | Project creation, import, export, and management |
| **⚙️ Base Tools** | 3 tools | Connection testing and tool discovery |

## 🛠️ Requirements

- **Python 3.10+**
- **Ignition Gateway 8.3+** with REST API enabled
- Valid Ignition Gateway credentials or API key

## 📚 Documentation Structure

This repository includes comprehensive documentation:

- **[Installation Guide](docs/installation.md)** - Step-by-step setup instructions
- **[Configuration Guide](docs/configuration.md)** - Environment and settings configuration  
- **[API Reference](docs/api-reference.md)** - Complete API documentation for all modules
- **[Usage Examples](docs/examples.md)** - Practical examples and tutorials
- **[Contributing Guide](docs/contributing.md)** - Development guidelines and contribution process
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/ignition-mcp.git
cd ignition-mcp

# Install with uv (recommended)
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e .
```

### 2. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit with your Ignition Gateway details
IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:8088
IGNITION_MCP_IGNITION_API_KEY=your_api_key_here
# Optional: configure WebDev endpoint used for tag management
IGNITION_MCP_WEBDEV_TAG_ENDPOINT=project/tagWriter
IGNITION_MCP_WEBDEV_TAG_METHOD=POST
```

### 3. Test & Run
```bash
# Test connection
python test_server.py

# Start MCP server
python -m ignition_mcp.main
```

## 🔗 Integration with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "ignition-mcp": {
      "command": "python",
      "args": ["-m", "ignition_mcp.main"],
      "cwd": "/path/to/ignition-mcp",
      "env": {
        "IGNITION_MCP_IGNITION_GATEWAY_URL": "http://localhost:8088",
        "IGNITION_MCP_IGNITION_API_KEY": "your_api_key"
      }
    }
  }
}
```

## 📖 Example Usage

```python
# Test gateway connection
{"tool": "test_connection", "arguments": {}}

# Get gateway status
{"tool": "get_gateway_status", "arguments": {}}

# List all available tools
{"tool": "list_available_tools", "arguments": {}}

# Activate a license
{"tool": "put_activation_activate_key", "arguments": {"key": "YOUR-LICENSE-KEY"}}

# Create gateway backup
{"tool": "get_backup", "arguments": {"includePeerLocal": false}}

# Get recent logs
{"tool": "get_logs", "arguments": {"limit": 100, "minLevel": "INFO"}}

# Create or update a tag through a WebDev endpoint
{"tool": "create_or_update_tag", "arguments": {"tagPath": "[default]MyFolder/NewTag", "value": 123, "dataType": "Integer"}}
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details on:

- Development setup
- Code style guidelines  
- Testing procedures
- Pull request process

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Model Context Protocol](https://github.com/modelcontextprotocol) - The MCP specification
- [Ignition Documentation](https://docs.inductiveautomation.com/) - Official Ignition docs
- [Claude Desktop](https://claude.ai/desktop) - AI assistant with MCP support

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/ignition-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ignition-mcp/discussions)
- **Documentation**: [Project Wiki](https://github.com/yourusername/ignition-mcp/wiki)
