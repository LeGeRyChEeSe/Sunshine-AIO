import os
import shutil
import subprocess
import winreg
import time
from pathlib import Path
from typing import List, Dict, Optional
from misc.SystemRequests import SystemRequests
from misc.Logger import log_success, log_info, log_warning, log_error, log_progress, log_header
from misc.InstallationTracker import get_installation_tracker


class SunshineAIOUninstaller:
    """
    Complete uninstaller manager for Sunshine-AIO.
    
    Attributes
    ----------
    sr: SystemRequests
        System requests manager instance.
    components: Dict
        Dictionary of components to uninstall.
    """

    def __init__(self, system_requests: SystemRequests) -> None:
        self._sr = system_requests
        self._tracker = get_installation_tracker(system_requests._base_path)
        self._components = {
            "sunshine": {
                "name": "Sunshine",
                "uninstaller_method": self._uninstall_sunshine_advanced,
                "verification_method": self._verify_sunshine_uninstalled
            },
            "virtual_display_driver": {
                "name": "Virtual Display Driver",
                "uninstaller_method": self._uninstall_vdd_advanced,
                "verification_method": self._verify_vdd_uninstalled
            },
            "sunshine_virtual_monitor": {
                "name": "Sunshine Virtual Monitor",
                "uninstaller_method": self._uninstall_svm_advanced,
                "verification_method": self._verify_svm_uninstalled
            },
            "playnite": {
                "name": "Playnite",
                "uninstaller_method": self._uninstall_playnite_advanced,
                "verification_method": self._verify_playnite_uninstalled
            },
            "playnite_watcher": {
                "name": "Playnite Watcher",
                "uninstaller_method": self._uninstall_playnite_watcher_advanced,
                "verification_method": self._verify_playnite_watcher_uninstalled
            },
            "multi_monitor_tool": {
                "name": "Multi Monitor Tool",
                "uninstaller_method": self._uninstall_mmt_advanced,
                "verification_method": self._verify_mmt_uninstalled
            },
            "vsync_toggle": {
                "name": "VSync Toggle",
                "uninstaller_method": self._uninstall_vsync_advanced,
                "verification_method": self._verify_vsync_uninstalled
            }
        }

    @property
    def sr(self):
        return self._sr

    @sr.setter
    def sr(self):
        raise ValueError("No manual edit allowed.")

    @property
    def components(self):
        return self._components

    @components.setter
    def components(self):
        raise ValueError("No manual edit allowed.")

    def uninstall_all(self, confirm: bool = True) -> bool:
        """
        Uninstall all Sunshine-AIO components.
        
        Parameters
        ----------
        confirm: bool
            Ask for confirmation before uninstallation.
            
        Returns
        -------
        bool
            True if uninstallation succeeded.
        """
        if confirm:
            print("This operation will completely remove all Sunshine-AIO components from your system.")
            print("Components that will be removed:")
            for component in self._components.values():
                print(f"  - {component['name']}")
            
            print("\n" + "="*50)
            response = input("Do you want to continue? (yes/no): ").lower().strip()
            if response not in ['yes', 'y', 'oui', 'o']:
                print("Uninstallation cancelled.")
                return False

        print("\nStarting complete uninstallation...")
        success = True

        # Stop processes and services first
        self._stop_all_processes()
        self._stop_all_services()

        # Uninstall each component with the new advanced methods
        for component_key, component in self._components.items():
            log_progress(f"Uninstalling {component['name']}...")
            try:
                if component.get('uninstaller_method'):
                    if component['uninstaller_method']():
                        log_success(f"{component['name']} uninstalled successfully")
                        # Remove installation tracking
                        self._tracker.remove_installation_tracking(component_key)
                    else:
                        log_warning(f"Issues during uninstallation of {component['name']}")
                        success = False
                else:
                    log_warning(f"Uninstallation method not defined for {component['name']}")
                    success = False
            except Exception as e:
                log_error(f"Error during uninstallation of {component['name']}: {e}")
                success = False

        # Clean up Windows firewall rules
        self._cleanup_firewall_rules()

        # Clean up startup entries
        self._cleanup_startup_entries()

        print(f"\nUninstallation {'completed successfully' if success else 'completed with warnings'}!")
        if not success:
            print("Some components may require manual cleanup or a system restart.")

        return success

    def uninstall_component(self, component_name: str) -> bool:
        """
        Uninstall a specific component.
        
        Parameters
        ----------
        component_name: str
            The name of the component to uninstall.
            
        Returns
        -------
        bool
            True if uninstallation succeeded.
        """
        component_key = component_name.lower().replace(" ", "_").replace("-", "_")

        if component_key not in self._components:
            log_error(f"Unknown component: {component_name}")
            return False

        component = self._components[component_key]
        log_progress(f"Uninstalling {component['name']}...")

        try:
            if component.get('uninstaller_method'):
                success = component['uninstaller_method']()
                if success:
                    log_success(f"{component['name']} uninstalled successfully")
                    # Remove installation tracking
                    self._tracker.remove_installation_tracking(component_key)
                    return True
                else:
                    log_error(f"Failed to uninstall {component['name']}")
                    return False
            else:
                log_error(f"Uninstallation method not defined for {component['name']}")
                return False
        except Exception as e:
            log_error(f"Error during uninstallation of {component['name']}: {e}")
            return False

    def _remove_files_and_directories(self, paths: List[str]) -> bool:
        """
        Removes a list of files and directories.
        CRITICAL: Never removes the main tools/ directory.
        
        Parameters
        ----------
        paths: List[str]
            List of paths to remove.
            
        Returns
        -------
        bool
            True if all elements were removed successfully.
        """
        success = True
        
        for path in paths:
            # CRITICAL PROTECTION: Never delete the main tools directory
            normalized_path = os.path.normpath(os.path.abspath(path))
            tools_dir_patterns = [
                os.path.normpath(os.path.abspath("tools")),
                os.path.normpath(os.path.abspath("./tools")),
                os.path.normpath(os.path.abspath("src/tools"))
            ]
            
            # Check if this is the main tools directory
            is_tools_dir = any(normalized_path.lower() == pattern.lower() for pattern in tools_dir_patterns)
            
            if is_tools_dir:
                log_warning(f"PROTECTED: Skipping removal of main tools directory: {path}")
                log_info("Only subdirectories of tools/ can be removed, never the tools/ directory itself")
                continue
            
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                        log_success(f"Directory removed: {path}")
                    else:
                        os.remove(path)
                        log_success(f"File removed: {path}")
                except Exception as e:
                    log_error(f"Failed to remove {path}: {e}")
                    success = False
            else:
                log_info(f"Path does not exist (already removed): {path}")
        
        return success

    def _stop_all_processes(self):
        """Stop all known processes."""
        all_processes = []
        for component in self._components.values():
            if 'processes' in component:
                all_processes.extend(component['processes'])

        if all_processes:
            self._stop_processes(all_processes)

    def _stop_all_services(self):
        """Stop all known services."""
        all_services = []
        for component in self._components.values():
            if 'services' in component:
                all_services.extend(component['services'])

        if all_services:
            self._stop_services(all_services)

    def _stop_processes(self, processes: List[str]) -> bool:
        """
        Stop specified processes.
        
        Parameters
        ----------
        processes: List[str]
            List of process names to stop.
            
        Returns
        -------
        bool
            True if all processes were stopped successfully.
        """
        success = True
        
        for process in processes:
            try:
                result = subprocess.run(['taskkill', '/F', '/IM', process], 
                                     capture_output=True, check=False)
                if result.returncode == 0:
                    log_success(f"Process stopped: {process}")
                else:
                    log_info(f"Process {process} was not running")
            except Exception as e:
                log_warning(f"Error stopping process {process}: {e}")
                success = False
        
        return success

    def _stop_services(self, services: List[str]) -> bool:
        """
        Stop and remove specified services.
        
        Parameters
        ----------
        services: List[str]
            List of service names to stop and remove.
            
        Returns
        -------
        bool
            True if all services were removed successfully.
        """
        success = True
        
        for service in services:
            try:
                # Stop service
                stop_result = subprocess.run(['sc', 'stop', service], 
                                           capture_output=True, check=False)
                
                # Wait for service to stop
                time.sleep(2)
                
                # Remove service
                delete_result = subprocess.run(['sc', 'delete', service], 
                                             capture_output=True, check=False)
                
                if delete_result.returncode == 0:
                    log_success(f"Service stopped and removed: {service}")
                else:
                    log_info(f"Service {service} did not exist or was already removed")
                    
            except Exception as e:
                log_warning(f"Error removing service {service}: {e}")
                success = False
        
        return success

    def _remove_registry_keys(self, keys: List[str]) -> bool:
        """
        Remove a list of registry keys.
        
        Parameters
        ----------
        keys: List[str]
            List of registry keys to remove.
            
        Returns
        -------
        bool
            True if all keys were removed successfully.
        """
        success = True
        
        for key_path in keys:
            try:
                self._remove_registry_key(key_path)
                log_success(f"Registry key removed: {key_path}")
            except Exception as e:
                log_warning(f"Failed to remove registry key {key_path}: {e}")
                # Do not consider as critical failure
        
        return success

    def _remove_registry_key(self, key_path: str):
        """
        Remove a registry key.
        
        Parameters
        ----------
        key_path: str
            Path of registry key to remove.
        """
        try:
            # Try HKEY_LOCAL_MACHINE first
            try:
                winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                return
            except FileNotFoundError:
                pass

            # Try HKEY_CURRENT_USER
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
                return
            except FileNotFoundError:
                pass

        except Exception as e:
            raise e

    def _cleanup_firewall_rules(self):
        """Remove firewall rules created by Sunshine."""
        try:
            # Remove Sunshine firewall rules
            subprocess.run([
                'netsh', 'advfirewall', 'firewall', 'delete', 'rule', 
                'name=Sunshine'
            ], capture_output=True)
            print("  Firewall rules cleaned")
        except Exception:
            pass

    def _cleanup_startup_entries(self):
        """Remove startup entries."""
        startup_paths = [
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        ]

        startup_files = ["Sunshine.lnk", "Playnite.lnk", "PlayniteWatcher.lnk"]

        for startup_path in startup_paths:
            for startup_file in startup_files:
                file_path = os.path.join(startup_path, startup_file)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"  Startup entry removed: {startup_file}")
                    except Exception:
                        pass
    
    def _uninstall_svm_advanced(self) -> bool:
        """
        Advanced uninstallation method for Sunshine Virtual Monitor.
        
        Returns
        -------
        bool
            True if uninstallation succeeded.
        """
        log_info("Starting Sunshine Virtual Monitor uninstallation...")
        success = True
        
        try:
            # 1. Try official uninstaller first (script)
            if self._find_and_run_official_uninstaller("sunshine_virtual_monitor"):
                log_success("Uninstallation via official script successful")
                # Check if everything was removed
                if self._verify_svm_uninstalled():
                    log_success("Sunshine Virtual Monitor uninstallation completed successfully")
                    return True
                else:
                    log_info("Cleaning up residuals after official script...")
            else:
                log_info("No uninstallation script found, manual procedure...")
            
            # 2. Manual procedure if necessary
            # Remove files and directories
            files_to_remove = self._tracker.get_files_to_remove("sunshine_virtual_monitor")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            if success:
                log_success("Sunshine Virtual Monitor uninstallation completed successfully")
            else:
                log_warning("SVM uninstallation completed with warnings")
            
            return success
            
        except Exception as e:
            log_error(f"Error during SVM uninstallation: {e}")
            return False
    
    def _verify_svm_uninstalled(self) -> bool:
        """
        Verify that Sunshine Virtual Monitor was correctly uninstalled.
        
        Returns
        -------
        bool
            True if SVM is completely uninstalled.
        """
        for path in self._tracker.get_all_installation_paths("sunshine_virtual_monitor"):
            if os.path.exists(path):
                return False
        return True
    
    def _uninstall_playnite_advanced(self) -> bool:
        """
        Advanced uninstallation method for Playnite.
        
        Returns
        -------
        bool
            True if uninstallation succeeded.
        """
        log_info("Starting advanced Playnite uninstallation...")
        success = True
        
        try:
            # 1. Try official uninstaller first
            log_progress("Step 1/4: Searching for official uninstaller...")
            if self._find_and_run_official_uninstaller("playnite"):
                log_success("Official uninstaller completed")
                # Check if everything was removed
                if self._verify_playnite_uninstalled():
                    log_success("Playnite uninstallation completed successfully")
                    return True
                else:
                    log_info("Cleaning up remaining files after official uninstall...")
            else:
                log_info("No official uninstaller found, proceeding with manual cleanup...")
            
            # 2. Manual cleanup if needed
            log_progress("Step 2/4: Stopping Playnite processes...")
            processes = ["Playnite.DesktopApp.exe", "Playnite.FullscreenApp.exe", "Playnite.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 3. Remove remaining files and folders
            log_progress("Step 3/4: Removing installation files...")
            files_to_remove = self._tracker.get_files_to_remove("playnite")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            # 4. Clean registry
            log_progress("Step 4/4: Cleaning registry entries...")
            registry_keys = self._tracker.get_registry_keys("playnite")
            if registry_keys and not self._remove_registry_keys(registry_keys):
                success = False
            
            if success:
                log_success("Playnite uninstallation completed successfully")
            else:
                log_warning("Playnite uninstallation completed with warnings")
            
            return success
            
        except Exception as e:
            log_error(f"Error during Playnite uninstallation: {e}")
            return False
    
    def _verify_playnite_uninstalled(self) -> bool:
        """
        Verify that Playnite was correctly uninstalled.
        
        Returns
        -------
        bool
            True if Playnite is completely uninstalled.
        """
        for path in self._tracker.get_all_installation_paths("playnite"):
            if os.path.exists(path):
                return False
        return True
    
    def _uninstall_playnite_watcher_advanced(self) -> bool:
        """
        Advanced uninstallation method for Playnite Watcher.
        
        Returns
        -------
        bool
            True if uninstallation succeeded.
        """
        log_info("Starting Playnite Watcher uninstallation...")
        success = True
        
        try:
            # 1. Stop process
            processes = ["PlayniteWatcher.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 2. Remove files and directories
            files_to_remove = self._tracker.get_files_to_remove("playnite_watcher")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            if success:
                log_success("Playnite Watcher uninstallation completed successfully")
            else:
                log_warning("Playnite Watcher uninstallation completed with warnings")
            
            return success
            
        except Exception as e:
            log_error(f"Error during Playnite Watcher uninstallation: {e}")
            return False
    
    def _verify_playnite_watcher_uninstalled(self) -> bool:
        """
        Verify that Playnite Watcher was correctly uninstalled.
        
        Returns
        -------
        bool
            True if Playnite Watcher is completely uninstalled.
        """
        for path in self._tracker.get_all_installation_paths("playnite_watcher"):
            if os.path.exists(path):
                return False
        return True
    
    def _uninstall_mmt_advanced(self) -> bool:
        """
        Advanced uninstallation method for Multi Monitor Tool.
        
        Returns
        -------
        bool
            True if uninstallation succeeded.
        """
        log_info("Starting Multi Monitor Tool uninstallation...")
        success = True
        
        try:
            # 1. Stop process
            processes = ["MultiMonitorTool.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 2. Remove files and directories
            files_to_remove = self._tracker.get_files_to_remove("multi_monitor_tool")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            if success:
                log_success("Multi Monitor Tool uninstallation completed successfully")
            else:
                log_warning("Multi Monitor Tool uninstallation completed with warnings")
            
            return success
            
        except Exception as e:
            log_error(f"Error during Multi Monitor Tool uninstallation: {e}")
            return False
    
    def _verify_mmt_uninstalled(self) -> bool:
        """
        Verify that Multi Monitor Tool was correctly uninstalled.
        
        Returns
        -------
        bool
            True if MMT is completely uninstalled.
        """
        for path in self._tracker.get_all_installation_paths("multi_monitor_tool"):
            if os.path.exists(path):
                return False
        return True
    
    def _uninstall_vsync_advanced(self) -> bool:
        """
        Advanced uninstallation method for VSync Toggle.
        
        Returns
        -------
        bool
            True if uninstallation succeeded.
        """
        log_info("Starting VSync Toggle uninstallation...")
        success = True
        
        try:
            # 1. Stop process
            processes = ["VSync Toggle.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 2. Remove files and directories
            files_to_remove = self._tracker.get_files_to_remove("vsync_toggle")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            if success:
                log_success("VSync Toggle uninstallation completed successfully")
            else:
                log_warning("VSync Toggle uninstallation completed with warnings")
            
            return success
            
        except Exception as e:
            log_error(f"Error during VSync Toggle uninstallation: {e}")
            return False
    
    def _verify_vsync_uninstalled(self) -> bool:
        """
        Verify that VSync Toggle was correctly uninstalled.
        
        Returns
        -------
        bool
            True if VSync Toggle is completely uninstalled.
        """
        for path in self._tracker.get_all_installation_paths("vsync_toggle"):
            if os.path.exists(path):
                return False
        return True
    
    def _detect_vdd_devices(self):
        """
        Detects all installed VDD devices.
        
        Returns:
            list: List of VDD devices with their information
        """
        vdd_devices = []
        
        try:
            # Use PowerShell to detect all VDD devices
            ps_command = '''
            Get-PnpDevice | Where-Object {
                $_.FriendlyName -match "Virtual Display Driver|Generic Monitor.*VDD.*MTT" -or
                $_.InstanceId -match "ROOT\\\\DISPLAY|DISPLAY\\\\MTT"
            } | Select-Object FriendlyName, InstanceId, Status | ConvertTo-Json
            '''
            
            result = subprocess.run([
                'powershell', '-Command', ps_command
            ], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0 and result.stdout.strip():
                import json
                devices_data = json.loads(result.stdout)
                
                # Handle case where there's only one device (not a list)
                if isinstance(devices_data, dict):
                    devices_data = [devices_data]
                
                for device in devices_data:
                    vdd_devices.append({
                        'name': device.get('FriendlyName', 'Unknown'),
                        'instance_id': device.get('InstanceId', ''),
                        'status': device.get('Status', 'Unknown')
                    })
                    
            log_info(f"Detected {len(vdd_devices)} VDD devices")
            
        except Exception as e:
            log_warning(f"Error detecting VDD devices: {e}")
            
            # Fallback: use known patterns
            known_patterns = [
                'ROOT\\DISPLAY\\0000',
                'DISPLAY\\MTT1337\\*'
            ]
            
            for pattern in known_patterns:
                vdd_devices.append({
                    'name': f'VDD Device ({pattern})',
                    'instance_id': pattern,
                    'status': 'Unknown'
                })
        
        return vdd_devices
    
    # =================== UTILITY METHODS ===================
    
    def _find_and_run_official_uninstaller(self, tool_name: str) -> bool:
        """
        Search for and execute an official uninstaller for a tool.
        
        Parameters
        ----------
        tool_name: str
            Tool name (sunshine, playnite, etc.)
            
        Returns
        -------
        bool
            True if an official uninstaller was found and executed successfully.
        """
        log_info(f"Searching for official uninstaller for {tool_name}...")
        
        # Possible installation paths from tracker
        install_paths = self._tracker.get_all_installation_paths(tool_name)
        
        # Define uninstaller patterns by tool
        uninstaller_patterns = {
            "sunshine": ["Uninstall.exe", "unins000.exe", "uninstall.exe"],
            "playnite": ["unins000.exe", "Uninstall.exe", "uninstall.exe"],
            "virtual_display_driver": [],  # No standard uninstaller
            "sunshine_virtual_monitor": ["uninstall.bat", "teardown_sunvdm.ps1"],
            "playnite_watcher": [],  # No standard uninstaller
            "multi_monitor_tool": [],  # Portable tool
            "vsync_toggle": []  # Portable tool
        }
        
        patterns = uninstaller_patterns.get(tool_name, [])
        if not patterns:
            log_info(f"No known official uninstaller for {tool_name}")
            return False
        
        # Search in installation paths with timeout protection
        for install_path in install_paths:
            if not install_path or not os.path.exists(install_path):
                continue
                
            for pattern in patterns:
                uninstaller_path = os.path.join(install_path, pattern)
                if os.path.exists(uninstaller_path):
                    log_progress(f"Official uninstaller found: {uninstaller_path}")
                    return self._execute_official_uninstaller(uninstaller_path, tool_name)
        
        # Search in Windows registry for installed programs with timeout
        log_progress("Searching Windows registry for uninstaller...")
        try:
            return self._find_uninstaller_in_registry(tool_name)
        except Exception as e:
            log_warning(f"Registry search failed: {e}")
            return False
    
    def _execute_official_uninstaller(self, uninstaller_path: str, tool_name: str) -> bool:
        """
        Execute an official uninstaller.
        
        Parameters
        ----------
        uninstaller_path: str
            Path to uninstaller
        tool_name: str
            Tool name
            
        Returns
        -------
        bool
            True if execution was successful.
        """
        try:
            log_progress(f"Executing official uninstaller: {uninstaller_path}")
            
            # Different arguments based on file type
            if uninstaller_path.endswith('.exe'):
                # Common silent arguments
                silent_args = ["/S", "/SILENT", "/VERYSILENT", "/QUIET", "/q", "/uninstall"]
                
                # Try with silent arguments first
                for arg in silent_args:
                    try:
                        log_progress(f"Trying uninstaller with argument: {arg}")
                        result = subprocess.run(
                            [uninstaller_path, arg], 
                            timeout=90,  # Reduced timeout
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            log_success(f"Official uninstaller executed successfully (argument: {arg})")
                            return True
                        else:
                            log_info(f"Uninstaller with {arg} returned code: {result.returncode}")
                    except subprocess.TimeoutExpired:
                        log_warning(f"Timeout during execution with argument {arg} (90s)")
                        # Kill any remaining processes
                        try:
                            subprocess.run(['taskkill', '/F', '/IM', os.path.basename(uninstaller_path)], 
                                         capture_output=True, timeout=10)
                        except:
                            pass
                        continue
                    except Exception as e:
                        log_info(f"Error with argument {arg}: {e}")
                        continue
                
                # If no silent argument works, inform user and skip interactive mode
                log_warning("No silent uninstall method worked, skipping interactive uninstaller")
                log_info("The uninstaller may require manual intervention - proceeding with manual cleanup")
                return False
                    
            elif uninstaller_path.endswith('.bat'):
                # Batch script
                try:
                    result = subprocess.run(
                        [uninstaller_path], 
                        cwd=os.path.dirname(uninstaller_path),
                        timeout=60, 
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        log_success("Batch uninstall script executed successfully")
                        return True
                    else:
                        log_warning(f"Batch script returned code: {result.returncode}")
                        return False
                except subprocess.TimeoutExpired:
                    log_warning("Batch script execution timed out")
                    return False
                    
            elif uninstaller_path.endswith('.ps1'):
                # PowerShell script
                try:
                    result = subprocess.run(
                        ["powershell", "-ExecutionPolicy", "Bypass", "-File", uninstaller_path], 
                        cwd=os.path.dirname(uninstaller_path),
                        timeout=60, 
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        log_success("PowerShell uninstall script executed successfully")
                        return True
                    else:
                        log_warning(f"PowerShell script returned code: {result.returncode}")
                        return False
                except subprocess.TimeoutExpired:
                    log_warning("PowerShell script execution timed out")
                    return False
            
            return False
            
        except Exception as e:
            log_error(f"Error executing official uninstaller: {e}")
            return False
    
    def _find_uninstaller_in_registry(self, tool_name: str) -> bool:
        """
        Searches for an uninstaller in Windows registry.
        
        Parameters
        ----------
        tool_name: str
            Tool name
            
        Returns
        -------
        bool
            True if an uninstaller was found and executed.
        """
        try:
            # Mapping tool names to program names in registry
            registry_names = {
                "sunshine": ["Sunshine", "LizardByte Sunshine"],
                "playnite": ["Playnite"],
                "virtual_display_driver": ["Virtual Display Driver", "IDD Sample Driver"],
            }
            
            names_to_search = registry_names.get(tool_name, [])
            if not names_to_search:
                log_info(f"No registry entries to search for {tool_name}")
                return False
            
            # Registry keys to check
            registry_keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            ]
            
            for hkey, subkey_path in registry_keys:
                try:
                    with winreg.OpenKey(hkey, subkey_path) as key:
                        # Enumerate all subkeys with limit to prevent hanging
                        i = 0
                        max_entries = 200  # Prevent infinite loops
                        while i < max_entries:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        
                                        # Check if this is our program
                                        for name in names_to_search:
                                            if name.lower() in display_name.lower():
                                                try:
                                                    uninstall_string = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                                    if uninstall_string:
                                                        log_progress(f"Uninstaller found in registry: {uninstall_string}")
                                                        return self._execute_registry_uninstaller(uninstall_string, tool_name)
                                                except FileNotFoundError:
                                                    continue
                                    except FileNotFoundError:
                                        continue
                                i += 1
                            except OSError:
                                break
                except Exception as e:
                    log_info(f"Registry search failed for {subkey_path}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            log_warning(f"Error during registry search: {e}")
            return False
    
    def _execute_registry_uninstaller(self, uninstall_string: str, tool_name: str) -> bool:
        """
        Execute an uninstallation command from the registry.
        
        Parameters
        ----------
        uninstall_string: str
            Uninstallation command from the registry
        tool_name: str
            Tool name
            
        Returns
        -------
        bool
            True if execution was successful.
        """
        try:
            # Parse the command (may contain quotes and arguments)
            import shlex
            
            # Clean and parse the command
            if uninstall_string.startswith('"'):
                # Command with quotes
                parts = shlex.split(uninstall_string)
            else:
                # Simple command
                parts = uninstall_string.split()
            
            if not parts:
                return False
            
            # Add silent arguments if possible
            if parts[0].lower().endswith('.exe'):
                # Try with silent arguments
                for silent_arg in ['/S', '/SILENT', '/VERYSILENT', '/QUIET']:
                    try:
                        cmd = parts + [silent_arg]
                        result = subprocess.run(cmd, timeout=120, capture_output=True)
                        if result.returncode == 0:
                            log_success(f"Registry uninstallation successful with {silent_arg}")
                            return True
                    except Exception:
                        continue
            
            # Execute the command as-is as last resort
            result = subprocess.run(parts, timeout=180, capture_output=True)
            if result.returncode == 0:
                log_success("Registry uninstallation successful")
                return True
            else:
                log_warning(f"Uninstallation command returned code: {result.returncode}")
                return False
            
        except Exception as e:
            log_error(f"Error executing uninstallation command: {e}")
            return False
    
    def _cleanup_sunshine_firewall_rules(self) -> bool:
        """
        Remove firewall rules created by Sunshine.
        
        Returns
        -------
        bool
            True if all rules were removed successfully.
        """
        try:
            # Remove Sunshine firewall rules
            firewall_rules = ["Sunshine", "sunshine.exe"]
            
            for rule in firewall_rules:
                result = subprocess.run([
                    'netsh', 'advfirewall', 'firewall', 'delete', 'rule', 
                    f'name={rule}'
                ], capture_output=True)
                
                if result.returncode == 0:
                    log_success(f"Firewall rule removed: {rule}")
                else:
                    log_info(f"Firewall rule {rule} did not exist")
            
            return True
            
        except Exception as e:
            log_warning(f"Error cleaning firewall rules: {e}")
            return False
    
    def _cleanup_sunshine_startup_entries(self) -> bool:
        """
        Remove startup entries related to Sunshine.
        
        Returns
        -------
        bool
            True if all entries were removed successfully.
        """
        startup_paths = [
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        ]

        startup_files = ["Sunshine.lnk", "sunshine.lnk"]
        success = True

        for startup_path in startup_paths:
            for startup_file in startup_files:
                file_path = os.path.join(startup_path, startup_file)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        log_success(f"Startup entry removed: {startup_file}")
                    except Exception as e:
                        log_warning(f"Unable to remove {startup_file}: {e}")
                        success = False
        
        return success
        
    @property
    def tracker(self):
        """Access to installation tracker."""
        return self._tracker

    def list_installed_components(self) -> List[str]:
        """
        List currently installed components.
        
        Returns
        -------
        List[str]
            List of installed component names.
        """
        installed = []

        for component_key, component in self._components.items():
            if self._tracker.is_tool_installed(component_key):
                installed.append(component['name'])

        return installed

    def generate_uninstall_report(self) -> str:
        """
        Generate a report of what would be uninstalled.
        
        Returns
        -------
        str
            Detailed uninstallation report.
        """
        report = []
        report.append("=== SUNSHINE-AIO UNINSTALLATION REPORT ===")
        report.append("")
        
        # Use installation tracker report
        report.append(self._tracker.get_installation_report())
        report.append("")
        report.append("UNINSTALLATION DETAILS:")
        report.append("")

        for component_key, component in self._components.items():
            if self._tracker.is_tool_installed(component_key):
                report.append(f"• {component['name'].upper()} - INSTALLED")
                
                # Installation paths
                paths = self._tracker.get_all_installation_paths(component_key)
                if paths:
                    report.append("  Paths to remove:")
                    for path in paths:
                        report.append(f"    - {path}")
                
                # Files to remove
                files = self._tracker.get_files_to_remove(component_key)
                if files:
                    report.append("  Files/Directories to remove:")
                    for file_path in files:
                        status = "EXISTS" if os.path.exists(file_path) else "NOT FOUND"
                        report.append(f"    - {file_path} ({status})")
                
                # Services
                services = self._tracker.get_services_to_remove(component_key)
                if services:
                    report.append("  Services to remove:")
                    for service in services:
                        report.append(f"    - {service}")
                
                # Drivers
                drivers = self._tracker.get_drivers_to_remove(component_key)
                if drivers:
                    report.append("  Drivers to remove:")
                    for driver in drivers:
                        report.append(f"    - {driver}")
                
                # Registry keys
                reg_keys = self._tracker.get_registry_keys(component_key)
                if reg_keys:
                    report.append("  Registry keys to remove:")
                    for key in reg_keys:
                        report.append(f"    - {key}")
                
                report.append("")
            else:
                report.append(f"• {component['name'].upper()} - NOT INSTALLED")
                report.append("")

        return "\n".join(report)
    
    # =================== ADVANCED UNINSTALLATION METHODS ===================
    
    def _uninstall_sunshine_advanced(self) -> bool:
        """
        Advanced Sunshine uninstallation method.
        
        Returns
        -------
        bool
            True if uninstallation was successful.
        """
        log_info("Starting advanced Sunshine uninstallation...")
        success = True
        
        try:
            # Check if Sunshine is actually installed first
            if not self._tracker.is_tool_installed("sunshine"):
                install_paths = self._tracker.get_all_installation_paths("sunshine")
                if not any(os.path.exists(path) for path in install_paths if path):
                    log_info("Sunshine is not installed - skipping uninstallation")
                    return True
            
            # 1. Try official uninstaller first
            log_progress("Step 1/5: Searching for official uninstaller...")
            if self._find_and_run_official_uninstaller("sunshine"):
                log_success("Official uninstaller completed")
                # Check if everything was removed
                if self._verify_sunshine_uninstalled():
                    log_success("Sunshine uninstallation completed successfully")
                    return True
                else:
                    log_info("Cleaning up remaining files after official uninstall...")
            else:
                log_info("No official uninstaller found, proceeding with manual cleanup...")
            
            # 2. Manual cleanup if needed
            log_progress("Step 2/5: Stopping Sunshine processes...")
            processes = ["sunshine.exe", "sunshine_console.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 3. Stop and remove Sunshine service
            log_progress("Step 3/5: Removing Sunshine service...")
            services = self._tracker.get_services_to_remove("sunshine")
            if services and not self._stop_services(services):
                success = False
            
            # 4. Remove remaining files and folders
            log_progress("Step 4/5: Removing installation files...")
            files_to_remove = self._tracker.get_files_to_remove("sunshine")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            # 5. Clean registry, firewall rules and startup entries
            log_progress("Step 5/5: Cleaning system entries...")
            registry_keys = self._tracker.get_registry_keys("sunshine")
            if registry_keys and not self._remove_registry_keys(registry_keys):
                success = False
            
            # Clean firewall rules and startup entries
            self._cleanup_sunshine_firewall_rules()
            self._cleanup_sunshine_startup_entries()
            
            if success:
                log_success("Sunshine uninstallation completed successfully")
            else:
                log_warning("Sunshine uninstallation completed with warnings")
            
            return success
            
        except Exception as e:
            log_error(f"Error during Sunshine uninstallation: {e}")
            return False
    
    def _verify_sunshine_uninstalled(self) -> bool:
        """
        Verify that Sunshine was correctly uninstalled.
        
        Returns
        -------
        bool
            True if Sunshine is completely uninstalled.
        """
        # Check installation paths
        for path in self._tracker.get_all_installation_paths("sunshine"):
            if os.path.exists(path):
                return False
        
        # Check registry keys
        for key in self._tracker.get_registry_keys("sunshine"):
            if self._tracker._check_registry_key_exists(key):
                return False
        
        return True
    
    def _uninstall_vdd_advanced(self) -> bool:
        """
        Advanced uninstallation method for Virtual Display Driver.
        
        Returns
        -------
        bool
            True if uninstallation succeeded.
        """
        log_info("Starting advanced Virtual Display Driver uninstallation...")
        success = True
        
        try:
            # 1. Uninstall all detected VDD devices
            log_progress("Uninstalling VDD devices...")
            
            # Detect and uninstall all VDD devices
            vdd_devices = self._detect_vdd_devices()
            if vdd_devices:
                for device in vdd_devices:
                    try:
                        log_progress(f"Uninstalling device: {device['name']} ({device['instance_id']})")
                        
                        # Uninstall device with pnputil
                        result = subprocess.run([
                            'pnputil', '/remove-device', device['instance_id']
                        ], capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            log_success(f"Device removed: {device['name']}")
                        else:
                            log_warning(f"Failed to remove device {device['name']}: {result.stderr}")
                            
                    except Exception as e:
                        log_warning(f"Error removing device {device['name']}: {e}")
            else:
                log_info("No VDD devices detected")
            
            # 2. Remove driver from driver store
            log_progress("Removing driver from driver store...")
            try:
                # List drivers to find iddsampledriver or mttvdd
                result = subprocess.run(['pnputil', '/enum-drivers'], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    driver_patterns = ['iddsampledriver.inf', 'mttvdd.inf']
                    drivers_found = []
                    
                    for pattern in driver_patterns:
                        published_name = None
                        for i, line in enumerate(lines):
                            if pattern in line.lower():
                                # Search for published name in previous lines
                                for j in range(max(0, i-10), i):
                                    if 'published name' in lines[j].lower():
                                        published_name = lines[j].split(':')[-1].strip()
                                        break
                                if published_name:
                                    drivers_found.append((pattern, published_name))
                                break
                    
                    if drivers_found:
                        for driver_pattern, published_name in drivers_found:
                            log_progress(f"Removing driver {driver_pattern} ({published_name})...")
                            result = subprocess.run([
                                'pnputil', '/delete-driver', published_name, '/uninstall'
                            ], capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                log_success(f"Driver {driver_pattern} removed successfully")
                            else:
                                log_warning(f"Failed to remove driver {driver_pattern}")
                                success = False
                    else:
                        log_warning("No VDD drivers (IddSampleDriver.inf or MttVDD.inf) found in driver store")
                        
            except Exception as e:
                log_error(f"Error removing driver: {e}")
                success = False
            
            # 3. Remove installation files
            files_to_remove = self._tracker.get_files_to_remove("virtual_display_driver")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            # 4. Clean registry
            registry_keys = self._tracker.get_registry_keys("virtual_display_driver")
            if registry_keys and not self._remove_registry_keys(registry_keys):
                success = False
            
            if success:
                log_success("Virtual Display Driver uninstallation completed successfully")
            else:
                log_warning("VDD uninstallation completed with warnings")
            
            return success
            
        except Exception as e:
            log_error(f"Error during VDD uninstallation: {e}")
            return False
    
    def _verify_vdd_uninstalled(self) -> bool:
        """
        Verify that Virtual Display Driver was correctly uninstalled.
        
        Returns
        -------
        bool
            True if VDD is completely uninstalled.
        """
        log_progress("Verifying complete VDD uninstallation...")
        
        # 1. Check installation files
        for path in self._tracker.get_all_installation_paths("virtual_display_driver"):
            if os.path.exists(path):
                log_warning(f"Remaining VDD file detected: {path}")
                return False
        
        # 2. Check driver store
        try:
            result = subprocess.run(['pnputil', '/enum-drivers'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                output_lower = result.stdout.lower()
                if 'iddsampledriver.inf' in output_lower or 'mttvdd.inf' in output_lower:
                    log_warning("VDD driver still present in driver store")
                    return False
        except Exception:
            pass
        
        # 3. Check that no VDD devices are still present
        remaining_devices = self._detect_vdd_devices()
        if remaining_devices:
            log_warning(f"VDD devices still present: {len(remaining_devices)}")
            for device in remaining_devices:
                log_warning(f"  - {device['name']} ({device['instance_id']})")
            return False
        
        # 4. Check with PowerShell that no VDD MTT monitors are present
        try:
            ps_command = '''
            Get-PnpDevice -Class Display | Where-Object {
                $_.FriendlyName -match "VDD.*MTT|Virtual Display Driver"
            } | Measure-Object | Select-Object -ExpandProperty Count
            '''
            
            result = subprocess.run([
                'powershell', '-Command', ps_command
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                count = int(result.stdout.strip())
                if count > 0:
                    log_warning(f"Detected {count} VDD display devices still present")
                    return False
        except Exception as e:
            log_info(f"Unable to check display devices: {e}")
        
        log_success("Complete verification: VDD fully uninstalled")
        return True