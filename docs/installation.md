# Installation Guide

This guide will walk you through installing and setting up the Ignition MCP Server.

## Prerequisites

Before installing, ensure you have:

- **Python 3.10 or higher** installed on your system
- **Ignition Gateway 8.3+** with REST API enabled
- Valid credentials for your Ignition Gateway (username/password or API key)
- Network access to your Ignition Gateway

## Installation Methods

### Method 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/ignition-mcp.git
cd ignition-mcp

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Method 2: Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/ignition-mcp.git
cd ignition-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Method 3: Development Installation

For development work, install with development dependencies:

```bash
# Using uv
uv pip install -e ".[dev]"

# Using pip
pip install -e ".[dev]"
```

## Configuration Setup

### 1. Create Environment File

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

### 2. Edit Configuration

Open `.env` in your text editor and configure:

```bash
# Gateway connection settings
IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:8088
IGNITION_MCP_IGNITION_USERNAME=admin
IGNITION_MCP_IGNITION_PASSWORD=password

# Optional: Use API key instead of username/password
IGNITION_MCP_IGNITION_API_KEY=your_api_key_here

# Server settings (optional)
IGNITION_MCP_SERVER_HOST=127.0.0.1
IGNITION_MCP_SERVER_PORT=8000
```

#### Configuration Options:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `IGNITION_GATEWAY_URL` | Gateway base URL | `http://localhost:8088` | Yes |
| `IGNITION_USERNAME` | Gateway username | `admin` | Yes* |
| `IGNITION_PASSWORD` | Gateway password | `password` | Yes* |
| `IGNITION_API_KEY` | Gateway API key | `""` | No** |
| `SERVER_HOST` | MCP server host | `127.0.0.1` | No |
| `SERVER_PORT` | MCP server port | `8000` | No |

*Required if no API key is provided  
**If provided, takes precedence over username/password

## Verification

### 1. Test Installation

Verify the installation works:

```bash
python -c "
import sys
sys.path.insert(0, 'src')
from ignition_mcp.ignition_tools import IgnitionTools
print('✅ Installation successful')
"
```

### 2. Test Gateway Connection

Run the connection test:

```bash
python test_server.py
```

Expected output:
```
✅ IgnitionTools import successful
✅ IgnitionTools initialization successful
✅ Generated 45 tools
   1. get_activation_activate_key: Activate license key
   2. get_activation_is_online: Check if gateway is online
   3. post_activation_offline_activate: Submit offline activation
```

### 3. Start MCP Server

Test running the MCP server:

```bash
python -m ignition_mcp.main
```

The server should start and wait for MCP client connections.

## Integration with Claude Desktop

### 1. Locate Claude Desktop Config

Find your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 2. Add MCP Server Configuration

Edit the configuration file to include:

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

### 3. Restart Claude Desktop

Close and restart Claude Desktop to load the new MCP server.

## Alternative Installation: Docker

For containerized deployment:

```bash
# Build Docker image
docker build -t ignition-mcp .

# Run container
docker run -d \
  --name ignition-mcp \
  -p 8000:8000 \
  -e IGNITION_MCP_IGNITION_GATEWAY_URL=http://your-gateway:8088 \
  -e IGNITION_MCP_IGNITION_API_KEY=your_api_key \
  ignition-mcp
```

## Troubleshooting Installation

### Common Issues

#### Python Version Error
```bash
# Check Python version
python --version

# Should show Python 3.10 or higher
```

#### Module Import Errors
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall in development mode
pip install -e .
```

#### Connection Timeout
```bash
# Test gateway connectivity
curl http://localhost:8088/system/gwinfo

# Check firewall settings
```

#### Permission Errors
```bash
# On macOS/Linux, ensure proper permissions
chmod +x run_server.sh

# On Windows, run as administrator if needed
```

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review [Configuration Documentation](configuration.md)
3. Open an issue on [GitHub](https://github.com/yourusername/ignition-mcp/issues)

## Next Steps

After successful installation:

1. Read the [Configuration Guide](configuration.md) for advanced settings
2. Explore [Usage Examples](examples.md) to learn the tools
3. Check out the [API Reference](api-reference.md) for detailed documentation