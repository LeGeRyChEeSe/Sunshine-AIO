import json
import os
import winreg
from typing import Dict, List, Optional, Any
from datetime import datetime
from misc.Logger import log_info, log_warning, log_error, log_success


class InstallationTracker:
    """
    Installation tracker system to monitor and save installation paths
    for proper uninstallation later
    """
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.tracker_file = os.path.join(base_path, "misc", "variables", "installation_tracker.json")
        self.installations = self._load_installations()
        
        # Default installation paths for each tool
        self.default_paths = {
            "sunshine": {
                "default_install_dir": "C:\\Program Files\\Sunshine",
                "default_data_dir": os.path.expandvars("%APPDATA%\\Sunshine"),
                "service_name": "SunshineService",
                "registry_keys": [
                    "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Sunshine",
                    "HKEY_LOCAL_MACHINE\\System\\CurrentControlSet\\Services\\SunshineService"
                ],
                "executables": ["sunshine.exe", "Uninstall.exe"],
                "config_files": ["config.json", "apps.json"]
            },
            "virtual_display_driver": {
                "default_install_dir": "C:\\IddSampleDriver",
                "driver_name": "IddSampleDriver",
                "device_manager_name": "IddSampleDriver",
                "registry_keys": [
                    "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\WUDF\\Services\\ParsecVDA\\Parameters"
                ],
                "files": ["iddsampledriver.inf", "option.txt"],
                "driver_store_pattern": "oem*.inf"
            },
            "sunshine_virtual_monitor": {
                "default_install_dir": os.path.join(base_path, "tools", "Sunshine Virtual Monitor"),
                "scripts": ["enable_monitor.bat", "disable_monitor.bat", "install.bat", "uninstall.bat"],
                "config_files": ["config.json"],
                "dependencies": ["virtual_display_driver"]
            },
            "playnite": {
                "default_install_dir": "C:\\Program Files\\Playnite",
                "alternative_install_dir": os.path.expandvars("%LOCALAPPDATA%\\Playnite"),
                "data_dir": os.path.expandvars("%APPDATA%\\Playnite"),
                "registry_keys": [
                    "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Playnite"
                ],
                "executables": ["Playnite.DesktopApp.exe", "Playnite.FullscreenApp.exe", "unins000.exe"],
                "config_files": ["config.json", "library\\games.db"]
            },
            "playnite_watcher": {
                "default_install_dir": os.path.join(base_path, "tools", "Playnite Watcher"),
                "executables": ["PlayniteWatcher.exe"],
                "config_files": ["config.json"],
                "dependencies": ["playnite"]
            },
            "multi_monitor_tool": {
                "default_install_dir": os.path.join(base_path, "tools", "MultiMonitorTool"),
                "executables": ["MultiMonitorTool.exe"],
                "config_files": ["MultiMonitorTool.cfg"]
            },
            "vsync_toggle": {
                "default_install_dir": os.path.join(base_path, "tools", "VSync Toggle"),
                "executables": ["VSync Toggle.exe"],
                "config_files": ["settings.json"]
            }
        }
    
    def _load_installations(self) -> Dict[str, Any]:
        """Load installation tracking data from file"""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                log_warning(f"Failed to load installation tracker: {e}")
                return {}
        return {}
    
    def _save_installations(self) -> bool:
        """Save installation tracking data to file"""
        try:
            os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
            with open(self.tracker_file, 'w', encoding='utf-8') as f:
                json.dump(self.installations, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            log_error(f"Failed to save installation tracker: {e}")
            return False
    
    def track_installation(self, tool_name: str, install_path: str, additional_info: Dict[str, Any] = None) -> bool:
        """Track a new installation with custom path and additional information"""
        try:
            if tool_name not in self.installations:
                self.installations[tool_name] = {}
            
            installation_data = {
                "install_path": install_path,
                "install_date": datetime.now().isoformat(),
                "version": additional_info.get("version", "unknown") if additional_info else "unknown",
                "installer_type": additional_info.get("installer_type", "manual") if additional_info else "manual",
                "custom_options": additional_info.get("custom_options", {}) if additional_info else {},
                "files_created": additional_info.get("files_created", []) if additional_info else [],
                "registry_entries": additional_info.get("registry_entries", []) if additional_info else [],
                "services_created": additional_info.get("services_created", []) if additional_info else [],
                "drivers_installed": additional_info.get("drivers_installed", []) if additional_info else []
            }
            
            self.installations[tool_name] = installation_data
            return self._save_installations()
            
        except Exception as e:
            log_error(f"Failed to track installation for {tool_name}: {e}")
            return False
    
    def get_installation_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get installation information for a specific tool"""
        return self.installations.get(tool_name)
    
    def get_install_path(self, tool_name: str) -> Optional[str]:
        """Get the installation path for a specific tool"""
        info = self.get_installation_info(tool_name)
        if info:
            return info.get("install_path")
        
        # Fallback to default path
        if tool_name in self.default_paths:
            return self.default_paths[tool_name].get("default_install_dir")
        
        return None
    
    def get_all_installation_paths(self, tool_name: str) -> List[str]:
        """Get all possible installation paths for a tool (custom + defaults)"""
        paths = []
        
        # Add tracked custom path
        custom_path = self.get_install_path(tool_name)
        if custom_path and os.path.exists(custom_path):
            paths.append(custom_path)
        
        # Add default paths
        if tool_name in self.default_paths:
            default_info = self.default_paths[tool_name]
            
            # Main default path
            default_path = default_info.get("default_install_dir")
            if default_path and default_path not in paths and os.path.exists(default_path):
                paths.append(default_path)
            
            # Alternative path (for tools like Playnite)
            alt_path = default_info.get("alternative_install_dir")
            if alt_path and alt_path not in paths and os.path.exists(alt_path):
                paths.append(alt_path)
        
        return paths
    
    def get_registry_keys(self, tool_name: str) -> List[str]:
        """Get registry keys to check/clean for a specific tool"""
        keys = []
        
        # Custom registry entries
        info = self.get_installation_info(tool_name)
        if info and "registry_entries" in info:
            keys.extend(info["registry_entries"])
        
        # Default registry keys
        if tool_name in self.default_paths:
            default_keys = self.default_paths[tool_name].get("registry_keys", [])
            keys.extend([key for key in default_keys if key not in keys])
        
        return keys
    
    def get_files_to_remove(self, tool_name: str) -> List[str]:
        """Get list of files/directories to remove for a tool"""
        files = []
        
        # Custom files
        info = self.get_installation_info(tool_name)
        if info and "files_created" in info:
            files.extend(info["files_created"])
        
        # Files in installation directories
        for install_path in self.get_all_installation_paths(tool_name):
            if os.path.exists(install_path):
                files.append(install_path)
        
        # Data directories
        if tool_name in self.default_paths:
            default_info = self.default_paths[tool_name]
            data_dir = default_info.get("data_dir")
            if data_dir and os.path.exists(data_dir):
                files.append(data_dir)
        
        return files
    
    def get_services_to_remove(self, tool_name: str) -> List[str]:
        """Get list of Windows services to remove for a tool"""
        services = []
        
        # Custom services
        info = self.get_installation_info(tool_name)
        if info and "services_created" in info:
            services.extend(info["services_created"])
        
        # Default services
        if tool_name in self.default_paths:
            service_name = self.default_paths[tool_name].get("service_name")
            if service_name and service_name not in services:
                services.append(service_name)
        
        return services
    
    def get_drivers_to_remove(self, tool_name: str) -> List[str]:
        """Get list of drivers to remove for a tool"""
        drivers = []
        
        # Custom drivers
        info = self.get_installation_info(tool_name)
        if info and "drivers_installed" in info:
            drivers.extend(info["drivers_installed"])
        
        # Default drivers
        if tool_name in self.default_paths:
            driver_name = self.default_paths[tool_name].get("driver_name")
            if driver_name and driver_name not in drivers:
                drivers.append(driver_name)
        
        return drivers
    
    def remove_installation_tracking(self, tool_name: str) -> bool:
        """Remove installation tracking for a tool after successful uninstall"""
        try:
            if tool_name in self.installations:
                del self.installations[tool_name]
                return self._save_installations()
            return True
        except Exception as e:
            log_error(f"Failed to remove installation tracking for {tool_name}: {e}")
            return False
    
    def is_tool_installed(self, tool_name: str) -> bool:
        """Check if a tool is installed based on tracked info and default paths"""
        # Check tracked installation
        if tool_name in self.installations:
            install_path = self.installations[tool_name].get("install_path")
            if install_path and os.path.exists(install_path):
                return True
        
        # Check default paths
        for path in self.get_all_installation_paths(tool_name):
            if os.path.exists(path):
                return True
        
        # Check registry for certain tools
        registry_keys = self.get_registry_keys(tool_name)
        for key_path in registry_keys:
            if self._check_registry_key_exists(key_path):
                return True
        
        return False
    
    def _check_registry_key_exists(self, key_path: str) -> bool:
        """Check if a registry key exists"""
        try:
            # Parse registry key path
            if key_path.startswith("HKEY_LOCAL_MACHINE"):
                root = winreg.HKEY_LOCAL_MACHINE
                subkey = key_path.replace("HKEY_LOCAL_MACHINE\\", "")
            elif key_path.startswith("HKEY_CURRENT_USER"):
                root = winreg.HKEY_CURRENT_USER
                subkey = key_path.replace("HKEY_CURRENT_USER\\", "")
            else:
                return False
            
            with winreg.OpenKey(root, subkey):
                return True
        except (FileNotFoundError, OSError):
            return False
    
    def get_installation_report(self) -> str:
        """Generate a detailed installation report"""
        report = ["=== SUNSHINE-AIO INSTALLATION TRACKER REPORT ===\n"]
        
        if not self.installations:
            report.append("No custom installations tracked.\n")
        else:
            report.append("TRACKED INSTALLATIONS:")
            for tool_name, info in self.installations.items():
                report.append(f"\n• {tool_name.upper()}:")
                report.append(f"  Path: {info.get('install_path', 'Unknown')}")
                report.append(f"  Date: {info.get('install_date', 'Unknown')}")
                report.append(f"  Version: {info.get('version', 'Unknown')}")
                if info.get('custom_options'):
                    report.append(f"  Options: {info['custom_options']}")
        
        report.append("\nDETECTED INSTALLATIONS:")
        for tool_name in self.default_paths.keys():
            if self.is_tool_installed(tool_name):
                report.append(f"\n• {tool_name.upper()}: INSTALLED")
                paths = self.get_all_installation_paths(tool_name)
                for path in paths:
                    report.append(f"  - {path}")
            else:
                report.append(f"\n• {tool_name.upper()}: NOT DETECTED")
        
        return "\n".join(report)
    
    def update_installation_info(self, tool_name: str, key: str, value: Any) -> bool:
        """Update specific information for an installation"""
        try:
            if tool_name not in self.installations:
                self.installations[tool_name] = {}
            
            self.installations[tool_name][key] = value
            self.installations[tool_name]["last_updated"] = datetime.now().isoformat()
            
            return self._save_installations()
        except Exception as e:
            log_error(f"Failed to update installation info for {tool_name}: {e}")
            return False


# Global instance
installation_tracker = None

def get_installation_tracker(base_path: str = None) -> InstallationTracker:
    """Get global installation tracker instance"""
    global installation_tracker
    if installation_tracker is None and base_path:
        installation_tracker = InstallationTracker(base_path)
    return installation_tracker