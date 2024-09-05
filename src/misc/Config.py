import json
import os
import shutil
import requests
import subprocess
from misc.SystemRequests import SystemRequests


class Config:

    def __init__(self, system_requests: SystemRequests) -> None:
        self._sr = system_requests
        self._release = self._sr.release

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

    def _reset_global_prep_cmd(self, file_path: str, new_commands: dict[str, str]):
        if not os.path.exists(file_path):
            return

        with open(file_path, 'r') as file:
            lines = file.readlines()

        global_prep_cmd = []
        for line in lines:
            if line.startswith("global_prep_cmd ="):
                try:
                    global_prep_cmd: list[dict[str, str]] = json.loads(line.split('=', 1)[1].strip())
                except json.JSONDecodeError as e:
                    print(f"Erreur de décodage JSON : {e}")
                    return
                break

        updated = False

        for existing_cmd in global_prep_cmd:
            if existing_cmd['do'].startswith(new_commands['do'].split('"')[0].strip()):
                existing_cmd.update(new_commands)
                updated = True

        if not updated:
            global_prep_cmd.append(new_commands)

        global_prep_cmd_str = json.dumps(global_prep_cmd)

        with open(file_path, 'w') as file:
            for line in lines:
                if not line.startswith("global_prep_cmd ="):
                    file.write(line)

            file.write(f'global_prep_cmd = {global_prep_cmd_str}\n')

    def _get_vdd_friendly_name(self):
        command = "Get-PnpDevice -Class Display | Select-Object FriendlyName | ConvertTo-Json"

        for _ in range(100):
            result = subprocess.run(f"powershell -Command \"{command}\"", capture_output=True, text=True)

            if result.returncode == 0:
                display_devices = json.loads(result.stdout)

                for device in display_devices:
                    friendly_name: str = device.get('FriendlyName', '')
                    if friendly_name != None:
                        if 'IddSampleDriver' in friendly_name or 'by MTT' in friendly_name:
                            return friendly_name

    def configure_sunshine(self):
        sunshine_install_dir = self._sr.all_configs["Sunshine"]["install_dir"]
        sunshine_service = self._sr.all_configs["Sunshine"]["service"]

        svm = self._sr.all_configs["SunshineVirtualMonitor"]
        svm_downloaded_dir_path = os.path.abspath(svm["downloaded_dir_path"])

        if not os.path.exists(sunshine_install_dir):
            raise OSError("Sunshine is not installed.")
        if not os.path.exists(svm_downloaded_dir_path):
            raise OSError("Sunshine Virtual Monitor is not downloaded.")

        setup_sunvdm = self._sr.find_file(os.path.join(
            svm_downloaded_dir_path, "setup_sunvdm.ps1"))
        teardown_sunvdm = self._sr.find_file(os.path.join(
            svm_downloaded_dir_path, "teardown_sunvdm.ps1"))
        sunvdm_log = os.path.join(svm_downloaded_dir_path, "sunvdm.log")

        subprocess.run(["powershell.exe", "-Command",
                        "Set-ExecutionPolicy RemoteSigned"])
        if setup_sunvdm and os.path.exists(setup_sunvdm):
            subprocess.run(["powershell.exe", "-Command", f"Unblock-File {setup_sunvdm}"])
        if teardown_sunvdm and os.path.exists(teardown_sunvdm):
            subprocess.run(["powershell.exe", "-Command", f"Unblock-File {teardown_sunvdm}"])

        self._sr.check_execution_policy()

        vdd_friendly_name = self._get_vdd_friendly_name()

        config_file = self._sr.find_file(os.path.join(
            sunshine_install_dir, "config", "sunshine.conf"))

        commands = {
            'do': f'cmd /C powershell.exe -executionpolicy bypass -windowstyle hidden -file "{setup_sunvdm}" %SUNSHINE_CLIENT_WIDTH% %SUNSHINE_CLIENT_HEIGHT% %SUNSHINE_CLIENT_FPS% %SUNSHINE_CLIENT_HDR% "{vdd_friendly_name}" > "{sunvdm_log}" 2>&1',
            'undo': f'cmd /C powershell.exe -executionpolicy bypass -windowstyle hidden -file "{teardown_sunvdm}" "{vdd_friendly_name}" >> "{sunvdm_log}" 2>&1',
            'elevated': 'true'
        }

        if config_file:
            self._reset_global_prep_cmd(config_file, commands)

        if not self._sr.restart_sunshine_as_service(sunshine_service):
            if not self._sr.restart_sunshine_as_program(self._sr.find_file(os.path.join(sunshine_install_dir, "sunshine.exe"))):
                print("Please manually restart Sunshine to apply changes.")

        print("Sunshine Commands Preparation was successfully configured.")

    def open_sunshine_settings(self):
        sunshine_settings_url = self._sr.all_configs["Sunshine"]["settings_url"]
        print("\nOpening Sunshine Settings...")
        print("\nNavigate to the Audio/Video tab to add your custom Resolutions and Frame Rates.")
        subprocess.run(f'start {sunshine_settings_url}', shell=True)
        self._sr.pause()

    def open_playnite(self):
        playnite_url = self._sr.all_configs["Playnite"]["url"]
        print("\nOpening Playnite...")
        subprocess.run(f'start {playnite_url}', shell=True)
        self._sr.pause()


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

    def _download_file(self, url: str, filter: str = "", from_github: bool = False, vdd_version: str = "11"):
        download_url, file_name = None, filter

        os.makedirs('tools', exist_ok=True)

        if from_github:
            url = url.replace("https://github.com/",
                              "https://api.github.com/repos/")

            response = requests.get(url)
            data = response.json()

            if vdd_version == "10":
                for release in data:
                    if not release["prerelease"]:
                        if "HDR" not in release["assets"][0]["name"]:
                            data = release
                            break

            try:
                for r in data['assets']:
                    if filter in r['name']:
                        file_name = r['name']
                        download_url = r['browser_download_url']
            except KeyError:
                return
            else:
                if download_url == None:
                    return

            response = requests.get(download_url)
        else:
            response = requests.get(url)

        file_path = os.path.abspath(os.path.join("tools", file_name))

        with open(file_path, 'wb') as file:
            print(f"\nDownloading {file_name}")
            file.write(response.content)

        print(f"\nFile downloaded to {file_path}")

        self._sr.extract_file(file_path)

    def download_all(self, install: bool = True):
        self._sr.clear_screen()
        os.makedirs('tools', exist_ok=True)
        self.download_sunshine(install)
        self.download_vdd(install)
        self.download_svm(install)
        self.download_playnite(install)
        self.download_playnite_watcher(install)

        if install:
            print("\nAll the files have been downloaded and installed correctly.")
            print(
                "\nAdd your custom resolutions/frame rates to \"C:\\IddSampleDriver\\option.txt\" (See 7. → 5.)")
            print("\nAdd your custom resolutions in Sunshine Settings. (See 7. → 6.)")
        else:
            print(
                "\nAll the files have been correctly downloaded into the \"tools\" folder.")

        self._sr.pause()

    def download_sunshine(self, install: bool = True, selective: bool = False):
        sunshine = self._sr.all_configs["Sunshine"]
        sunshine_download_url = sunshine["download_url"]
        sunshine_download_pattern = sunshine["download_pattern"]
        sunshine_downloaded_dir_path = os.path.abspath(
            sunshine["downloaded_dir_path"])

        self._download_file(sunshine_download_url,
                            sunshine_download_pattern, from_github=True)

        sunshine_downloaded_file_path = self._sr.find_file(
            os.path.join(sunshine_downloaded_dir_path, r"sunshine*.exe"))

        if sunshine_downloaded_file_path and install:
            subprocess.run(f"start /wait {os.path.abspath(sunshine_downloaded_file_path)}", shell=True, check=True)

        if install and selective:
            svm_downloaded_dir_path = os.path.abspath(
                self._sr.all_configs["SunshineVirtualMonitor"]["downloaded_dir_path"])
            if not os.path.exists(svm_downloaded_dir_path):
                self.download_svm()
            self.config.configure_sunshine()
            print("\nSunshine has been well configured.")
        elif not install and selective:
            self._sr.pause()

    def download_vdd(self, install: bool = True, selective: bool = False):
        vdd = self._sr.all_configs["VirtualDisplayDriver"]
        vdd_download_pattern = vdd[f"download_pattern_w{self.config.release}"]
        vdd_download_url = vdd[f"download_url_w{self.config.release}"]
        vdd_device_id = vdd["device_id"]

        self._download_file(vdd_download_url, vdd_download_pattern,
                            from_github=True, vdd_version=self.config.release)

        vdd_downloaded_dir_path = self._sr.find_file(
            vdd[f"downloaded_dir_path_w{self.config.release}"])

        if not vdd_downloaded_dir_path:
            print("\nVirtual Display Driver was not correctly downloaded.")
            self._sr.pause()
            return

        if not install:
            self._sr.pause()
            return

        nefconw = self._sr.all_configs["Nefcon"]
        nefcon_download_url = nefconw["download_url"]
        nefcon_download_pattern = nefconw["download_pattern"]

        self._download_file(nefcon_download_url,
                            nefcon_download_pattern, from_github=True)

        nefcon_downloaded_dir_path = self._sr.find_file(
            nefconw["downloaded_dir_path"])
        if not nefcon_downloaded_dir_path:
            print("\nNefcon was not correctly downloaded.")
            return

        nefcon_downloaded_file_path = self._sr.find_file(
            os.path.join(nefcon_downloaded_dir_path, "nefconw.exe"))

        inf_file_path = self._sr.find_file(os.path.join(
            vdd_downloaded_dir_path, "IddSampleDriver.inf"))

        self._sr.copy_option_file()
        self._sr.install_cert(install)

        commands = [
            f"pnputil /remove-device /deviceid {vdd_device_id}",
            f"{nefcon_downloaded_file_path} --create-device-node --class-name Display --class-guid 4D36E968-E325-11CE-BFC1-08002BE10318 --hardware-id {vdd_device_id}",
            f"{nefcon_downloaded_file_path} --install-driver --inf-path {inf_file_path}",
            f"pnputil /disable-device /deviceid {vdd_device_id}"
        ]

        print("\nInstalling Virtual Display Driver...")

        for command in commands:
            try:
                subprocess.run(f"powershell.exe -Command \"{command}\"", shell=True, check=True)
            except subprocess.SubprocessError as e:
                print(e)

        vdd_friendly_name = self._config._get_vdd_friendly_name()
        subprocess.run(f"powershell.exe -Command \"Get-PnpDevice -FriendlyName '{vdd_friendly_name}' | Disable-PnpDevice -Confirm: $false\"", shell=True, check=True)

        print("\nVirtual Display Driver Installed.")
        print("\nAdd your custom resolutions/frame rates to \"C:\\IddSampleDriver\\option.txt\" (See 7. → 5.)")
        print("\nAdd your custom resolutions in Sunshine Settings. (See 7. → 6.)")

        if selective:
            self._sr.pause()

    def download_svm(self, install: bool = True, selective: bool = False):
        svm = self._sr.all_configs["SunshineVirtualMonitor"]
        svm_download_url = svm["download_url"]
        svm_download_pattern = svm["download_pattern"]

        self._download_file(svm_download_url, svm_download_pattern)

        if not install:
            self._sr.pause()
            return

        self._sr.install_windows_display_manager()
        self.download_mmt()
        self.download_vsync_toggle()
        self.config.configure_sunshine()

        print("\nSunshine Virtual Monitor was successfully installed.")

        if selective:
            self._sr.pause()

    def download_mmt(self, selective: bool = False):
        mmt = self._sr.all_configs["MultiMonitorTool"]
        mmt_download_url = mmt["download_url"]
        mmt_download_pattern = mmt["download_pattern"]
        mmt_downloaded_dir_path = mmt["downloaded_dir_path"]
        svm_downloaded_dir_path = self._sr.find_file(
            self._sr.all_configs["SunshineVirtualMonitor"]["downloaded_dir_path"])

        self._download_file(
            mmt_download_url, mmt_download_pattern)

        if svm_downloaded_dir_path:
            destination_folder = os.path.join(
                svm_downloaded_dir_path, "multimonitortool-x64")
            if os.path.exists(destination_folder):
                shutil.rmtree(destination_folder)
            print(f"\nMove {mmt_downloaded_dir_path} to {destination_folder}")
            shutil.move(mmt_downloaded_dir_path, destination_folder)

        if selective:
            self._sr.pause()

    def download_vsync_toggle(self, selective: bool = False):
        vsync = self._sr.all_configs["VsyncToggle"]
        vsync_download_url = vsync["download_url"]
        vsync_download_pattern = vsync["download_pattern"]
        vsync_downloaded_dir_path = vsync["downloaded_dir_path"]

        self._download_file(vsync_download_url,
                            vsync_download_pattern, from_github=True)

        source_file = self._sr.find_file(os.path.join(
            vsync_downloaded_dir_path, r"vsynctoggle*.exe"))
        destination_folder = self._sr.find_file(os.path.join(
            vsync_downloaded_dir_path, "sunshine-virtual-monitor-main"))

        if source_file and destination_folder:
            destination_file = os.path.join(
                destination_folder, "vsynctoggle-1.1.0-x86_64.exe")
            if os.path.exists(destination_file):
                os.remove(destination_file)
            print(f"\nMove {source_file} to {destination_file}")
            shutil.move(source_file, destination_file)

        if selective:
            self._sr.pause()

    def download_playnite(self, install: bool = True, selective: bool = False):
        playnite = self._sr.all_configs["Playnite"]
        playnite_download_url = playnite["download_url"]
        playnite_download_pattern = playnite["download_pattern"]
        playnite_downloaded_dir_path = playnite["downloaded_dir_path"]

        self._download_file(playnite_download_url, playnite_download_pattern)

        if not install:
            self._sr.pause()
            return

        playnite_downloaded_file_path = self._sr.find_file(
            os.path.join(playnite_downloaded_dir_path, playnite_download_pattern))

        if playnite_downloaded_file_path:
            subprocess.run(f"start /wait {os.path.abspath(playnite_downloaded_file_path)}", shell=True, check=True)
        print("\nPlaynite was successfully installed.")

        if selective:
            self._sr.pause()

    def download_playnite_watcher(self, install: bool = True, selective: bool = False):
        playnitew = self._sr.all_configs["PlayniteWatcher"]
        playnitew_download_url = playnitew["download_url"]
        playnitew_download_pattern = playnitew["download_pattern"]
        playnitew_guide_url = playnitew["guide_url"]
        playnitew_addon_url = playnitew["addon_url"]

        self._download_file(playnitew_download_url,
                            playnitew_download_pattern, from_github=True)

        if not install:
            playnitew_guide = input(
                "\nOpen PlayNite Watcher Setup Guide ? (Y/n) ")

            if playnitew_guide.lower().strip() in ['y', 'ye', 'yes', '']:
                subprocess.run(
                    f"start {playnitew_guide_url}", shell=True)
            self._sr.pause()
            return

        if self.config.release == '11':
            windows_settings = input(
                "\nPlease set the default terminal to Windows Console Host. Open Windows Settings ? (Y/n) ")
            if windows_settings.lower().strip() in ['y', 'ye', 'yes', '']:
                subprocess.run(f"start ms-settings:developers", shell=True, check=True)

        sap = input("\nInstall 'Sunshine App Export' on Playnite ? (Y/n) ")

        if sap.lower().strip() in ['y', 'ye', 'yes', '']:
            subprocess.run(
                f"start {playnitew_addon_url}", shell=True, check=True)

        playnitew_guide = input(
            "\nOpen PlayNite Watcher Setup Guide ? (Y/n) ")

        if playnitew_guide.lower().strip() in ['y', 'ye', 'yes', '']:
            subprocess.run(
                f"start {playnitew_guide_url}", shell=True)

        print("\nPlaynite Watcher was successfully installed.")

        if selective:
            self._sr.pause()
