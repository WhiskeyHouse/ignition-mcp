# Contributing Guide

Thank you for your interest in contributing to the Ignition MCP Server! This guide will help you get started with development and contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Development Workflow](#development-workflow)
- [Release Process](#release-process)

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.10+** installed
- **Git** for version control
- **uv** or **pip** for package management
- Access to an **Ignition Gateway 8.3+** for testing
- Familiarity with **asyncio** and **MCP protocol**

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

```bash
git clone https://github.com/yourusername/ignition-mcp.git
cd ignition-mcp
```

3. **Add upstream remote**:

```bash
git remote add upstream https://github.com/originalowner/ignition-mcp.git
```

## Development Setup

### 1. Create Development Environment

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Using pip
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Install Pre-commit Hooks

```bash
pre-commit install
```

This ensures code formatting and linting on every commit.

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your test gateway details
```

### 4. Verify Setup

```bash
# Run tests
pytest

# Test code formatting
black --check .
isort --check-only .
ruff check .

# Test server
python test_server.py
```

## Code Style Guidelines

We follow Python best practices and use automated tooling to maintain consistent code style.

### Formatting Tools

- **Black**: Code formatting (100 character line length)
- **isort**: Import sorting
- **Ruff**: Fast linting and code quality checks
- **mypy**: Static type checking

### Style Rules

#### 1. Code Formatting

```python
# Good: Black-formatted code
async def get_gateway_status(self) -> Dict[str, Any]:
    """Get gateway status information."""
    return await self._request("GET", "/system/gateway-network/remote-servers/status")


# Bad: Inconsistent formatting
async def get_gateway_status(self)->Dict[str,Any]:
    return await self._request( "GET","/system/gateway-network/remote-servers/status" )
```

#### 2. Type Hints

Always use type hints for function signatures:

```python
# Good: Complete type hints
async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Execute an Ignition Gateway API call."""
    ...

# Bad: Missing type hints
async def call_tool(self, name, arguments):
    """Execute an Ignition Gateway API call."""
    ...
```

#### 3. Docstrings

Use Google-style docstrings:

```python
async def execute_api_call(
    self, 
    client: IgnitionClient, 
    tool_def: Dict[str, Any], 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute the actual API call.
    
    Args:
        client: Ignition client instance
        tool_def: Tool definition dictionary
        arguments: Call arguments
        
    Returns:
        API response data
        
    Raises:
        httpx.HTTPStatusError: On API errors
    """
```

#### 4. Import Organization

Follow isort configuration:

```python
# Standard library imports
import asyncio
import json
from typing import Dict, Any, List

# Third-party imports
import httpx
from mcp.types import Tool, CallToolResult

# Local imports
from .config import settings
from .ignition_client import IgnitionClient
```

#### 5. Error Handling

Use specific exceptions and proper error messages:

```python
# Good: Specific error handling
try:
    result = await client._request(method, final_path, **kwargs)
except httpx.HTTPStatusError as e:
    return CallToolResult(
        content=[TextContent(type="text", text=f"HTTP {e.response.status_code}: {e.response.text}")],
        isError=True
    )
except httpx.ConnectError:
    return CallToolResult(
        content=[TextContent(type="text", text="Failed to connect to gateway")],
        isError=True
    )

# Bad: Generic error handling
try:
    result = await client._request(method, final_path, **kwargs)
except Exception as e:
    return CallToolResult(
        content=[TextContent(type="text", text=str(e))],
        isError=True
    )
```

### Running Style Checks

```bash
# Format code
black .
isort .

# Check style
ruff check .
mypy src/

# Run all checks
pre-commit run --all-files
```

## Testing

### Test Structure

```
tests/
├── unit/
│   ├── test_config.py
│   ├── test_api_generator.py
│   └── test_ignition_tools.py
├── integration/
│   ├── test_ignition_client.py
│   └── test_server.py
└── fixtures/
    ├── sample_openapi.json
    └── mock_responses.py
```

### Writing Tests

#### 1. Unit Tests

```python
# tests/unit/test_config.py
import pytest
from ignition_mcp.config import Settings


def test_default_settings():
    """Test default configuration values."""
    settings = Settings()
    assert settings.ignition_gateway_url == "http://localhost:8088"
    assert settings.server_port == 8000


def test_environment_override():
    """Test environment variable override."""
    import os
    os.environ["IGNITION_MCP_SERVER_PORT"] = "9000"
    
    settings = Settings()
    assert settings.server_port == 9000
    
    # Cleanup
    del os.environ["IGNITION_MCP_SERVER_PORT"]
```

#### 2. Integration Tests

```python
# tests/integration/test_ignition_client.py
import pytest
from ignition_mcp.ignition_client import IgnitionClient


@pytest.mark.asyncio
async def test_get_openapi_spec():
    """Test OpenAPI spec retrieval."""
    async with IgnitionClient() as client:
        spec = await client.get_openapi_spec()
        assert "openapi" in spec
        assert "paths" in spec


@pytest.mark.asyncio 
async def test_connection_error():
    """Test connection error handling."""
    client = IgnitionClient(gateway_url="http://invalid-gateway:8088")
    
    with pytest.raises(Exception):
        async with client:
            await client.get_openapi_spec()
```

#### 3. Mock Testing

```python
# tests/unit/test_ignition_tools.py
import pytest
from unittest.mock import AsyncMock, patch
from ignition_mcp.ignition_tools import IgnitionTools


@pytest.fixture
def mock_api_generator():
    """Mock API generator with sample tools."""
    with patch('ignition_mcp.ignition_tools.IgnitionAPIGenerator') as mock:
        mock.return_value.generate_tools.return_value = [
            {
                'name': 'test_tool',
                'description': 'Test tool',
                'inputSchema': {'type': 'object', 'properties': {}},
                '_ignition_path': '/test',
                '_ignition_method': 'GET'
            }
        ]
        yield mock


def test_get_tools(mock_api_generator):
    """Test tool generation."""
    tools_manager = IgnitionTools()
    tools = tools_manager.get_tools()
    
    assert len(tools) == 1
    assert tools[0].name == 'test_tool'
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/ignition_mcp --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_config.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_config"
```

### Test Configuration

Create `pytest.ini` for consistent test configuration:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

## Pull Request Process

### 1. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write code following the style guidelines
- Add tests for new functionality
- Update documentation if needed
- Ensure all tests pass

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add support for custom timeout configuration

- Add timeout parameter to IgnitionClient
- Update configuration with timeout setting
- Add tests for timeout functionality
- Update documentation"
```

#### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(tools): add project import validation
fix(client): handle connection timeout errors
docs: update installation guide for Windows
test: add integration tests for backup tools
```

### 4. Push and Create PR

```bash
# Push feature branch
git push origin feature/your-feature-name

# Create pull request on GitHub
```

### 5. PR Requirements

Your pull request must:

- [ ] Include clear description of changes
- [ ] Have passing tests (`pytest`)
- [ ] Pass code quality checks (`ruff`, `black`, `isort`, `mypy`)
- [ ] Include documentation updates if needed
- [ ] Follow semantic versioning for breaking changes
- [ ] Have appropriate commit messages

### 6. Review Process

- Maintainers will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged

## Issue Guidelines

### Reporting Bugs

Use the bug report template:

```markdown
**Bug Description**
A clear description of what the bug is.

**Steps to Reproduce**
1. Go to '...'
2. Click on '....'
3. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g. macOS 14.0]
- Python: [e.g. 3.11.0]
- Ignition Version: [e.g. 8.1.25]
- MCP Server Version: [e.g. 0.1.0]

**Additional Context**
Any other context about the problem.
```

### Feature Requests

Use the feature request template:

```markdown
**Feature Description**
A clear description of what you want to happen.

**Use Case**
Describe the use case that would benefit from this feature.

**Proposed Solution**
If you have ideas on how to implement this, describe them here.

**Alternatives Considered**
Describe any alternative solutions you've considered.

**Additional Context**
Any other context or screenshots about the feature request.
```

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `priority:high`: High priority issue
- `priority:low`: Low priority issue

## Development Workflow

### 1. Daily Development

```bash
# Start development session
git checkout main
git pull upstream main
git checkout -b feature/new-feature

# Make changes, test frequently
pytest tests/unit/
python test_server.py

# Commit often with good messages
git add .
git commit -m "feat: implement basic functionality"

# Continue development...
```

### 2. Before Submitting

```bash
# Run full test suite
pytest

# Check code quality
pre-commit run --all-files

# Update documentation if needed
# Update CHANGELOG.md if significant changes

# Rebase on latest main
git fetch upstream
git rebase upstream/main

# Push and create PR
git push origin feature/new-feature
```

### 3. Keeping Fork Updated

```bash
# Regularly sync with upstream
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

### Release Steps

1. **Update Version**:
   - Update `pyproject.toml`
   - Update `CHANGELOG.md`

2. **Create Release PR**:
   ```bash
   git checkout -b release/v1.2.3
   # Make version updates
   git commit -m "chore: bump version to 1.2.3"
   ```

3. **Tag Release**:
   ```bash
   git tag v1.2.3
   git push upstream v1.2.3
   ```

4. **GitHub Release**:
   - Create release on GitHub
   - Include changelog
   - Attach built packages

## Getting Help

### Development Questions

- **GitHub Discussions**: For general questions
- **Discord/Slack**: Real-time chat (if available)
- **Issues**: For specific bugs or features

### Resources

- [MCP Protocol Documentation](https://github.com/modelcontextprotocol)
- [Ignition API Documentation](https://docs.inductiveautomation.com/)
- [Python AsyncIO Guide](https://docs.python.org/3/library/asyncio.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to the Ignition MCP Server! Your contributions help make this project better for everyone.