# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Ignition MCP Server.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Connection Problems](#connection-problems)
- [Authentication Errors](#authentication-errors)
- [Tool Execution Failures](#tool-execution-failures)
- [Performance Issues](#performance-issues)
- [Claude Desktop Integration Issues](#claude-desktop-integration-issues)
- [Common Error Messages](#common-error-messages)
- [Debug Mode and Logging](#debug-mode-and-logging)
- [Getting Help](#getting-help)

## Quick Diagnostics

### Health Check Script

Run this comprehensive health check to identify common issues:

```bash
#!/bin/bash
echo "=== Ignition MCP Server Health Check ==="

# 1. Check Python version
echo "1. Python Version:"
python --version

# 2. Check virtual environment
echo -e "\n2. Virtual Environment:"
which python
echo "VIRTUAL_ENV: $VIRTUAL_ENV"

# 3. Check package installation
echo -e "\n3. Package Installation:"
python -c "
try:
    import ignition_mcp
    print('✅ ignition_mcp package found')
except ImportError as e:
    print(f'❌ ignition_mcp package not found: {e}')

try:
    from mcp.server import Server
    print('✅ MCP package found')
except ImportError as e:
    print(f'❌ MCP package not found: {e}')
"

# 4. Test configuration loading
echo -e "\n4. Configuration:"
python -c "
try:
    from ignition_mcp.config import settings
    print(f'✅ Configuration loaded')
    print(f'   Gateway URL: {settings.ignition_gateway_url}')
    print(f'   API Key: {'SET' if settings.ignition_api_key else 'NOT SET'}')
    print(f'   Username: {settings.ignition_username}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"

# 5. Test server startup
echo -e "\n5. Server Test:"
python test_server.py

echo -e "\n=== Health Check Complete ==="
```

### Environment Validation

```bash
# Check environment variables
env | grep IGNITION_MCP

# Verify .env file exists and is readable
ls -la .env
cat .env | head -5
```

## Installation Issues

### Python Version Incompatibility

**Problem**: Error messages about unsupported Python version.

**Solution**:
```bash
# Check Python version
python --version

# Should show 3.10 or higher
# If not, install Python 3.10+

# On macOS with Homebrew
brew install python@3.11

# On Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# Create new virtual environment with correct Python
python3.11 -m venv .venv
source .venv/bin/activate
```

### Package Installation Failures

#### Missing Build Dependencies

**Error**: 
```
error: Microsoft Visual C++ 14.0 is required
```

**Solution (Windows)**:
```bash
# Install Visual Studio Build Tools
# Download from: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
```

**Error**:
```
error: Failed building wheel for package
```

**Solution**:
```bash
# Install system dependencies (Linux)
sudo apt install build-essential python3-dev

# Use pre-compiled wheels
pip install --only-binary=all -e .

# Or use conda/mamba for problematic packages
conda install package_name
```

#### Network/Proxy Issues

**Error**:
```
Could not fetch URL https://pypi.org/simple/
```

**Solution**:
```bash
# Configure pip for proxy
pip config set global.proxy http://proxy.company.com:8080

# Or use --proxy flag
pip install --proxy http://proxy.company.com:8080 -e .

# Trust internal PyPI
pip config set global.trusted-host pypi.company.com
```

### Virtual Environment Issues

**Problem**: Commands not found or wrong packages used.

**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Verify activation
which python
which pip

# Recreate if needed
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Connection Problems

### Gateway Unreachable

**Symptoms**:
- `test_connection` tool fails
- Connection timeout errors
- "Connection refused" messages

**Diagnosis**:
```bash
# Test basic connectivity
curl http://gateway-host:8088/system/gwinfo

# Test from same network
ping gateway-host

# Check DNS resolution
nslookup gateway-host

# Test specific port
telnet gateway-host 8088
# or
nc -zv gateway-host 8088
```

**Solutions**:

1. **Check Gateway URL**:
   ```bash
   # Common URL formats
   IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:8088
   IGNITION_MCP_IGNITION_GATEWAY_URL=http://192.168.1.100:8088
   IGNITION_MCP_IGNITION_GATEWAY_URL=https://gateway.company.com:8043
   ```

2. **Firewall Issues**:
   ```bash
   # Check if port is open
   sudo ufw status  # Ubuntu
   # Ensure port 8088 (or custom port) is open
   ```

3. **Gateway Not Running**:
   - Verify Ignition Gateway service is running
   - Check Ignition Gateway logs
   - Restart Gateway if needed

### SSL/TLS Issues

**Error**:
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions**:

1. **Use HTTP instead of HTTPS** (for testing):
   ```bash
   IGNITION_MCP_IGNITION_GATEWAY_URL=http://gateway:8088
   ```

2. **Trust self-signed certificates** (development only):
   ```python
   # Add to ignition_client.py (temporary fix)
   import ssl
   ssl_context = ssl.create_default_context()
   ssl_context.check_hostname = False
   ssl_context.verify_mode = ssl.CERT_NONE
   ```

3. **Add certificate to system trust store**:
   ```bash
   # Linux
   sudo cp gateway-cert.crt /usr/local/share/ca-certificates/
   sudo update-ca-certificates
   
   # macOS
   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain gateway-cert.crt
   ```

### Network Proxy Issues

**Problem**: Corporate proxy blocking connections.

**Solution**:
```bash
# Set proxy environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,gateway.local

# Configure in code (if needed)
# Add proxy support to httpx client in ignition_client.py
```

## Authentication Errors

### Invalid API Key

**Error**: `HTTP 401: Unauthorized`

**Diagnosis**:
```bash
# Test API key manually
curl -H "X-Ignition-API-Token: your_key" http://gateway:8088/system/gwinfo

# Check key format (should be alphanumeric string)
echo $IGNITION_MCP_IGNITION_API_KEY
```

**Solutions**:

1. **Regenerate API Key**:
   - Log into Ignition Gateway
   - Go to Config → Security → Users, Roles
   - Select user → Generate new API key
   - Update configuration

2. **Check Key Permissions**:
   - Ensure user has appropriate roles
   - Verify key hasn't expired
   - Check if key is active

### Basic Authentication Issues

**Error**: `HTTP 401: Unauthorized`

**Diagnosis**:
```bash
# Test basic auth manually
curl -u username:password http://gateway:8088/system/gwinfo

# Check credentials
echo "Username: $IGNITION_MCP_IGNITION_USERNAME"
echo "Password: [hidden]"
```

**Solutions**:

1. **Verify Credentials**:
   ```bash
   # Clear any cached credentials
   unset IGNITION_MCP_IGNITION_API_KEY
   
   # Set correct username/password
   IGNITION_MCP_IGNITION_USERNAME=admin
   IGNITION_MCP_IGNITION_PASSWORD=correct_password
   ```

2. **Check User Account**:
   - Verify account exists and is enabled
   - Check password hasn't expired
   - Ensure user has API access permissions

### Mixed Authentication

**Problem**: Both API key and basic auth configured.

**Solution**:
```bash
# API key takes precedence
# To use basic auth, clear API key
IGNITION_MCP_IGNITION_API_KEY=""

# Or use only API key
IGNITION_MCP_IGNITION_USERNAME=""
IGNITION_MCP_IGNITION_PASSWORD=""
```

## Tool Execution Failures

### Tool Not Found

**Error**: `Tool 'tool_name' not found`

**Diagnosis**:
```python
# List available tools
{"tool": "list_available_tools", "arguments": {}}

# Check exact tool name and spelling
```

**Solutions**:

1. **Update OpenAPI Spec**:
   ```bash
   python fetch_openapi.py
   python demo_tools.py  # View updated tools
   ```

2. **Check Tool Generation**:
   ```python
   from ignition_mcp.api_generator import IgnitionAPIGenerator
   generator = IgnitionAPIGenerator()
   tools = generator.generate_tools()
   print([tool['name'] for tool in tools])
   ```

### Invalid Parameters

**Error**: `Invalid parameters for tool`

**Diagnosis**:
```python
# Check tool schema
{"tool": "list_available_tools", "arguments": {}}
# Look for required parameters in the response
```

**Solutions**:

1. **Check Parameter Names**:
   ```python
   # Body parameters need 'body_' prefix
   {"tool": "post_projects", "arguments": {
       "body_name": "ProjectName",  # Correct
       "name": "ProjectName"        # Incorrect
   }}
   ```

2. **Check Parameter Types**:
   ```python
   # Ensure correct data types
   {"tool": "get_logs", "arguments": {
       "limit": 100,        # number, not string
       "minLevel": "INFO"   # string
   }}
   ```

### Gateway API Errors

**Error**: `HTTP 400: Bad Request`

**Diagnosis**:
```bash
# Check gateway logs
{"tool": "get_logs", "arguments": {"limit": 10, "minLevel": "ERROR"}}

# Test API call manually
curl -X POST -H "Content-Type: application/json" \
  -H "X-Ignition-API-Token: your_key" \
  -d '{"name":"test"}' \
  http://gateway:8088/data/api/v1/projects
```

**Solutions**:

1. **Check API Compatibility**:
   - Verify Ignition version supports the API
   - Check if endpoint requires specific modules
   - Review Ignition documentation

2. **Validate Request Data**:
   - Ensure required fields are provided
   - Check data format and types
   - Verify enum values are correct

## Performance Issues

### Slow Tool Execution

**Symptoms**:
- Tool calls take longer than expected
- Timeout errors
- Gateway becomes unresponsive

**Diagnosis**:
```python
# Check gateway performance
{"tool": "get_system_gwinfo", "arguments": {}}

# Monitor resource usage
{"tool": "get_logs", "arguments": {
    "limit": 20,
    "pattern": "memory|cpu|performance"
}}
```

**Solutions**:

1. **Increase Timeout**:
   ```python
   # Edit src/ignition_mcp/ignition_client.py
   self._client = httpx.AsyncClient(
       base_url=self.gateway_url,
       timeout=60.0  # Increase from 30.0
   )
   ```

2. **Optimize Requests**:
   ```python
   # Reduce data size in requests
   {"tool": "get_logs", "arguments": {
       "limit": 50,     # Reduce from larger number
       "minLevel": "WARN"  # Higher threshold
   }}
   ```

3. **Check Gateway Resources**:
   - Increase Gateway memory allocation
   - Check for memory leaks
   - Review Gateway performance settings

### Memory Issues

**Error**: `OutOfMemoryError` or high memory usage

**Solutions**:

1. **Increase Gateway Memory**:
   ```bash
   # Edit gateway configuration
   # Increase Java heap size in wrapper.conf
   wrapper.java.initmemory=512
   wrapper.java.maxmemory=2048
   ```

2. **Optimize Tool Usage**:
   ```python
   # Process data in smaller chunks
   # Instead of getting all logs at once
   for i in range(0, total_logs, 100):
       batch = {"tool": "get_logs", "arguments": {
           "limit": 100,
           "offset": i
       }}
   ```

## Claude Desktop Integration Issues

### MCP Server Not Loading

**Problem**: Claude Desktop doesn't show MCP tools.

**Diagnosis**:
```bash
# Check Claude Desktop config
cat ~/.config/Claude/claude_desktop_config.json  # Linux
cat "~/Library/Application Support/Claude/claude_desktop_config.json"  # macOS

# Test server manually
python -m ignition_mcp.main
```

**Solutions**:

1. **Fix Configuration Path**:
   ```json
   {
     "mcpServers": {
       "ignition-mcp": {
         "command": "python",
         "args": ["-m", "ignition_mcp.main"],
         "cwd": "/absolute/path/to/ignition-mcp"
       }
     }
   }
   ```

2. **Check Python Path**:
   ```json
   {
     "mcpServers": {
       "ignition-mcp": {
         "command": "/path/to/.venv/bin/python",
         "args": ["-m", "ignition_mcp.main"],
         "cwd": "/path/to/ignition-mcp"
       }
     }
   }
   ```

3. **Environment Variables**:
   ```json
   {
     "mcpServers": {
       "ignition-mcp": {
         "command": "python",
         "args": ["-m", "ignition_mcp.main"],
         "cwd": "/path/to/ignition-mcp",
         "env": {
           "IGNITION_MCP_IGNITION_GATEWAY_URL": "http://localhost:8088",
           "IGNITION_MCP_IGNITION_API_KEY": "your_key"
         }
       }
     }
   }
   ```

### Claude Desktop Connection Errors

**Error**: MCP server crashes or disconnects.

**Solutions**:

1. **Check Server Logs**:
   ```bash
   # Run server manually to see errors
   python -m ignition_mcp.main
   ```

2. **Validate JSON Configuration**:
   ```bash
   # Check for JSON syntax errors
   python -m json.tool ~/.config/Claude/claude_desktop_config.json
   ```

3. **Test Standalone**:
   ```bash
   # Test without Claude Desktop
   echo '{"jsonrpc": "2.0", "method": "initialize", "id": 1}' | python -m ignition_mcp.main
   ```

## Common Error Messages

### `ModuleNotFoundError: No module named 'ignition_mcp'`

**Cause**: Package not installed or virtual environment not activated.

**Solution**:
```bash
source .venv/bin/activate
pip install -e .
```

### `FileNotFoundError: [Errno 2] No such file or directory: 'ignition_openapi.json'`

**Cause**: OpenAPI specification file missing.

**Solution**:
```bash
python fetch_openapi.py
```

### `ConnectionError: Failed to connect to gateway`

**Cause**: Gateway unreachable or wrong URL.

**Solution**:
```bash
# Check gateway URL and connectivity
curl http://your-gateway:8088/system/gwinfo
```

### `ValidationError: 1 validation error for Settings`

**Cause**: Invalid configuration values.

**Solution**:
```bash
# Check environment variables and .env file
python -c "from ignition_mcp.config import settings; print(settings.dict())"
```

### `HTTPStatusError: 401 Client Error: Unauthorized`

**Cause**: Invalid authentication credentials.

**Solution**:
```bash
# Verify API key or username/password
curl -H "X-Ignition-API-Token: test_key" http://gateway:8088/system/gwinfo
```

## Debug Mode and Logging

### Enable Debug Logging

Add debug logging to troubleshoot issues:

```python
# Add to beginning of main.py or server.py
import logging
logging.basicConfig(level=logging.DEBUG)

# Or create debug configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ignition_mcp_debug.log'),
        logging.StreamHandler()
    ]
)
```

### HTTP Request Debugging

Debug HTTP requests to Ignition Gateway:

```python
# Add to ignition_client.py
import httpx
import logging

# Enable httpx debug logging
logging.getLogger("httpx").setLevel(logging.DEBUG)

# Or add custom request logging
async def _request(self, method: str, endpoint: str, **kwargs):
    print(f"Making {method} request to {endpoint}")
    print(f"Headers: {kwargs.get('headers', {})}")
    print(f"Data: {kwargs.get('json', {})}")
    
    response = await self._client.request(method=method, url=endpoint, **kwargs)
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    return response
```

### MCP Protocol Debugging

Debug MCP protocol messages:

```python
# Add to server.py
import json

# Log all MCP messages
original_call_tool = self.server.call_tool

def debug_call_tool():
    async def wrapper(name: str, arguments: dict):
        print(f"MCP Tool Call: {name}")
        print(f"Arguments: {json.dumps(arguments, indent=2)}")
        
        result = await original_call_tool(name, arguments)
        
        print(f"Result: {json.dumps(result.dict(), indent=2)}")
        return result
    
    return wrapper

self.server.call_tool = debug_call_tool()
```

## Getting Help

### Before Asking for Help

1. **Run the health check script** (see Quick Diagnostics)
2. **Check this troubleshooting guide** for your specific issue
3. **Search existing issues** on GitHub
4. **Gather debug information**:
   - Error messages (full traceback)
   - Configuration (sanitized)
   - Environment details
   - Steps to reproduce

### Where to Get Help

1. **GitHub Issues**: https://github.com/yourusername/ignition-mcp/issues
   - For bugs and feature requests
   - Include debug information

2. **GitHub Discussions**: https://github.com/yourusername/ignition-mcp/discussions
   - For questions and general help
   - Community support

3. **Documentation**:
   - [Installation Guide](installation.md)
   - [Configuration Guide](configuration.md)
   - [API Reference](api-reference.md)
   - [Usage Examples](examples.md)

### Information to Include

When asking for help, include:

```
**Problem Description**
Clear description of the issue

**Steps to Reproduce**
1. Step 1
2. Step 2
3. Error occurs

**Environment**
- OS: macOS 14.0
- Python: 3.11.0
- Ignition Version: 8.1.25
- MCP Server Version: 0.1.0

**Configuration** (sanitized)
IGNITION_MCP_IGNITION_GATEWAY_URL=http://localhost:8088
IGNITION_MCP_IGNITION_API_KEY=[REDACTED]

**Error Messages**
Full error traceback here

**Debug Output**
Any debug logs or additional information
```

This troubleshooting guide should help you resolve most common issues. If you encounter a problem not covered here, please let us know so we can improve this guide.