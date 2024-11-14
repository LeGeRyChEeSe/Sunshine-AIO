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
        self.vdd_friendly_name = ''

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

    def _download_file(self, url: str, name_filter: str = "", from_github: bool = False, vdd_version: str = "0"):
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
            print(f"\nDownloading {file_name}")
            file.write(response.content)

        print(f'\nFile downloaded to "{file_path}"')

        final_file_name = self.sr.extract_file(file_path)

        return final_file_name

    def download_all(self, install: bool = True):
        self.sr.clear_screen()
        self.sr.reset_tools_folder()
        self.download_sunshine(install)
        self.download_vdd(install)
        self.download_svm(install)
        self.download_playnite(install)
        self.download_playnite_watcher(install)

        if install:
            print('\nAll the files have been downloaded and installed correctly.')
        else:
            print(
                '\nAll the files have been correctly downloaded into the "tools" folder.')

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
            subprocess.run(
                ["start", "/wait", os.path.abspath(sunshine_downloaded_file_path)], shell=True, check=True)

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
        vdd_device_id = vdd["device_id"]

        if selective:
            self.sr.clear_screen()

        file_name = self._download_file(vdd_download_url, from_github=True,
                                        vdd_version=self.config.release)

        vdd_downloaded_dir_path = self.sr.find_file(file_name)

        if not vdd_downloaded_dir_path:
            print("\nVirtual Display Driver was not correctly downloaded.")
            print(vdd_downloaded_dir_path, self.config.release, vdd_download_url)
            self.sr.pause()
            return

        if not install:
            self.sr.pause()
            return

        nefconw = self.sr.all_configs["Nefcon"]
        nefcon_download_url = nefconw["download_url"]
        nefcon_download_pattern = nefconw["download_pattern"]

        self._download_file(nefcon_download_url,
                            nefcon_download_pattern, from_github=True)

        nefcon_downloaded_dir_path = self.sr.find_file(
            nefconw["downloaded_dir_path"])
        if not nefcon_downloaded_dir_path:
            print("\nNefcon was not correctly downloaded.")
            return

        nefcon_downloaded_file_path = self.sr.find_file(
            os.path.join(nefcon_downloaded_dir_path, "nefconw.exe"))

        inf_file_path = self.sr.find_file(os.path.join(
            vdd_downloaded_dir_path, "IddSampleDriver.inf"))

        self.sr.install_cert(install)

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

        self.vdd_friendly_name = self._config._get_vdd_friendly_name()
        subprocess.run(["powershell.exe", "-Command", "'Get-PnpDevice", "-FriendlyName",
                        self.vdd_friendly_name, "|", "Disable-PnpDevice", "-Confirm:", "$false'"], check=True)

        print("\nVirtual Display Driver Installed.")

        if selective:
            self.sr.pause()

    def download_svm(self, install: bool = True, selective: bool = False):
        svm = self.sr.all_configs["SunshineVirtualMonitor"]
        svm_download_url = svm["download_url"]
        svm_download_pattern = svm["download_pattern"]

        if selective:
            self.sr.clear_screen()

        self._download_file(svm_download_url, svm_download_pattern)

        if not install:
            self.sr.pause()
            return

        self.sr.install_windows_display_manager()
        self.download_mmt()
        self.download_vsync_toggle()
        self.config.configure_sunshine()

        print("\nSunshine Virtual Monitor was successfully installed.")

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
            subprocess.run(
                ["start", "/wait", os.path.abspath(playnite_downloaded_file_path)], shell=True, check=True)
        print("\nPlaynite was successfully installed.")

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

        print("\nPlaynite Watcher was successfully installed.")

        if selective:
            self.sr.pause()
