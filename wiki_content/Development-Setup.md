# Development Setup

Complete guide for setting up a development environment to contribute to Sunshine-AIO.

## 🛠️ Prerequisites

### Required Software

**For End Users:**
- Just run: `irm https://sunshine-aio.com/script.ps1 | iex` (installs everything automatically)

**For Developers:**
- **Python 3.8+** (recommended: Python 3.11)
- **Git** for version control
- **Visual Studio Code** or **PyCharm** (recommended IDEs)
- **Windows 10/11** for testing (primary target platform)

**Optional Tools:**
- **GitHub Desktop** for easier Git management
- **Windows Subsystem for Linux (WSL)** for cross-platform testing
- **Docker** for containerized testing environments

### Python Environment Setup

**Install Python:**
```bash
# Download from python.org or use winget
winget install Python.Python.3.11

# Verify installation
python --version
pip --version
```

**Virtual Environment (Recommended):**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows Command Prompt:
venv\Scripts\activate
# Windows PowerShell:
venv\Scripts\Activate.ps1
# Git Bash/Linux:
source venv/bin/activate

# Verify activation (should show (venv) prefix)
```

## 📥 Project Setup

### Fork and Clone Repository

**1. Fork the Repository:**
```
1. Visit: https://github.com/LeGeRyChEeSe/Sunshine-AIO
2. Click "Fork" button (top right)
3. Create fork in your account
```

**2. Clone Your Fork:**
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Sunshine-AIO.git
cd Sunshine-AIO

# Add upstream remote
git remote add upstream https://github.com/LeGeRyChEeSe/Sunshine-AIO.git

# Verify remotes
git remote -v
```

**3. Install Dependencies:**
```bash
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements_dev.txt  # If exists

# Or install in development mode
pip install -e .
```

### Development Dependencies

**Core Dependencies:**
```python
# requirements.txt
requests>=2.31.0
urllib3>=2.2.2
zstandard>=0.23.0
psutil>=6.0.0
colorama>=0.4.6
customtkinter>=5.2.0
```

**Development Dependencies:**
```python
# requirements_dev.txt
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
pre-commit>=3.0.0
sphinx>=6.0.0
```

## 🏗️ Project Structure

### Directory Layout
```
Sunshine-AIO/
├── src/                          # Source code
│   ├── main.py                   # CLI entry point
│   ├── gui_main.py              # GUI entry point
│   ├── gui/                     # GUI components
│   │   ├── __init__.py
│   │   ├── main_window.py       # Main application window
│   │   ├── pages/              # UI pages
│   │   │   ├── __init__.py
│   │   │   ├── install_page.py
│   │   │   ├── uninstall_page.py
│   │   │   └── settings_page.py
│   │   └── adapters/           # Business logic
│   │       ├── __init__.py
│   │       └── menu_adapter.py
│   └── misc/                    # Core modules
│       ├── __init__.py
│       ├── Config.py           # Configuration management
│       ├── SystemRequests.py   # System operations
│       ├── InstallationTracker.py # Installation tracking
│       ├── Uninstaller.py      # Removal system
│       ├── MenuHandler.py      # CLI menu logic
│       └── Logger.py           # Logging system
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test data
├── docs/                       # Documentation
├── tools/                      # Downloaded components
├── requirements.txt            # Python dependencies
├── requirements_dev.txt        # Development dependencies
├── pyproject.toml             # Project configuration
├── README.md                  # Project overview
├── LICENSE                    # MIT License
└── .gitignore                 # Git ignore rules
```

### Code Organization

**Core Principles:**
- **Separation of Concerns:** GUI, business logic, and system operations are separate
- **Dependency Injection:** Components receive dependencies rather than creating them
- **Error Handling:** Comprehensive error handling with proper logging
- **Testability:** Code designed to be easily testable

**Module Dependencies:**
```
GUI Layer (gui/) → Business Logic (adapters/) → Core Logic (misc/)
```

## 🧪 Testing Framework

### Running Tests

**Unit Tests:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py

# Run specific test method
pytest tests/unit/test_config.py::TestConfig::test_sunshine_installation
```

**Integration Tests:**
```bash
# Run integration tests (requires admin privileges)
pytest tests/integration/ --admin

# Run without admin-required tests
pytest tests/integration/ -m "not admin_required"
```

### Writing Tests

**Unit Test Example:**
```python
# tests/unit/test_installation_tracker.py
import unittest
from unittest.mock import Mock, patch, mock_open
import json
from src.misc.InstallationTracker import InstallationTracker

class TestInstallationTracker(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.base_path = "C:\\test\\path"
        self.tracker = InstallationTracker(self.base_path)
        
    @patch('builtins.open', new_callable=mock_open, read_data='{}')
    def test_track_installation(self, mock_file):
        """Test installation tracking functionality."""
        # Test data
        component = "test_component"
        install_path = "C:\\test\\install"
        metadata = {
            "version": "1.0.0",
            "installer_type": "test_installer"
        }
        
        # Execute
        self.tracker.track_installation(component, install_path, metadata)
        
        # Verify
        self.assertTrue(self.tracker.is_tool_installed(component))
        paths = self.tracker.get_all_installation_paths(component)
        self.assertIn(install_path, paths)
        
    def test_installation_verification(self):
        """Test installation verification logic."""
        # Mock installation data
        self.tracker.installations = {
            "sunshine": {
                "install_path": "C:\\Program Files\\Sunshine",
                "files_created": ["sunshine.exe"]
            }
        }
        
        # Test verification
        with patch('os.path.exists', return_value=True):
            self.assertTrue(self.tracker.is_tool_installed("sunshine"))
            
        with patch('os.path.exists', return_value=False):
            self.assertFalse(self.tracker.is_tool_installed("sunshine"))
```

**Integration Test Example:**
```python
# tests/integration/test_download_flow.py
import pytest
import os
import tempfile
from src.misc.Config import Config
from src.misc.SystemRequests import SystemRequests

class TestDownloadFlow:
    def setup_method(self):
        """Set up integration test environment."""
        self.sr = SystemRequests()
        self.config = Config(self.sr)
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_download_and_extract(self):
        """Test complete download and extraction workflow."""
        # Use a known small file for testing
        test_url = "https://github.com/LeGeRyChEeSe/Sunshine-AIO/archive/refs/heads/main.zip"
        download_path = os.path.join(self.temp_dir, "test.zip")
        extract_path = os.path.join(self.temp_dir, "extracted")
        
        # Test download
        success = self.sr.download_file(test_url, download_path)
        assert success, "Download should succeed"
        assert os.path.exists(download_path), "Downloaded file should exist"
        
        # Test extraction
        success = self.sr.extract_archive(download_path, extract_path)
        assert success, "Extraction should succeed"
        assert os.path.exists(extract_path), "Extracted directory should exist"
```

### Test Configuration

**pytest.ini:**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    admin_required: marks tests that require admin privileges
    integration: marks integration tests
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
```

**pyproject.toml:**
```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --disable-warnings"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow",
    "admin_required: marks tests that require admin privileges",
    "integration: marks integration tests"
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/build/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

## 🎨 Code Style

### Code Formatting

**Black Configuration:**
```toml
[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'
exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
  | tools
)/
'''
```

**Apply Formatting:**
```bash
# Format all code
black src/ tests/

# Check formatting without changes
black --check src/ tests/

# Format specific file
black src/misc/Config.py
```

### Linting

**Flake8 Configuration:**
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503, E501
exclude = 
    .git,
    __pycache__,
    venv,
    build,
    dist,
    tools
max-complexity = 10
```

**Run Linting:**
```bash
# Lint all code
flake8 src/ tests/

# Lint specific file
flake8 src/misc/Config.py
```

### Type Checking

**MyPy Configuration:**
```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true

[[tool.mypy.overrides]]
module = ["tests.*"]
ignore_errors = true
```

**Type Annotations Example:**
```python
from typing import List, Dict, Optional, Union, Tuple

def install_component(
    component_name: str,
    install_path: Optional[str] = None,
    options: Optional[Dict[str, Union[str, int, bool]]] = None
) -> Tuple[bool, str]:
    """
    Install a component with type safety.
    
    Args:
        component_name: Name of component to install
        install_path: Optional custom installation path
        options: Optional configuration parameters
        
    Returns:
        Tuple of success status and message
    """
    pass
```

## 🔧 Pre-commit Hooks

### Setup Pre-commit

**Install Pre-commit:**
```bash
pip install pre-commit

# Install git hooks
pre-commit install
```

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
      
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
      
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

**Run Pre-commit:**
```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Skip hooks for emergency commit
git commit -m "emergency fix" --no-verify
```

## 🚀 Development Workflow

### Branch Management

**Create Feature Branch:**
```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/new-component-installer

# Work on feature
# ... make changes ...

# Commit changes
git add .
git commit -m "feat: add new component installer"

# Push to your fork
git push origin feature/new-component-installer
```

**Branch Naming Conventions:**
```
feature/description  - New features
bugfix/description   - Bug fixes
hotfix/description   - Critical fixes
docs/description     - Documentation updates
refactor/description - Code refactoring
```

### Commit Messages

**Conventional Commits Format:**
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Examples:**
```bash
feat: add HDR support for streaming
fix: resolve installation tracker memory leak
docs: update API reference documentation
refactor: simplify configuration management
test: add unit tests for uninstaller
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting changes
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks

### Pull Request Process

**Before Creating PR:**
```bash
# Ensure tests pass
pytest

# Ensure code is formatted
black src/ tests/
flake8 src/ tests/

# Ensure type checking passes
mypy src/

# Update documentation if needed
```

**PR Template:**
```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated (if needed)
- [ ] No breaking changes (or clearly documented)
```

## 🐛 Debugging

### Debug Configuration

**VS Code launch.json:**
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug CLI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/main.py",
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug GUI",
            "type": "python", 
            "request": "launch",
            "program": "${workspaceFolder}/src/gui_main.py",
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

### Logging Configuration

**Debug Logging Setup:**
```python
import logging

# Configure debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

## 📚 Documentation

### Code Documentation

**Docstring Style (Google Format):**
```python
def install_component(component_name: str, options: dict = None) -> bool:
    """Install a component with specified options.
    
    This function downloads and installs the specified component
    with the given configuration options.
    
    Args:
        component_name (str): Name of the component to install.
        options (dict, optional): Configuration options. Defaults to None.
        
    Returns:
        bool: True if installation successful, False otherwise.
        
    Raises:
        InstallationError: If installation fails.
        DownloadError: If download fails.
        
    Example:
        >>> install_component("sunshine", {"port": 47990})
        True
    """
    pass
```

### Building Documentation

**Sphinx Setup:**
```bash
# Install sphinx
pip install sphinx sphinx-rtd-theme

# Initialize documentation
cd docs/
sphinx-quickstart

# Build documentation
make html

# View documentation
# Open docs/_build/html/index.html
```

## 🤝 Contributing Guidelines

### Code Review Checklist

**Before Requesting Review:**
- [ ] All tests pass
- [ ] Code is properly formatted
- [ ] Type hints are complete
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No breaking changes (or properly documented)

**Review Process:**
1. **Automated Checks** - GitHub Actions run tests and linting
2. **Code Review** - Maintainers review code changes
3. **Testing** - Manual testing if needed
4. **Approval** - At least one maintainer approval required
5. **Merge** - Squash and merge to main branch

### Getting Help

**Community Resources:**
- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - Questions and general discussion
- **Wiki** - Documentation and guides
- **Code Comments** - Inline documentation

**Development Questions:**
- Create GitHub issue with `question` label
- Check existing issues for similar questions
- Review architecture documentation
- Ask in GitHub discussions

---

*Ready to contribute? Check out the [good first issue](https://github.com/LeGeRyChEeSe/Sunshine-AIO/labels/good%20first%20issue) label for beginner-friendly tasks!*