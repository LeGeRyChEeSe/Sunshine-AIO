---
project_name: Sunshine-AIO
user_name: Kilian
date: 2026-02-20
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_rules']
existing_patterns_found: 6
status: 'complete'
rule_count: 35
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Core Technologies
- **Python 3.x** - Primary language
- **Nuitka 2.4.8+** - Compiler for Windows executable generation

### Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| requests | >=2.32.3 | HTTP library for downloads |
| python-dotenv | >=1.0.1 | Environment variable management |
| colorama | >=0.4.6 | Terminal color output |
| psutil | >=6.0.0 | System utilities |
| zstandard | >=0.23.0 | Compression library |
| ordered-set | >=4.1.0 | Ordered collection |

### Build Tools
- **Nuitka** - Compile Python to standalone Windows executables
- **Batch scripts** - Windows compilation workflow

### Platform
- Windows 10/11 only
- PowerShell installation method

---

## Critical Implementation Rules

### Path Handling
- **ALWAYS use absolute paths**: `os.path.abspath(os.path.dirname(__file__))`
- Never use relative paths - they fail in different execution contexts

### Logging
- Use the centralized Logger from `misc.Logger`
- Log levels: SUCCESS, INFO, WARNING, ERROR, PROGRESS, HEADER
- Include icons in log messages: ✓, ℹ, ⚠, ✗, →, ■
- Always log to both console and file
- Keep max 5 log files (auto-rotation)

### Error Handling
- Always use try/except blocks with detailed error messages
- Log exceptions with traceback: `logger.exception(message, exc)`
- Provide user-friendly error messages with `input("Press Enter to exit...")`

### Admin Privileges
- Check with `ctypes.windll.shell32.IsUserAnAdmin()`
- Use `rerun_as_admin()` for elevated operations
- Reuse existing logs when running as admin

### GitHub Downloads
- Use fallback pattern matching for release asset names
- Validate URLs before making requests
- Log detailed error messages including attempted patterns

---

## Code Patterns

### Naming Conventions
- **Classes**: PascalCase (e.g., `MenuHandler`, `Logger`, `SystemRequests`)
- **Functions/variables**: snake_case (e.g., `get_app_name()`, `_base_path`)
- **Private members**: Leading underscore (e.g., `_page`, `_choices`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `MODULE_NAME`)

### Type Hints
- Always use type hints from `typing` module
- Common imports: `List`, `Dict`, `Optional`, `Tuple`

```python
from typing import List, Dict, Optional

def example_function(items: List[str]) -> Optional[Dict[str, str]]:
    pass
```

### Imports
- Absolute imports from `misc` package
- Format: `from misc.ModuleName import function_name`

```python
from misc.MenuHandler import MenuHandler
from misc.Logger import log_info, log_error
from misc.Config import DownloadManager
```

### Docstrings
- Google style docstrings for classes and functions

```python
class ExampleClass:
    """
    Description of the class.

    Attributes:
        attribute: Description of attribute.
    """

    def method(self, param: str) -> bool:
        """
        Description of method.

        Args:
            param: Description of parameter.

        Returns:
            Description of return value.
        """
        pass
```

### String Formatting
- Use f-strings exclusively
- Avoid backslashes in f-strings

```python
# Good
message = f"Downloading {filename}..."

# Avoid (causes SyntaxError)
message = f"Path: C:\folder\{filename}"
```

### Property Decorators
- Use `@property` for read-only attributes
- Raise `ValueError` in setters to prevent manual edits

```python
@property
def release(self):
    return self._release

@release.setter
def release(self):
    raise ValueError("No manual edit allowed.")
```

### Windows-Specific Patterns
- Use `ctypes.windll.shell32.IsUserAnAdmin()` for admin checks
- Use `subprocess.run()` with `["powershell.exe", "-Command", "..."]` for PowerShell
- Use `os.name == 'nt'` or check for Windows-specific paths
- Always use `encoding='utf-8'` when opening files

### CLI Patterns
- Entry point: `main()` function with `if __name__ == "__main__": main()`
- Use `input()` for user prompts
- Handle `KeyboardInterrupt` gracefully
- Use `sys.exit()` for clean exits

### Code Quality
- Keep files under ~2000 lines
- Single responsibility principle for functions
- Group imports: stdlib → third-party → local
- No unused imports or variables

---

## Critical Don't-Miss Rules

### Anti-Patterns to Avoid
- **NEVER use relative paths** - Always use `os.path.abspath()`
- **NEVER use .format()** - Use f-strings only
- **NEVER skip encoding='utf-8'** when opening files
- **NEVER use print()** - Use Logger functions instead
- **NEVER omit traceback** when logging exceptions

### Edge Cases
- Admin check after rerun: reuse existing logs
- GitHub downloads: always use fallback patterns
- Log rotation: max 5 log files
- Windows path separators: use `os.path.join()` not `/`

### Security Rules
- Never hardcode credentials
- Keep .env in .gitignore
- Validate URLs before HTTP requests

### File Organization
```
src/
├── main.py              # Entry point
└── misc/
    ├── __init__.py
    ├── Logger.py        # Logging system
    ├── MenuHandler.py   # Main menu logic
    ├── Config.py        # Configuration
    ├── SystemRequests.py # System operations
    ├── Uninstaller.py   # Uninstall functionality
    ├── constants.py     # Constants
    ├── variables/       # JSON config files
    └── ressources/      # Static resources
```

### Menu Pattern
- Use dictionary mapping for menu options
- Lambda functions for option handlers
- Page-based navigation

```python
self._map = [
    {
        "1": self.action_one,
        "2": lambda: self.action_two(param=True),
        "0": sys.exit
    }
]
```

### JSON Configuration
- Store menu choices in `variables/menu_choices.json`
- Store app config in `variables/config.json`
- Use `json.load()` and `json.dump()` for persistence

### Logging Pattern
```python
from misc.Logger import log_info, log_error, log_header

log_info("Starting process...")
log_header("MAJOR_SECTION")

try:
    result = perform_action()
    log_success(f"Completed: {result}")
except Exception as e:
    log_error(f"Failed: {e}")
    log_exception("Action failed", e)
```

---

## Development Workflow

### Branch Naming
- Feature branches: `feature/NewFeature`
- Bug fixes: `fix/IssueDescription`

### Commit Messages
- Use clear, descriptive messages
- Reference issue numbers when applicable

### Versioning
- Follow Keep a Changelog format
- Update CHANGELOG.md on each release

### Building Executable
```bash
pip install -r requirements_dev.txt
cd compiler
compile_executable.bat
```

---

## File Paths

- Project root: `{repository root}`
- Source code: `src/`
- Logs: `logs/` (gitignored)
- User data: `src/user_data/` (gitignored)
- Configuration: `src/misc/variables/`

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-02-20
