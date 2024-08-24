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
import re

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
		ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
		sys.exit()

	checkExecutionPolicy()

	while True:
		os.system("cls")
		logo()
		print("Menu:")
		
		if page == 0:
			print("1. Download and Install EVERYTHING")
			print("2. Download, install and configure Sunshine")
			print("3. Download and install Virtual Display Driver")
			print("4. Download and configure Sunshine Virtual Monitor")
			print("5. Download and install Playnite")
			print("6. Download and configure Playnite Watcher")
			print("7. Extra")
		elif page == 1:
			print("1. Download EVERYTHING without installing")
			print("2. Selective Download")
			print("3. Configure Sunshine (only if you need to reset the preparation commands)")
			print("4. Install WindowsDisplayManager (powershell module required)")
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
				downloadSunshine(True)
			elif choice == '3':
				downloadVDD(True)
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
				installWindowsDisplayManager()
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
	# TEST
	#return
	# End TEST

	os.system("cls")

	os.makedirs('tools', exist_ok=True)

	downloadSunshine(install)
	downloadVDD(install)
	downloadSVM(install)
	downloadPlaynite(install)
	downloadPlayniteWatcher(install)

	if install:
		print("\nAll the files have been downloaded and installed correctly.")
	else:
		print("\nAll the files have been downloaded correctly.")

	os.system('pause')

def is_admin():
	try:
		return ctypes.windll.shell32.IsUserAnAdmin()
	except:
		return False

def downloadFile(url: str, filter: str = "", from_github: bool = False, selective: bool = False):
	os.makedirs('tools', exist_ok=True)

	if from_github:
		if not url.startswith("https://api.github.com/"):
			url = url.replace("https://github.com/", "https://api.github.com/repos/")

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

	if selective:
		os.system('pause')
		return

	extractFile(file_path)

def extractFile(zip_file: str):
	if zip_file.endswith('.zip'):
		file_name = zip_file.rsplit('.', 1)[0]
		with zipfile.ZipFile(zip_file, 'r') as zip_ref:
			print(f"\nExtracting {zip_file} to {file_name}")
			zip_ref.extractall(file_name)
		os.remove(zip_file)

def downloadSunshine(install: bool = True, selective: bool = False):
	downloadFile("https://github.com/LizardByte/Sunshine/releases/latest", "sunshine-windows-installer", from_github=True, selective=selective)

	if not install:
		return

	sunshine_install_path = 'tools\\sunshine-windows-installer.exe'
	subprocess.run(f"start /wait {sunshine_install_path}", shell=True)

def downloadVDD(install: bool = True, selective: bool = False):
	downloadFile("https://github.com/itsmikethetech/Virtual-Display-Driver/releases/latest", "VDD.HDR", from_github=True, selective=selective)

	if not install:
		return

	downloadFile("https://github.com/nefarius/nefcon/releases/latest", from_github=True)
	nefconw = findFile(r'tools\*\x64\nefconw.exe')
	inf_file_path = findFile(r'tools\VDD.HDR.*\VDD*\\*\\IddSampleDriver.inf')
	
	copyOption()
	installCert(install)

	commands = [
		f'start /wait {nefconw} --remove-device-node --hardware-id Root\\IddSampleDriver --class-guid "4D36E968-E325-11CE-BFC1-08002BE10318"',
		f'start /wait {nefconw} --create-device-node --class-name Display --class-guid "4D36E968-E325-11CE-BFC1-08002BE10318" --hardware-id Root\\IddSampleDriver',
		f'start /wait {nefconw} --install-driver --inf-path "{inf_file_path}"',
		'start /wait pnputil /disable-device /deviceid Root\\IddSampleDriver'
	]

	for command in commands:
		try:
			subprocess.run(command, shell=True, check=True)
		except:
			pass

def downloadSVM(install: bool = True, selective: bool = False):
	downloadFile("https://github.com/Cynary/sunshine-virtual-monitor/archive/refs/heads/main.zip", "sunshine-virtual-monitor-main.zip", selective=selective)
	
	if not install and selective:
		return
	
	installWindowsDisplayManager()
	downloadMMT(selective)
	downloadVsyncToggle(selective)
	configureSunshine(True)

def downloadMMT(selective: bool = False):
	downloadFile("https://www.nirsoft.net/utils/multimonitortool-x64.zip", "multimonitortool-x64.zip", selective=selective)

	if selective:
		return

	source_folder = 'tools\\multimonitortool-x64'
	destination_folder = 'tools\\sunshine-virtual-monitor-main\\sunshine-virtual-monitor-main\\multimonitortool-x64'

	if source_folder:
		if os.path.exists(destination_folder):
			shutil.rmtree(destination_folder)
		print(f"\nMove {source_folder} to {destination_folder}")
		shutil.move(source_folder, destination_folder)

def downloadVsyncToggle(selective: bool = False):
	downloadFile("https://github.com/xanderfrangos/vsync-toggle/releases/latest", "vsynctoggle", from_github=True, selective=selective)
	
	if selective:
		return

	source_file = findFile(r'tools\vsynctoggle*.exe')
	destination_folder = findFile(r'tools\*\sunshine-virtual-monitor-main')
	destination_file = f"{destination_folder}\\vsynctoggle-1.1.0-x86_64.exe"

	if source_file:
		if os.path.exists(destination_file):
			os.remove(destination_file)
		print(f"\nMove {source_file} to {destination_file}")
		shutil.move(source_file, destination_file)

def downloadPlaynite(install: bool = True, selective: bool = False):
	downloadFile("https://playnite.link/download/PlayniteInstaller.exe", "PlayniteInstaller.exe", selective=selective)

	if not install:
		return

	playnite_install_path = 'tools\\PlayniteInstaller.exe'
	subprocess.run(f"start /wait {playnite_install_path}", shell=True)

def downloadPlayniteWatcher(install: bool = True, selective: bool = False):
	playnite_watcher = downloadFile("https://github.com/Nonary/PlayNiteWatcher/releases/latest", "PlayniteWatcher.zip", from_github=True, selective=selective)

	if not install and selective:
		input("\nPress any key to open PlayNite Watcher Setup Guide...")
		subprocess.run("start https://github.com/Nonary/PlayNiteWatcher#setup-instructions", shell=True)
		return

	if platform.release() == '11':
		print("\nPlease set the default terminal to Windows Console Host.")
		input("Press any key to open the Windows parameters...")
		subprocess.run(f"start /wait ms-settings:developers", shell=True, check=True)

	sap = input("\nInstall 'Sunshine App Export' on Playnite ? (Y/n) ")
	if sap.lower() in ['y', 'ye', 'yes', '']:
		subprocess.run("start /wait playnite://playnite/installaddon/SunshineAppExport", shell=True)
	input("\nPress any key to open PlayNite Watcher Setup Guide...")
	subprocess.run("start https://github.com/Nonary/PlayNiteWatcher#setup-instructions", shell=True)

def copyOption():
	source_file = findFile(r'tools\VDD.HDR.*\VDD*\\*\\option.txt')
	destination_file = 'C:\\IddSampleDriver\\option.txt'
	os.makedirs('C:\\IddSampleDriver', exist_ok=True)
	
	if source_file:
		print(f"\nCopy {source_file} to {destination_file}")
		shutil.copy(source_file, destination_file)

def installCert(install: bool = True):
	if not install:
		return

	batch_file_path = findFile(r'tools\VDD.HDR.*\VDD*\\*\\InstallCert.bat')

	print(f"{batch_file_path} installing...")
	subprocess.run(['cmd.exe', '/c', batch_file_path])

def findFile(pattern: str) -> str:
	files = glob.glob(pattern)

	if files:
		return os.path.abspath(files[0])

def configureSunshine(first_install: bool = False):
	sunshine_path = 'C:\\Program Files\\Sunshine'
	svm_path = findFile(r'tools\*\\sunshine-virtual-monitor-main')
	setup_sunvdm = findFile(r'tools\*\*\\setup_sunvdm.ps1')
	teardown_sunvdm = findFile(r'tools\*\*\teardown_sunvdm.ps1')
	sunvdm_log = f'{svm_path}\\sunvdm.log'

	if not os.path.exists(sunshine_path):
		sunshine_path = input('\nPlease enter the path to the Sunshine installation folder (the common installation folder should be C:\\Program Files\\Sunshine). :')
		if not os.path.exists(sunshine_path):
			input('\nSunshine Installation folder was not found in this location. Please press any key to go back to the menu...')
			return
	if not os.path.exists(svm_path):
		svm_path = input('\nPlease enter the path to the Sunshine Virtual Monitor folder :')
		if not os.path.exists(svm_path):
			input('\nSunshine Virtual Monitor folder was not found in this location. Please press any key to go back to the menu...')
			return

	config_file = f'{sunshine_path}\\config\\sunshine.conf'

	commands = [
		{
			'do': f'powershell.exe -executionpolicy bypass -windowstyle hidden -file "{setup_sunvdm}" %SUNSHINE_CLIENT_WIDTH% %SUNSHINE_CLIENT_HEIGHT% %SUNSHINE_CLIENT_FPS% %SUNSHINE_CLIENT_HDR% > "{sunvdm_log}" 2>&1',
			'undo': f'powershell.exe -executionpolicy bypass -windowstyle hidden -file "{teardown_sunvdm}" >> "{sunvdm_log}" 2>&1',
			'elevated': 'true'
		}
	]

	reset_global_prep_cmd(config_file, commands)

	if not first_install:
		print("\nSunshine config correctly reset.\nPlaynite Watcher config also erased, please configure it again. (see 2. Selective Download -> 7. Download Playnite Watcher)")
		os.system('pause')

def installWindowsDisplayManager():
	if not checkModuleInstalled("WindowsDisplayManager"):
		subprocess.run(["powershell", "-Command", "Install-Module -Name WindowsDisplayManager"])

def checkModuleInstalled(module_name: str) -> bool:
    command = f"Get-Module -ListAvailable -Name {module_name}"
    
    try:
        result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)

        if result.stdout:
            return True
        else:
            return False

    except:
    	return False

def checkExecutionPolicy() -> bool:
    command = "Get-ExecutionPolicy"

    result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)

    policy = result.stdout.strip()
    if policy != "Undefined":
        subprocess.run(["powershell", "-Command", "Set-ExecutionPolicy Undefined"])
        return True

def reset_global_prep_cmd(file_path, new_commands):
	if not os.path.exists(file_path):
		return

	with open(file_path, 'r') as file:
		lines = file.readlines()

	with open(file_path, 'w') as file:
		for line in lines:
			if not line.startswith("global_prep_cmd ="):
				file.write(line)
		
		file.write('global_prep_cmd = [')
		for cmd in new_commands:
			file.write(f'{json.dumps(cmd)}')
		file.write("]\n")