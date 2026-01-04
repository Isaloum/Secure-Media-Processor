# Contributing to Secure Media Processor

Thank you for your interest in contributing to Secure Media Processor! This document provides guidelines and instructions for contributing to the project.

## 🌟 Ways to Contribute

There are many ways to contribute to this project:

- 🐛 **Report bugs** - Help us identify and fix issues
- 💡 **Suggest features** - Share your ideas for improvements
- 📝 **Improve documentation** - Help make our docs clearer and more comprehensive
- 🔧 **Submit code** - Fix bugs or implement new features
- 🧪 **Write tests** - Improve test coverage and reliability
- 🎨 **Design** - Improve UI/UX or create visual assets
- 🌍 **Translate** - Help make the project accessible in more languages

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have:
- Python 3.8 or higher installed
- Git installed and configured
- A GitHub account
- Familiarity with Python and basic Git workflows

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork**:
```bash
git clone https://github.com/YOUR_USERNAME/Secure-Media-Processor.git
cd Secure-Media-Processor
```

3. **Add upstream remote**:
```bash
git remote add upstream https://github.com/Isaloum/Secure-Media-Processor.git
```

4. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

5. **Install dependencies**:
```bash
pip install -r requirements.txt
```

6. **Install development dependencies**:
```bash
pip install pytest pytest-cov black flake8 mypy
```

7. **Create a branch for your work**:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## 📋 Development Guidelines

### Code Style

We follow Python best practices and PEP 8 guidelines:

- **Formatting**: Use `black` for code formatting
  ```bash
  black src/ tests/
  ```

- **Linting**: Use `flake8` for linting
  ```bash
  flake8 src/ tests/ --max-line-length=100
  ```

- **Type Hints**: Add type hints to all functions
  ```python
  def process_file(file_path: Path, output: str) -> Dict[str, Any]:
      pass
  ```

- **Docstrings**: Use Google-style docstrings
  ```python
  def upload_file(file_path: str, remote_path: str) -> Dict[str, Any]:
      """Upload a file to cloud storage.
      
      Args:
          file_path: Path to the local file.
          remote_path: Remote destination path.
          
      Returns:
          Dictionary containing upload result with keys:
              - success (bool): Whether upload succeeded
              - remote_path (str): Remote path of uploaded file
              
      Raises:
          FileNotFoundError: If file_path doesn't exist.
      """
      pass
  ```

### Project Structure

```
Secure-Media-Processor/
├── src/                    # Source code
│   ├── connectors/        # Cloud storage connectors
│   ├── encryption.py      # Encryption module
│   ├── gpu_processor.py   # GPU processing
│   ├── cli.py            # CLI interface
│   └── config.py         # Configuration
├── tests/                 # Test suite
├── docs/                  # Documentation (if needed)
├── .github/              # GitHub templates and workflows
└── main.py               # Entry point
```

### Coding Standards

1. **Keep it modular**: Each module should have a single, well-defined purpose
2. **Error handling**: Always handle exceptions appropriately
3. **Logging**: Use the logging module, not print statements
4. **Security**: Never commit credentials or sensitive data
5. **Testing**: Write tests for new features
6. **Documentation**: Document complex logic inline

### Example of Good Code

```python
"""Module for secure file operations."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SecureFileHandler:
    """Handle secure file operations with encryption.
    
    This class provides methods for encrypting, decrypting, and
    securely deleting files.
    """
    
    def __init__(self, key_path: Path):
        """Initialize the handler.
        
        Args:
            key_path: Path to encryption key file.
        """
        self.key_path = key_path
        logger.info(f"Initialized SecureFileHandler with key: {key_path}")
    
    def encrypt_file(
        self,
        input_path: Path,
        output_path: Path
    ) -> Dict[str, Any]:
        """Encrypt a file.
        
        Args:
            input_path: Path to file to encrypt.
            output_path: Path for encrypted output.
            
        Returns:
            Dictionary with encryption results.
            
        Raises:
            FileNotFoundError: If input_path doesn't exist.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")
        
        try:
            # Implementation here
            logger.info(f"Successfully encrypted {input_path}")
            return {'success': True, 'output': str(output_path)}
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return {'success': False, 'error': str(e)}
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_encryption.py

# Run specific test
pytest tests/test_encryption.py::test_key_generation
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names
- Test both success and failure cases
- Use fixtures for common setup

Example:

```python
"""Tests for encryption module."""

import pytest
from pathlib import Path
from src.encryption import MediaEncryptor


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Test content")
    return file_path


def test_encryption_success(temp_file, tmp_path):
    """Test successful file encryption."""
    key_path = tmp_path / "test.key"
    encryptor = MediaEncryptor(key_path)
    output_path = tmp_path / "encrypted.bin"
    
    result = encryptor.encrypt_file(temp_file, output_path)
    
    assert result['success'] is True
    assert output_path.exists()


def test_encryption_missing_file(tmp_path):
    """Test encryption with missing input file."""
    key_path = tmp_path / "test.key"
    encryptor = MediaEncryptor(key_path)
    
    with pytest.raises(FileNotFoundError):
        encryptor.encrypt_file(Path("nonexistent.txt"), tmp_path / "out.bin")
```

## 📝 Commit Guidelines

### Commit Message Format

Use clear, descriptive commit messages following this format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(connectors): add Azure Blob Storage connector

Implement Azure connector with upload, download, and list operations.
Includes full error handling and checksum verification.

Closes #42

---

fix(encryption): handle corrupted key files gracefully

Previously crashed when key file was corrupted. Now catches exception
and provides helpful error message.

---

docs(readme): update installation instructions

Add troubleshooting section and clarify Python version requirements.
```

## 🔄 Pull Request Process

1. **Update your fork**:
```bash
git fetch upstream
git checkout main
git merge upstream/main
```

2. **Create a feature branch**:
```bash
git checkout -b feature/amazing-feature
```

3. **Make your changes**:
   - Write code following our style guidelines
   - Add tests for new functionality
   - Update documentation as needed

4. **Test your changes**:
```bash
pytest
black src/ tests/
flake8 src/ tests/
```

5. **Commit your changes**:
```bash
git add .
git commit -m "feat(component): add amazing feature"
```

6. **Push to your fork**:
```bash
git push origin feature/amazing-feature
```

7. **Open a Pull Request**:
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill out the PR template
   - Link any related issues

### Pull Request Checklist

Before submitting, ensure:
- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] No merge conflicts with main branch
- [ ] No sensitive data in commits

## 🐛 Reporting Bugs

### Before Reporting

1. Check if the bug has already been reported in [Issues](https://github.com/Isaloum/Secure-Media-Processor/issues)
2. Verify you're using the latest version
3. Check if it's a security issue (see [SECURITY.md](SECURITY.md))

### Bug Report Template

```markdown
**Description**
A clear description of the bug.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.10.5]
- GPU: [e.g., NVIDIA RTX 3080]
- Version: [e.g., 1.0.0]

**Logs**
```
Paste relevant logs here
```

**Screenshots**
If applicable, add screenshots.

**Additional Context**
Any other relevant information.
```

## 💡 Suggesting Features

We love feature suggestions! To suggest a feature:

1. Check [Issues](https://github.com/Isaloum/Secure-Media-Processor/issues) to see if it's already suggested
2. Open a new issue with the "Feature Request" template
3. Provide a clear use case and rationale
4. Be open to discussion and feedback

### Feature Request Template

```markdown
**Feature Description**
Clear description of the proposed feature.

**Use Case**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How should this feature work?

**Alternatives Considered**
What other approaches have you thought about?

**Additional Context**
Any other relevant information, mockups, or examples.
```

## 🎯 Adding New Cloud Connectors

To add support for a new cloud provider:

1. **Create connector file**: `src/connectors/yourcloud_connector.py`

2. **Inherit from CloudConnector**:
```python
from .base_connector import CloudConnector

class YourCloudConnector(CloudConnector):
    """Connector for YourCloud storage."""
    
    def __init__(self, **kwargs):
        super().__init__()
        # Your initialization
    
    def connect(self) -> bool:
        # Implement connection logic
        pass
    
    # Implement all abstract methods
```

3. **Update `__init__.py`**: Add your connector to exports

4. **Add tests**: Create `tests/test_yourcloud_connector.py`

5. **Update documentation**: Add setup instructions to GETTING_STARTED.md

6. **Update requirements.txt**: Add any new dependencies

## 📚 Documentation

- Keep README.md up to date with new features
- Update GETTING_STARTED.md for user-facing changes
- Add docstrings to all public functions and classes
- Include usage examples for complex features

## 🔒 Security

- Never commit credentials, API keys, or secrets
- Use environment variables for sensitive configuration
- Follow security best practices in code
- Report security vulnerabilities privately (see [SECURITY.md](SECURITY.md))

## 💬 Code Review

All submissions require code review. We'll review:
- Code quality and style
- Test coverage
- Documentation
- Security implications
- Performance impact

Be patient and open to feedback. Code review helps maintain quality!

## 🏆 Recognition

Contributors will be recognized in:
- Project README
- Release notes
- GitHub contributors page

## 📞 Getting Help

- **Questions**: Open a [GitHub Discussion](https://github.com/Isaloum/Secure-Media-Processor/discussions)
- **Chat**: Join our community chat (link TBD)
- **Email**: Contact maintainers (see profiles)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Secure Media Processor! Together we're building better privacy tools for everyone.** 🙏
