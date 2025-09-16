# Usage Examples and Tutorials

This guide provides practical examples and tutorials for using the Ignition MCP Server with various tools and scenarios.

## Table of Contents

- [Getting Started](#getting-started)
- [Basic Operations](#basic-operations)
- [Gateway Management](#gateway-management)
- [Project Operations](#project-operations)
- [Backup and Restore](#backup-and-restore)
- [Log Management](#log-management)
- [Module Management](#module-management)
- [Advanced Workflows](#advanced-workflows)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Troubleshooting Examples](#troubleshooting-examples)

## Getting Started

### 1. First Connection Test

Before using any tools, verify your connection to the Ignition Gateway:

```python
# Test basic connectivity
{"tool": "test_connection", "arguments": {}}
```

**Expected Response**:
```json
{
  "status": "success",
  "message": "Connection successful"
}
```

### 2. List Available Tools

See all available tools organized by category:

```python
{"tool": "list_available_tools", "arguments": {}}
```

**Response Structure**:
```json
{
  "total_tools": 45,
  "categories": {
    "activation": [...],
    "backup": [...],
    "logs": [...],
    "modules": [...],
    "projects": [...]
  }
}
```

### 3. Get Gateway Status

Check the overall gateway health:

```python
{"tool": "get_gateway_status", "arguments": {}}
```

## Basic Operations

### Check Gateway Online Status

Verify if the gateway is online and responding:

```python
{"tool": "get_activation_is_online", "arguments": {}}
```

**Use Case**: System health checks, monitoring scripts

### View Gateway Information

Get detailed gateway information:

```python
{"tool": "get_system_gwinfo", "arguments": {}}
```

**Response Includes**:
- Gateway version
- License information  
- System resources
- Network configuration

## Gateway Management

### License Activation

#### Activate a New License Key

```python
{"tool": "put_activation_activate_key", "arguments": {"key": "IGN-XXXX-XXXX-XXXX-XXXX"}}
```

**Use Case**: 
- Setting up new gateway
- Upgrading licenses
- Adding module licenses

#### Check License Status

```python
{"tool": "get_activation", "arguments": {}}
```

**Response Includes**:
- License expiration
- Module entitlements
- Activation status

#### Offline Activation

For air-gapped environments:

```python
# 1. Get activation challenge
{"tool": "get_activation_challenge", "arguments": {"key": "IGN-XXXX-XXXX-XXXX-XXXX"}}

# 2. Submit offline activation response (after processing through IA website)
{"tool": "post_activation_offline_activate", "arguments": {"response": "activation_response_string"}}
```

### Gateway Configuration

#### Reset License

```python
{"tool": "post_activation_reset", "arguments": {}}
```

**Warning**: This removes all licensing. Use with caution.

## Project Operations

### Project Lifecycle Management

#### Create a New Project

```python
{"tool": "post_projects", "arguments": {
  "body_name": "MyNewProject",
  "body_title": "My New Project",
  "body_description": "Project created via MCP",
  "body_enabled": true
}}
```

#### List All Projects

```python
{"tool": "get_projects", "arguments": {}}
```

**Response**: Array of project objects with names, status, and metadata

#### Export Project

```python
{"tool": "get_projects_export_name", "arguments": {
  "projectName": "MyProject"
}}
```

**Use Cases**:
- Project backups
- Version control
- Environment migrations

#### Import Project

```python
{"tool": "post_projects_import_name", "arguments": {
  "projectName": "ImportedProject",
  "body_projectData": "base64_encoded_project_data"
}}
```

### Project Configuration

#### Update Project Properties

```python
{"tool": "put_projects_name", "arguments": {
  "projectName": "MyProject",
  "body_title": "Updated Project Title",
  "body_description": "Updated description",
  "body_enabled": true
}}
```

#### Delete Project

```python
{"tool": "delete_projects_name", "arguments": {
  "projectName": "ProjectToDelete"
}}
```

**Warning**: This permanently deletes the project.

## Backup and Restore

### Create Gateway Backup

#### Full Gateway Backup

```python
{"tool": "get_backup", "arguments": {
  "includePeerLocal": false
}}
```

**Parameters**:
- `includePeerLocal`: Include peer-local data (for distributed architectures)

**Response**: Base64-encoded backup file

#### Scheduled Backup Example

```python
# Create backup with timestamp
import datetime
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

backup_result = {"tool": "get_backup", "arguments": {"includePeerLocal": false}}
# Save backup_result to file with timestamp
```

### Restore Gateway

```python
{"tool": "post_backup", "arguments": {
  "body_backupData": "base64_encoded_backup_data"
}}
```

**Use Cases**:
- Disaster recovery
- Environment synchronization
- Configuration rollbacks

## Log Management

### View Recent Logs

#### Get Latest Log Entries

```python
{"tool": "get_logs", "arguments": {
  "limit": 100,
  "minLevel": "INFO"
}}
```

**Parameters**:
- `limit`: Number of entries (default: 100)
- `minLevel`: Minimum log level (TRACE, DEBUG, INFO, WARN, ERROR)

#### Search Logs by Pattern

```python
{"tool": "get_logs", "arguments": {
  "limit": 50,
  "pattern": "error",
  "minLevel": "ERROR"
}}
```

### Download Log Files

#### Get Available Log Files

```python
{"tool": "get_logs_loggers", "arguments": {}}
```

#### Download Specific Log File

```python
{"tool": "get_logs_download", "arguments": {
  "logName": "wrapper.log"
}}
```

**Common Log Files**:
- `wrapper.log` - Gateway startup and system logs
- `ignition.log` - Main application logs
- `oia.log` - OPC server logs

### Log Configuration

#### Reset Logger Levels

```python
{"tool": "post_logs_levelreset", "arguments": {}}
```

#### Set Logger Level

```python
{"tool": "put_logs_logger", "arguments": {
  "loggerName": "org.eclipse.jetty",
  "body_level": "INFO"
}}
```

**Log Levels**: TRACE, DEBUG, INFO, WARN, ERROR, OFF

## Module Management

### Module Health and Status

#### List Healthy Modules

```python
{"tool": "get_modules_healthy", "arguments": {}}
```

#### Get All Modules

```python
{"tool": "get_modules", "arguments": {}}
```

**Response Includes**:
- Module name and version
- License status
- Health state
- Dependencies

### Certificate Management

#### View Module EULAs

```python
{"tool": "get_modules_eula", "arguments": {}}
```

#### Accept Certificates

```python
{"tool": "post_modules_certificate", "arguments": {
  "body_certificates": ["certificate_id_1", "certificate_id_2"]
}}
```

### Module Configuration

#### Install Module

```python
{"tool": "post_modules_install", "arguments": {
  "body_moduleData": "base64_encoded_module_file"
}}
```

#### Restart Module

```python
{"tool": "post_modules_restart", "arguments": {
  "moduleName": "ModuleToRestart"
}}
```

## Advanced Workflows

### Complete Environment Setup

Here's a workflow for setting up a new Ignition environment:

```python
# 1. Test connection
{"tool": "test_connection", "arguments": {}}

# 2. Activate license
{"tool": "put_activation_activate_key", "arguments": {"key": "YOUR-LICENSE-KEY"}}

# 3. Create project structure
{"tool": "post_projects", "arguments": {
  "body_name": "Production",
  "body_title": "Production Environment",
  "body_enabled": true
}}

# 4. Import configuration
{"tool": "post_projects_import_name", "arguments": {
  "projectName": "Production",
  "body_projectData": "your_project_backup_data"
}}

# 5. Create initial backup
{"tool": "get_backup", "arguments": {"includePeerLocal": false}}

# 6. Verify health
{"tool": "get_modules_healthy", "arguments": {}}
```

### Health Check Automation

Monitor gateway health regularly:

```python
# Gateway connectivity
connection_test = {"tool": "test_connection", "arguments": {}}

# License status
license_status = {"tool": "get_activation", "arguments": {}}

# Module health
module_health = {"tool": "get_modules_healthy", "arguments": {}}

# Recent errors
error_logs = {"tool": "get_logs", "arguments": {
  "limit": 10,
  "minLevel": "ERROR"
}}

# System resources
gateway_info = {"tool": "get_system_gwinfo", "arguments": {}}
```

### Backup Automation

Automated backup workflow:

```python
import schedule
import time

def create_backup():
    # Create timestamped backup
    backup = {"tool": "get_backup", "arguments": {"includePeerLocal": false}}
    
    # Log the backup creation
    log_entry = {"tool": "get_logs", "arguments": {"limit": 1}}
    
    return backup

# Schedule daily backups at 2 AM
schedule.every().day.at("02:00").do(create_backup)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Claude Desktop Integration

### Setting Up Claude Desktop

1. **Configure Claude Desktop** (`claude_desktop_config.json`):

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

### Claude Conversation Examples

#### Example 1: Gateway Health Check

**User**: "Check the health of my Ignition gateway"

**Claude**: "I'll check your Ignition gateway health using several tools."

```python
# Claude automatically uses these tools:
{"tool": "test_connection", "arguments": {}}
{"tool": "get_activation_is_online", "arguments": {}}
{"tool": "get_modules_healthy", "arguments": {}}
{"tool": "get_logs", "arguments": {"limit": 5, "minLevel": "ERROR"}}
```

#### Example 2: Project Management

**User**: "Create a new project called 'TestEnvironment' and export my existing 'Production' project"

**Claude**: "I'll create the new project and export the existing one."

```python
# Create new project
{"tool": "post_projects", "arguments": {
  "body_name": "TestEnvironment",
  "body_title": "Test Environment",
  "body_enabled": true
}}

# Export existing project
{"tool": "get_projects_export_name", "arguments": {
  "projectName": "Production"
}}
```

#### Example 3: Log Analysis

**User**: "Show me any recent errors in the gateway logs"

**Claude**: "Let me check for recent errors in your gateway logs."

```python
{"tool": "get_logs", "arguments": {
  "limit": 20,
  "minLevel": "ERROR"
}}
```

### Natural Language Queries

The MCP integration allows natural language interactions:

- "Create a backup of the gateway"
- "What projects are currently running?"
- "Show me the license status"
- "Are there any module health issues?"
- "Export the HMI project"

## Troubleshooting Examples

### Connection Issues

#### Test Different Authentication Methods

```python
# Test with current configuration
{"tool": "test_connection", "arguments": {}}

# If failed, check gateway info directly
{"tool": "get_system_gwinfo", "arguments": {}}
```

#### Verify Gateway Accessibility

```bash
# Manual curl test
curl -H "X-Ignition-API-Token: your_key" http://gateway:8088/system/gwinfo

# or with basic auth
curl -u username:password http://gateway:8088/system/gwinfo
```

### Tool Execution Errors

#### Debug Tool Parameters

```python
# First, list available tools to verify name
{"tool": "list_available_tools", "arguments": {}}

# Check specific tool schema
# Look for required parameters in the response
```

#### Check Gateway Logs for Errors

```python
{"tool": "get_logs", "arguments": {
  "limit": 10,
  "minLevel": "ERROR",
  "pattern": "REST"
}}
```

### Performance Monitoring

#### Monitor Resource Usage

```python
# Get system information
{"tool": "get_system_gwinfo", "arguments": {}}

# Check for memory-related errors
{"tool": "get_logs", "arguments": {
  "limit": 20,
  "pattern": "memory|OutOfMemory"
}}
```

## Best Practices

### 1. Error Handling

Always check tool results:

```python
result = {"tool": "test_connection", "arguments": {}}
# Check if result indicates success before proceeding
```

### 2. Backup Before Changes

Create backups before making significant changes:

```python
# Create backup before importing project
backup = {"tool": "get_backup", "arguments": {"includePeerLocal": false}}

# Then proceed with changes
project_import = {"tool": "post_projects_import_name", "arguments": {...}}
```

### 3. Gradual Operations

For large operations, work incrementally:

```python
# Instead of importing all projects at once, do them one by one
projects = ["Project1", "Project2", "Project3"]

for project in projects:
    result = {"tool": "post_projects_import_name", "arguments": {
        "projectName": project,
        "body_projectData": get_project_data(project)
    }}
    # Check result before continuing
```

### 4. Regular Health Checks

Implement regular monitoring:

```python
# Daily health check
health_tools = [
    {"tool": "test_connection", "arguments": {}},
    {"tool": "get_activation_is_online", "arguments": {}},
    {"tool": "get_modules_healthy", "arguments": {}},
    {"tool": "get_logs", "arguments": {"limit": 5, "minLevel": "ERROR"}}
]
```

This comprehensive guide should help you get started with the Ignition MCP Server and provide practical examples for common use cases.