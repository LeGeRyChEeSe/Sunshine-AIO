import json
import sys
import os
from typing import List, Dict
from misc.Config import DownloadManager
from misc.SystemRequests import SystemRequests
from misc.Uninstaller import SunshineAIOUninstaller
from misc.Logger import log_success, log_info, log_warning, log_error, log_progress, log_header, get_log_file_path
from misc.MenuDisplay import display_logo, display_version, display_menu, display_prompt, display_status, display_header, clear_screen
from . import __version__


class MenuHandler:
    """
        The Menu Handler.

        Attribtues
        ----------
        page: :class:`int`
            The current page.
        choices: :class:`JSON`
            The list of all choices.
        user_input: :class:`int`
            The user input.
    """

    def __init__(self, base_path: str) -> None:
        self._page: int = 0
        self._choices: List[Dict[str, str]]
        self._choices_number: int
        self._sr: SystemRequests = SystemRequests(base_path)
        self._logo_menu_path: str = f"{self._sr._base_path}\\misc\\ressources\\logo_menu.txt"
        self._menu_choices_path: str = f"{self._sr._base_path}\\misc\\variables\\menu_choices.json"
        self._user_input: int
        self._rerun_as_admin = self._sr.rerun_as_admin
        self._dm: DownloadManager = DownloadManager(self._sr, self._page)
        self._config = self._dm.config
        self._uninstaller: SunshineAIOUninstaller = SunshineAIOUninstaller(self._sr)
        self._map = [
            {
                "1": self._dm.download_all,
                "2": lambda: self._dm.download_sunshine(selective=True),
                "3": lambda: self._dm.download_vdd(selective=True),
                "4": lambda: self._dm.download_svm(selective=True),
                "5": lambda: self._dm.download_playnite(selective=True),
                "6": lambda: self._dm.download_playnite_watcher(selective=True),
                "7": self._next_page,
                "8": self._show_uninstall_menu,
                "0": sys.exit
            },
            {
                "1": lambda: self._dm.download_all(install=False),
                "2": self._next_page,
                "3": lambda: self._config.configure_sunshine(selective=True),
                "4": lambda: self._sr.install_windows_display_manager(selective=True),
                "5": self._config.open_sunshine_settings,
                "6": self._config.open_playnite,
                "7": self._open_vdd_control,
                "8": self._previous_page,
                "0": sys.exit
            },
            {
                "1": lambda: self._dm.download_sunshine(install=False, selective=True),
                "2": lambda: self._dm.download_vdd(install=False, selective=True),
                "3": lambda: self._dm.download_svm(install=False, selective=True),
                "4": lambda: self._dm.download_mmt(selective=True),
                "5": lambda: self._dm.download_vsync_toggle(selective=True),
                "6": lambda: self._dm.download_playnite(install=False, selective=True),
                "7": lambda: self._dm.download_playnite_watcher(install=False, selective=True),
                "8": self._previous_page,
                "0": sys.exit
            },
            {
                "1": self._show_uninstall_report,
                "2": self._show_installed_components,
                "3": self._uninstall_specific_component,
                "4": self._uninstall_all_components,
                "5": self._back_to_main_menu,
                "0": sys.exit
            }
        ]

        self._set_choices()

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self):
        raise ValueError("No manual edit allowed.")

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self):
        raise ValueError("No manual edit allowed.")

    @property
    def choices_number(self):
        return self._choices_number

    @choices_number.setter
    def choices_number(self):
        raise ValueError("No manual edit allowed.")

    @property
    def logo_menu_path(self):
        return self._logo_menu_path

    @logo_menu_path.setter
    def logo_menu_path(self):
        raise ValueError("No manual edit allowed.")

    @property
    def menu_choices_path(self):
        return self._menu_choices_path

    @menu_choices_path.setter
    def menu_choices_path(self):
        raise ValueError("No manual edit allowed.")

    @property
    def user_input(self):
        return self._user_input

    @user_input.setter
    def user_input(self):
        raise ValueError("No manual edit allowed.")

    @property
    def sr(self):
        return self._sr

    @sr.setter
    def sr(self):
        raise ValueError("No manual edit allowed.")

    @property
    def rerun_as_admin(self):
        return self._rerun_as_admin

    @rerun_as_admin.setter
    def rerun_as_admin(self):
        raise ValueError("No manual edit allowed.")

    @property
    def dm(self):
        return self._dm

    @dm.setter
    def dm(self):
        raise ValueError("No manual edit allowed.")

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self):
        raise ValueError("No manual edit allowed.")

    @property
    def map(self):
        return self._map

    @map.setter
    def map(self):
        raise ValueError("No manual edit allowed.")

    def _print_logo(self) -> None:
        display_logo()

    def _print_version(self) -> None:
        display_version(__version__)
        # Show log file path (compact)
        log_file = get_log_file_path()
        log_info(f"Log: {os.path.basename(log_file)}")

    def _set_choices(self) -> None:
        with open(self._menu_choices_path, 'rb') as choices:
            self._choices = json.loads(choices.read())
        self._set_choices_number()

    def _set_choices_number(self) -> None:
        self._choices_number = len(self._choices[self._page]) - 1

    def _print_page(self) -> None:
        # Determine menu title based on page
        page_titles = {
            0: "Main Menu",
            1: "Extra Tools & Configuration", 
            2: "Selective Download",
            3: "Uninstall Components"
        }
        title = page_titles.get(self._page, "Menu Options")
        display_menu(self._choices[self._page], title)

    def _get_user_input(self) -> bool:
        try:
            user_input_str = display_prompt(self._choices_number)
            user_input = int(user_input_str)
            if 0 <= user_input <= self._choices_number:
                self._user_input = user_input
                return True
            else:
                display_status("Invalid option. Please try again.", "error")
                input("\nPress Enter to continue...")
                return False
        except ValueError:
            display_status("Please enter a valid number.", "error")
            input("\nPress Enter to continue...")
            return False

    def _next_page(self):
        self._page += 1
        self._set_choices_number()

    def _previous_page(self):
        self._page -= 1
        self._set_choices_number()
    
    def _back_to_main_menu(self):
        """Return to main menu (page 0)"""
        self._page = 0
        self._set_choices_number()

    def _get_selection(self):
        return self._map[self._page][str(self._user_input)]

    def _execute_selection(self):
        # Execute the method associated with the user_input
        selection_func = self._get_selection()
        selection_func()

        # Add a pause after action execution, except for navigation and exit
        # Navigation functions: _next_page, _previous_page, _back_to_main_menu, _show_uninstall_menu
        # Exit function: sys.exit
        if selection_func not in [self._next_page, self._previous_page, self._back_to_main_menu, self._show_uninstall_menu, sys.exit]:
            input("\nPress Enter to continue...")

    def _show_uninstall_menu(self):
        """Display the uninstallation menu."""
        self._page = 3  # Uninstallation page
        self._set_choices_number()

    def _show_uninstall_report(self):
        """Display uninstallation report."""
        clear_screen()
        display_header("Uninstallation Report", "System Analysis")
        print(self._uninstaller.generate_uninstall_report())
        input("\nPress Enter to continue...")

    def _show_installed_components(self):
        """Display installed components."""
        clear_screen()
        display_header("Installed Components", "System Status")
        
        # Try to detect and update existing installations
        log_info("Scanning system for existing installations...")
        self._detect_and_update_installations()
        
        installed = self._uninstaller.list_installed_components()
        
        if installed:
            log_info("Sunshine-AIO installed components:")
            for component in installed:
                log_success(f"{component}")
        else:
            log_warning("No Sunshine-AIO components detected on this system.")
        
        input("\nPress Enter to continue...")

    def _detect_and_update_installations(self):
        """Detect existing installations and update tracker."""
        log_info("Performing comprehensive installation detection...")
        
        # Detect Sunshine installation using DownloadManager's detection method
        sunshine_path = self._dm._detect_sunshine_installation_path()
        if sunshine_path:
            log_info(f"Detected Sunshine installation at: {sunshine_path}")
            self._config._update_sunshine_tracker_if_needed(sunshine_path)
        else:
            log_info("No Sunshine installation detected")
        
        # Detect VDD Control installation
        vdd_control_path = os.path.join("tools", "VDD Control")
        if os.path.exists(vdd_control_path):
            vdd_control_exe = os.path.join(vdd_control_path, "VDD Control.exe")
            if os.path.exists(vdd_control_exe):
                log_info(f"Detected VDD Control at: {vdd_control_path}")
                # Update tracker for VDD if not already tracked
                if not self._uninstaller._tracker.is_tool_installed("virtual_display_driver"):
                    install_info = {
                        "version": "latest",
                        "installer_type": "manual_vdd_control",
                        "files_created": [vdd_control_path],
                        "custom_options": {
                            "control_executable": vdd_control_exe,
                            "installation_method": "Detected existing VDD Control",
                            "detected_path": vdd_control_path
                        }
                    }
                    self._uninstaller._tracker.track_installation("virtual_display_driver", vdd_control_path, install_info)
                    log_success("VDD Control installation tracked")
        
        # Detect other tools in tools/ directory
        tools_dir = "tools"
        if os.path.exists(tools_dir):
            for item in os.listdir(tools_dir):
                item_path = os.path.join(tools_dir, item)
                if os.path.isdir(item_path):
                    self._detect_and_track_tool_in_directory(item, item_path)
        
        log_success("Installation detection completed")
    
    def _detect_and_track_tool_in_directory(self, dir_name: str, dir_path: str):
        """Detect and track a tool based on directory name and content."""
        tool_mappings = {
            "sunshine-virtual-monitor": "sunshine_virtual_monitor",
            "multimonitortool": "multi_monitor_tool", 
            "playnite watcher": "playnite_watcher",
            "vsync toggle": "vsync_toggle"
        }
        
        dir_name_lower = dir_name.lower()
        tool_key = None
        
        # Find matching tool
        for pattern, key in tool_mappings.items():
            if pattern in dir_name_lower:
                tool_key = key
                break
        
        if tool_key and not self._uninstaller._tracker.is_tool_installed(tool_key):
            log_info(f"Detected {dir_name} at: {dir_path}")
            install_info = {
                "version": "detected",
                "installer_type": "auto_detected",
                "files_created": [dir_path],
                "custom_options": {
                    "installation_method": "Auto-detected existing installation",
                    "detected_path": dir_path,
                    "original_name": dir_name
                }
            }
            self._uninstaller._tracker.track_installation(tool_key, dir_path, install_info)
            log_success(f"{dir_name} installation tracked")

    def _uninstall_specific_component(self):
        """Uninstall a specific component."""
        clear_screen()
        display_header("Component Uninstaller", "Select component to remove")
        
        components_list = list(self._uninstaller._components.values())
        
        # Create options dict for display
        options = {}
        for i, component in enumerate(components_list, 1):
            options[str(i)] = component['name']
        options['0'] = "Cancel"
        
        display_menu(options, "Available Components")
        
        try:
            choice_str = display_prompt(len(components_list))
            choice = int(choice_str)
            
            if choice == 0:
                return
            elif 1 <= choice <= len(components_list):
                component_name = components_list[choice - 1]['name']
                log_progress(f"Uninstalling {component_name}...")
                
                if self._uninstaller.uninstall_component(component_name):
                    log_success(f"{component_name} uninstalled successfully!")
                else:
                    log_error(f"Issues encountered during {component_name} uninstallation")
            else:
                display_status("Invalid selection.", "error")
        except ValueError:
            display_status("Please enter a valid number.", "error")
        
        input("\nPress Enter to continue...")

    def _uninstall_all_components(self):
        """Uninstall all components."""
        clear_screen()
        display_header("Complete Uninstallation", "WARNING: This will remove ALL components")
        
        log_warning("This operation will remove ALL Sunshine-AIO components!")
        log_warning("This action is irreversible.")
        
        confirm = input("\nType 'CONFIRM' to proceed or press Enter to cancel: ")
        if confirm.upper() != 'CONFIRM':
            log_info("Uninstallation cancelled.")
            input("\nPress Enter to continue...")
            return
        
        log_progress("Starting complete uninstallation...")
        if self._uninstaller.uninstall_all():
            log_success("Complete uninstallation finished successfully!")
        else:
            log_warning("Uninstallation completed with warnings.")
            log_info("Check the messages above for details.")
        
        input("\nPress Enter to continue...")

    def _open_vdd_control(self):
        """Opens VDD Control if available."""
        import os
        import subprocess
        
        clear_screen()
        display_header("VDD Control Launcher", "Virtual Display Driver Configuration")
        
        vdd_control_path = os.path.join("tools", "VDD Control")
        vdd_control_exe_path = os.path.join(vdd_control_path, "VDD Control.exe")
        
        if os.path.exists(vdd_control_exe_path):
            log_progress("Launching VDD Control...")
            try:
                subprocess.Popen([vdd_control_exe_path], cwd=vdd_control_path)
                log_success("VDD Control launched successfully!")
            except Exception as e:
                log_error(f"Failed to launch VDD Control: {e}")
        else:
            log_warning("VDD Control is not available.")
            log_info("Please download and install Virtual Display Driver first.")
            log_info(f"Expected location: {vdd_control_exe_path}")
        
        input("\nPress Enter to continue...")

    def print_menu(self):
        while True:
            clear_screen()
            self._print_logo()
            self._print_version()
            self._print_page()
            if self._get_user_input():
                self._execute_selection()
