"""
Menu Adapter for GUI Integration

This adapter provides a clean interface between the GUI and the existing
CLI-based business logic, allowing the GUI to use all existing functionality
without modifying the original code.
"""

import os
import sys
from typing import Optional, Callable, Any

# Add the parent directory to the path to import misc modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from misc.MenuHandler import MenuHandler
from misc.Config import Config, DownloadManager
from misc.SystemRequests import SystemRequests
from misc.Uninstaller import SunshineAIOUninstaller
from misc.InstallationTracker import get_installation_tracker


class MenuAdapter:
    """
    Adapter to interface GUI with existing CLI business logic.
    This class provides a clean API for the GUI while preserving all existing functionality.
    """
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        self._system_requests: Optional[SystemRequests] = None
        self._menu_handler: Optional[MenuHandler] = None
        self._config: Optional[Config] = None
        self._download_manager: Optional[DownloadManager] = None
        self._uninstaller: Optional[SunshineAIOUninstaller] = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all business logic components"""
        try:
            # Initialize SystemRequests (core system interface)
            self._system_requests = SystemRequests(self.base_path)
            
            # Initialize MenuHandler (main controller)
            self._menu_handler = MenuHandler(self.base_path)
            
            # Initialize Config and DownloadManager
            self._config = Config(self._system_requests)
            self._download_manager = DownloadManager(self._system_requests, 0)  # Start with page 0
            
            # Initialize Uninstaller (needs SystemRequests object, not base_path)
            self._uninstaller = SunshineAIOUninstaller(self._system_requests)
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize menu adapter: {e}")
    
    # Properties for accessing business logic components
    @property
    def system_requests(self) -> SystemRequests:
        return self._system_requests
    
    @property
    def menu_handler(self) -> MenuHandler:
        return self._menu_handler
    
    @property
    def config(self) -> Config:
        return self._config
    
    @property
    def download_manager(self) -> DownloadManager:
        return self._download_manager
    
    @property
    def uninstaller(self) -> SunshineAIOUninstaller:
        return self._uninstaller
    
    # Main Menu Actions (Page 0)
    def install_everything(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install all components - equivalent to CLI option 1"""
        try:
            if progress_callback:
                progress_callback("Starting complete installation...")
            
            self._download_manager.download_all(install=True)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def install_sunshine(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install and configure Sunshine - equivalent to CLI option 2"""
        try:
            if progress_callback:
                progress_callback("Installing Sunshine...")
            
            self._download_manager.download_sunshine(install=True, selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def install_vdd(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install Virtual Display Driver - equivalent to CLI option 3"""
        try:
            if progress_callback:
                progress_callback("Installing Virtual Display Driver...")
            
            # Use silent VDD installation to avoid console interactions
            return self._install_vdd_silently(progress_callback)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def install_svm(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install Sunshine Virtual Monitor - equivalent to CLI option 4"""
        try:
            if progress_callback:
                progress_callback("Installing Sunshine Virtual Monitor...")
            
            self._download_manager.download_svm(install=True, selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def install_playnite(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install Playnite - equivalent to CLI option 5"""
        try:
            if progress_callback:
                progress_callback("Installing Playnite...")
            
            self._download_manager.download_playnite(install=True, selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def install_playnite_watcher(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install Playnite Watcher - equivalent to CLI option 6"""
        try:
            if progress_callback:
                progress_callback("Installing Playnite Watcher...")
            
            # Use silent Playnite Watcher installation to avoid console interactions
            return self._install_playnite_watcher_silently(progress_callback)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    # Extra Tools Actions (Page 1)
    def download_everything_no_install(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download all components without installing"""
        try:
            if progress_callback:
                progress_callback("Downloading all components...")
            
            self._download_manager.download_all(install=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def configure_sunshine(self, progress_callback: Optional[Callable] = None) -> bool:
        """Configure Sunshine settings"""
        try:
            if progress_callback:
                progress_callback("Configuring Sunshine...")
            
            self._config.configure_sunshine(selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def install_windows_display_manager(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install Windows Display Manager PowerShell module"""
        try:
            if progress_callback:
                progress_callback("Installing Windows Display Manager...")
            
            self._system_requests.install_windows_display_manager()
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def open_sunshine_settings(self) -> bool:
        """Open Sunshine web settings"""
        try:
            self._config.open_sunshine_settings()
            return True
        except Exception:
            return False
    
    def open_playnite(self) -> bool:
        """Open Playnite application"""
        try:
            self._config.open_playnite()
            return True
        except Exception:
            return False
    
    def open_vdd_control(self) -> bool:
        """Open VDD Control application"""
        try:
            vdd_path = os.path.join("tools", "VDD Control", "VDD Control.exe")
            if os.path.exists(vdd_path):
                import subprocess
                subprocess.Popen([vdd_path])
                return True
            return False
        except Exception:
            return False
    
    # Selective Download Actions (Page 2)
    def download_sunshine_only(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download Sunshine only"""
        try:
            if progress_callback:
                progress_callback("Downloading Sunshine...")
            
            self._download_manager.download_sunshine(install=False, selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def download_vdd_only(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download VDD only"""
        try:
            if progress_callback:
                progress_callback("Downloading Virtual Display Driver...")
            
            self._download_manager.download_vdd(install=False, selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def download_svm_only(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download SVM only"""
        try:
            if progress_callback:
                progress_callback("Downloading Sunshine Virtual Monitor...")
            
            self._download_manager.download_svm(install=False, selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def download_mmt_only(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download Multi Monitor Tool only"""
        try:
            if progress_callback:
                progress_callback("Downloading Multi Monitor Tool...")
            
            self._download_manager.download_mmt(selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def download_vsync_toggle_only(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download VSync Toggle only"""
        try:
            if progress_callback:
                progress_callback("Downloading VSync Toggle...")
            
            self._download_manager.download_vsync_toggle(selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def download_playnite_only(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download Playnite only"""
        try:
            if progress_callback:
                progress_callback("Downloading Playnite...")
            
            self._download_manager.download_playnite(install=False, selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def download_playnite_watcher_only(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download Playnite Watcher only"""
        try:
            if progress_callback:
                progress_callback("Downloading Playnite Watcher...")
            
            self._download_manager.download_playnite_watcher(install=False, selective=False)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    # Uninstall Actions (Page 3)
    def get_uninstall_report(self) -> str:
        """Get uninstallation report"""
        try:
            # Capture the report output
            import io
            import contextlib
            
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                self._uninstaller.show_uninstallation_report()
            
            return f.getvalue()
        except Exception as e:
            return f"Error generating report: {e}"
    
    def get_installed_components(self) -> list:
        """Get list of installed components"""
        try:
            tracker = get_installation_tracker(self.base_path)
            return tracker.get_all_installed_components()
        except Exception:
            return []
    
    def uninstall_component(self, component_name: str, progress_callback: Optional[Callable] = None) -> bool:
        """Uninstall specific component"""
        try:
            if progress_callback:
                progress_callback(f"Uninstalling {component_name}...")
            
            result = self._uninstaller.uninstall_component(component_name)
            return result
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def uninstall_all_components(self, progress_callback: Optional[Callable] = None) -> bool:
        """Uninstall all components"""
        try:
            if progress_callback:
                progress_callback("Uninstalling all components...")
            
            result = self._uninstaller.uninstall_all_components()
            return result
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    # Utility methods
    def get_app_info(self) -> dict:
        """Get application information"""
        try:
            from misc.AppMetadata import get_app_name, get_app_version
            return {
                "name": get_app_name(),
                "version": get_app_version(),
                "base_path": self.base_path
            }
        except Exception:
            return {
                "name": "Sunshine-AIO",
                "version": "Unknown",
                "base_path": self.base_path
            }
    
    def check_admin_privileges(self) -> bool:
        """Check if running with admin privileges"""
        try:
            return self._system_requests.is_admin()
        except Exception:
            return False
    
    def _install_vdd_silently(self, progress_callback: Optional[Callable] = None) -> bool:
        """
        Install VDD silently without console interactions.
        This method replicates the VDD installation process but eliminates input() prompts.
        """
        try:
            import shutil
            import time
            from misc.InstallationTracker import get_installation_tracker
            from misc.Logging import log_progress, log_success, log_error, log_info, log_warning, log_header, log_step
            
            # Get VDD configuration
            vdd = self._system_requests.all_configs["VirtualDisplayDriver"]
            vdd_download_url = vdd["download_url"]
            vdd_download_pattern = vdd["download_pattern"]
            
            if progress_callback:
                progress_callback("Downloading Virtual Display Driver...")
            
            # Download and extract VDD
            log_progress("Downloading Virtual Display Driver from GitHub...")
            file_name = self._config._download_file(vdd_download_url, vdd_download_pattern, from_github=True, extract=True)
            
            # file_name is the extracted directory path
            vdd_extracted_dir_path = file_name
            
            if not os.path.exists(vdd_extracted_dir_path):
                if progress_callback:
                    progress_callback("VDD extraction failed")
                return False
            
            if progress_callback:
                progress_callback("Setting up VDD Control...")
            
            # Setup VDD Control directory
            vdd_final_path = os.path.join("tools", "VDD Control")
            
            # Step 1: Locate VDD Control.exe
            log_step(1, 2, "Locating VDD Control executable")
            def find_vdd_control(path):
                """Recursively find VDD Control.exe"""
                for root, dirs, files in os.walk(path):
                    if "VDD Control.exe" in files:
                        return os.path.join(root, "VDD Control.exe")
                return None
            
            vdd_control_exe_in_extracted = find_vdd_control(vdd_extracted_dir_path)
            
            if not vdd_control_exe_in_extracted:
                if progress_callback:
                    progress_callback("VDD Control.exe not found")
                return False
            
            original_folder_path = os.path.dirname(vdd_control_exe_in_extracted)
            
            # Step 2: Setup VDD Control directory
            log_step(2, 2, "Setting up VDD Control for installation")
            if os.path.exists(vdd_final_path):
                log_info("Removing existing VDD Control directory...")
                shutil.rmtree(vdd_final_path)
                time.sleep(1.0)
            
            try:
                # Rename extracted folder to "VDD Control"
                os.rename(vdd_extracted_dir_path, vdd_final_path)
                log_success(f"VDD Control renamed to: {vdd_final_path}")
            except Exception as e:
                # Alternative method: copy then remove original
                if os.path.exists(vdd_final_path):
                    shutil.rmtree(vdd_final_path)
                shutil.copytree(original_folder_path, vdd_final_path)
                shutil.rmtree(vdd_extracted_dir_path)
                log_success(f"VDD Control copied to: {vdd_final_path}")
            
            # Final verification
            vdd_control_exe = os.path.join(vdd_final_path, "VDD Control.exe")
            if not os.path.exists(vdd_control_exe):
                if progress_callback:
                    progress_callback("VDD Control setup verification failed")
                return False
            
            log_success("VDD Control extracted and configured successfully")
            
            if progress_callback:
                progress_callback("Launching VDD Control for driver installation...")
            
            # Launch VDD Control silently (without waiting for user input)
            log_header("Virtual Display Driver Installation")
            log_info("Launching VDD Control application...")
            log_info("The VDD Control window will open for driver installation.")
            log_info("Please install the driver through the VDD Control interface.")
            log_info(f"VDD Control is available at: {vdd_final_path}")
            
            # Launch VDD Control without waiting for input
            import subprocess
            subprocess.Popen([vdd_control_exe], cwd=vdd_final_path)
            log_success("VDD Control launched successfully!")
            
            if progress_callback:
                progress_callback("VDD Control launched - please complete driver installation")
            
            # Register installation in tracker (without waiting for completion)
            try:
                install_info = {
                    "version": "latest",
                    "installer_type": "manual_vdd_control",
                    "files_created": [vdd_final_path],
                    "drivers_installed": [],
                    "device_ids": [],
                    "custom_options": {
                        "control_executable": vdd_control_exe,
                        "installation_method": "VDD Control extraction (GUI mode)",
                        "driver_type": "pending_manual_installation"
                    }
                }
                
                tracker = get_installation_tracker(self.base_path)
                tracker.track_installation("virtual_display_driver", vdd_final_path, install_info)
                log_info("Installation tracked for future uninstallation")
                
            except Exception as e:
                log_warning(f"Could not track installation: {e}")
            
            log_success("Virtual Display Driver setup completed!")
            log_info(f"VDD Control is available at: {vdd_final_path}")
            log_info("Complete the driver installation through the VDD Control interface that was launched.")
            
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"VDD installation error: {e}")
            return False
    
    def _install_playnite_watcher_silently(self, progress_callback: Optional[Callable] = None) -> bool:
        """
        Install Playnite Watcher silently without console interactions.
        This method replicates the Playnite Watcher installation process but eliminates input() prompts.
        """
        try:
            import subprocess
            from misc.InstallationTracker import get_installation_tracker
            from misc.Logging import log_progress, log_success, log_info, log_warning
            
            # Get Playnite Watcher configuration
            playnitew = self._system_requests.all_configs["PlayniteWatcher"]
            playnitew_download_url = playnitew["download_url"]
            playnitew_download_pattern = playnitew["download_pattern"]
            playnitew_guide_url = playnitew.get("guide_url", "")
            playnitew_addon_url = playnitew.get("addon_url", "")
            
            if progress_callback:
                progress_callback("Downloading Playnite Watcher...")
            
            # Download Playnite Watcher
            log_progress("Downloading Playnite Watcher from GitHub...")
            self._config._download_file(playnitew_download_url, playnitew_download_pattern, from_github=True)
            
            if progress_callback:
                progress_callback("Setting up Playnite Watcher...")
            
            # Skip all console interactions - handle them silently with default actions
            
            # For Windows 11 users, we could automatically open settings, but for GUI mode,
            # we'll just log the information instead of prompting
            if hasattr(self._config, 'release') and self._config.release == '11':
                log_info("Note: If you're on Windows 11, please set the default terminal to Windows Console Host in Settings > Developers.")
            
            # Automatically open Sunshine App Export addon for Playnite (default yes behavior)
            if playnitew_addon_url:
                try:
                    if progress_callback:
                        progress_callback("Opening Sunshine App Export addon for Playnite...")
                    subprocess.run(["start", playnitew_addon_url], shell=True, check=True)
                    log_info("Sunshine App Export addon opened for Playnite installation")
                except Exception as e:
                    log_warning(f"Could not open Sunshine App Export addon: {e}")
            
            # Automatically open setup guide (default yes behavior)
            if playnitew_guide_url:
                try:
                    if progress_callback:
                        progress_callback("Opening Playnite Watcher setup guide...")
                    subprocess.run(["start", playnitew_guide_url], shell=True)
                    log_info("Playnite Watcher setup guide opened")
                except Exception as e:
                    log_warning(f"Could not open setup guide: {e}")
            
            # Register installation in tracker
            try:
                install_info = {
                    "version": "latest",
                    "installer_type": "github_download",
                    "files_created": [],
                    "custom_options": {
                        "installation_method": "Download and automatic guide opening (GUI mode)",
                        "guide_url": playnitew_guide_url,
                        "addon_url": playnitew_addon_url
                    }
                }
                
                tracker = get_installation_tracker(self.base_path)
                tracker.track_installation("playnite_watcher", "tools", install_info)
                log_info("Installation tracked for future uninstallation")
                
            except Exception as e:
                log_warning(f"Could not track installation: {e}")
            
            log_success("Playnite Watcher installation completed!")
            log_info("Setup guide and addon links have been opened automatically.")
            
            if progress_callback:
                progress_callback("Playnite Watcher installation completed - guides opened")
            
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Playnite Watcher installation error: {e}")
            return False