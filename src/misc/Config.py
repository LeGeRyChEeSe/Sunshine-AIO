import json
import os
import shutil
import requests
import subprocess
from misc.SystemRequests import SystemRequests
from misc.Logger import log_success, log_info, log_warning, log_error, log_progress, log_header, log_step, log_exception, log_section_start, log_section_end
from misc.InstallationTracker import get_installation_tracker


class Config:

    def __init__(self, system_requests: SystemRequests) -> None:
        self._sr = system_requests
        self._release = self._sr.release
        self.vdd_friendly_name = ''
        self._tracker = get_installation_tracker(system_requests._base_path)

    @property
    def sr(self):
        return self._sr

    @sr.setter
    def sr(self):
        raise ValueError("No manual edit allowed.")

    @property
    def release(self):
        return self._release

    @release.setter
    def release(self):
        raise ValueError("No manual edit allowed.")

    def _reset_global_prep_cmd(self, sunshine_install_dir: str = '', config_file: str = '', setup_sunvdm: str = '', teardown_sunvdm: str = '', sunvdm_log: str = ''):
        if not sunshine_install_dir:
            sunshine_install_dir = self.sr.all_configs["Sunshine"]["install_dir"]

        svm = self.sr.all_configs["SunshineVirtualMonitor"]
        svm_downloaded_dir_path = os.path.abspath(svm["downloaded_dir_path"])

        if not os.path.exists(sunshine_install_dir):
            raise OSError("Sunshine is not installed.")
        if not os.path.exists(svm_downloaded_dir_path):
            raise OSError("Sunshine Virtual Monitor is not downloaded.")

        if setup_sunvdm == '':
            setup_sunvdm = self.sr.find_file(os.path.join(
                svm_downloaded_dir_path, "setup_sunvdm.ps1"))

        if teardown_sunvdm == '':
            teardown_sunvdm = self.sr.find_file(os.path.join(
                svm_downloaded_dir_path, "teardown_sunvdm.ps1"))

        if sunvdm_log == '':
            sunvdm_log = os.path.join(svm_downloaded_dir_path, "sunvdm.log")

        subprocess.run(["powershell.exe", "-Command",
                        "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass"])
        if setup_sunvdm and os.path.exists(setup_sunvdm):
            subprocess.run(["powershell.exe", "-Command", f'Unblock-File "{setup_sunvdm}"'])
        if teardown_sunvdm and os.path.exists(teardown_sunvdm):
            subprocess.run(["powershell.exe", "-Command", f'Unblock-File "{teardown_sunvdm}"'])

        if self.vdd_friendly_name == '':
            self.vdd_friendly_name = self._get_vdd_friendly_name()

        if config_file == '':
            config_file = self.sr.find_file(os.path.join(
                sunshine_install_dir, "config", "sunshine.conf"))
        if not os.path.exists(config_file):
            return

        with open(config_file, 'r') as file:
            lines = file.readlines()

        global_prep_cmd = []
        for line in lines:
            if line.startswith("global_prep_cmd ="):
                try:
                    global_prep_cmd: list[dict[str, str]] = json.loads(line.split('=', 1)[1].strip())
                except json.JSONDecodeError as e:
                    print(f"JSON decoding error : {e}")
                    return
                break

        updated = False

        new_commands = {
            'do': f'cmd /C powershell.exe -executionpolicy bypass -windowstyle hidden -file "{setup_sunvdm}" %SUNSHINE_CLIENT_WIDTH% %SUNSHINE_CLIENT_HEIGHT% %SUNSHINE_CLIENT_FPS% %SUNSHINE_CLIENT_HDR% > "{sunvdm_log}" 2>&1',
            'undo': f'cmd /C powershell.exe -executionpolicy bypass -windowstyle hidden -file "{teardown_sunvdm}" >> "{sunvdm_log}" 2>&1',
            'elevated': 'true'
        }

        for existing_cmd in global_prep_cmd:
            if existing_cmd['do'].startswith(new_commands['do'].split('"')[0].strip()):
                existing_cmd.update(new_commands)
                updated = True

        if not updated:
            global_prep_cmd.append(new_commands)

        global_prep_cmd_str = json.dumps(global_prep_cmd)

        with open(config_file, 'w') as file:
            for line in lines:
                if not line.startswith("global_prep_cmd ="):
                    file.write(line)

            file.write(f'global_prep_cmd = {global_prep_cmd_str}\n')

    def _get_vdd_friendly_name(self):
        result = subprocess.run(["powershell.exe", "-Command", "(Get-PnpDevice", "-Class", "Display", "|", "Where-Object",
                                 "{$_.FriendlyName", "-like", "'*idd*'", "-or", "$_.FriendlyName", "-like", "'*mtt*'}).FriendlyName"], capture_output=True, text=True)
        if result.returncode != 0:
            return result.stderr
        return result.stdout.strip()

    def configure_sunshine(self, selective: bool = False, sunshine_path: str = None):
        # Use provided path if available
        if sunshine_path:
            sunshine_install_dir = sunshine_path
            log_info(f"Using provided Sunshine installation path: {sunshine_install_dir}")
            # Always update tracker when path is provided
            self._update_sunshine_tracker_if_needed(sunshine_install_dir)
        else:
            # Try to detect Sunshine installation path
            detected_path = self._detect_sunshine_installation_path()
            
            if detected_path:
                sunshine_install_dir = detected_path
                log_info(f"Using detected Sunshine installation path: {sunshine_install_dir}")
                # Always update tracker when path is detected
                self._update_sunshine_tracker_if_needed(sunshine_install_dir)
            else:
                # Prompt user for path
                user_path = self._prompt_for_sunshine_path()
                if user_path:
                    sunshine_install_dir = user_path
                    log_info(f"Using user-provided Sunshine installation path: {sunshine_install_dir}")
                    # Update tracker with user-provided path
                    self._update_sunshine_tracker_if_needed(sunshine_install_dir)
                else:
                    # Fall back to default if user cancels
                    sunshine_install_dir = self.sr.all_configs["Sunshine"]["install_dir"]
                    log_warning(f"Using default Sunshine installation path: {sunshine_install_dir}")
        
        sunshine_service = self.sr.all_configs["Sunshine"]["service"]

        self._reset_global_prep_cmd(sunshine_install_dir)

        if not self.sr.restart_sunshine_as_service(sunshine_service):
            if not self.sr.restart_sunshine_as_program(self.sr.find_file(os.path.join(sunshine_install_dir, "sunshine.exe"))):
                print("\nPlease manually restart Sunshine to apply changes.")

        print("\nSunshine was successfully configured.")
        if selective:
            self.sr.pause()

    def open_sunshine_settings(self):
        sunshine_settings_url = self.sr.all_configs["Sunshine"]["settings_url"]
        print("\nOpening Sunshine Settings...")
        print("\nNavigate to the Audio/Video tab to add your custom Resolutions and Frame Rates.")
        subprocess.run(f'start {sunshine_settings_url}', shell=True)
        self.sr.pause()

    def open_playnite(self):
        playnite_url = self.sr.all_configs["Playnite"]["url"]
        print("\nOpening Playnite...")
        subprocess.run(f'start {playnite_url}', shell=True)
        self.sr.pause()

    def _detect_sunshine_installation_path(self):
        """
        Detect the actual Sunshine installation path after installation.
        
        Returns:
            str: Detected installation path, or None if not found
        """
        import winreg
        
        # Method 1: Check registry for installation path
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Sunshine"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Sunshine"),
        ]
        
        for hkey, subkey_path in registry_keys:
            try:
                with winreg.OpenKey(hkey, subkey_path) as key:
                    try:
                        install_location = winreg.QueryValueEx(key, "InstallLocation")[0]
                        if install_location and os.path.exists(install_location):
                            sunshine_exe = os.path.join(install_location, "sunshine.exe")
                            if os.path.exists(sunshine_exe):
                                log_info(f"Found Sunshine installation via registry: {install_location}")
                                return install_location
                    except FileNotFoundError:
                        continue
            except Exception:
                continue
        
        # Method 2: Check common installation directories
        common_paths = [
            os.path.expandvars(r"%PROGRAMFILES%\Sunshine"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Sunshine"),
            os.path.expandvars(r"%LOCALAPPDATA%\Sunshine"),
            os.path.expandvars(r"%APPDATA%\Sunshine"),
        ]
        
        for path in common_paths:
            sunshine_exe = os.path.join(path, "sunshine.exe")
            if os.path.exists(sunshine_exe):
                log_info(f"Found Sunshine installation in common path: {path}")
                return path
        
        # Method 3: Check PATH environment variable
        import shutil
        sunshine_exe_path = shutil.which("sunshine")
        if sunshine_exe_path:
            install_dir = os.path.dirname(sunshine_exe_path)
            log_info(f"Found Sunshine installation via PATH: {install_dir}")
            return install_dir
        
        return None

    def _update_sunshine_tracker_if_needed(self, sunshine_install_dir: str):
        """
        Update installation tracker with detected Sunshine path if not already tracked.
        
        Parameters:
            sunshine_install_dir (str): The detected installation directory
        """
        from misc.InstallationTracker import InstallationTracker
        
        # Initialize tracker if needed
        if not hasattr(self, '_tracker'):
            self._tracker = InstallationTracker()
        
        # Check if Sunshine is already tracked
        tracked_paths = self._tracker.get_all_installation_paths("sunshine")
        
        if not tracked_paths or sunshine_install_dir not in tracked_paths:
            log_info("Updating installation tracker with detected Sunshine path")
            install_info = {
                "version": "unknown",
                "installer_type": "official_installer", 
                "files_created": [sunshine_install_dir],
                "registry_entries": [],
                "shortcuts_created": []
            }
            
            self._tracker.track_installation("sunshine", sunshine_install_dir, install_info)
            log_success("Installation tracker updated with detected path")


class DownloadManager:
    """
    Download all the files needed to run Sunshine and other tools.
    """

    def __init__(self, system_requests: SystemRequests, page: int) -> None:
        self._page: int = page
        self._choice: int
        self._sr = system_requests
        self._config = Config(self._sr)
        self._tracker = get_installation_tracker(system_requests._base_path)

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self):
        raise ValueError("No manual edit allowed.")

    @property
    def choice(self):
        return self._choice

    @choice.setter
    def choice(self):
        raise ValueError("No manual edit allowed.")

    @property
    def sr(self):
        return self._sr

    @sr.setter
    def sr(self):
        raise ValueError("No manual edit allowed.")

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self):
        raise ValueError("No manual edit allowed.")

    def _detect_sunshine_installation_path(self):
        """
        Detect the actual Sunshine installation path after installation.
        
        Returns:
            str: Detected installation path, or None if not found
        """
        import winreg
        
        # Method 1: Check registry for installation path
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Sunshine"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Sunshine"),
        ]
        
        for hkey, subkey_path in registry_keys:
            try:
                with winreg.OpenKey(hkey, subkey_path) as key:
                    try:
                        install_location = winreg.QueryValueEx(key, "InstallLocation")[0]
                        if install_location and os.path.exists(install_location):
                            sunshine_exe = os.path.join(install_location, "sunshine.exe")
                            if os.path.exists(sunshine_exe):
                                return install_location.rstrip('\\')
                    except FileNotFoundError:
                        continue
            except FileNotFoundError:
                continue
        
        # Method 2: Check common installation paths
        common_paths = [
            r"C:\Program Files\Sunshine",
            r"C:\Program Files (x86)\Sunshine",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Sunshine"),
            os.path.expandvars(r"%APPDATA%\Sunshine"),
        ]
        
        # Method 3: Check user's Documents folder (where you installed)
        documents_path = os.path.expandvars(r"%USERPROFILE%\Documents\Sunshine")
        common_paths.append(documents_path)
        
        for path in common_paths:
            if os.path.exists(path):
                sunshine_exe = os.path.join(path, "sunshine.exe")
                if os.path.exists(sunshine_exe):
                    return path
        
        # Method 4: Search for sunshine.exe in likely locations
        search_paths = [
            os.path.expandvars(r"%USERPROFILE%\Documents"),
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                for root, dirs, files in os.walk(search_path):
                    if "sunshine.exe" in files and "Sunshine" in root:
                        return root
                    # Limit search depth to avoid long searches
                    if root.count(os.sep) - search_path.count(os.sep) >= 2:
                        dirs.clear()
        
        return None

    def _prompt_for_sunshine_path(self):
        """
        Prompt user for Sunshine installation path when automatic detection fails.
        
        Returns:
            str: Validated Sunshine installation path, or None if user cancels
        """
        return None  # Disabled manual prompting - use detected or default paths only


    def _download_file(self, url: str, name_filter: str = "", from_github: bool = False, vdd_version: str = "0", extract: bool = True):
        download_url, file_name = "", name_filter

        os.makedirs('tools', exist_ok=True)

        if from_github:
            download_type = self.sr.check_download_url(url)
            url = url.replace("https://github.com/",
                              "https://api.github.com/repos/")

            response = requests.get(url)
            data = response.json()

            if download_type == "releases":
                for release in data:
                    if not release["prerelease"]:
                        if vdd_version != '0':
                            if f"Windows {vdd_version}" in release["name"]:
                                file_name = release["assets"][0]["name"]
                                download_url = release["assets"][0]["browser_download_url"]
                                break
                        else:
                            for r in release['assets']:
                                if name_filter in r['name']:
                                    file_name = r['name']
                                    download_url = r['browser_download_url']

            elif download_type == "latest":
                release = data
                if not release["prerelease"]:
                    for r in release['assets']:
                        if name_filter in r['name']:
                            file_name = r['name']
                            download_url = r['browser_download_url']

            elif download_type == "direct":
                download_url = url

            else:
                print("URL format is not supported.")
                return ""

            response = requests.get(download_url)
        else:
            response = requests.get(url)

        file_path = os.path.abspath(os.path.join("tools", file_name))

        self.sr.is_path_contains_spaces(file_path)

        with open(file_path, 'wb') as file:
            log_progress(f"Downloading {file_name}")
            file.write(response.content)

        log_success(f'File downloaded to "{file_path}"')

        if extract:
            final_file_name = self.sr.extract_file(file_path)
        else:
            final_file_name = file_path

        return final_file_name

    def download_all(self, install: bool = True):
        log_section_start("Complete Installation")
        log_header("Sunshine-AIO Complete Setup", "Installing all components")
        
        try:
            self.sr.clear_screen()
            self.sr.reset_tools_folder()
            
            components = [
                ("Sunshine", self.download_sunshine),
                ("Virtual Display Driver", self.download_vdd),
                ("Sunshine Virtual Monitor", self.download_svm),
                ("Playnite", self.download_playnite),
                ("Playnite Watcher", self.download_playnite_watcher)
            ]
            
            success_count = 0
            total_components = len(components)
            
            for i, (name, func) in enumerate(components, 1):
                try:
                    log_progress(f"Component {i}/{total_components}: {name}")
                    func(install)
                    success_count += 1
                    log_success(f"{name} completed successfully")
                except Exception as e:
                    log_exception(f"Failed to install {name}", e)
                    log_error(f"{name} installation failed - continuing with next component")

            # Final summary
            if success_count == total_components:
                if install:
                    log_success('All components have been downloaded and installed successfully!')
                else:
                    log_success('All components have been downloaded to the "tools" folder.')
            else:
                log_warning(f'Installation completed with issues: {success_count}/{total_components} components successful')
                log_info('Check the log file for detailed error information')
                
        except Exception as e:
            log_exception("Critical error during complete installation", e)
        finally:
            log_section_end("Complete Installation")
            self.sr.pause()

    def download_sunshine(self, install: bool = True, selective: bool = False):
        sunshine = self.sr.all_configs["Sunshine"]
        sunshine_download_url = sunshine["download_url"]
        sunshine_download_pattern = sunshine["download_pattern"]
        sunshine_downloaded_dir_path = os.path.abspath(
            sunshine["downloaded_dir_path"])

        if selective:
            self.sr.clear_screen()

        self._download_file(sunshine_download_url,
                            sunshine_download_pattern, from_github=True)

        sunshine_downloaded_file_path = self.sr.find_file(
            os.path.join(sunshine_downloaded_dir_path, r"sunshine*.exe"))

        if sunshine_downloaded_file_path and install:
            log_progress("Installing Sunshine...")
            try:
                subprocess.run(
                    ["start", "/wait", os.path.abspath(sunshine_downloaded_file_path)], shell=True, check=True)
                
                # Detect actual installation path
                sunshine_install_dir = self._detect_sunshine_installation_path()
                if not sunshine_install_dir:
                    # Fallback to default path from config
                    sunshine_install_dir = self.sr.all_configs["Sunshine"]["install_dir"]
                    log_warning("Could not detect Sunshine installation path, using default")
                else:
                    log_info(f"Detected Sunshine installation at: {sunshine_install_dir}")
                
                # Register installation in tracker
                install_info = {
                    "version": "latest",
                    "installer_type": "official_installer",
                    "files_created": [sunshine_install_dir],
                    "services_created": ["SunshineService"],
                    "registry_entries": [
                        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Sunshine"
                    ],
                    "custom_options": {
                        "installer_path": sunshine_downloaded_file_path,
                        "installation_method": "Windows installer"
                    }
                }
                self._tracker.track_installation("sunshine", sunshine_install_dir, install_info)
                log_info("Sunshine installation tracked for future uninstallation")
                
            except Exception as e:
                log_error(f"Sunshine installation failed: {e}")
                if selective:
                    self.sr.pause()
                return

        if install and selective:
            svm_downloaded_dir_path = os.path.abspath(
                self.sr.all_configs["SunshineVirtualMonitor"]["downloaded_dir_path"])
            if not os.path.exists(svm_downloaded_dir_path):
                self.download_svm()
            
            # Use detected installation path for configuration
            detected_path = self._detect_sunshine_installation_path()
            self.config.configure_sunshine(sunshine_path=detected_path)
            print("\nSunshine has been well configured.")
        elif not install and selective:
            self.sr.pause()

    def download_vdd(self, install: bool = True, selective: bool = False):
        vdd = self.sr.all_configs["VirtualDisplayDriver"]
        vdd_download_url = vdd["download_url"]
        vdd_download_pattern = vdd["download_pattern"]
        vdd_device_id = vdd["device_id"]

        if selective:
            self.sr.clear_screen()

        log_progress("Downloading Virtual Display Driver from GitHub...")
        file_name = self._download_file(vdd_download_url, vdd_download_pattern, from_github=True, extract=True)

        # Now file_name is the extracted directory path
        vdd_extracted_dir_path = file_name

        if not os.path.exists(vdd_extracted_dir_path):
            log_error("Virtual Display Driver extraction failed")
            log_info(f"Expected path: {vdd_extracted_dir_path}")
            self.sr.pause()
            return

        if not install:
            # Mode "download only" - garder le nom original
            log_success(f"VDD Control downloaded successfully to: {vdd_extracted_dir_path}")
            self.sr.pause()
            return

        # Mode "download and install" - renommer vers "VDD Control"
        import time
        vdd_final_path = os.path.join("tools", "VDD Control")
        
        # Locate VDD Control.exe in extracted folder
        log_step(1, 2, "Locating VDD Control executable")
        try:
            def find_vdd_control(path):
                """Recursively find VDD Control.exe"""
                for root, dirs, files in os.walk(path):
                    if "VDD Control.exe" in files:
                        return os.path.join(root, "VDD Control.exe")
                return None
            
            vdd_control_exe_in_extracted = find_vdd_control(vdd_extracted_dir_path)
            
            if not vdd_control_exe_in_extracted:
                log_error("VDD Control.exe not found in the extracted files")
                self.sr.pause()
                return
            
            original_folder_path = os.path.dirname(vdd_control_exe_in_extracted)
            
        except Exception as e:
            log_error(f"VDD Control search failed: {e}")
            self.sr.pause()
            return
        
        # Step 2: Renommer/déplacer vers "VDD Control"
        log_step(2, 2, "Setting up VDD Control for installation")
        try:
            # Remove existing "VDD Control" folder if it exists
            if os.path.exists(vdd_final_path):
                log_info("Removing existing VDD Control directory...")
                shutil.rmtree(vdd_final_path)
                time.sleep(1.0)
            
            # Rename extracted folder to "VDD Control"
            os.rename(vdd_extracted_dir_path, vdd_final_path)
            log_success(f"VDD Control renamed to: {vdd_final_path}")
                
        except Exception as e:
            log_warning(f"Rename failed, trying copy method: {e}")
            # Alternative method: copy then remove original
            try:
                if os.path.exists(vdd_final_path):
                    shutil.rmtree(vdd_final_path)
                shutil.copytree(original_folder_path, vdd_final_path)
                # Remove original folder to avoid duplicates
                shutil.rmtree(vdd_extracted_dir_path)
                log_success(f"VDD Control copied to: {vdd_final_path}")
            except Exception as e2:
                log_error(f"Configuration de VDD Control échouée: {e2}")
                self.sr.pause()
                return
        
        # Final verification
        vdd_control_exe = os.path.join(vdd_final_path, "VDD Control.exe")
        if not os.path.exists(vdd_control_exe):
            log_error("VDD Control setup verification failed")
            self.sr.pause()
            return

        log_success("VDD Control extracted and configured successfully")

        log_header("Virtual Display Driver Installation")
        log_info("A 'Virtual Display Driver Control' window will open.")
        log_info("Please follow these steps:")
        log_info("1. Click on the 'Install Driver' button")
        log_info("2. Wait for the installation to complete")
        log_info("3. Close the VDD Control program properly")
        log_info("4. Return here and press Enter to continue")
        log_info(f"Note: VDD Control will remain available at: {vdd_final_path}")
        input("\nPress Enter to launch VDD Control...")

        try:
            import subprocess
            subprocess.Popen([vdd_control_exe], cwd=vdd_final_path)
            log_success("VDD Control launched successfully!")
        except Exception as e:
            log_error(f"Failed to launch VDD Control: {e}")
            self.sr.pause()
            return

        input("\nAfter closing VDD Control, press Enter to continue...")
        
        # Register installation in tracker with driver type detection
        try:
            # Detect installed driver type
            driver_info = self._detect_installed_vdd_driver()
            
            install_info = {
                "version": "latest",
                "installer_type": "manual_vdd_control",
                "files_created": [vdd_final_path],
                "drivers_installed": driver_info.get("drivers", []),
                "device_ids": driver_info.get("device_ids", []),
                "custom_options": {
                    "control_executable": vdd_control_exe,
                    "installation_method": "VDD Control extraction",
                    "driver_type": driver_info.get("driver_type", "unknown"),
                    "driver_path": driver_info.get("driver_path", ""),
                    "device_id_detected": driver_info.get("device_id_detected", "")
                }
            }
            self._tracker.track_installation("virtual_display_driver", vdd_final_path, install_info)
            log_info("Installation tracked for future uninstallation")
            
            if driver_info.get("driver_type"):
                log_info(f"Driver type detected: {driver_info['driver_type']}")
                if driver_info.get("device_id_detected"):
                    log_info(f"Device ID detected: {driver_info['device_id_detected']}")
                    
        except Exception as e:
            log_warning(f"Could not track installation: {e}")
        
        log_success("Virtual Display Driver installation completed!")
        log_info(f"VDD Control remains available at: {vdd_final_path}")

        if selective:
            self.sr.pause()

    def _detect_installed_vdd_driver(self):
        """
        Detect VDD driver type installed by analyzing driver store.
        Supports both old (IddSampleDriver) and new (MttVDD) drivers.
        
        Returns:
            dict: Informations sur le driver détecté
        """
        driver_info = {
            "driver_type": "unknown",
            "drivers": [],
            "device_ids": [],
            "driver_path": "",
            "device_id_detected": ""
        }
        
        try:
            # Get driver patterns from config
            vdd_config = self.sr.all_configs.get("VirtualDisplayDriver", {})
            
            # List all installed drivers
            result = subprocess.run(['pnputil', '/enum-drivers'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                
                # Support both old and new drivers
                driver_patterns = [
                    (vdd_config.get("driver_inf_old", "iddsampledriver.inf"), "IddSampleDriver", vdd_config.get("device_id", "root\\iddsampledriver")),
                    (vdd_config.get("driver_inf_new", "mttvdd.inf"), "MttVDD", vdd_config.get("device_id_new", "root\\mttvdd"))
                ]
                
                drivers_found = []
                
                for i, line in enumerate(lines):
                    for pattern, driver_type, device_id in driver_patterns:
                        if pattern.lower() in line.lower():
                            # Search for driver information in surrounding lines
                            published_name = None
                            driver_path = ""
                            
                            for j in range(max(0, i-10), min(len(lines), i+10)):
                                current_line = lines[j].lower()
                                
                                # Search for published name
                                if 'published name' in current_line:
                                    published_name = lines[j].split(':')[-1].strip()
                                
                                # Search for driver path
                                if 'driver package' in current_line or 'inf name' in current_line:
                                    if pattern.lower() in current_line:
                                        driver_path = lines[j].split(':')[-1].strip()
                            
                            if published_name:
                                drivers_found.append({
                                    "pattern": pattern,
                                    "driver_type": driver_type,
                                    "device_id": device_id,
                                    "published_name": published_name,
                                    "driver_path": driver_path
                                })
                                log_info(f"Driver VDD détecté: {driver_type} ({pattern})")
                
                # Process found drivers
                if drivers_found:
                    # Use the most recent/preferred driver (MttVDD if available, else IddSampleDriver)
                    preferred_driver = None
                    for driver in drivers_found:
                        if driver["driver_type"] == "MttVDD":
                            preferred_driver = driver
                            break
                    
                    if not preferred_driver:
                        preferred_driver = drivers_found[0]
                    
                    driver_info["driver_type"] = preferred_driver["driver_type"]
                    driver_info["device_id_detected"] = preferred_driver["device_id"]
                    driver_info["driver_path"] = preferred_driver["driver_path"]
                    
                    # Add all found drivers to the list
                    for driver in drivers_found:
                        driver_info["drivers"].append(driver["published_name"])
                        driver_info["device_ids"].append(driver["device_id"])
            
        except Exception as e:
            log_warning(f"Error detecting VDD driver: {e}")
        
        return driver_info

    def download_svm(self, install: bool = True, selective: bool = False):
        log_section_start("Sunshine Virtual Monitor Setup")
        
        try:
            svm = self.sr.all_configs["SunshineVirtualMonitor"]
            svm_download_url = svm["download_url"]
            svm_download_pattern = svm["download_pattern"]

            if selective:
                self.sr.clear_screen()

            log_progress("Starting Sunshine Virtual Monitor download and setup")
            log_info(f"Download URL: {svm_download_url}")
            log_info(f"Pattern: {svm_download_pattern}")

            # Step 1: Download SVM
            log_step(1, 5, "Downloading Sunshine Virtual Monitor")
            try:
                self._download_file(svm_download_url, svm_download_pattern)
                log_success("Sunshine Virtual Monitor downloaded successfully")
            except Exception as e:
                log_exception("Failed to download Sunshine Virtual Monitor", e)
                if selective:
                    self.sr.pause()
                return

            if not install:
                log_info("Download-only mode, skipping installation")
                if selective:
                    self.sr.pause()
                return

            # Step 2: Install Windows Display Manager
            log_step(2, 5, "Installing Windows Display Manager PowerShell module")
            try:
                self.sr.install_windows_display_manager()
                log_success("Windows Display Manager installed successfully")
            except Exception as e:
                log_exception("Failed to install Windows Display Manager", e)
                # Continue with installation despite this error

            # Step 3: Download Multi Monitor Tool
            log_step(3, 5, "Downloading Multi Monitor Tool")
            try:
                self.download_mmt()
                log_success("Multi Monitor Tool downloaded and configured")
            except Exception as e:
                log_exception("Failed to download/configure Multi Monitor Tool", e)
                # Continue with installation

            # Step 4: Download VSync Toggle
            log_step(4, 5, "Downloading VSync Toggle")
            try:
                self.download_vsync_toggle()
                log_success("VSync Toggle downloaded successfully")
            except Exception as e:
                log_exception("Failed to download VSync Toggle", e)
                # Continue with installation

            # Step 5: Configure Sunshine
            log_step(5, 5, "Configuring Sunshine for Virtual Monitor")
            try:
                # Use detected installation path for configuration
                detected_path = self._detect_sunshine_installation_path()
                self.config.configure_sunshine(sunshine_path=detected_path)
                log_success("Sunshine configured for Virtual Monitor use")
            except Exception as e:
                log_exception("Failed to configure Sunshine", e)
                # Continue to completion

            # Enregistrer l'installation dans le tracker
            try:
                svm_install_path = os.path.abspath(svm["downloaded_dir_path"])
                install_info = {
                    "version": "latest",
                    "installer_type": "script_package",
                    "files_created": [svm_install_path],
                    "custom_options": {
                        "download_url": svm_download_url,
                        "pattern": svm_download_pattern,
                        "installation_method": "Script extraction and configuration",
                        "dependencies": ["virtual_display_driver", "multi_monitor_tool", "vsync_toggle"]
                    }
                }
                self._tracker.track_installation("sunshine_virtual_monitor", svm_install_path, install_info)
                log_info("Sunshine Virtual Monitor installation tracked for future uninstallation")
            except Exception as e:
                log_warning(f"Could not track SVM installation: {e}")
            
            log_success("Sunshine Virtual Monitor installation completed!")
            log_info("All components have been downloaded and configured")

        except Exception as e:
            log_exception("Critical error during Sunshine Virtual Monitor setup", e)
            log_error("Sunshine Virtual Monitor setup failed")
        finally:
            log_section_end("Sunshine Virtual Monitor Setup")
            if selective:
                self.sr.pause()

    def download_mmt(self, selective: bool = False):
        mmt = self.sr.all_configs["MultiMonitorTool"]
        mmt_download_url = mmt["download_url"]
        mmt_download_pattern = mmt["download_pattern"]
        mmt_downloaded_dir_path = mmt["downloaded_dir_path"]
        svm_downloaded_dir_path = self.sr.find_file(
            self.sr.all_configs["SunshineVirtualMonitor"]["downloaded_dir_path"])

        if selective:
            self.sr.clear_screen()

        self._download_file(
            mmt_download_url, mmt_download_pattern)

        if svm_downloaded_dir_path:
            destination_folder = os.path.join(
                svm_downloaded_dir_path, "multimonitortool-x64")
            if os.path.exists(destination_folder):
                shutil.rmtree(destination_folder)
            print(f'\nMove "{mmt_downloaded_dir_path}" to "{destination_folder}"')
            shutil.move(mmt_downloaded_dir_path, destination_folder)
            
            # Enregistrer l'installation dans le tracker
            try:
                install_info = {
                    "version": "latest",
                    "installer_type": "portable_tool",
                    "files_created": [destination_folder],
                    "custom_options": {
                        "download_url": mmt_download_url,
                        "pattern": mmt_download_pattern,
                        "installation_method": "Portable tool extraction",
                        "parent_tool": "sunshine_virtual_monitor"
                    }
                }
                self._tracker.track_installation("multi_monitor_tool", destination_folder, install_info)
                log_info("Multi Monitor Tool installation tracked for future uninstallation")
            except Exception as e:
                log_warning(f"Could not track MMT installation: {e}")

        if selective:
            self.sr.pause()

    def download_vsync_toggle(self, selective: bool = False):
        vsync = self.sr.all_configs["VsyncToggle"]
        vsync_download_url = vsync["download_url"]
        vsync_download_pattern = vsync["download_pattern"]
        vsync_downloaded_dir_path = vsync["downloaded_dir_path"]

        if selective:
            self.sr.clear_screen()

        self._download_file(vsync_download_url,
                            vsync_download_pattern, from_github=True)

        source_file = self.sr.find_file(os.path.join(
            vsync_downloaded_dir_path, r"vsynctoggle*.exe"))
        destination_folder = self.sr.find_file(os.path.join(
            vsync_downloaded_dir_path, "sunshine-virtual-monitor-main"))

        if source_file and destination_folder:
            destination_file = os.path.join(
                destination_folder, "vsynctoggle-1.1.0-x86_64.exe")
            if os.path.exists(destination_file):
                os.remove(destination_file)
            print(f'\nMove "{source_file}" to "{destination_file}"')
            shutil.move(source_file, destination_file)
            
            # Enregistrer l'installation dans le tracker
            try:
                install_info = {
                    "version": "1.1.0",
                    "installer_type": "portable_tool",
                    "files_created": [destination_file],
                    "custom_options": {
                        "download_url": vsync_download_url,
                        "pattern": vsync_download_pattern,
                        "installation_method": "Portable executable extraction",
                        "parent_tool": "sunshine_virtual_monitor",
                        "original_source": source_file
                    }
                }
                self._tracker.track_installation("vsync_toggle", destination_file, install_info)
                log_info("VSync Toggle installation tracked for future uninstallation")
            except Exception as e:
                log_warning(f"Could not track VSync Toggle installation: {e}")

        if selective:
            self.sr.pause()

    def download_playnite(self, install: bool = True, selective: bool = False):
        playnite = self.sr.all_configs["Playnite"]
        playnite_download_url = playnite["download_url"]
        playnite_download_pattern = playnite["download_pattern"]
        playnite_downloaded_dir_path = playnite["downloaded_dir_path"]

        if selective:
            self.sr.clear_screen()

        self._download_file(playnite_download_url, playnite_download_pattern)

        if not install:
            self.sr.pause()
            return

        playnite_downloaded_file_path = self.sr.find_file(
            os.path.join(playnite_downloaded_dir_path, playnite_download_pattern))

        if playnite_downloaded_file_path:
            log_progress("Installing Playnite...")
            try:
                subprocess.run(
                    ["start", "/wait", os.path.abspath(playnite_downloaded_file_path)], shell=True, check=True)
                
                # Register installation in tracker
                # Playnite installe généralement dans AppData ou Program Files
                playnite_install_dir = os.path.expandvars(r"%LOCALAPPDATA%\Playnite")
                install_info = {
                    "version": "latest",
                    "installer_type": "official_installer",
                    "files_created": [playnite_install_dir],
                    "registry_entries": [
                        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Playnite"
                    ],
                    "custom_options": {
                        "installer_path": playnite_downloaded_file_path,
                        "installation_method": "Windows installer"
                    }
                }
                self._tracker.track_installation("playnite", playnite_install_dir, install_info)
                log_info("Playnite installation tracked for future uninstallation")
                
            except Exception as e:
                log_error(f"Playnite installation failed: {e}")
                if selective:
                    self.sr.pause()
                return
        
        log_success("Playnite was successfully installed.")

        if selective:
            self.sr.pause()

    def download_playnite_watcher(self, install: bool = True, selective: bool = False):
        playnitew = self.sr.all_configs["PlayniteWatcher"]
        playnitew_download_url = playnitew["download_url"]
        playnitew_download_pattern = playnitew["download_pattern"]
        playnitew_guide_url = playnitew["guide_url"]
        playnitew_addon_url = playnitew["addon_url"]

        if selective:
            self.sr.clear_screen()

        self._download_file(playnitew_download_url,
                            playnitew_download_pattern, from_github=True)

        if not install:
            playnitew_guide = input(
                "\nOpen PlayNite Watcher Setup Guide ? (Y/n) ")

            if playnitew_guide.strip().lower() in ['y', 'ye', 'yes', '']:
                subprocess.run(["start", playnitew_guide_url], shell=True)
            self.sr.pause()
            return

        if self.config.release == '11':
            windows_settings = input(
                "\nPlease set the default terminal to Windows Console Host. Open Windows Settings ? (Y/n) ")
            if windows_settings.strip().lower() in ['y', 'ye', 'yes', '']:
                subprocess.run(
                    ["start", "ms-settings:developers"], shell=True, check=True)

        sap = input("\nInstall 'Sunshine App Export' on Playnite ? (Y/n) ")

        if sap.strip().lower() in ['y', 'ye', 'yes', '']:
            subprocess.run(["start", playnitew_addon_url],
                           shell=True, check=True)

        playnitew_guide = input(
            "\nOpen PlayNite Watcher Setup Guide ? (Y/n) ")

        if playnitew_guide.strip().lower() in ['y', 'ye', 'yes', '']:
            subprocess.run(["start", playnitew_guide_url], shell=True)

        # Enregistrer l'installation dans le tracker
        try:
            playnitew_install_path = self.sr.all_configs["PlayniteWatcher"]["downloaded_dir_path"]
            install_info = {
                "version": "latest",
                "installer_type": "manual_setup",
                "files_created": [playnitew_install_path],
                "custom_options": {
                    "download_url": playnitew_download_url,
                    "pattern": playnitew_download_pattern,
                    "installation_method": "Manual setup with addon",
                    "guide_url": playnitew_guide_url,
                    "addon_url": playnitew_addon_url,
                    "requires_manual_configuration": True
                }
            }
            self._tracker.track_installation("playnite_watcher", playnitew_install_path, install_info)
            log_info("Playnite Watcher installation tracked for future uninstallation")
        except Exception as e:
            log_warning(f"Could not track Playnite Watcher installation: {e}")

        log_success("Playnite Watcher was successfully installed.")

        if selective:
            self.sr.pause()
