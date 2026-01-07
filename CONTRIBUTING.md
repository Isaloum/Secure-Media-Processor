# Contributing to Secure Media Processor

Thank you for your interest in contributing to Secure Media Processor! This document provides guidelines and procedures for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Adding New Cloud Connectors](#adding-new-cloud-connectors)
- [Pull Request Process](#pull-request-process)
- [CI/CD Pipeline](#cicd-pipeline)
- [Documentation](#documentation)

## 🤝 Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please:

- Be respectful and constructive in all interactions
- Focus on what is best for the community and project
- Show empathy towards other contributors
- Accept constructive criticism gracefully

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.8 or higher (3.11+ recommended)
- **Git**: For version control
- **GitHub Account**: For submitting pull requests
- **Virtual Environment**: For isolated dependency management

### Setup Development Environment

1. **Fork and clone the repository**:
```bash
git clone https://github.com/YOUR_USERNAME/Secure-Media-Processor.git
cd Secure-Media-Processor
```

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install pytest pytest-cov  # Testing dependencies
```

4. **Verify setup**:
```bash
pytest tests/ -v
```

## 🔄 Development Workflow

1. **Create a feature branch**:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

2. **Make your changes** following the code style guidelines

3. **Write or update tests** for your changes

4. **Run tests locally**:
```bash
pytest tests/ --cov=src/connectors --cov-report=term-missing -v
```

5. **Commit your changes**:
```bash
git add .
git commit -m "Clear, descriptive commit message"
```

6. **Push to your fork**:
```bash
git push origin feature/your-feature-name
```

7. **Open a Pull Request** on GitHub

## 🎨 Code Style Guidelines

### General Principles

- **Follow PEP 8**: Python's official style guide
- **Use Type Hints**: Annotate function parameters and return types
- **Write Docstrings**: Document all public functions, classes, and methods
- **Keep It Simple**: Prefer clarity over cleverness
- **DRY Principle**: Don't Repeat Yourself - extract reusable code

### Python Conventions

```python
# Good: Clear naming, type hints, docstring
def upload_file(self, local_path: str, remote_key: str) -> bool:
    """
    Upload a file to cloud storage.
    
    Args:
        local_path: Path to the local file
        remote_key: Remote storage key/path
        
    Returns:
        True if upload succeeded, False otherwise
        
    Raises:
        FileNotFoundError: If local file doesn't exist
        ConnectionError: If cloud service is unreachable
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"File not found: {local_path}")
    
    # Implementation...
    return True

# Bad: No type hints, unclear naming, no documentation
def upload(f, k):
    if not os.path.exists(f):
        raise FileNotFoundError(f"File not found: {f}")
    return True
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `S3Connector`, `ConnectorManager`)
- **Functions/Methods**: `snake_case` (e.g., `upload_file`, `get_metadata`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private Methods**: Prefix with `_` (e.g., `_validate_credentials`)

### Import Organization

```python
# Standard library imports
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List

# Third-party imports
import boto3
from botocore.exceptions import ClientError

# Local imports
from src.connectors.base_connector import BaseConnector
from src.config import Config
```

### Error Handling

- Use specific exceptions rather than generic `Exception`
- Always log errors with appropriate severity levels
- Provide meaningful error messages
- Clean up resources in `finally` blocks or use context managers

```python
# Good
try:
    response = self.client.upload_file(local_path, remote_key)
    logger.info(f"Successfully uploaded {local_path} to {remote_key}")
    return True
except ClientError as e:
    logger.error(f"Failed to upload {local_path}: {e}")
    return False
except FileNotFoundError as e:
    logger.error(f"Local file not found: {e}")
    raise

# Bad
try:
    response = self.client.upload_file(local_path, remote_key)
    return True
except Exception:
    return False
```

## ✅ Testing Requirements

### Testing Philosophy

- **All new code must include tests** - PRs without tests will not be merged
- **Maintain or improve coverage** - Don't decrease overall code coverage
- **Use global mocking fixtures** - Follow established testing patterns
- **Test edge cases** - Include error scenarios, empty inputs, large files

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_s3_connector_new.py -v

# Run with coverage report
pytest tests/ --cov=src/connectors --cov-report=term-missing

# Run specific test function
pytest tests/test_s3_connector_new.py::test_upload_file -v
```

### Test Coverage Expectations

- **Minimum coverage**: 65% for new connectors
- **Target coverage**: 80%+ for production-ready code
- **Critical paths**: 100% coverage for security/encryption functions

### Writing Tests for Cloud Connectors

All connector tests use **global mocking fixtures** to avoid actual cloud API calls. This is the **required testing pattern** for all cloud connectors:

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def mock_sdk_global(monkeypatch):
    """Global mock for SDK client - automatically used in all tests"""
    mock = MagicMock()
    
    # Mock the SDK constructor
    monkeypatch.setattr('sdk_module.Client', lambda *args, **kwargs: mock)
    
    yield mock
    
    # Reset mock between tests for accurate call counts
    mock.reset_mock()

def test_upload_file(mock_sdk_global):
    """Test file upload functionality"""
    # Arrange
    connector = MyConnector(api_key='test-key')
    
    # Act
    result = connector.upload_file('local.txt', 'remote.txt')
    
    # Assert
    assert result is True
    assert mock_sdk_global.upload.called
    assert mock_sdk_global.upload.call_count == 1
    
def test_upload_file_error(mock_sdk_global):
    """Test upload error handling"""
    # Arrange
    mock_sdk_global.upload.side_effect = Exception("Network error")
    connector = MyConnector(api_key='test-key')
    
    # Act
    result = connector.upload_file('local.txt', 'remote.txt')
    
    # Assert
    assert result is False
```

### Key Testing Patterns

**Global Fixture Requirements**:
- Use `autouse=True` to apply fixture to all tests automatically
- Use `scope="function"` for per-test isolation
- Call `reset_mock()` after yielding to reset state between tests
- Mock at the SDK constructor level, not the connector level

**Real-World Examples**:

See our production test files for reference:
- [tests/test_dropbox_connector.py](tests/test_dropbox_connector.py) - Dropbox SDK mocking
- [tests/test_s3_connector_new.py](tests/test_s3_connector_new.py) - boto3 client/resource mocking
- [tests/test_google_drive_connector_new.py](tests/test_google_drive_connector_new.py) - Google API mocking

### Test Organization

- **One test file per connector**: `test_<connector>_connector.py`
- **Descriptive test names**: `test_upload_file_with_valid_path`
- **AAA Pattern**: Arrange, Act, Assert structure
- **Test both success and failure**: Every method needs error handling tests

## 🔌 Adding New Cloud Connectors

### Step-by-Step Guide

#### 1. Create Connector Class

Create `src/connectors/<provider>_connector.py`:

```python
from datetime import datetime, timezone
from typing import Optional
import logging

from src.connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)

class NewProviderConnector(BaseConnector):
    """Connector for NewProvider cloud storage"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__()
        self.api_key = api_key
        self.client = None
        
    def connect(self) -> bool:
        """Establish connection to NewProvider"""
        try:
            # Initialize SDK client
            self.client = NewProviderSDK(api_key=self.api_key)
            self.connected = True
            logger.info("Connected to NewProvider")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NewProvider: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Close NewProvider connection"""
        self.connected = False
        self.client = None
        logger.info("Disconnected from NewProvider")
        return True
    
    def upload_file(self, local_path: str, remote_key: str) -> bool:
        """Upload file to NewProvider"""
        if not self.connected:
            logger.error("Not connected to NewProvider")
            return False
            
        try:
            with open(local_path, 'rb') as f:
                self.client.upload(remote_key, f)
            
            logger.info(f"Uploaded {local_path} to {remote_key}")
            return True
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    # Implement other required methods: download_file, delete_file, list_files, get_metadata
```

**Important datetime note**: Always use `datetime.now(timezone.utc)` instead of deprecated `datetime.utcnow()`:

```python
from datetime import datetime, timezone

# Good
modified_time = datetime.now(timezone.utc)

# Bad - deprecated in Python 3.12+
modified_time = datetime.utcnow()
```

#### 2. Create Test File

Create `tests/test_<provider>_connector.py`:

```python
import pytest
from unittest.mock import MagicMock, mock_open
from src.connectors.newprovider_connector import NewProviderConnector

@pytest.fixture(autouse=True)
def mock_provider_global(monkeypatch):
    """Global mock for NewProvider SDK"""
    mock = MagicMock()
    monkeypatch.setattr('newprovider_sdk.Client', lambda *args, **kwargs: mock)
    yield mock
    mock.reset_mock()

def test_connect(mock_provider_global):
    """Test successful connection"""
    connector = NewProviderConnector(api_key='test-key')
    result = connector.connect()
    assert result is True
    assert connector.connected is True

def test_upload_file(mock_provider_global, monkeypatch):
    """Test file upload"""
    monkeypatch.setattr('builtins.open', mock_open(read_data=b'test data'))
    
    connector = NewProviderConnector(api_key='test-key')
    connector.connect()
    result = connector.upload_file('test.txt', 'remote.txt')
    
    assert result is True
    assert mock_provider_global.upload.called

def test_upload_file_not_connected(mock_provider_global):
    """Test upload without connection"""
    connector = NewProviderConnector(api_key='test-key')
    result = connector.upload_file('test.txt', 'remote.txt')
    assert result is False

def test_upload_file_error(mock_provider_global, monkeypatch):
    """Test upload error handling"""
    monkeypatch.setattr('builtins.open', mock_open(read_data=b'test data'))
    mock_provider_global.upload.side_effect = Exception("Network error")
    
    connector = NewProviderConnector(api_key='test-key')
    connector.connect()
    result = connector.upload_file('test.txt', 'remote.txt')
    
    assert result is False
    assert mock_provider_global.upload.called

# Add comprehensive tests for: download_file, delete_file, list_files, get_metadata
```

**Required test coverage**:
- ✅ Connection success and failure
- ✅ Each method's success path
- ✅ Each method's error handling
- ✅ Edge cases (not connected, file not found, etc.)
- ✅ Minimum 65% code coverage

#### 3. Update CI Workflow

Add your test file to `.github/workflows/python-tests.yml`:

```yaml
- name: Run cloud connector tests with coverage
  run: |
    pytest tests/test_dropbox_connector.py \
           tests/test_s3_connector_new.py \
           tests/test_google_drive_connector_new.py \
           tests/test_newprovider_connector.py \
      --maxfail=2 --disable-warnings -v \
      --cov=src/connectors --cov-report=xml --cov-report=term-missing
```

#### 4. Update Documentation

- Add connector to [README.md](README.md) features list
- Update connector examples in README
- Document any provider-specific requirements
- Add configuration instructions

#### 5. Update Requirements

Add SDK dependency to `requirements.txt`:
```
newprovider-sdk>=1.0.0
```

## 🔀 Pull Request Process

### Before Submitting

- [ ] All tests pass locally (`pytest tests/ -v`)
- [ ] Code coverage meets minimum requirements (65%+)
- [ ] Code follows style guidelines (PEP 8)
- [ ] Docstrings added for new functions/classes
- [ ] README updated if adding new features
- [ ] Commit messages are clear and descriptive
- [ ] No deprecation warnings introduced

### PR Description Template

```markdown
## Description
Brief description of changes made

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Coverage maintained or improved
- [ ] Manual testing completed

## Coverage Report
```
Current coverage: XX%
Previous coverage: XX%
Change: +/-X%
```

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No breaking changes (or documented if unavoidable)
- [ ] No new deprecation warnings

## Related Issues
Closes #issue_number
```

### Review Process

1. **Automated CI checks** must pass (tests, coverage)
2. **Code review** by at least one maintainer
3. **Feedback addressed** - make requested changes
4. **Final approval** - maintainer merges PR

### Merge Requirements

- ✅ All CI checks passing
- ✅ No merge conflicts
- ✅ Approved by maintainer
- ✅ Coverage not decreased
- ✅ Documentation updated

## 🤖 CI/CD Pipeline

### GitHub Actions Workflow

Every push and pull request to `main` branch triggers our CI workflow:

**Workflow File**: [`.github/workflows/python-tests.yml`](.github/workflows/python-tests.yml)

**Pipeline Steps**:

1. **Checkout Code**: Fetches repository code
2. **Set up Python 3.11**: Installs Python runtime
3. **Install Dependencies**: Installs all required packages from requirements.txt
4. **Install Testing Tools**: Installs pytest and pytest-cov
5. **Run Tests**: Executes all connector tests with verbose output
6. **Generate Coverage**: Creates XML and terminal coverage reports
7. **Upload to Codecov**: Publishes coverage metrics with `connector-tests` flag

### Current Test Suite

- **45 tests total** across 3 connectors
- **Execution time**: ~1 second (all mocked, no network calls)
- **Coverage**: 66% overall
  - S3 Connector: 87%
  - Google Drive Connector: 82%
  - Dropbox Connector: 65%

### Viewing CI Results

- **Actions Tab**: [View all workflow runs](https://github.com/Isaloum/Secure-Media-Processor/actions)
- **PR Checks**: Status badges displayed on pull request page
- **Coverage Reports**: Detailed metrics on [Codecov](https://codecov.io/gh/Isaloum/Secure-Media-Processor)
- **Workflow Badge**: [![Tests](https://github.com/Isaloum/Secure-Media-Processor/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Isaloum/Secure-Media-Processor/actions/workflows/python-tests.yml)

### Debugging CI Failures

If CI fails on your PR:

1. **Check workflow logs**: Click on the failed job in the Actions tab
2. **Run tests locally**: `pytest tests/ -v`
3. **Check specific failures**: Look for error messages in test output
4. **Verify coverage**: `pytest tests/ --cov=src/connectors --cov-report=term-missing`
5. **Fix issues**: Address failing tests or coverage gaps
6. **Push fixes**: CI automatically re-runs on new commits

### Local CI Simulation

Run the same checks that CI runs:

```bash
# Full CI test suite
pytest tests/test_dropbox_connector.py \
       tests/test_s3_connector_new.py \
       tests/test_google_drive_connector_new.py \
  --maxfail=2 --disable-warnings -v \
  --cov=src/connectors --cov-report=xml --cov-report=term-missing
```

## 📚 Documentation

### Code Documentation

- **Docstrings**: Required for all public functions, classes, methods
- **Type Hints**: Use for all function parameters and return values
- **Inline Comments**: Explain complex logic or non-obvious decisions
- **TODO Comments**: Mark temporary code or future improvements

### Project Documentation

- **README.md**: Keep feature list and examples up-to-date
- **CONTRIBUTING.md**: Update when processes change
- **CHANGELOG.md**: Document notable changes (if maintained)

### Docstring Format

Use Google-style docstrings:

```python
def process_file(input_path: str, output_path: str, 
                format: str = 'json') -> bool:
    """
    Process input file and save to output path.
    
    Args:
        input_path: Path to input file
        output_path: Path to save processed output
        format: Output format (json, xml, csv). Default is 'json'
        
    Returns:
        True if processing succeeded, False otherwise
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If format is not supported
        
    Example:
        >>> process_file('input.txt', 'output.json', format='json')
        True
    """
```

## 🐛 Reporting Bugs

### Before Reporting

- Check if bug already reported in [Issues](https://github.com/Isaloum/Secure-Media-Processor/issues)
- Verify bug exists in latest version
- Collect reproduction steps and environment details

### Bug Report Template

```markdown
## Bug Description
Clear and concise description of what the bug is

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- OS: [e.g., macOS 14.1, Ubuntu 22.04, Windows 11]
- Python Version: [e.g., 3.11.5]
- Package Version: [e.g., 1.0.0]
- Cloud Provider: [e.g., AWS S3, Google Drive, Dropbox]

## Error Messages
```
Paste any error messages or stack traces here
```

## Additional Context
Screenshots, logs, or other relevant information
```

## 💡 Feature Requests

We welcome feature suggestions! Please:

1. Check if feature already requested in [Issues](https://github.com/Isaloum/Secure-Media-Processor/issues)
2. Open new issue with "enhancement" label
3. Clearly describe the feature and use cases
4. Explain why it would benefit the project
5. Provide examples if possible

## 📞 Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Request Comments**: For code-specific questions during review

## 🙏 Recognition

Contributors are recognized in:

- GitHub contributor graphs
- Release notes (for significant contributions)
- Project README acknowledgments
- Special mention for major features or fixes

## 📖 Additional Resources

- [README.md](README.md) - Project overview and features
- [Testing & CI/CD Documentation](README.md#-testing--cicd) - Detailed testing guide
- [GitHub Actions](https://github.com/Isaloum/Secure-Media-Processor/actions) - View CI/CD runs
- [Codecov Dashboard](https://codecov.io/gh/Isaloum/Secure-Media-Processor) - Coverage metrics

---

**Thank you for contributing to Secure Media Processor!** 🚀

Your efforts help make secure media processing accessible to everyone. Every contribution, no matter how small, makes a difference.
