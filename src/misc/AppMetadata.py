import os
import sys
import ctypes
from ctypes import wintypes
from typing import Optional


def get_version_from_init():
    """Get version dynamically from __init__.py"""
    try:
        # Try different possible paths to find __init__.py
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "__init__.py"),
            os.path.join(os.path.dirname(__file__), "__init__.py"),
            "__init__.py"
        ]
        
        for init_path in possible_paths:
            abs_path = os.path.abspath(init_path)
            if os.path.exists(abs_path):
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for __version__ = "something"
                    import re
                    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1)
        
        # If not found, try importing from misc module  
        try:
            from . import __version__
            return __version__
        except ImportError:
            pass
            
        # Last resort - try importing from parent module
        try:
            import misc
            return getattr(misc, '__version__', 'v0.3.0')
        except ImportError:
            pass
            
    except Exception:
        pass
    
    # Fallback version
    return "v0.3.0"


class AppMetadata:
    """
    Application metadata and branding management for Sunshine-AIO
    """
    
    APP_NAME = "Sunshine-AIO"
    APP_DESCRIPTION = "All-in-One Tool for Sunshine Game Streaming Setup"
    APP_AUTHOR = "Sunshine-AIO Team"
    APP_COPYRIGHT = "© 2024 Sunshine-AIO"
    
    @property
    def APP_VERSION(self):
        """Get version dynamically"""
        if not hasattr(self, '_cached_version'):
            self._cached_version = get_version_from_init()
        return self._cached_version
    
    def __init__(self):
        self.is_windows = os.name == 'nt'
        
    def set_console_title(self, title: Optional[str] = None) -> bool:
        """Set the console window title"""
        if not self.is_windows:
            return False
            
        try:
            if title is None:
                title = f"{self.APP_NAME} {self.APP_VERSION} - {self.APP_DESCRIPTION}"
            
            ctypes.windll.kernel32.SetConsoleTitleW(title)
            return True
        except Exception as e:
            print(f"Warning: Could not set console title: {e}")
            return False
    
    def _find_icon_path(self) -> Optional[str]:
        """Find the Sunshine-AIO icon file"""
        possible_paths = [
            "ressources/sunshine-aio.ico",  # From project root
            "../ressources/sunshine-aio.ico",  # From src directory
            "../../ressources/sunshine-aio.ico",  # From src/misc directory
            os.path.join(os.path.dirname(__file__), "../../ressources/sunshine-aio.ico"),
        ]
        
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                return abs_path
        
        return None
    
    def set_console_icon(self, icon_path: Optional[str] = None) -> bool:
        """Set the console window icon"""
        if not self.is_windows:
            return False
            
        try:
            # Get console window handle
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            
            console_window = kernel32.GetConsoleWindow()
            if not console_window:
                return False
            
            # Find icon path if not provided
            if icon_path is None:
                icon_path = self._find_icon_path()
            
            if icon_path and os.path.exists(icon_path):
                # Load icon from file
                hicon = user32.LoadImageW(
                    None, icon_path, 1, 0, 0, 
                    0x00000010 | 0x00008000  # LR_LOADFROMFILE | LR_SHARED
                )
                
                if hicon:
                    # Set both small and large icons
                    user32.SendMessageW(console_window, 0x0080, 0, hicon)  # WM_SETICON, ICON_SMALL
                    user32.SendMessageW(console_window, 0x0080, 1, hicon)  # WM_SETICON, ICON_LARGE
                    return True
            else:
                # Use default system icon as fallback
                hicon = user32.LoadIconW(None, 32512)  # IDI_APPLICATION
                if hicon:
                    user32.SendMessageW(console_window, 0x0080, 0, hicon)
                    user32.SendMessageW(console_window, 0x0080, 1, hicon)
                    return True
                
        except Exception as e:
            # Silently handle icon loading errors to avoid disrupting the application
            pass
            
        return False
    
    def get_process_description(self) -> str:
        """Get process description for UAC and task manager"""
        return f"{self.APP_NAME} - {self.APP_DESCRIPTION}"
    
    def setup_console_appearance(self, icon_path: Optional[str] = None) -> None:
        """Setup complete console appearance"""
        self.set_console_title()
        self.set_console_icon(icon_path)
        
        # Additional console setup
        if self.is_windows:
            try:
                # Enable ANSI color support on Windows 10+
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                mode = wintypes.DWORD()
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            except Exception:
                pass  # Ignore if not supported
    
    def create_application_manifest(self) -> str:
        """Create an application manifest for UAC customization"""
        manifest_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
    <assemblyIdentity
        version="{self.APP_VERSION.lstrip('v')}.0"
        processorArchitecture="*"
        name="{self.APP_NAME}"
        type="win32"
    />
    <description>{self.APP_DESCRIPTION}</description>
    
    <!-- Request administrator privileges -->
    <trustInfo xmlns="urn:schemas-microsoft-com:asm.v2">
        <security>
            <requestedPrivileges xmlns="urn:schemas-microsoft-com:asm.v3">
                <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
            </requestedPrivileges>
        </security>
    </trustInfo>
    
    <!-- Application compatibility -->
    <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
        <application>
            <!-- Windows 10 and Windows 11 -->
            <supportedOS Id="{{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}}"/>
            <!-- Windows 8.1 -->
            <supportedOS Id="{{1f676c76-80e1-4239-95bb-83d0f6d0da78}}"/>
            <!-- Windows 8 -->
            <supportedOS Id="{{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}}"/>
            <!-- Windows 7 -->
            <supportedOS Id="{{35138b9a-5d96-4fbd-8e2d-a2440225f93a}}"/>
        </application>
    </compatibility>
    
    <!-- DPI Awareness -->
    <application xmlns="urn:schemas-microsoft-com:asm.v3">
        <windowsSettings>
            <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>
            <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
        </windowsSettings>
    </application>
</assembly>'''
        
        return manifest_content
    
    def get_app_info(self) -> dict:
        """Get complete application information"""
        return {
            "name": self.APP_NAME,
            "description": self.APP_DESCRIPTION, 
            "version": self.APP_VERSION,
            "author": self.APP_AUTHOR,
            "copyright": self.APP_COPYRIGHT,
            "process_description": self.get_process_description()
        }


# Global instance
app_metadata = AppMetadata()


# Convenience functions
def setup_console() -> None:
    """Setup console appearance and branding"""
    app_metadata.setup_console_appearance()


def get_app_name() -> str:
    """Get application name"""
    return app_metadata.APP_NAME


def get_app_version() -> str:
    """Get application version dynamically"""
    return app_metadata.APP_VERSION


def get_app_description() -> str:
    """Get application description"""
    return app_metadata.APP_DESCRIPTION


def set_console_title(title: Optional[str] = None) -> bool:
    """Set console title"""
    return app_metadata.set_console_title(title)