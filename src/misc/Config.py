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

    def _reset_global_prep_cmd(self, config_file: str = '', setup_sunvdm: str = '', teardown_sunvdm: str = '', sunvdm_log: str = ''):
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

    def configure_sunshine(self, selective: bool = False):
        sunshine_install_dir = self.sr.all_configs["Sunshine"]["install_dir"]
        sunshine_service = self.sr.all_configs["Sunshine"]["service"]

        self._reset_global_prep_cmd()

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


class DownloadManager:
    """
    Download all the files needed to run Sunshine and other tools.
    """

    def __init__(self, system_requests: SystemRequests, page: int) -> None:
        self._page: int = page
        self._choice: int
        self._sr = system_requests
        self._config = Config(self._sr)

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
                
                # Enregistrer l'installation dans le tracker
                sunshine_install_dir = self.sr.all_configs["Sunshine"]["install_dir"]
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
            self.config.configure_sunshine()
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
        file_name = self._download_file(vdd_download_url, vdd_download_pattern, from_github=True, extract=False)

        # Since we disabled auto-extraction, file_name is now the zip file path
        vdd_downloaded_file_path = file_name

        if not os.path.exists(vdd_downloaded_file_path):
            log_error("Virtual Display Driver download failed")
            log_info(f"Expected path: {vdd_downloaded_file_path}")
            self.sr.pause()
            return

        if not install:
            self.sr.pause()
            return

        import zipfile
        import time
        vdd_final_path = os.path.join("tools", "VDD Control")
        temp_extract_path = os.path.join("tools", "temp_vdd_extract")
        
        # Remove existing directories if they exist
        if os.path.exists(vdd_final_path):
            try:
                log_info("Removing existing VDD Control directory...")
                shutil.rmtree(vdd_final_path)
                time.sleep(1.0)
            except Exception as e:
                log_warning(f"Could not remove existing VDD Control directory: {e}")
                
        if os.path.exists(temp_extract_path):
            try:
                shutil.rmtree(temp_extract_path)
                time.sleep(0.5)
            except Exception as e:
                log_warning(f"Could not remove temporary directory: {e}")
        
        # Step 1: Extract archive
        log_step(1, 3, "Extracting VDD archive")
        os.makedirs(temp_extract_path, exist_ok=True)
        
        try:
            with zipfile.ZipFile(vdd_downloaded_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_path)
            time.sleep(1.0)
            
        except Exception as e:
            log_error(f"ZIP extraction failed: {e}")
            self.sr.pause()
            return
        
        # Step 2: Locate VDD Control.exe
        log_step(2, 3, "Locating VDD Control executable")
        try:
            def find_vdd_control(path):
                """Recursively find VDD Control.exe"""
                for root, dirs, files in os.walk(path):
                    if "VDD Control.exe" in files:
                        return os.path.join(root, "VDD Control.exe")
                return None
            
            vdd_control_exe_in_temp = find_vdd_control(temp_extract_path)
            
            if not vdd_control_exe_in_temp:
                log_error("VDD Control.exe not found in the archive")
                self.sr.pause()
                return
            
            original_folder_path = os.path.dirname(vdd_control_exe_in_temp)
            
        except Exception as e:
            log_error(f"Archive analysis failed: {e}")
            self.sr.pause()
            return
        
        # Step 3: Setup VDD Control
        log_step(3, 3, "Setting up VDD Control")
        try:
            shutil.copytree(original_folder_path, vdd_final_path)
            time.sleep(0.5)
            
            # Clean up temp directory and original archive
            try:
                shutil.rmtree(temp_extract_path)
                os.remove(vdd_downloaded_file_path)
            except Exception as e:
                log_warning(f"Could not clean up temporary files: {e}")
                
        except Exception as e:
            log_warning(f"Primary setup method failed: {e}")
            # Try alternative method
            try:
                if os.path.exists(vdd_final_path):
                    shutil.rmtree(vdd_final_path)
                shutil.move(original_folder_path, vdd_final_path)
                try:
                    shutil.rmtree(temp_extract_path)
                    os.remove(vdd_downloaded_file_path)
                except:
                    pass
            except Exception as e2:
                log_error(f"VDD Control setup failed: {e2}")
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
        
        # Enregistrer l'installation dans le tracker
        try:
            install_info = {
                "version": "latest",
                "installer_type": "manual_vdd_control",
                "files_created": [vdd_final_path],
                "custom_options": {
                    "control_executable": vdd_control_exe,
                    "installation_method": "VDD Control extraction"
                }
            }
            self._tracker.track_installation("virtual_display_driver", vdd_final_path, install_info)
            log_info("Installation tracked for future uninstallation")
        except Exception as e:
            log_warning(f"Could not track installation: {e}")
        
        log_success("Virtual Display Driver installation completed!")
        log_info(f"VDD Control remains available at: {vdd_final_path}")

        if selective:
            self.sr.pause()

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
                self.config.configure_sunshine()
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
                
                # Enregistrer l'installation dans le tracker
                playnite_install_dir = self.sr.all_configs["Playnite"]["install_dir"]
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
