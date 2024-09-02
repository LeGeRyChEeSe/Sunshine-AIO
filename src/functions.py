import os
import platform
import sys
import requests
import zipfile
import shutil
import subprocess
import glob
import ctypes
import json
import time


def logo():
    logo = r'''

    ____                  _     _                 _    ___ ___
   / ___| _   _ _ __  ___| |__ (_)_ __   ___     / \  |_ _/ _ \
   \___ \| | | | '_ \/ __| '_ \| | '_ \ / _ \   / _ \  | | | | |
    ___) | |_| | | | \__ \ | | | | | | |  __/  / ___ \ | | |_| |
   |____/ \__,_|_| |_|___/_| |_|_|_| |_|\___| /_/   \_\___\___/


    '''
    print(logo)


def menu(page: int = 0):
    os.system("cls")
    if not is_admin():
        sys.stdout.write('Not running as admin, relaunching...?\n')
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    checkExecutionPolicy()

    while True:
        os.system("cls")
        logo()
        print("Menu:")

        if page == 0:
            print("1. Download and Install EVERYTHING")
            print("2. Download, install and configure Sunshine")
            print(
                "3. Download and install Virtual Display Driver (WARNING: This resets the option.txt file)")
            print("4. Download and configure Sunshine Virtual Monitor")
            print("5. Download and install Playnite")
            print("6. Download and configure Playnite Watcher")
            print("7. Extra")
        elif page == 1:
            print("1. Download EVERYTHING without installing")
            print("2. Selective Download")
            print(
                "3. Reset Sunshine Commands Preparation")
            print("4. Install WindowsDisplayManager (PowerShell Module Required)")
            print("5. Go Back")
        elif page == 2:
            print("1. Download Sunshine")
            print("2. Download Virtual Display Driver")
            print("3. Download Sunshine Virtual Monitor")
            print("4. Download Multi Monitor Tool")
            print("5. Download VSYNC Toggle")
            print("6. Download Playnite")
            print("7. Download Playnite Watcher")
            print("8. Go Back")

        print("0. Exit")

        if page == 0:
            choice = input("\nPlease choose an option (0-7): ")
            if choice == '0':
                sys.exit()
            elif choice == '1':
                downloadAll()
            elif choice == '2':
                downloadSunshine(selective=True)
            elif choice == '3':
                downloadVDD(selective=True)
            elif choice == '4':
                downloadSVM()
            elif choice == '5':
                downloadPlaynite()
            elif choice == '6':
                downloadPlayniteWatcher()
            elif choice == '7':
                page += 1
        elif page == 1:
            choice = input("\nPlease choose an option (0-5): ")
            if choice == '0':
                sys.exit()
            elif choice == '1':
                downloadAll(False)
            elif choice == '2':
                page += 1
            elif choice == '3':
                configureSunshine()
            elif choice == '4':
                installWindowsDisplayManager(True)
            elif choice == '5':
                page -= 1
        elif page == 2:
            choice = input("\nPlease choose an option (0-8): ")
            if choice == '0':
                sys.exit()
            elif choice == '1':
                downloadSunshine(False, True)
            elif choice == '2':
                downloadVDD(False, True)
            elif choice == '3':
                downloadSVM(False, True)
            elif choice == '4':
                downloadMMT(True)
            elif choice == '5':
                downloadVsyncToggle(True)
            elif choice == '6':
                downloadPlaynite(False, True)
            elif choice == '7':
                downloadPlayniteWatcher(False, True)
            elif choice == '8':
                page -= 1


def downloadAll(install: bool = True):
    os.system("cls")
    os.makedirs('tools', exist_ok=True)
    downloadSunshine(install)
    downloadVDD(install)
    downloadSVM(install)
    downloadPlaynite(install)
    downloadPlayniteWatcher(install)

    if install:
        print("\nAll the files have been downloaded and installed correctly.")
        print("\nMake sure to add your custom resolutions with framerate to \"C:\\IddSampleDriver\\option.txt\" and also in Sunshine Config (See https://localhost:47990/config# -> Audio/Video)")
    else:
        print("\nAll the files have been downloaded correctly.")

    os.system('pause')


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def downloadFile(url: str, filter: str = "", from_github: bool = False, selective: bool = False):
    download_url, file_name = None, None

    os.makedirs('tools', exist_ok=True)

    if from_github:
        if not url.startswith("https://api.github.com/"):
            url = url.replace("https://github.com/",
                              "https://api.github.com/repos/")

        response = requests.get(url)
        data = response.json()

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
        file_name = filter

    file_path = f"tools\\{file_name}"

    with open(file_path, 'wb') as file:
        print(f"\nDownloading {file_name}")
        file.write(response.content)

    print(f"\nFile downloaded to {os.path.abspath(file_path)}")

    extractFile(file_path)

    if selective:
        print("")
        os.system('pause')


def extractFile(zip_file: str):
    file_name = ""
    if zip_file.endswith('.zip'):
        file_name = zip_file.rsplit('.', 1)[0]
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            print(f"\nExtracting {zip_file} to {file_name}")
            zip_ref.extractall(file_name)
        os.remove(zip_file)
    mergeFolders(file_name)


def mergeFolders(folder: str):
    if not os.path.isdir(folder):
        return

    name_folder: str = os.path.basename(folder)
    folder_formatted = folder.split('\\')[1].replace('.', ' ')

    for element in os.listdir(folder):
        element_formatted: str = element.replace('.', ' ')
        element_path = os.path.join(folder, element)

        if os.path.isdir(element_path):
            if element_formatted in folder_formatted or folder_formatted in element_formatted:
                for sub_element in os.listdir(element_path):
                    path_sub_element = os.path.join(element_path, sub_element)
                    destination_path = os.path.join(folder, sub_element)

                    # Vérifie si le fichier ou dossier existe déjà
                    if os.path.exists(destination_path):
                        # Supprimer le fichier ou dossier existant
                        if os.path.isdir(destination_path):
                            # Supprime le dossier
                            shutil.rmtree(destination_path)
                        else:
                            os.remove(destination_path)  # Supprime le fichier

                    # Déplace le sous-élément
                    shutil.move(path_sub_element, folder)

                os.rmdir(element_path)


def downloadSunshine(install: bool = True, selective: bool = False):
    downloadFile("https://github.com/LizardByte/Sunshine/releases/latest",
                 "sunshine-windows-installer", from_github=True, selective=selective if not install else False)

    if not install and selective:
        return

    sunshine_install_path = 'tools\\sunshine-windows-installer.exe'
    subprocess.run(f"start /wait {sunshine_install_path}", shell=True)

    if install and selective:
        configureSunshine()
        print("\nSunshine has been well configured.")


def downloadVDD(install: bool = True, selective: bool = False):
    downloadFile("https://github.com/itsmikethetech/Virtual-Display-Driver/releases/latest",
                 "VDD.HDR", from_github=True, selective=selective if not install else False)

    if not install and selective:
        return

    downloadFile("https://github.com/nefarius/nefcon/releases/latest",
                 from_github=True)
    nefconw = findFile(r'tools\*\x64\nefconw.exe')
    inf_file_path = findFile(r'tools\VDD.HDR.*\*\\IddSampleDriver.inf')

    copyOption()
    installCert(install)

    commands = [
        'pnputil /remove-device /deviceid Root\\IddSampleDriver',
        f'"{nefconw}" --create-device-node --class-name Display --class-guid 4D36E968-E325-11CE-BFC1-08002BE10318 --hardware-id Root\\IddSampleDriver',
        f'"{nefconw}" --install-driver --inf-path "{inf_file_path}"',
        'pnputil /disable-device /deviceid Root\\IddSampleDriver'
    ]

    print("\nInstalling Virtual Display Driver...")

    for command in commands:
        try:
            subprocess.run(f'powershell.exe -Command {command}', shell=True, check=True)
        except subprocess.SubprocessError as e:
            print(e)

    print("\nVirtual Display Driver Installed.")

    if selective:
        print("\nMake sure to add your custom resolutions\\frame rates to option.txt file. See https://github.com/LeGeRyChEeSe/Sunshine-AIO/tree/dev-AIO#add-custom-resolutionsframe-rates for more information.\n")
        os.system("pause")


def downloadSVM(install: bool = True, selective: bool = False):
    downloadFile("https://github.com/Cynary/sunshine-virtual-monitor/archive/refs/heads/main.zip",
                 "sunshine-virtual-monitor-main.zip", selective=selective)

    if not install and selective:
        return

    installWindowsDisplayManager()
    downloadMMT(selective)
    downloadVsyncToggle(selective)
    configureSunshine(install)


def downloadMMT(selective: bool = False):
    downloadFile("https://www.nirsoft.net/utils/multimonitortool-x64.zip",
                 "multimonitortool-x64.zip", selective=selective)

    if selective:
        return

    source_folder = "tools\\multimonitortool-x64"
    destination_folder = "tools\\sunshine-virtual-monitor-main\\multimonitortool-x64"

    if source_folder:
        if os.path.exists(destination_folder):
            shutil.rmtree(destination_folder)
        print(f"\nMove {source_folder} to {destination_folder}")
        shutil.move(source_folder, destination_folder)


def downloadVsyncToggle(selective: bool = False):
    downloadFile("https://github.com/xanderfrangos/vsync-toggle/releases/latest",
                 "vsynctoggle", from_github=True, selective=selective)

    if selective:
        return

    source_file = findFile(r'tools\vsynctoggle*.exe')
    destination_folder = findFile(r'tools\sunshine-virtual-monitor-main')
    destination_file = f"{destination_folder}\\vsynctoggle-1.1.0-x86_64.exe"

    if source_file:
        if os.path.exists(destination_file):
            os.remove(destination_file)
        print(f"\nMove {source_file} to {destination_file}")
        shutil.move(source_file, destination_file)


def downloadPlaynite(install: bool = True, selective: bool = False):
    downloadFile("https://playnite.link/download/PlayniteInstaller.exe",
                 "PlayniteInstaller.exe", selective=selective)

    if not install:
        return

    playnite_install_path = "tools\\PlayniteInstaller.exe"
    subprocess.run(f"start /wait {playnite_install_path}", shell=True, check=True)


def downloadPlayniteWatcher(install: bool = True, selective: bool = False):
    playnite_watcher = downloadFile("https://github.com/Nonary/PlayNiteWatcher/releases/latest",
                                    "PlayniteWatcher.zip", from_github=True, selective=selective)

    if not install and selective:
        input("\nPress any key to open PlayNite Watcher Setup Guide...")
        subprocess.run(
            "start https://github.com/Nonary/PlayNiteWatcher#setup-instructions", shell=True)
        return
    elif not install:
        return

    if platform.release() == '11':
        print("\nPlease set the default terminal to Windows Console Host.")
        input("Press any key to open the Windows parameters...")
        subprocess.run(f"start ms-settings:developers", shell=True, check=True)

    sap = input("\nInstall 'Sunshine App Export' on Playnite ? (Y/n) ")
    if sap.lower() in ['y', 'ye', 'yes', '']:
        subprocess.run(
            "start playnite://playnite/installaddon/SunshineAppExport", shell=True, check=True)
    input("\nPress any key to open PlayNite Watcher Setup Guide...")
    subprocess.run(
        "start /wait https://github.com/Nonary/PlayNiteWatcher#setup-instructions", shell=True)


def copyOption():
    source_file = findFile(r'tools\VDD.HDR.*\*\\option.txt')
    destination_file = 'C:\\IddSampleDriver\\option.txt'
    os.makedirs('C:\\IddSampleDriver', exist_ok=True)

    if source_file:
        print(f"\nCopy {source_file} to {destination_file}")
        shutil.copy(source_file, destination_file)


def installCert(install: bool = True):
    if not install:
        return

    batch_file_path = findFile(r'tools\VDD.HDR.*\*\\InstallCert.bat')

    if batch_file_path:
        print("\nInstalling Virtual Display Driver certificat...")
        process = subprocess.Popen(['cmd.exe', '/c', batch_file_path], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate(b'\n')

    print("\nVirtual Display Driver certificat installed.")


def findFile(pattern: str) -> (str | None):
    files = glob.glob(pattern)

    if files:
        return os.path.abspath(files[0])


def configureSunshine(install: bool = True):
    if not install:
        return

    sunshine_path = "C:\\Program Files\\Sunshine"
    svm_path = findFile("tools\\sunshine-virtual-monitor-main")
    setup_sunvdm = f"{svm_path}\\setup_sunvdm.ps1"
    teardown_sunvdm = f"{svm_path}\\teardown_sunvdm.ps1"
    sunvdm_log = f'{svm_path}\\sunvdm.log'

    if not os.path.exists(sunshine_path):
        downloadSunshine(selective=True)
        return
    if svm_path == None or not os.path.exists(svm_path):
        downloadSVM()
        return

    subprocess.run(["powershell.exe", "-Command",
                    "Set-ExecutionPolicy RemoteSigned"])
    if os.path.exists(setup_sunvdm):
        subprocess.run(["powershell.exe", "-Command", f"Unblock-File {setup_sunvdm}"])
    if os.path.exists(teardown_sunvdm):
        subprocess.run(["powershell.exe", "-Command", f"Unblock-File {teardown_sunvdm}"])

    checkExecutionPolicy()

    vdd_name = getVddName()

    config_file = f"{sunshine_path}\\config\\sunshine.conf"

    commands = {
        'do': f'cmd /C powershell.exe -executionpolicy bypass -windowstyle hidden -file "{setup_sunvdm}" %SUNSHINE_CLIENT_WIDTH% %SUNSHINE_CLIENT_HEIGHT% %SUNSHINE_CLIENT_FPS% %SUNSHINE_CLIENT_HDR% "{vdd_name}" > "{sunvdm_log}" 2>&1',
        'undo': f'cmd /C powershell.exe -executionpolicy bypass -windowstyle hidden -file "{teardown_sunvdm}" "{vdd_name}" >> "{sunvdm_log}" 2>&1',
        'elevated': 'true'
    }

    reset_global_prep_cmd(config_file, commands)

    if not restart_sunshine_as_service('SunshineService'):
        if not restart_sunshine_as_program(f"{sunshine_path}\\sunshine.exe"):
            print("Please manually restart Sunshine to apply changes.")

    print("Sunshine Commands Preparation have been correctly configured.")

    os.system('pause')


def installWindowsDisplayManager(selective: bool = False):
    if not checkModuleInstalled("WindowsDisplayManager"):
        try:
            subprocess.run(["powershell.exe", "-Command",
                            "Install-Module -Name WindowsDisplayManager"], shell=True, check=True)
        except:
            print("\nThe WindowsDisplayManager module was not installed due to an error.")
        else:
            print("\nThe WindowsDisplayManager module is now installed.")
    else:
        print("\nThe WindowsDisplayManager module is already installed.")

    if selective:
        print("")
        os.system("pause")


def checkModuleInstalled(module_name: str) -> bool:
    command = f"Get-Module -ListAvailable -Name {module_name}"

    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", command], capture_output=True, text=True)

        if result.stdout:
            return True
        else:
            return False
    except:
        return False


def checkExecutionPolicy() -> bool:
    command = "Get-ExecutionPolicy"

    result = subprocess.run(
        ["powershell.exe", "-Command", command], capture_output=True, text=True)

    policy = result.stdout.strip()
    if policy != "Undefined":
        subprocess.run(["powershell.exe", "-Command",
                        "Set-ExecutionPolicy Undefined"])
        return True
    return False


def reset_global_prep_cmd(file_path: str, new_commands: dict[str, str]):
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


def restart_sunshine_as_service(service_name) -> bool:
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


def restart_sunshine_as_program(sunshine_executable_path) -> bool:
    # Arrêter Sunshine
    try:
        subprocess.run([sunshine_executable_path, '--stop'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nError when stopping Sunshine: {e}")
        return False

    # Attendre quelques secondes pour s'assurer que le processus est complètement arrêté
    time.sleep(2)

    # Démarrer Sunshine
    try:
        subprocess.run([sunshine_executable_path, '--start'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nError when starting Sunshine: {e}")
        return False

    print("\nSunshine has been successfully restarted.\n")
    return True


def getVddName():
    command = "Get-PnpDevice -Class Display | Select-Object FriendlyName | ConvertTo-Json"

    result = subprocess.run(
        ["powershell", "-Command", command], capture_output=True, text=True)

    if result.returncode == 0:
        display_devices = json.loads(result.stdout)

        for device in display_devices:
            friendly_name: str = device.get('FriendlyName', '')
            if 'IddSampleDriver' in friendly_name:
                return friendly_name
