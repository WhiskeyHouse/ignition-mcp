# Configuration Guide

This guide covers all configuration options for the Ignition MCP Server, including environment variables, authentication methods, and advanced settings.

## Configuration Overview

The Ignition MCP Server uses a hierarchical configuration system:

1. **Environment variables** (highest priority)
2. **`.env` file** (medium priority)  
3. **Default values** (lowest priority)

All environment variables are prefixed with `IGNITION_MCP_` to avoid conflicts.

## Environment Variables

### Gateway Connection Settings

#### `IGNITION_MCP_IGNITION_GATEWAY_URL`
- **Description**: Base URL for your Ignition Gateway
- **Default**: `http://localhost:8088`
- **Format**: `http://hostname:port` or `https://hostname:port`
- **Example**: `https://production-gateway.company.com:8043`

```bash
# Local development
IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:8088

# Production with HTTPS
IGNITION_MCP_IGNITION_GATEWAY_URL=https://gateway.example.com:8043

# Custom port
IGNITION_MCP_IGNITION_GATEWAY_URL=http://192.168.1.100:9088
```

### Authentication Settings

Choose **one** of the following authentication methods:

#### Option 1: API Key Authentication (Recommended)

**`IGNITION_MCP_IGNITION_API_KEY`**
- **Description**: API key for Ignition Gateway REST API
- **Default**: `""` (empty)
- **Security**: Preferred method for production environments
- **Format**: String token generated from Ignition Gateway

```bash
IGNITION_MCP_IGNITION_API_KEY=IGN-API-KEY-1234567890abcdef
```

#### Option 2: Basic Authentication

**`IGNITION_MCP_IGNITION_USERNAME`**
- **Description**: Username for Ignition Gateway
- **Default**: `admin`
- **Note**: Used only if no API key is provided

**`IGNITION_MCP_IGNITION_PASSWORD`**
- **Description**: Password for Ignition Gateway
- **Default**: `password`
- **Security**: Consider using API keys for production

```bash
IGNITION_MCP_IGNITION_USERNAME=gateway_admin
IGNITION_MCP_IGNITION_PASSWORD=secure_password_123
```

### MCP Server Settings

#### `IGNITION_MCP_SERVER_HOST`
- **Description**: Host address to bind the MCP server
- **Default**: `127.0.0.1`
- **Options**: 
  - `127.0.0.1` (localhost only)
  - `0.0.0.0` (all interfaces)
  - Specific IP address

#### `IGNITION_MCP_SERVER_PORT`
- **Description**: Port for the MCP server
- **Default**: `8000`
- **Range**: `1024-65535` (unprivileged ports)

```bash
# Bind to all interfaces on port 9000
IGNITION_MCP_SERVER_HOST=0.0.0.0
IGNITION_MCP_SERVER_PORT=9000
```

## Configuration Files

### `.env` File

Create a `.env` file in the project root for local configuration:

```bash
# Gateway Settings
IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:8088
IGNITION_MCP_IGNITION_API_KEY=your_api_key_here

# Server Settings  
IGNITION_MCP_SERVER_HOST=127.0.0.1
IGNITION_MCP_SERVER_PORT=8000

# Optional: Override defaults
IGNITION_MCP_IGNITION_USERNAME=admin
IGNITION_MCP_IGNITION_PASSWORD=password
```

### Environment-Specific Configuration

#### Development Environment (`.env.dev`)
```bash
IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:8088
IGNITION_MCP_IGNITION_USERNAME=admin
IGNITION_MCP_IGNITION_PASSWORD=password
IGNITION_MCP_SERVER_HOST=127.0.0.1
IGNITION_MCP_SERVER_PORT=8000
```

#### Production Environment (`.env.prod`)
```bash
IGNITION_MCP_IGNITION_GATEWAY_URL=https://production-gateway.company.com:8043
IGNITION_MCP_IGNITION_API_KEY=${IGNITION_API_KEY}
IGNITION_MCP_SERVER_HOST=0.0.0.0
IGNITION_MCP_SERVER_PORT=8080
```

#### Testing Environment (`.env.test`)
```bash
IGNITION_MCP_IGNITION_GATEWAY_URL=http://test-gateway:8088
IGNITION_MCP_IGNITION_API_KEY=test_api_key
IGNITION_MCP_SERVER_HOST=127.0.0.1
IGNITION_MCP_SERVER_PORT=8001
```

## Authentication Setup

### Creating an API Key in Ignition

1. **Open Ignition Gateway Webpage**
   - Navigate to `http://your-gateway:8088`

2. **Access Configuration**
   - Click "Config" tab
   - Enter admin credentials

3. **Navigate to Security**
   - Go to "Security" → "Users, Roles"
   - Select or create a user

4. **Generate API Key**
   - In user details, find "API Keys" section
   - Click "Generate New Key"
   - Copy the generated key
   - Set appropriate permissions/roles

5. **Configure MCP Server**
   ```bash
   IGNITION_MCP_IGNITION_API_KEY=your_generated_key_here
   ```

### Setting Up Basic Authentication

If API keys aren't available, configure basic authentication:

1. **Create Dedicated User** (Recommended)
   - Create a user specifically for MCP operations
   - Assign minimal required roles
   - Use a strong password

2. **Use Existing Admin** (Not Recommended for Production)
   ```bash
   IGNITION_MCP_IGNITION_USERNAME=admin
   IGNITION_MCP_IGNITION_PASSWORD=your_admin_password
   ```

## Advanced Configuration

### SSL/TLS Configuration

For secure connections to Ignition Gateway:

```bash
# Use HTTPS URL
IGNITION_MCP_IGNITION_GATEWAY_URL=https://gateway.example.com:8043

# Optional: Custom certificate verification
# (Configure in code if needed for self-signed certificates)
```

### Timeout Settings

Currently hardcoded to 30 seconds. To modify, edit `src/ignition_mcp/ignition_client.py`:

```python
self._client = httpx.AsyncClient(
    base_url=self.gateway_url,
    timeout=60.0  # Increase to 60 seconds
)
```

### Proxy Configuration

For environments requiring proxy access:

```bash
# Set system environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1
```

## Configuration Validation

### Validate Configuration

Test your configuration with the provided script:

```bash
python test_server.py
```

Expected output:
```
✅ IgnitionTools import successful
✅ IgnitionTools initialization successful  
✅ Generated 45 tools
```

### Test Gateway Connection

```bash
python -c "
import asyncio
from ignition_mcp.ignition_client import IgnitionClient

async def test():
    async with IgnitionClient() as client:
        try:
            result = await client.get_openapi_spec()
            print('✅ Connection successful')
        except Exception as e:
            print(f'❌ Connection failed: {e}')

asyncio.run(test())
"

## Configuration Examples

### Docker Environment

```yaml
# docker-compose.yml
version: '3.8'
services:
  ignition-mcp:
    build: .
    environment:
      - IGNITION_MCP_IGNITION_GATEWAY_URL=http://gateway:8088
      - IGNITION_MCP_IGNITION_API_KEY=${IGNITION_API_KEY}
      - IGNITION_MCP_SERVER_HOST=0.0.0.0
      - IGNITION_MCP_SERVER_PORT=8000
    ports:
      - "8000:8000"
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ignition-mcp-config
data:
  IGNITION_MCP_IGNITION_GATEWAY_URL: "http://ignition-gateway:8088"
  IGNITION_MCP_SERVER_HOST: "0.0.0.0"
  IGNITION_MCP_SERVER_PORT: "8000"
---
apiVersion: v1
kind: Secret
metadata:
  name: ignition-mcp-secret
type: Opaque
stringData:
  IGNITION_MCP_IGNITION_API_KEY: "your_secret_api_key"
```

### Claude Desktop Integration

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

## Security Best Practices

### Production Recommendations

1. **Use API Keys**: Prefer API keys over username/password
2. **Principle of Least Privilege**: Create dedicated users with minimal roles
3. **Secure Storage**: Use environment variables or secret management systems
4. **Network Security**: Use HTTPS when possible
5. **Regular Rotation**: Rotate API keys periodically

### Development Recommendations

1. **Local .env**: Use `.env` files for local development
2. **Version Control**: Add `.env` to `.gitignore`
3. **Test Credentials**: Use separate credentials for testing
4. **Documentation**: Document required permissions for team members

## Troubleshooting Configuration

### Common Issues

#### Authentication Failures
```bash
# Test credentials manually
curl -u username:password http://gateway:8088/system/gwinfo

# Test API key
curl -H "X-Ignition-API-Token: your_key" http://gateway:8088/system/gwinfo
```

#### Network Connectivity
```bash
# Test basic connectivity
curl http://gateway:8088/system/gwinfo

# Check DNS resolution
nslookup gateway.example.com

# Test specific port
telnet gateway.example.com 8088
```

#### Configuration Loading
```bash
# Verify environment variables
env | grep IGNITION_MCP

# Test configuration parsing
python -c "from ignition_mcp.config import settings; print(settings.model_dump())"

### Getting Help

For configuration issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review [Installation Guide](installation.md)
3. Open an issue on [GitHub](https://github.com/yourusername/ignition-mcp/issues)