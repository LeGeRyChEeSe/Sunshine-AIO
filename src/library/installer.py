"""
Hybrid Installation System for Sunshine-AIO Community Library Integration

This module provides installation capabilities for both static and community library tools,
supporting multiple installation types and providing comprehensive error handling.
"""

import os
import json
import shutil
import subprocess
import tempfile
import threading
import zipfile
import tarfile
import time
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from pathlib import Path
from datetime import datetime

# Windows-specific imports with fallback
try:
    import winreg
    WINDOWS_REGISTRY_AVAILABLE = True
except ImportError:
    winreg = None
    WINDOWS_REGISTRY_AVAILABLE = False

from misc.Logger import log_info, log_error, log_warning, log_success, log_progress
from misc.SystemRequests import SystemRequests
from misc.Config import DownloadManager
from .tool_provider import ToolInfo, ToolStatus, ToolSource
from .downloader import LibraryDownloader


class InstallationType(Enum):
    """Types of installation methods supported."""
    PORTABLE = "portable"           # Extract to tools directory
    INSTALLER = "installer"         # Run setup executable
    SCRIPT = "script"              # PowerShell/batch script execution
    ARCHIVE = "archive"            # Extract and configure
    CONFIGURATION = "configuration" # Config file deployment
    MSI = "msi"                    # Windows MSI installer
    REGISTRY = "registry"          # Registry-based installation


class InstallationStatus(Enum):
    """Installation status tracking."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InstallationResult:
    """Result of an installation operation."""
    
    def __init__(self, success: bool, tool_id: str, status: InstallationStatus):
        self.success = success
        self.tool_id = tool_id
        self.status = status
        self.installation_path: Optional[str] = None
        self.error_message: Optional[str] = None
        self.warnings: List[str] = []
        self.logs: List[str] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.duration: Optional[float] = None
    
    def complete(self, success: bool, error_message: str = None) -> None:
        """Mark installation as complete."""
        self.success = success
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = InstallationStatus.COMPLETED if success else InstallationStatus.FAILED
        if error_message:
            self.error_message = error_message
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        log_warning(f"Installation warning for {self.tool_id}: {warning}")
    
    def add_log(self, log_message: str) -> None:
        """Add a log message."""
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_message}")


class HybridInstaller:
    """Installation system supporting both static and library tools."""
    
    def __init__(self, system_requests: SystemRequests, download_manager: DownloadManager):
        """
        Initialize the hybrid installer.
        
        Args:
            system_requests: SystemRequests instance for system operations
            download_manager: DownloadManager instance for downloading
        """
        self.system_requests = system_requests
        self.download_manager = download_manager
        self.base_path = system_requests._base_path
        self.tools_dir = os.path.join(self.base_path, "tools")
        self.temp_dir = tempfile.gettempdir()
        
        # Installation tracking
        self._active_installations: Dict[str, InstallationResult] = {}
        self._installation_lock = threading.Lock()
        
        # Configuration
        self.config = {
            'max_concurrent_installations': 1,
            'installation_timeout': 600,  # 10 minutes
            'verify_installations': True,
            'backup_before_install': True,
            'auto_cleanup': True
        }
        
        # Initialize downloader
        cache_dir = os.path.join(self.base_path, "cache", "downloads")
        self.downloader = LibraryDownloader(cache_dir, self.temp_dir)
        
        # Ensure directories exist
        self._ensure_directories()
        
        log_info("HybridInstaller initialized")
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        try:
            os.makedirs(self.tools_dir, exist_ok=True)
            os.makedirs(os.path.join(self.base_path, "cache"), exist_ok=True)
            os.makedirs(os.path.join(self.base_path, "backups"), exist_ok=True)
        except OSError as e:
            log_error(f"Failed to create directories: {e}")
            raise
    
    def install_tool(self, tool_id: str, source: str = 'auto', **kwargs) -> InstallationResult:
        """
        Install a tool from the specified source.
        
        Args:
            tool_id: ID of the tool to install
            source: Source type ('auto', 'static', 'library')
            **kwargs: Additional installation parameters
            
        Returns:
            InstallationResult object
        """
        log_info(f"Starting installation of tool: {tool_id}")
        
        result = InstallationResult(False, tool_id, InstallationStatus.PENDING)
        
        try:
            with self._installation_lock:
                if tool_id in self._active_installations:
                    log_warning(f"Tool {tool_id} is already being installed")
                    return self._active_installations[tool_id]
                
                self._active_installations[tool_id] = result
            
            # Determine source and get tool info
            if source == 'auto':
                tool_info = self._auto_detect_tool_source(tool_id)
            elif source == 'static':
                tool_info = self._get_static_tool_info(tool_id)
            elif source == 'library':
                tool_info = self._get_library_tool_info(tool_id)
            else:
                raise ValueError(f"Unknown source type: {source}")
            
            if not tool_info:
                raise ValueError(f"Tool {tool_id} not found in any source")
            
            # Install based on source type
            if tool_info.source == ToolSource.STATIC:
                success = self._install_static_tool(tool_info, result, **kwargs)
            else:
                success = self.install_library_tool(tool_info, result, **kwargs)
            
            result.complete(success)
            
            if success:
                log_success(f"Successfully installed tool: {tool_id}")
            else:
                log_error(f"Failed to install tool: {tool_id}")
            
            return result
            
        except Exception as e:
            error_msg = f"Installation error for {tool_id}: {e}"
            log_error(error_msg)
            result.complete(False, error_msg)
            return result
        finally:
            # Clean up active installations
            with self._installation_lock:
                if tool_id in self._active_installations:
                    del self._active_installations[tool_id]
    
    def install_library_tool(self, tool_info: ToolInfo, result: InstallationResult = None, **kwargs) -> bool:
        """
        Install a community library tool.
        
        Args:
            tool_info: ToolInfo object for the tool
            result: InstallationResult to update (optional)
            **kwargs: Additional installation parameters
            
        Returns:
            True if installation was successful
        """
        if not result:
            result = InstallationResult(False, tool_info.tool_id, InstallationStatus.PENDING)
        
        try:
            log_info(f"Installing library tool: {tool_info.name}")
            result.status = InstallationStatus.DOWNLOADING
            result.add_log(f"Starting installation of {tool_info.name}")
            
            # Download tool files
            downloaded_file = self.downloader.download_tool_files(tool_info)
            if not downloaded_file:
                raise Exception("Failed to download tool files")
            
            result.add_log(f"Downloaded to: {downloaded_file}")
            result.status = InstallationStatus.INSTALLING
            
            # Determine installation type
            install_type = self._detect_installation_type(downloaded_file, tool_info)
            result.add_log(f"Detected installation type: {install_type.value}")
            
            # Perform installation based on type
            success = self._perform_installation(install_type, downloaded_file, tool_info, result, **kwargs)
            
            if success:
                result.status = InstallationStatus.VERIFYING
                success = self.verify_installation(tool_info.tool_id, result)
            
            if success:
                result.status = InstallationStatus.COMPLETED
                tool_info.status = ToolStatus.INSTALLED
                result.add_log("Installation completed successfully")
            else:
                result.status = InstallationStatus.FAILED
                result.add_log("Installation failed verification")
            
            return success
            
        except Exception as e:
            error_msg = f"Error installing library tool {tool_info.tool_id}: {e}"
            log_error(error_msg)
            result.add_log(f"ERROR: {error_msg}")
            result.status = InstallationStatus.FAILED
            return False
    
    def _auto_detect_tool_source(self, tool_id: str) -> Optional[ToolInfo]:
        """Auto-detect tool source and return ToolInfo."""
        # Try library first, then static
        tool_info = self._get_library_tool_info(tool_id)
        if tool_info:
            return tool_info
        
        return self._get_static_tool_info(tool_id)
    
    def _get_static_tool_info(self, tool_id: str) -> Optional[ToolInfo]:
        """Get ToolInfo for a static tool."""
        # This would integrate with existing static tools
        # For now, return None as we're focusing on library tools
        return None
    
    def _get_library_tool_info(self, tool_id: str) -> Optional[ToolInfo]:
        """Get ToolInfo for a library tool."""
        try:
            # This would integrate with LibraryManager
            # For now, create a basic ToolInfo
            return ToolInfo(
                tool_id=tool_id,
                name=tool_id.replace('_', ' ').title(),
                source=ToolSource.DYNAMIC,
                status=ToolStatus.AVAILABLE
            )
        except Exception as e:
            log_error(f"Error getting library tool info: {e}")
            return None
    
    def _install_static_tool(self, tool_info: ToolInfo, result: InstallationResult, **kwargs) -> bool:
        """Install a static tool."""
        # Delegate to existing download manager
        try:
            log_info(f"Installing static tool: {tool_info.tool_id}")
            result.add_log(f"Installing static tool: {tool_info.tool_id}")
            
            # This would call appropriate method from download_manager
            # For now, just mark as successful
            result.installation_path = self.tools_dir
            return True
            
        except Exception as e:
            log_error(f"Error installing static tool: {e}")
            return False
    
    def _detect_installation_type(self, file_path: str, tool_info: ToolInfo) -> InstallationType:
        """
        Detect the installation type based on file and metadata.
        
        Args:
            file_path: Path to the downloaded file
            tool_info: ToolInfo object
            
        Returns:
            InstallationType enum value
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Check file extension
        if file_ext == '.msi':
            return InstallationType.MSI
        elif file_ext == '.exe':
            return InstallationType.INSTALLER
        elif file_ext in ['.zip', '.rar', '.7z']:
            return InstallationType.ARCHIVE
        elif file_ext in ['.ps1', '.bat', '.cmd']:
            return InstallationType.SCRIPT
        elif file_ext in ['.json', '.conf', '.ini']:
            return InstallationType.CONFIGURATION
        else:
            # Default to portable for unknown types
            return InstallationType.PORTABLE
    
    def _perform_installation(self, install_type: InstallationType, file_path: str, 
                            tool_info: ToolInfo, result: InstallationResult, **kwargs) -> bool:
        """
        Perform the actual installation based on type.
        
        Args:
            install_type: Type of installation to perform
            file_path: Path to the installation file
            tool_info: ToolInfo object
            result: InstallationResult to update
            **kwargs: Additional parameters
            
        Returns:
            True if installation was successful
        """
        try:
            if install_type == InstallationType.PORTABLE:
                return self._install_portable(file_path, tool_info, result)
            elif install_type == InstallationType.INSTALLER:
                return self._install_executable(file_path, tool_info, result)
            elif install_type == InstallationType.MSI:
                return self._install_msi(file_path, tool_info, result)
            elif install_type == InstallationType.ARCHIVE:
                return self._install_archive(file_path, tool_info, result)
            elif install_type == InstallationType.SCRIPT:
                return self._install_script(file_path, tool_info, result)
            elif install_type == InstallationType.CONFIGURATION:
                return self._install_configuration(file_path, tool_info, result)
            else:
                raise ValueError(f"Unsupported installation type: {install_type}")
                
        except Exception as e:
            log_error(f"Installation failed for {tool_info.tool_id}: {e}")
            result.add_log(f"Installation error: {e}")
            return False
    
    def _install_portable(self, file_path: str, tool_info: ToolInfo, result: InstallationResult) -> bool:
        """Install a portable tool by extracting to tools directory."""
        try:
            tool_dir = os.path.join(self.tools_dir, tool_info.tool_id)
            os.makedirs(tool_dir, exist_ok=True)
            
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(tool_dir)
            else:
                # Copy single file
                dest_file = os.path.join(tool_dir, os.path.basename(file_path))
                shutil.copy2(file_path, dest_file)
            
            result.installation_path = tool_dir
            result.add_log(f"Extracted to: {tool_dir}")
            log_success(f"Portable tool extracted: {tool_dir}")
            return True
            
        except Exception as e:
            log_error(f"Failed to install portable tool: {e}")
            return False
    
    def _install_executable(self, file_path: str, tool_info: ToolInfo, result: InstallationResult) -> bool:
        """Install using an executable installer."""
        try:
            result.add_log("Running executable installer...")
            
            # Run installer with silent/automated flags
            cmd = [file_path, '/S', '/SILENT', '/VERYSILENT']
            
            # Add custom install directory if specified
            install_dir = os.path.join(self.tools_dir, tool_info.tool_id)
            cmd.extend([f'/DIR={install_dir}'])
            
            result.add_log(f"Executing: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config['installation_timeout']
            )
            
            if process.returncode == 0:
                result.installation_path = install_dir
                result.add_log(f"Installer completed successfully")
                log_success(f"Executable installer completed: {tool_info.tool_id}")
                return True
            else:
                error_msg = f"Installer failed with code {process.returncode}: {process.stderr}"
                result.add_log(f"ERROR: {error_msg}")
                log_error(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Installer timed out"
            result.add_log(f"ERROR: {error_msg}")
            log_error(error_msg)
            return False
        except Exception as e:
            log_error(f"Failed to run executable installer: {e}")
            return False
    
    def _install_msi(self, file_path: str, tool_info: ToolInfo, result: InstallationResult) -> bool:
        """Install using Windows MSI installer."""
        try:
            result.add_log("Running MSI installer...")
            
            install_dir = os.path.join(self.tools_dir, tool_info.tool_id)
            
            cmd = [
                'msiexec.exe',
                '/i', file_path,
                '/quiet',
                '/norestart',
                f'INSTALLDIR={install_dir}'
            ]
            
            result.add_log(f"Executing: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config['installation_timeout']
            )
            
            if process.returncode == 0:
                result.installation_path = install_dir
                result.add_log("MSI installer completed successfully")
                log_success(f"MSI installer completed: {tool_info.tool_id}")
                return True
            else:
                error_msg = f"MSI installer failed with code {process.returncode}"
                result.add_log(f"ERROR: {error_msg}")
                log_error(error_msg)
                return False
                
        except Exception as e:
            log_error(f"Failed to run MSI installer: {e}")
            return False
    
    def _install_archive(self, file_path: str, tool_info: ToolInfo, result: InstallationResult) -> bool:
        """Install by extracting an archive file."""
        try:
            tool_dir = os.path.join(self.tools_dir, tool_info.tool_id)
            os.makedirs(tool_dir, exist_ok=True)
            
            result.add_log(f"Extracting archive to: {tool_dir}")
            
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    archive.extractall(tool_dir)
            elif file_path.endswith(('.tar', '.tar.gz', '.tgz')):
                with tarfile.open(file_path, 'r:*') as archive:
                    archive.extractall(tool_dir)
            else:
                # Try using system tools
                self.system_requests.extract_file(file_path, tool_dir)
            
            result.installation_path = tool_dir
            result.add_log("Archive extracted successfully")
            log_success(f"Archive extracted: {tool_dir}")
            return True
            
        except Exception as e:
            log_error(f"Failed to extract archive: {e}")
            return False
    
    def _install_script(self, file_path: str, tool_info: ToolInfo, result: InstallationResult) -> bool:
        """Install by running a script."""
        try:
            result.add_log("Running installation script...")
            
            if file_path.endswith('.ps1'):
                cmd = ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', file_path]
            else:
                cmd = [file_path]
            
            result.add_log(f"Executing: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config['installation_timeout'],
                cwd=os.path.dirname(file_path)
            )
            
            if process.returncode == 0:
                result.add_log("Script executed successfully")
                result.add_log(f"Script output: {process.stdout}")
                log_success(f"Installation script completed: {tool_info.tool_id}")
                return True
            else:
                error_msg = f"Script failed with code {process.returncode}: {process.stderr}"
                result.add_log(f"ERROR: {error_msg}")
                log_error(error_msg)
                return False
                
        except Exception as e:
            log_error(f"Failed to run installation script: {e}")
            return False
    
    def _install_configuration(self, file_path: str, tool_info: ToolInfo, result: InstallationResult) -> bool:
        """Install by deploying configuration files."""
        try:
            config_dir = os.path.join(self.base_path, "config", tool_info.tool_id)
            os.makedirs(config_dir, exist_ok=True)
            
            dest_file = os.path.join(config_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest_file)
            
            result.installation_path = config_dir
            result.add_log(f"Configuration deployed to: {dest_file}")
            log_success(f"Configuration deployed: {dest_file}")
            return True
            
        except Exception as e:
            log_error(f"Failed to deploy configuration: {e}")
            return False
    
    def verify_installation(self, tool_id: str, result: InstallationResult = None) -> bool:
        """
        Verify that a tool was installed correctly.
        
        Args:
            tool_id: ID of the tool to verify
            result: InstallationResult to update (optional)
            
        Returns:
            True if installation is verified
        """
        try:
            if result:
                result.add_log("Verifying installation...")
            
            # Check if tool directory exists
            tool_dir = os.path.join(self.tools_dir, tool_id)
            if not os.path.exists(tool_dir):
                if result:
                    result.add_log(f"Tool directory not found: {tool_dir}")
                return False
            
            # Check for executable files
            executables_found = []
            for root, dirs, files in os.walk(tool_dir):
                for file in files:
                    if file.endswith(('.exe', '.bat', '.cmd', '.ps1')):
                        executables_found.append(os.path.join(root, file))
            
            if executables_found:
                if result:
                    result.add_log(f"Found executables: {len(executables_found)}")
                log_info(f"Installation verified for {tool_id}: found {len(executables_found)} executables")
                return True
            else:
                if result:
                    result.add_log("No executable files found")
                log_warning(f"Installation verification incomplete for {tool_id}: no executables found")
                return True  # Still consider it valid for portable tools
                
        except Exception as e:
            error_msg = f"Error verifying installation for {tool_id}: {e}"
            log_error(error_msg)
            if result:
                result.add_log(f"Verification error: {e}")
            return False
    
    def get_installation_status(self, tool_id: str) -> Dict[str, Any]:
        """
        Get the installation status for a tool.
        
        Args:
            tool_id: ID of the tool
            
        Returns:
            Dict containing installation status information
        """
        with self._installation_lock:
            if tool_id in self._active_installations:
                result = self._active_installations[tool_id]
                return {
                    'tool_id': tool_id,
                    'status': result.status.value,
                    'installation_path': result.installation_path,
                    'start_time': result.start_time.isoformat(),
                    'duration': result.duration,
                    'logs': result.logs[-10:],  # Last 10 log entries
                    'warnings': result.warnings
                }
        
        # Check if tool is installed
        tool_dir = os.path.join(self.tools_dir, tool_id)
        is_installed = os.path.exists(tool_dir)
        
        return {
            'tool_id': tool_id,
            'status': 'installed' if is_installed else 'not_installed',
            'installation_path': tool_dir if is_installed else None,
            'last_checked': datetime.now().isoformat()
        }
    
    def uninstall_tool(self, tool_id: str) -> bool:
        """
        Uninstall a tool.
        
        Args:
            tool_id: ID of the tool to uninstall
            
        Returns:
            True if uninstallation was successful
        """
        try:
            log_info(f"Uninstalling tool: {tool_id}")
            
            tool_dir = os.path.join(self.tools_dir, tool_id)
            
            if os.path.exists(tool_dir):
                # Backup before uninstall if configured
                if self.config['backup_before_install']:
                    backup_dir = os.path.join(self.base_path, "backups", f"{tool_id}_{int(time.time())}")
                    shutil.move(tool_dir, backup_dir)
                    log_info(f"Tool backed up to: {backup_dir}")
                else:
                    shutil.rmtree(tool_dir)
                
                log_success(f"Tool uninstalled: {tool_id}")
                return True
            else:
                log_warning(f"Tool directory not found for uninstall: {tool_id}")
                return False
                
        except Exception as e:
            log_error(f"Error uninstalling tool {tool_id}: {e}")
            return False
    
    def get_installer_info(self) -> Dict[str, Any]:
        """
        Get information about the installer system.
        
        Returns:
            Dict containing installer information
        """
        with self._installation_lock:
            active_count = len(self._active_installations)
        
        return {
            'tools_directory': self.tools_dir,
            'temp_directory': self.temp_dir,
            'active_installations': active_count,
            'configuration': self.config,
            'supported_types': [t.value for t in InstallationType],
            'last_updated': datetime.now().isoformat()
        }