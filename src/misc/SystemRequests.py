import ctypes
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from misc.constants import *
from typing import Dict, Optional


class SystemRequests():

    def __init__(self, base_path: str) -> None:
        self._all_configs: Dict[str, Dict[str, str]] = {}
        self._base_path = base_path
        self._release = self._get_platform_release()

        self._set_config()

    @property
    def all_configs(self):
        return self._all_configs

    @all_configs.setter
    def all_configs(self):
        raise ValueError("No manual edit allowed.")

    @property
    def base_path(self):
        return self._base_path

    @base_path.setter
    def base_path(self):
        raise ValueError("No manual edit allowed.")

    @property
    def release(self):
        return self._release

    @release.setter
    def release(self):
        raise ValueError("No manual edit allowed.")

    def _set_config(self):
        with open(f"{self._base_path}\\misc\\variables\\config.json", "rb") as config:
            self._all_configs = json.loads(config.read())

    def _check_module_installed(self) -> bool:
        command = f"Get-Module -ListAvailable -Name {MODULE_NAME}"

        try:
            result = subprocess.run(
                ["powershell.exe", "-Command", command], capture_output=True, text=True)

            if result.stdout:
                return True
            else:
                return False
        except:
            return False

    def _move_content_up(self, folder: str):
        if not os.path.isdir(folder):
            return

        items = os.listdir(folder)

        while len(items) == 1:
            folder_path = os.path.join(folder, items[0])

            if not os.path.isdir(folder_path):
                break
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)

                try:
                    shutil.move(item_path, folder)
                except Exception as e:
                    print(f"Error with moving {item_path}: {e}")

            try:
                os.rmdir(folder_path)
            except OSError as e:
                print(f"Error with deleting folder {folder_path}: {e}")

            items = os.listdir(folder)

    def _get_platform_release(self):
        release = platform.release()
        return release if release == "11" else "10"

    def pause(self):
        print()
        os.system("pause")

    def clear_screen(self):
        os.system('cls')

    def rerun_as_admin(self):
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            print(f"Error with admin verification: {e}")
        else:
            if not is_admin:
                print('Starting as an admin...\n')
                try:
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                except Exception as e:
                    print(f"Error when starting as admin: {e}")
                sys.exit()

    def extract_file(self, zip_file: str):
        file_name = ""
        zip_file = os.path.abspath(zip_file)
        if zip_file.endswith('.zip'):
            file_name = zip_file.rsplit('.', 1)[0]

            if os.path.exists(file_name):
                shutil.rmtree(file_name)

            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                print(f"\nExtracting {zip_file} to {file_name}")
                zip_ref.extractall(file_name)
            os.remove(zip_file)
        self._move_content_up(file_name)

    def restart_sunshine_as_service(self, service_name) -> bool:
        # Arrêter le service Sunshine
        try:
            print(f"\nStop Service {service_name}...")
            subprocess.run(['sc', 'stop', service_name], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"\nError during the service shutdown {service_name}: {e}")
            return False

        # Attendre quelques secondes pour s'assurer que le service est complètement arrêté
        time.sleep(2)

        # Démarrer le service Sunshine
        try:
            print(f"\nStart Service {service_name}...")
            subprocess.run(['sc', 'start', service_name], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"\nError during the start of service {service_name}: {e}")
            return False

        print(f"\n{service_name} has been successfully restarted.\n")
        return True

    def restart_sunshine_as_program(self, sunshine_executable_path) -> bool:
        # Arrêter Sunshine
        try:
            subprocess.run(
                [sunshine_executable_path, '--stop'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\nError when stopping Sunshine: {e}")
            return False

        # Attendre quelques secondes pour s'assurer que le processus est complètement arrêté
        time.sleep(2)

        # Démarrer Sunshine
        try:
            subprocess.run(
                [sunshine_executable_path, '--start'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\nError when starting Sunshine: {e}")
            return False

        print("\nSunshine has been successfully restarted.\n")
        return True

    def copy_option_file(self):
        vdd = self.all_configs["VirtualDisplayDriver"]
        vdd_downloaded_dir_path = self.find_file(vdd[f"downloaded_dir_path_w{self._release}"])

        if not vdd_downloaded_dir_path:
            print("\nPlease download Virtual Display Driver first.")
            return False

        vdd_option_path = os.path.join(vdd_downloaded_dir_path, "option.txt")
        destination_file = "C:\\IddSampleDriver\\option.txt"

        os.makedirs("C:\\IddSampleDriver", exist_ok=True)

        if vdd_option_path and not os.path.exists(destination_file):
            print(f"\nCopy {vdd_option_path} to {destination_file}")
            shutil.copy(vdd_option_path, destination_file)

        return True

    def open_option_file(self):
        option_file_path = "C:\\IddSampleDriver\\option.txt"
        if not os.path.exists(option_file_path):
            print(f"\nCreating '{option_file_path}' file...")
            if not self.copy_option_file():
                print(f"\nFailed to create '{option_file_path}' file.")
                self.pause()
                return

        print(f"\nOpening '{option_file_path}' file...")
        print("\nAdd your custom Resolutions and Frame Rates in there.")
        print("\nFormat is: RES_WIDTH, RES_HEIGHT, FRAME_RATE")
        subprocess.run(
            ['notepad.exe', 'C:\\IddSampleDriver\\option.txt'], check=True)
        print("\n'C:\\IddSampleDriver\\option.txt' edited.")
        print(
            "\nAdd your custom Resolutions and Frame Rates also in Sunshine Config. (See 6.)")
        print("\nMake sure to disable the Virtual Display Driver in the device manager before streaming games.")
        self.pause()

    def install_cert(self, install: bool = True):
        if not install:
            return

        batch_file_path = self.find_file(
            r'tools\VDD.HDR.*\*\\InstallCert.bat')

        if batch_file_path:
            print("\nInstalling Virtual Display Driver certificat...")
            process = subprocess.Popen(['cmd.exe', '/c', batch_file_path], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate(b'\n')

        print("\nVirtual Display Driver certificat installed.")

    def check_execution_policy(self) -> bool:
        command = "Get-ExecutionPolicy"

        result = subprocess.run(
            ["powershell.exe", "-Command", command], capture_output=True, text=True)

        policy = result.stdout.strip()
        if policy != "Undefined":
            subprocess.run(["powershell.exe", "-Command",
                            "Set-ExecutionPolicy Undefined"])
            return True
        return False

    def find_file(self, pattern: str) -> Optional[str]:
        files = glob.glob(os.path.abspath(pattern))

        if files:
            return os.path.abspath(files[0])

    def install_windows_display_manager(self, selective: bool = False):
        if not self._check_module_installed():
            try:
                subprocess.run(["powershell.exe", "-Command",
                                f"Install-Module -Name {MODULE_NAME}"], shell=True, check=True)
            except:
                print(
                    f"\nThe {MODULE_NAME} module was not installed due to an error.")
            else:
                print(f"\nThe {MODULE_NAME} module is now installed.")
        else:
            print(f"\nThe {MODULE_NAME} module is already installed.")

        if selective:
            self.pause()
