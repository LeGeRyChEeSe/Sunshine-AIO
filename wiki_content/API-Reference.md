# API Reference

Technical documentation for developers working with or extending Sunshine-AIO.

## 📚 Core Modules

### SystemRequests (`src/misc/SystemRequests.py`)

Central system operations manager for platform-specific tasks.

#### Class: `SystemRequests`

```python
class SystemRequests:
    def __init__(self):
        """Initialize system request manager with platform detection."""
        
    def _get_system_info(self) -> dict:
        """Get comprehensive system information."""
        
    def _is_admin(self) -> bool:
        """Check if running with administrator privileges."""
        
    def _run_as_admin(self, command: str) -> bool:
        """Execute command with elevated privileges."""
```

**Methods:**

```python
def execute_command(self, command: str, shell: bool = False) -> tuple:
    """
    Execute system command with proper error handling.
    
    Args:
        command (str): Command to execute
        shell (bool): Use shell interpretation
        
    Returns:
        tuple: (success: bool, output: str, error: str)
    """

def download_file(self, url: str, destination: str) -> bool:
    """
    Download file with progress tracking and verification.
    
    Args:
        url (str): Download URL
        destination (str): Local file path
        
    Returns:
        bool: Success status
    """

def extract_archive(self, archive_path: str, destination: str) -> bool:
    """
    Extract compressed archives (zip, 7z, tar, etc.).
    
    Args:
        archive_path (str): Path to archive file
        destination (str): Extraction directory
        
    Returns:
        bool: Success status
    """
```

### InstallationTracker (`src/misc/InstallationTracker.py`)

Tracks all installed components for complete uninstallation capability.

#### Class: `InstallationTracker`

```python
class InstallationTracker:
    def __init__(self, base_path: str):
        """
        Initialize installation tracker.
        
        Args:
            base_path (str): Project base directory path
        """
        
    def track_installation(self, component: str, install_path: str, metadata: dict):
        """
        Record component installation details.
        
        Args:
            component (str): Component identifier
            install_path (str): Installation directory
            metadata (dict): Additional installation data
        """
        
    def get_all_installation_paths(self, component: str) -> List[str]:
        """
        Retrieve all installation paths for component.
        
        Args:
            component (str): Component identifier
            
        Returns:
            List[str]: List of installation paths
        """
        
    def is_tool_installed(self, component: str) -> bool:
        """
        Check if component is installed.
        
        Args:
            component (str): Component identifier
            
        Returns:
            bool: Installation status
        """
```

**Installation Metadata Structure:**

```python
INSTALLATION_SCHEMA = {
    "component_name": {
        "install_path": str,           # Primary installation directory
        "install_date": str,           # ISO format timestamp
        "version": str,                # Component version
        "installer_type": str,         # Installation method
        "custom_options": dict,        # Component-specific options
        "files_created": List[str],    # Created files and directories
        "registry_entries": List[str], # Windows registry modifications
        "services_created": List[str], # Windows services installed
        "drivers_installed": List[str] # Device drivers installed
    }
}
```

### Config (`src/misc/Config.py`)

Download and configuration management for all components.

#### Class: `Config`

```python
class Config:
    def __init__(self, system_requests: SystemRequests):
        """
        Initialize configuration manager.
        
        Args:
            system_requests (SystemRequests): System operations manager
        """
```

**Component Installation Methods:**

```python
def install_sunshine(self, custom_options: dict = None) -> bool:
    """
    Install Sunshine streaming server.
    
    Args:
        custom_options (dict): Custom installation parameters
        
    Returns:
        bool: Installation success status
    """

def install_vdd(self, custom_options: dict = None) -> bool:
    """
    Install Virtual Display Driver.
    
    Args:
        custom_options (dict): VDD configuration options
        
    Returns:
        bool: Installation success status
    """

def install_sunshine_virtual_monitor(self, custom_options: dict = None) -> bool:
    """
    Install Sunshine Virtual Monitor tools.
    
    Args:
        custom_options (dict): SVM configuration
        
    Returns:
        bool: Installation success status
    """

def install_playnite(self, custom_options: dict = None) -> bool:
    """
    Install Playnite game library manager.
    
    Args:
        custom_options (dict): Playnite settings
        
    Returns:
        bool: Installation success status
    """
```

### Uninstaller (`src/misc/Uninstaller.py`)

Complete removal system for all installed components.

#### Class: `SunshineAIOUninstaller`

```python
class SunshineAIOUninstaller:
    def __init__(self, system_requests: SystemRequests):
        """
        Initialize uninstaller with system access.
        
        Args:
            system_requests (SystemRequests): System operations manager
        """
        
    def uninstall_component(self, component_key: str) -> bool:
        """
        Uninstall specific component completely.
        
        Args:
            component_key (str): Component identifier
            
        Returns:
            bool: Uninstallation success status
        """
        
    def uninstall_all_components(self) -> dict:
        """
        Remove all tracked components.
        
        Returns:
            dict: Uninstallation results per component
        """
        
    def get_uninstallation_preview(self) -> dict:
        """
        Preview what will be removed without executing.
        
        Returns:
            dict: Files, services, and registry entries to remove
        """
```

## 🎨 GUI Framework

### Main Window (`src/gui/main_window.py`)

Primary GUI application window using CustomTkinter.

#### Class: `MainWindow`

```python
class MainWindow(ctk.CTk):
    def __init__(self):
        """Initialize main application window with modern UI."""
        
    def show_page(self, page_name: str):
        """
        Navigate to specific page.
        
        Args:
            page_name (str): Page identifier
        """
        
    def update_progress(self, progress: float, message: str):
        """
        Update installation progress display.
        
        Args:
            progress (float): Progress percentage (0-100)
            message (str): Status message
        """
```

### Menu Adapter (`src/gui/adapters/menu_adapter.py`)

Business logic adapter connecting GUI to core functionality.

#### Class: `MenuAdapter`

```python
class MenuAdapter:
    def __init__(self, base_path: str):
        """
        Initialize adapter with project path.
        
        Args:
            base_path (str): Project base directory
        """
        
    def install_selected_components(self, components: List[str], 
                                  progress_callback: callable = None) -> dict:
        """
        Install multiple components with progress tracking.
        
        Args:
            components (List[str]): Component identifiers to install
            progress_callback (callable): Progress update function
            
        Returns:
            dict: Installation results per component
        """
        
    def get_component_status(self) -> dict:
        """
        Get installation status of all components.
        
        Returns:
            dict: Component status information
        """
```

## 🔌 Extension Points

### Adding New Components

#### Step 1: Create Component Installer

```python
class MyComponentInstaller:
    def __init__(self, system_requests: SystemRequests, tracker: InstallationTracker):
        self.sr = system_requests
        self.tracker = tracker
        
    def install(self, custom_options: dict = None) -> bool:
        """Component-specific installation logic."""
        # 1. Download component files
        # 2. Execute installation
        # 3. Configure component  
        # 4. Track installation details
        # 5. Return success status
        pass
        
    def verify_installation(self) -> bool:
        """Verify component was installed correctly."""
        pass
```

#### Step 2: Register Component

```python
# In Config.py
COMPONENTS_REGISTRY = {
    "my_component": {
        "name": "My Component",
        "installer_class": MyComponentInstaller,
        "dependencies": ["sunshine"],  # Optional dependencies
        "optional": True,              # Required vs optional
        "description": "Component description"
    }
}
```

#### Step 3: Add to GUI

```python
# In install_page.py
def _create_component_checkboxes(self):
    # Add checkbox for new component
    self.component_checkboxes["my_component"] = ctk.CTkCheckBox(
        self, text="My Component", 
        variable=self.component_vars["my_component"]
    )
```

### Custom Configuration Options

```python
# Component-specific options schema
COMPONENT_OPTIONS_SCHEMA = {
    "sunshine": {
        "port": int,                    # Custom port number
        "resolution": str,              # Default resolution
        "bitrate": int,                 # Default bitrate
        "enable_hdr": bool             # HDR support
    },
    "vdd": {
        "resolution": str,              # Virtual display resolution
        "refresh_rate": int,           # Display refresh rate
        "hdr_support": bool            # HDR capability
    }
}
```

## 🧪 Testing Framework

### Unit Tests

```python
import unittest
from unittest.mock import Mock, patch
from src.misc.Config import Config

class TestConfig(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.mock_sr = Mock()
        self.config = Config(self.mock_sr)
        
    def test_sunshine_installation(self):
        """Test Sunshine installation process."""
        # Mock successful installation
        self.mock_sr.download_file.return_value = True
        self.mock_sr.execute_command.return_value = (True, "Success", "")
        
        result = self.config.install_sunshine()
        self.assertTrue(result)
        
    @patch('src.misc.Config.os.path.exists')
    def test_installation_verification(self, mock_exists):
        """Test installation verification."""
        mock_exists.return_value = True
        
        result = self.config._verify_sunshine_installation()
        self.assertTrue(result)
```

### Integration Tests

```python
class TestInstallationFlow(unittest.TestCase):
    def test_complete_installation_flow(self):
        """Test complete installation workflow."""
        # Test component selection
        # Test download process
        # Test installation execution
        # Test tracking updates
        # Test verification
        pass
        
    def test_uninstallation_flow(self):
        """Test complete uninstallation workflow."""
        # Test component detection
        # Test removal process
        # Test cleanup verification
        pass
```

## 🔒 Security Considerations

### Input Validation

```python
def validate_url(url: str) -> bool:
    """
    Validate download URLs against whitelist.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: URL is safe to use
    """
    ALLOWED_DOMAINS = [
        'github.com',
        'releases.github.com', 
        'api.github.com'
    ]
    
    parsed = urlparse(url)
    return parsed.netloc in ALLOWED_DOMAINS and parsed.scheme == 'https'

def sanitize_path(path: str) -> str:
    """
    Sanitize file paths to prevent directory traversal.
    
    Args:
        path (str): File path to sanitize
        
    Returns:
        str: Safe file path
    """
    return os.path.abspath(os.path.normpath(path))
```

### Privilege Management

```python
def requires_admin(func):
    """Decorator to ensure function runs with admin privileges."""
    def wrapper(*args, **kwargs):
        if not is_admin():
            raise PermissionError("Administrator privileges required")
        return func(*args, **kwargs)
    return wrapper

@requires_admin
def install_driver(driver_path: str) -> bool:
    """Install device driver (requires admin)."""
    pass
```

## 📊 Error Handling

### Exception Hierarchy

```python
class SunshineAIOException(Exception):
    """Base exception for all Sunshine-AIO errors."""
    pass

class InstallationError(SunshineAIOException):
    """Raised when component installation fails."""
    pass

class DownloadError(SunshineAIOException):
    """Raised when file download fails."""
    pass

class ConfigurationError(SunshineAIOException):
    """Raised when configuration is invalid."""
    pass
```

### Error Handling Patterns

```python
def safe_install_component(component: str) -> tuple:
    """
    Safely install component with comprehensive error handling.
    
    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        result = install_component(component)
        return (True, "")
    except DownloadError as e:
        log_error(f"Download failed: {e}")
        return (False, f"Failed to download {component}: {e}")
    except InstallationError as e:
        log_error(f"Installation failed: {e}")
        return (False, f"Failed to install {component}: {e}")
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        return (False, f"Unexpected error installing {component}: {e}")
```

## 🔧 Configuration Files

### Application Configuration

```json
{
  "version": "0.3.2",
  "components": {
    "sunshine": {
      "required": true,
      "download_url": "https://github.com/LizardByte/Sunshine/releases/latest",
      "installer_args": "/S /D={install_dir}"
    },
    "vdd": {
      "required": false,
      "download_url": "https://github.com/itsmikethetech/Virtual-Display-Driver/releases/latest"
    }
  },
  "defaults": {
    "install_location": "C:\\Program Files\\Sunshine-AIO",
    "create_shortcuts": true,
    "add_to_startup": false
  }
}
```

### User Configuration Override

```json
{
  "sunshine": {
    "port": 47990,
    "resolution": "1920x1080",
    "bitrate": 20000
  },
  "gui": {
    "theme": "dark",
    "auto_start_installation": false
  }
}
```

---

*For implementation examples and advanced usage, see the [Architecture Overview](Architecture-Overview) and [Development Setup](Development-Setup) guides.*