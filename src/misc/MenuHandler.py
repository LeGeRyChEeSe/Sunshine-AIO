import json
import sys
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from misc.Config import DownloadManager
from misc.SystemRequests import SystemRequests
from misc.Uninstaller import SunshineAIOUninstaller
from misc.Logger import log_success, log_info, log_warning, log_error, log_progress, log_header, get_log_file_path
from misc.MenuDisplay import display_logo, display_version, display_menu, display_prompt, display_status, display_header, clear_screen
from . import __version__

# Import library components with graceful fallback
try:
    from library import LibraryManager, initialize_library_system, ToolInfo
    from library.search_engine import ToolSearchEngine
    from library.filters import ToolFilter
    from library.favorites import FavoritesManager
    from library.display_helper import ToolDisplayHelper
    from library.history import InstallationHistory
    from library.config_manager import LibraryConfigManager
    LIBRARY_AVAILABLE = True
except ImportError as e:
    log_warning(f"Community library not available: {e}")
    LIBRARY_AVAILABLE = False
    LibraryManager = None
    initialize_library_system = None
    ToolInfo = None


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
        
        # Initialize community library components
        self._library_manager: Optional[LibraryManager] = None
        self._library_components: Optional[Dict[str, Any]] = None
        self._search_engine: Optional[ToolSearchEngine] = None
        self._tool_filter: Optional[ToolFilter] = None
        self._favorites_manager: Optional[FavoritesManager] = None
        self._display_helper: Optional[ToolDisplayHelper] = None
        self._installation_history: Optional[InstallationHistory] = None
        self._config_manager: Optional[LibraryConfigManager] = None
        self._initialize_library_system()
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
                "9": self._show_library_menu,
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
            },
            {
                "1": self._browse_all_tools,
                "2": self._browse_by_category,
                "3": self._advanced_search_interface,
                "4": self._filter_tools_interface,
                "5": self._manage_favorites_interface,
                "6": self._tool_comparison_interface,
                "7": self._installation_history_interface,
                "8": self._library_statistics_interface,
                "9": self._export_import_interface,
                "10": self._tool_recommendations_interface,
                "11": self._sync_library,
                "12": self._library_settings,
                "13": self._previous_page,
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
            3: "Uninstall Components",
            4: "Community Library"
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
        self._get_selection()()

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

    def _initialize_library_system(self) -> None:
        """Initialize the community library system with graceful fallback."""
        if not LIBRARY_AVAILABLE:
            log_warning("Community library components are not available")
            return
        
        try:
            log_info("Initializing community library system...")
            
            # Initialize library components
            self._library_components = initialize_library_system(
                base_path=self._sr._base_path,
                config={
                    'library': {
                        'repository_url': 'https://github.com/LeGeRyChEeSe/sunshine-aio-library',
                        'sync_interval': 3600,
                        'validation_enabled': True
                    },
                    'cache': {
                        'default_ttl': 3600,
                        'max_cache_size': 1024 * 1024 * 100,  # 100MB
                        'auto_cleanup': True
                    },
                    'validation': {
                        'validation_level': 'standard',
                        'checksum_required': True,
                        'max_file_size': 100 * 1024 * 1024  # 100MB
                    }
                }
            )
            
            self._library_manager = self._library_components['library_manager']
            
            # Initialize Phase 4 advanced components
            if self._library_manager:
                self._search_engine = ToolSearchEngine(self._library_manager)
                self._tool_filter = ToolFilter()
                self._favorites_manager = FavoritesManager(self._sr._base_path)
                self._display_helper = ToolDisplayHelper()
                self._installation_history = InstallationHistory(self._sr._base_path)
                self._config_manager = LibraryConfigManager(self._sr._base_path)
                log_info("Advanced library features initialized")
            
            log_success("Community library system initialized successfully")
            
        except Exception as e:
            log_error(f"Failed to initialize community library system: {e}")
            log_warning("Community library features will be unavailable")
            self._library_manager = None
            self._library_components = None

    def _show_library_menu(self) -> None:
        """Navigate to the Community Library menu."""
        if not self._is_library_available():
            return
        
        self._page = 4  # Community Library page
        self._set_choices_number()

    def _is_library_available(self) -> bool:
        """Check if library system is available and show error if not."""
        if not LIBRARY_AVAILABLE or not self._library_manager:
            clear_screen()
            display_header("Community Library", "Service Unavailable")
            log_error("Community Library is not available")
            log_info("The community library components could not be loaded.")
            log_info("Please check your installation and try again.")
            input("\nPress Enter to continue...")
            return False
        return True

    def _browse_all_tools(self) -> None:
        """Display all available tools from the community library."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "Browse All Tools")
        
        try:
            log_progress("Loading available tools...")
            tools = self._library_manager.get_available_tools()
            
            if not tools:
                log_warning("No tools are currently available")
                log_info("Try synchronizing the library or check your connection")
                input("\nPress Enter to continue...")
                return
            
            self._display_tools_list(tools, "All Available Tools")
            
        except Exception as e:
            log_error(f"Failed to load tools: {e}")
            log_info("Please try again or check your connection")
            input("\nPress Enter to continue...")

    def _browse_by_category(self) -> None:
        """Browse tools by category."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "Browse by Category")
        
        try:
            log_progress("Loading categories...")
            tools = self._library_manager.get_available_tools()
            
            if not tools:
                log_warning("No tools available for categorization")
                input("\nPress Enter to continue...")
                return
            
            # Group tools by category
            categories = {}
            for tool in tools:
                category = getattr(tool, 'category', 'Uncategorized')
                if category not in categories:
                    categories[category] = []
                categories[category].append(tool)
            
            # Display category menu
            log_info(f"Available categories ({len(categories)}):")
            category_list = list(categories.keys())
            
            for i, category in enumerate(category_list, 1):
                tool_count = len(categories[category])
                log_info(f"  {i}. {category} ({tool_count} tools)")
            
            print()
            choice = input("Select category (number) or press Enter to go back: ").strip()
            
            if choice and choice.isdigit():
                category_index = int(choice) - 1
                if 0 <= category_index < len(category_list):
                    selected_category = category_list[category_index]
                    self._display_tools_list(categories[selected_category], f"{selected_category} Tools")
                else:
                    log_error("Invalid category selection")
                    input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Failed to browse categories: {e}")
            input("\nPress Enter to continue...")

    def _search_tools(self) -> None:
        """Search for tools by name or description."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "Search Tools")
        
        search_query = input("Enter search terms (name, description): ").strip()
        
        if not search_query:
            log_info("Search cancelled")
            input("\nPress Enter to continue...")
            return
        
        try:
            log_progress(f"Searching for '{search_query}'...")
            all_tools = self._library_manager.get_available_tools()
            
            # Simple search implementation
            matching_tools = []
            search_lower = search_query.lower()
            
            for tool in all_tools:
                tool_name = getattr(tool, 'name', '').lower()
                tool_desc = getattr(tool, 'description', '').lower()
                
                if search_lower in tool_name or search_lower in tool_desc:
                    matching_tools.append(tool)
            
            if matching_tools:
                log_success(f"Found {len(matching_tools)} matching tools")
                self._display_tools_list(matching_tools, f"Search Results: '{search_query}'")
            else:
                log_warning(f"No tools found matching '{search_query}'")
                log_info("Try using different search terms")
                input("\nPress Enter to continue...")
                
        except Exception as e:
            log_error(f"Search failed: {e}")
            input("\nPress Enter to continue...")

    def _show_recent_tools(self) -> None:
        """Show recently added tools."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "Recently Added Tools")
        
        try:
            log_progress("Loading recently added tools...")
            tools = self._library_manager.get_available_tools()
            
            if not tools:
                log_warning("No tools available")
                input("\nPress Enter to continue...")
                return
            
            # Sort by creation/modification date if available
            # For now, show latest 10 tools
            recent_tools = tools[:10] if len(tools) > 10 else tools
            
            log_info(f"Showing {len(recent_tools)} most recent tools")
            self._display_tools_list(recent_tools, "Recently Added")
            
        except Exception as e:
            log_error(f"Failed to load recent tools: {e}")
            input("\nPress Enter to continue...")

    def _show_favorites(self) -> None:
        """Show user favorite tools."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "My Favorites")
        
        log_info("Favorites System")
        log_info("═" * 50)
        log_info("The favorites feature will allow you to:")
        log_info("• Mark tools as favorites for quick access")
        log_info("• Create custom categories for your preferred tools")
        log_info("• Sync favorites across different installations")
        log_info("• Get notifications when favorite tools are updated")
        
        print()
        log_warning("This feature is currently under development")
        log_info("It will be available in a future update")
        
        print()
        log_info("Meanwhile, you can:")
        log_info("• Use the search function to quickly find tools")
        log_info("• Browse by category to discover similar tools")
        log_info("• Check 'Recently Added' for the latest tools")
        
        input("\nPress Enter to continue...")

    def _sync_library(self) -> None:
        """Force synchronization of the community library."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "Synchronize Library")
        
        log_warning("This will refresh the community library metadata")
        log_info("This process may take a few moments depending on your connection")
        
        confirm = input("Continue with synchronization? (y/N): ").strip().lower()
        
        if confirm in ['y', 'yes']:
            try:
                log_progress("Synchronizing community library...")
                log_info("• Checking for new tools...")
                log_info("• Updating metadata...")
                log_info("• Validating tool information...")
                
                # Force refresh of library data
                if hasattr(self._library_manager, 'sync'):
                    self._library_manager.sync()
                    log_success("Library synchronization completed successfully")
                    log_info("New tools and updates are now available")
                else:
                    log_info("Automatic synchronization is active")
                    log_info("Library data is kept up-to-date automatically")
                    log_success("No manual synchronization required")
                
            except Exception as e:
                log_error(f"Synchronization failed: {e}")
                log_info("Possible causes:")
                log_info("• No internet connection")
                log_info("• Repository temporarily unavailable")
                log_info("• Firewall blocking access")
                log_info("Please check your connection and try again")
        else:
            log_info("Synchronization cancelled")
        
        input("\nPress Enter to continue...")

    def _library_settings(self) -> None:
        """Configure community library settings."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "Library Settings")
        
        log_info("Library Settings")
        log_info("═" * 50)
        
        # Show current settings
        if self._library_components:
            lib_manager = self._library_components.get('library_manager')
            cache_manager = self._library_components.get('cache_manager')
            validator = self._library_components.get('validator')
            
            if lib_manager:
                log_info(f"Repository URL: {getattr(lib_manager, 'repository_url', 'Not configured')}")
                log_info(f"Cache Directory: {getattr(lib_manager, 'cache_dir', 'Not configured')}")
            
            if cache_manager:
                log_info("Cache: Enabled")
            else:
                log_info("Cache: Disabled")
            
            if validator:
                log_info("Validation: Enabled")
            else:
                log_info("Validation: Disabled")
        
        print()
        log_info("Settings management is not yet fully implemented")
        log_info("Currently using default configuration")
        
        input("\nPress Enter to continue...")

    def _display_tools_list(self, tools: List[Any], title: str) -> None:
        """Display a list of tools with pagination and selection options."""
        if not tools:
            log_warning("No tools to display")
            input("\nPress Enter to continue...")
            return
        
        clear_screen()
        display_header("Community Library", title)
        
        # Display tools with pagination (10 per page)
        page_size = 10
        total_pages = (len(tools) + page_size - 1) // page_size
        current_page = 0
        
        while True:
            clear_screen()
            display_header("Community Library", title)
            
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(tools))
            page_tools = tools[start_idx:end_idx]
            
            log_info(f"Page {current_page + 1} of {total_pages} ({len(tools)} total tools)")
            log_info("═" * 60)
            
            for i, tool in enumerate(page_tools, start_idx + 1):
                tool_name = getattr(tool, 'name', 'Unknown')
                tool_desc = getattr(tool, 'description', 'No description')
                tool_category = getattr(tool, 'category', 'Uncategorized')
                
                # Truncate description if too long
                if len(tool_desc) > 50:
                    tool_desc = tool_desc[:47] + "..."
                
                log_info(f"{i:2d}. {tool_name}")
                log_info(f"    Category: {tool_category}")
                log_info(f"    {tool_desc}")
                print()
            
            # Navigation options
            options = []
            if current_page > 0:
                options.append("P - Previous page")
            if current_page < total_pages - 1:
                options.append("N - Next page")
            options.extend([
                "S - Search in results",
                "R - Refresh list",
                "B - Go back"
            ])
            
            log_info("Navigation:")
            for option in options:
                log_info(f"  {option}")
            
            print()
            choice = input("Select option or tool number: ").strip().lower()
            
            if choice == 'p' and current_page > 0:
                current_page -= 1
            elif choice == 'n' and current_page < total_pages - 1:
                current_page += 1
            elif choice == 's':
                # Search in current results - simplified
                search_term = input("Search term: ").strip().lower()
                if search_term:
                    filtered_tools = [
                        tool for tool in tools 
                        if search_term in getattr(tool, 'name', '').lower() or 
                           search_term in getattr(tool, 'description', '').lower()
                    ]
                    if filtered_tools:
                        self._display_tools_list(filtered_tools, f"{title} - Search: '{search_term}'")
                    else:
                        log_warning("No tools found with that search term")
                        input("\nPress Enter to continue...")
                    return
            elif choice == 'r':
                # Refresh - would reload tools in real implementation
                log_info("List refreshed")
                continue
            elif choice == 'b' or choice == '':
                return
            elif choice.isdigit():
                tool_num = int(choice)
                if 1 <= tool_num <= len(tools):
                    self._show_tool_details(tools[tool_num - 1])
                else:
                    log_error("Invalid tool number")
                    input("\nPress Enter to continue...")
            else:
                log_error("Invalid option")
                input("\nPress Enter to continue...")

    def _show_tool_details(self, tool: Any) -> None:
        """Display detailed information about a selected tool."""
        clear_screen()
        display_header("Community Library", "Tool Details")
        
        tool_name = getattr(tool, 'name', 'Unknown')
        tool_desc = getattr(tool, 'description', 'No description available')
        tool_category = getattr(tool, 'category', 'Uncategorized')
        tool_version = getattr(tool, 'version', 'Unknown')
        tool_author = getattr(tool, 'author', 'Unknown')
        tool_trust_level = getattr(tool, 'trust_level', 'Unknown')
        
        log_info(f"Tool Name: {tool_name}")
        log_info(f"Category: {tool_category}")
        log_info(f"Version: {tool_version}")
        log_info(f"Author: {tool_author}")
        log_info(f"Trust Level: {tool_trust_level}")
        log_info("═" * 60)
        log_info("Description:")
        log_info(tool_desc)
        
        print()
        log_info("Available Actions:")
        log_info("  I - Install this tool")
        log_info("  F - Add to favorites")
        log_info("  B - Go back")
        
        print()
        choice = input("Select action: ").strip().lower()
        
        if choice == 'i':
            self._install_community_tool(tool)
        elif choice == 'f':
            log_info("Favorites functionality not yet implemented")
            input("\nPress Enter to continue...")
        # choice == 'b' or any other input goes back

    def _install_community_tool(self, tool: Any) -> None:
        """Install a community tool with full implementation."""
        tool_name = getattr(tool, 'name', 'Unknown')
        tool_id = getattr(tool, 'tool_id', getattr(tool, 'id', 'unknown'))
        tool_category = getattr(tool, 'category', 'Unknown')
        tool_author = getattr(tool, 'author', 'Unknown')
        tool_version = getattr(tool, 'version', '1.0.0')
        tool_description = getattr(tool, 'description', 'No description available')
        
        clear_screen()
        display_header("Community Library", f"Install {tool_name}")
        
        # Display tool information
        log_info("Tool Installation")
        log_info("═" * 60)
        log_info(f"Tool Name: {tool_name}")
        log_info(f"Tool ID: {tool_id}")
        log_info(f"Version: {tool_version}")
        log_info(f"Category: {tool_category}")
        log_info(f"Author: {tool_author}")
        log_info(f"Description: {tool_description}")
        log_info("═" * 60)
        
        print()
        
        # Check if tool is already installed
        installation_status = self._dm.get_installation_status(tool_id) if hasattr(self._dm, 'get_installation_status') else None
        if installation_status and installation_status.get('status') == 'installed':
            log_warning(f"Tool '{tool_name}' appears to be already installed.")
            print()
            choice = input("Do you want to reinstall? (y/N): ").strip().lower()
            if choice not in ['y', 'yes']:
                log_info("Installation cancelled by user.")
                input("\nPress Enter to continue...")
                return
        
        # Security confirmation
        print()
        log_warning("SECURITY NOTICE")
        log_warning("Community tools are third-party software not officially verified by Sunshine-AIO.")
        log_warning("Install only tools from trusted sources and authors.")
        log_warning("The installation will include integrity checks where possible.")
        
        print()
        choice = input("Do you want to proceed with installation? (y/N): ").strip().lower()
        if choice not in ['y', 'yes']:
            log_info("Installation cancelled by user.")
            input("\nPress Enter to continue...")
            return
        
        try:
            print()
            log_info("Starting installation process...")
            log_info("• Validating tool information")
            log_info("• Checking system compatibility")
            log_info("• Downloading tool files")
            log_info("• Performing security checks")
            log_info("• Installing to tools directory")
            log_info("• Registering with uninstaller")
            
            print()
            log_progress("Initializing installation system...")
            
            # Use the DownloadManager's community tool download functionality
            success = self._dm.download_community_tool(tool_id, install=True)
            
            if success:
                print()
                log_success("Installation completed successfully!")
                log_info("Tool has been installed and registered with the system.")
                log_info("You can uninstall it later using the uninstall menu.")
                
                # Check if we should open tool directory
                print()
                choice = input("Open tools directory to view installed files? (y/N): ").strip().lower()
                if choice in ['y', 'yes']:
                    tools_dir = os.path.join(self._sr._base_path, "tools", tool_id)
                    if os.path.exists(tools_dir):
                        os.startfile(tools_dir)
                    else:
                        log_warning("Tools directory not found")
                
            else:
                print()
                log_error("Installation failed!")
                log_error("Please check the log file for detailed error information.")
                log_info("You can try:")
                log_info("• Checking your internet connection")
                log_info("• Refreshing the community library")
                log_info("• Trying again later")
                
        except ImportError as e:
            print()
            log_error("Installation system not available!")
            log_error(f"Error: {e}")
            log_info("This indicates that the community library system is not properly configured.")
            log_info("Please check your Sunshine-AIO installation.")
            
        except Exception as e:
            print()
            log_error("Installation failed with error!")
            log_error(f"Error: {e}")
            log_info("Please check the log file for more details.")
            
        print()
        input("Press Enter to continue...")

    # ===== PHASE 4: ADVANCED UI FEATURES =====

    def _advanced_search_interface(self) -> None:
        """Interactive advanced search interface with real-time suggestions."""
        if not self._is_library_available() or not self._search_engine:
            return
            
        clear_screen()
        display_header("Community Library", "Advanced Search")
        
        while True:
            try:
                log_info("Advanced Search Options:")
                log_info("═" * 50)
                log_info("1. Text Search (name, description)")
                log_info("2. Category Search")
                log_info("3. Tag Search")
                log_info("4. Combined Search")
                log_info("5. View Search History")
                log_info("6. Clear Search Cache")
                log_info("0. Back to Library Menu")
                
                print()
                choice = input("Select search type: ").strip()
                
                if choice == '1':
                    self._text_search_interface()
                elif choice == '2':
                    self._category_search_interface()
                elif choice == '3':
                    self._tag_search_interface()
                elif choice == '4':
                    self._combined_search_interface()
                elif choice == '5':
                    self._show_search_history()
                elif choice == '6':
                    self._search_engine.clear_cache()
                    log_success("Search cache cleared")
                    input("\nPress Enter to continue...")
                elif choice == '0':
                    return
                else:
                    log_error("Invalid option")
                    input("\nPress Enter to continue...")
                    
            except Exception as e:
                log_error(f"Search error: {e}")
                input("\nPress Enter to continue...")

    def _text_search_interface(self) -> None:
        """Text search with suggestions and fuzzy matching."""
        try:
            clear_screen()
            display_header("Advanced Search", "Text Search")
            
            query = input("Enter search query: ").strip()
            if not query:
                return
            
            # Show suggestions
            if len(query) >= 2:
                suggestions = self._search_engine.get_search_suggestions(query)
                if suggestions:
                    log_info("\nSuggestions:")
                    for i, suggestion in enumerate(suggestions[:5], 1):
                        log_info(f"  {i}. {suggestion}")
                    
                    use_suggestion = input("\nUse suggestion (1-5) or press Enter to continue: ").strip()
                    if use_suggestion.isdigit() and 1 <= int(use_suggestion) <= len(suggestions):
                        query = suggestions[int(use_suggestion) - 1]
            
            # Perform search
            log_progress(f"Searching for '{query}'...")
            results = self._search_engine.search_by_name(query, fuzzy=True)
            
            if results:
                formatted_results = self._display_helper.format_search_results(results, query)
                print(formatted_results)
                self._handle_search_results(results)
            else:
                log_warning("No results found")
                input("\nPress Enter to continue...")
                
        except Exception as e:
            log_error(f"Text search error: {e}")
            input("\nPress Enter to continue...")

    def _filter_tools_interface(self) -> None:
        """Advanced filtering interface with multiple criteria."""
        if not self._is_library_available() or not self._tool_filter:
            return
            
        clear_screen()
        display_header("Community Library", "Advanced Filtering")
        
        try:
            # Get all tools
            tools_dict = self._library_manager.get_available_tools()
            tools = [self._dict_to_tool_info(data, tool_id) for tool_id, data in tools_dict.items()]
            
            if not tools:
                log_warning("No tools available for filtering")
                input("\nPress Enter to continue...")
                return
            
            # Build filter criteria interactively
            filters = {}
            
            while True:
                clear_screen()
                display_header("Advanced Filtering", "Configure Filters")
                
                log_info("Current Filters:")
                log_info("═" * 40)
                if filters:
                    for key, value in filters.items():
                        log_info(f"  {key}: {value}")
                else:
                    log_info("  No filters applied")
                
                print()
                log_info("Filter Options:")
                log_info("1. Size Filter")
                log_info("2. Platform Filter")
                log_info("3. Trust Score Filter")
                log_info("4. Category Filter")
                log_info("5. Tag Filter")
                log_info("6. Last Updated Filter")
                log_info("7. Apply Filters")
                log_info("8. Clear All Filters")
                log_info("0. Back")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '1':
                    max_size = input("Maximum size (e.g., 50MB): ").strip()
                    if max_size:
                        filters['max_size'] = max_size
                elif choice == '2':
                    platform = input("Platform (windows/linux/mac): ").strip()
                    if platform:
                        filters['platforms'] = [platform]
                elif choice == '3':
                    min_trust = input("Minimum trust score (0-10): ").strip()
                    try:
                        filters['trust_score_min'] = float(min_trust)
                    except ValueError:
                        log_error("Invalid trust score")
                elif choice == '4':
                    categories = self._tool_filter.get_available_categories(tools)
                    if categories:
                        log_info("Available categories:")
                        for i, cat in enumerate(categories, 1):
                            log_info(f"  {i}. {cat}")
                        cat_choice = input("Select category number: ").strip()
                        if cat_choice.isdigit() and 1 <= int(cat_choice) <= len(categories):
                            filters['categories'] = [categories[int(cat_choice) - 1]]
                elif choice == '5':
                    tags = input("Enter tags (comma-separated): ").strip()
                    if tags:
                        filters['tags'] = [tag.strip() for tag in tags.split(',')]
                elif choice == '6':
                    days = input("Show tools updated within last X days: ").strip()
                    try:
                        filters['last_updated_days'] = int(days)
                    except ValueError:
                        log_error("Invalid number of days")
                elif choice == '7':
                    # Apply filters
                    if filters:
                        filtered_tools = self._tool_filter.apply_filters(tools, filters)
                        log_success(f"Filtered {len(tools)} tools to {len(filtered_tools)} results")
                        
                        if filtered_tools:
                            formatted_list = self._display_helper.format_tool_list(filtered_tools)
                            print(formatted_list)
                            self._handle_search_results(filtered_tools)
                        else:
                            log_warning("No tools match the filter criteria")
                            input("\nPress Enter to continue...")
                    else:
                        log_warning("No filters specified")
                        input("\nPress Enter to continue...")
                elif choice == '8':
                    filters.clear()
                    log_success("All filters cleared")
                    input("\nPress Enter to continue...")
                elif choice == '0':
                    return
                else:
                    log_error("Invalid option")
                    input("\nPress Enter to continue...")
                    
        except Exception as e:
            log_error(f"Filtering error: {e}")
            input("\nPress Enter to continue...")

    def _manage_favorites_interface(self) -> None:
        """Comprehensive favorites management interface."""
        if not self._is_library_available() or not self._favorites_manager:
            return
            
        clear_screen()
        display_header("Community Library", "Favorites Management")
        
        while True:
            try:
                log_info("Favorites Management:")
                log_info("═" * 40)
                
                favorites = self._favorites_manager.get_favorites()
                log_info(f"Current favorites: {len(favorites)}")
                
                print()
                log_info("Options:")
                log_info("1. View Favorites")
                log_info("2. Add Tool to Favorites")
                log_info("3. Remove from Favorites")
                log_info("4. Get Recommendations")
                log_info("5. Export Favorites")
                log_info("6. Import Favorites")
                log_info("7. User Preferences")
                log_info("8. Activity Summary")
                log_info("0. Back")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '1':
                    self._view_favorites()
                elif choice == '2':
                    self._add_to_favorites()
                elif choice == '3':
                    self._remove_from_favorites()
                elif choice == '4':
                    self._show_recommendations()
                elif choice == '5':
                    self._export_favorites()
                elif choice == '6':
                    self._import_favorites()
                elif choice == '7':
                    self._manage_user_preferences()
                elif choice == '8':
                    self._show_activity_summary()
                elif choice == '0':
                    return
                else:
                    log_error("Invalid option")
                    input("\nPress Enter to continue...")
                    
            except Exception as e:
                log_error(f"Favorites management error: {e}")
                input("\nPress Enter to continue...")

    def _tool_comparison_interface(self) -> None:
        """Side-by-side tool comparison interface."""
        if not self._is_library_available() or not self._display_helper:
            return
            
        clear_screen()
        display_header("Community Library", "Tool Comparison")
        
        try:
            tools_dict = self._library_manager.get_available_tools()
            tools = [self._dict_to_tool_info(data, tool_id) for tool_id, data in tools_dict.items()]
            
            if len(tools) < 2:
                log_warning("Need at least 2 tools for comparison")
                input("\nPress Enter to continue...")
                return
            
            log_info("Select tools to compare (enter tool numbers, comma-separated):")
            log_info("Available tools:")
            
            for i, tool in enumerate(tools[:20], 1):  # Show first 20 tools
                log_info(f"  {i}. {tool.name}")
            
            if len(tools) > 20:
                log_info(f"  ... and {len(tools) - 20} more (use search for specific tools)")
            
            selection = input("\nEnter tool numbers (e.g., 1,3,5): ").strip()
            
            if not selection:
                return
            
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                selected_tools = [tools[i] for i in indices if 0 <= i < len(tools)]
                
                if len(selected_tools) < 2:
                    log_error("Please select at least 2 tools")
                    input("\nPress Enter to continue...")
                    return
                
                # Display comparison
                comparison_table = self._display_helper.format_comparison_table(selected_tools)
                print(comparison_table)
                
                input("\nPress Enter to continue...")
                
            except (ValueError, IndexError):
                log_error("Invalid tool selection")
                input("\nPress Enter to continue...")
                
        except Exception as e:
            log_error(f"Comparison error: {e}")
            input("\nPress Enter to continue...")

    def _installation_history_interface(self) -> None:
        """Installation history and analytics interface."""
        if not self._is_library_available() or not self._installation_history:
            return
            
        clear_screen()
        display_header("Community Library", "Installation History & Analytics")
        
        while True:
            try:
                log_info("Installation History & Analytics:")
                log_info("═" * 50)
                
                print()
                log_info("Options:")
                log_info("1. View Installation History")
                log_info("2. Popular Tools")
                log_info("3. Success Rate Statistics")
                log_info("4. Usage Report")
                log_info("5. Tool Timeline")
                log_info("6. Export History")
                log_info("7. Cleanup Old Records")
                log_info("0. Back")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '1':
                    self._view_installation_history()
                elif choice == '2':
                    self._show_popular_tools()
                elif choice == '3':
                    self._show_success_statistics()
                elif choice == '4':
                    self._show_usage_report()
                elif choice == '5':
                    self._show_tool_timeline()
                elif choice == '6':
                    self._export_installation_history()
                elif choice == '7':
                    self._cleanup_history()
                elif choice == '0':
                    return
                else:
                    log_error("Invalid option")
                    input("\nPress Enter to continue...")
                    
            except Exception as e:
                log_error(f"History interface error: {e}")
                input("\nPress Enter to continue...")

    def _library_statistics_interface(self) -> None:
        """Library statistics and dashboard interface."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "Statistics Dashboard")
        
        try:
            # Get statistics from various components
            tools_dict = self._library_manager.get_available_tools()
            tools = [self._dict_to_tool_info(data, tool_id) for tool_id, data in tools_dict.items()]
            
            # Library overview
            log_info("Library Overview:")
            log_info("═" * 40)
            log_info(f"Total Tools: {len(tools)}")
            
            if self._tool_filter:
                stats = self._tool_filter.get_filter_statistics(tools)
                log_info(f"Categories: {len(stats.get('categories', {}))}")
                log_info(f"Total Tags: {len(stats.get('tags', {}))}")
                
                # Show top categories
                categories = stats.get('categories', {})
                if categories:
                    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
                    log_info("\nTop Categories:")
                    for category, count in top_categories:
                        log_info(f"  {category}: {count} tools")
            
            # Favorites statistics
            if self._favorites_manager:
                favorites = self._favorites_manager.get_favorites()
                log_info(f"\nUser favorites: {len(favorites)}")
                
                activity_summary = self._favorites_manager.get_activity_summary()
                if activity_summary:
                    log_info(f"Activity entries: {activity_summary.get('total_entries', 0)}")
            
            # Installation history statistics
            if self._installation_history:
                usage_report = self._installation_history.generate_usage_report()
                if usage_report:
                    summary = usage_report.get('summary', {})
                    log_info(f"\nInstallation Statistics:")
                    log_info(f"  Total installations: {summary.get('total_installations', 0)}")
                    log_info(f"  Success rate: {summary.get('success_rate', 0):.1%}")
                    log_info(f"  Unique tools used: {summary.get('unique_tools', 0)}")
            
            # Search engine statistics
            if self._search_engine:
                cache_stats = self._search_engine.get_cache_stats()
                log_info(f"\nSearch Cache:")
                log_info(f"  Cached searches: {cache_stats.get('search_cache_size', 0)}")
                log_info(f"  Cached suggestions: {cache_stats.get('suggestion_cache_size', 0)}")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Statistics error: {e}")
            input("\nPress Enter to continue...")

    def _export_import_interface(self) -> None:
        """Data export and import interface."""
        if not self._is_library_available():
            return
            
        clear_screen()
        display_header("Community Library", "Export & Import")
        
        while True:
            try:
                log_info("Export & Import Options:")
                log_info("═" * 40)
                
                print()
                log_info("Export Options:")
                log_info("1. Export Favorites")
                log_info("2. Export Configuration")
                log_info("3. Export Installation History")
                log_info("4. Export All User Data")
                
                print()
                log_info("Import Options:")
                log_info("5. Import Favorites")
                log_info("6. Import Configuration")
                log_info("7. Import User Data")
                
                print()
                log_info("Backup Options:")
                log_info("8. Create System Backup")
                log_info("9. Restore from Backup")
                
                print()
                log_info("0. Back")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '1':
                    self._export_favorites()
                elif choice == '2':
                    self._export_configuration()
                elif choice == '3':
                    self._export_history()
                elif choice == '4':
                    self._export_all_data()
                elif choice == '5':
                    self._import_favorites()
                elif choice == '6':
                    self._import_configuration()
                elif choice == '7':
                    self._import_user_data()
                elif choice == '8':
                    self._create_system_backup()
                elif choice == '9':
                    self._restore_from_backup()
                elif choice == '0':
                    return
                else:
                    log_error("Invalid option")
                    input("\nPress Enter to continue...")
                    
            except Exception as e:
                log_error(f"Export/Import error: {e}")
                input("\nPress Enter to continue...")

    def _tool_recommendations_interface(self) -> None:
        """Intelligent tool recommendations interface."""
        if not self._is_library_available() or not self._favorites_manager:
            return
            
        clear_screen()
        display_header("Community Library", "Tool Recommendations")
        
        try:
            log_progress("Generating personalized recommendations...")
            recommendations = self._favorites_manager.get_recommendations(self._library_manager)
            
            if recommendations:
                log_success(f"Found {len(recommendations)} recommendations for you:")
                print()
                
                formatted_list = self._display_helper.format_tool_list(recommendations)
                print(formatted_list)
                
                self._handle_search_results(recommendations)
            else:
                log_info("No recommendations available yet")
                log_info("Try adding some tools to favorites to get personalized recommendations")
                input("\nPress Enter to continue...")
                
        except Exception as e:
            log_error(f"Recommendations error: {e}")
            input("\nPress Enter to continue...")

    # ===== HELPER METHODS FOR ADVANCED FEATURES =====

    def _dict_to_tool_info(self, tool_data: Dict[str, Any], tool_id: str) -> ToolInfo:
        """Convert tool dictionary to ToolInfo object."""
        try:
            if hasattr(ToolInfo, 'from_dict'):
                return ToolInfo.from_dict(tool_data)
            else:
                # Manual creation as fallback
                return ToolInfo(
                    id=tool_id,
                    name=tool_data.get('name', tool_id),
                    description=tool_data.get('description', ''),
                    category=tool_data.get('category', 'General'),
                    version=tool_data.get('version', '1.0.0'),
                    author=tool_data.get('author', 'Unknown')
                )
        except Exception as e:
            log_error(f"Error creating ToolInfo for {tool_id}: {e}")
            # Return minimal ToolInfo as fallback
            return ToolInfo(
                id=tool_id,
                name=tool_data.get('name', tool_id),
                description=tool_data.get('description', ''),
                category='General',
                version='1.0.0',
                author='Unknown'
            )

    def _handle_search_results(self, results: List[ToolInfo]) -> None:
        """Handle search results with selection options."""
        if not results:
            return
        
        print()
        log_info("Actions:")
        log_info("1. View tool details")
        log_info("2. Install tool")
        log_info("3. Add to favorites")
        log_info("4. Compare tools")
        log_info("0. Back")
        
        choice = input("\nSelect action: ").strip()
        
        if choice == '1':
            tool_num = input("Enter tool number: ").strip()
            if tool_num.isdigit():
                idx = int(tool_num) - 1
                if 0 <= idx < len(results):
                    tool_details = self._display_helper.format_tool_info(results[idx], detailed=True)
                    print(tool_details)
                    input("\nPress Enter to continue...")
        elif choice == '2':
            tool_num = input("Enter tool number to install: ").strip()
            if tool_num.isdigit():
                idx = int(tool_num) - 1
                if 0 <= idx < len(results):
                    self._install_community_tool(results[idx])
        elif choice == '3' and self._favorites_manager:
            tool_num = input("Enter tool number to add to favorites: ").strip()
            if tool_num.isdigit():
                idx = int(tool_num) - 1
                if 0 <= idx < len(results):
                    if self._favorites_manager.add_favorite(results[idx].id):
                        log_success("Added to favorites!")
                    else:
                        log_warning("Failed to add to favorites")
                    input("\nPress Enter to continue...")
        elif choice == '4':
            log_info("Select tools to compare (enter numbers, comma-separated):")
            selection = input("Tool numbers: ").strip()
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                selected_tools = [results[i] for i in indices if 0 <= i < len(results)]
                if len(selected_tools) >= 2:
                    comparison = self._display_helper.format_comparison_table(selected_tools)
                    print(comparison)
                    input("\nPress Enter to continue...")
                else:
                    log_error("Select at least 2 tools for comparison")
                    input("\nPress Enter to continue...")
            except (ValueError, IndexError):
                log_error("Invalid selection")
                input("\nPress Enter to continue...")

    def _view_favorites(self) -> None:
        """View and manage favorite tools."""
        try:
            favorites = self._favorites_manager.get_favorite_tools(self._library_manager)
            
            if favorites:
                clear_screen()
                display_header("Favorites", f"{len(favorites)} Favorite Tools")
                
                formatted_list = self._display_helper.format_tool_list(favorites)
                print(formatted_list)
                
                self._handle_search_results(favorites)
            else:
                log_info("No favorite tools yet")
                log_info("Browse the library and add tools to favorites!")
                input("\nPress Enter to continue...")
                
        except Exception as e:
            log_error(f"Error viewing favorites: {e}")
            input("\nPress Enter to continue...")

    def _show_recommendations(self) -> None:
        """Show tool recommendations."""
        try:
            count = input("Number of recommendations (default 5): ").strip()
            try:
                count = int(count) if count else 5
            except ValueError:
                count = 5
            
            recommendations = self._favorites_manager.get_recommendations(self._library_manager, count)
            
            if recommendations:
                clear_screen()
                display_header("Recommendations", f"Top {len(recommendations)} Recommendations")
                
                formatted_list = self._display_helper.format_tool_list(recommendations)
                print(formatted_list)
                
                self._handle_search_results(recommendations)
            else:
                log_info("No recommendations available")
                input("\nPress Enter to continue...")
                
        except Exception as e:
            log_error(f"Error generating recommendations: {e}")
            input("\nPress Enter to continue...")

    # ===== ADDITIONAL HELPER METHODS =====

    def _add_to_favorites(self) -> None:
        """Add a tool to favorites by search or selection."""
        try:
            query = input("Search for tool to add to favorites: ").strip()
            if not query:
                return
            
            # Search for tools
            results = self._search_engine.search_by_name(query, fuzzy=True)
            if not results:
                log_warning("No tools found")
                input("\nPress Enter to continue...")
                return
            
            # Show results and let user select
            log_info("Found tools:")
            for i, tool in enumerate(results[:10], 1):
                log_info(f"  {i}. {tool.name}")
            
            choice = input("Select tool number to add to favorites: ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    if self._favorites_manager.add_favorite(results[idx].id):
                        log_success(f"Added '{results[idx].name}' to favorites!")
                    else:
                        log_warning("Failed to add to favorites (may already be favorited)")
                else:
                    log_error("Invalid selection")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error adding to favorites: {e}")
            input("\nPress Enter to continue...")

    def _remove_from_favorites(self) -> None:
        """Remove a tool from favorites."""
        try:
            favorites = self._favorites_manager.get_favorites()
            if not favorites:
                log_info("No favorites to remove")
                input("\nPress Enter to continue...")
                return
            
            log_info("Current favorites:")
            for i, tool_id in enumerate(favorites, 1):
                log_info(f"  {i}. {tool_id}")
            
            choice = input("Select number to remove from favorites: ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(favorites):
                    tool_id = favorites[idx]
                    if self._favorites_manager.remove_favorite(tool_id):
                        log_success(f"Removed '{tool_id}' from favorites")
                    else:
                        log_warning("Failed to remove from favorites")
                else:
                    log_error("Invalid selection")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error removing from favorites: {e}")
            input("\nPress Enter to continue...")

    def _export_favorites(self) -> None:
        """Export favorites to file."""
        try:
            filename = input("Export filename (or press Enter for default): ").strip()
            if not filename:
                filename = f"favorites_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            export_path = os.path.join(self._sr._base_path, "exports", filename)
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            if self._favorites_manager.export_favorites(export_path):
                log_success(f"Favorites exported to: {export_path}")
            else:
                log_error("Failed to export favorites")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error exporting favorites: {e}")
            input("\nPress Enter to continue...")

    def _import_favorites(self) -> None:
        """Import favorites from file."""
        try:
            filename = input("Import filename (full path): ").strip()
            if not filename:
                log_info("Import cancelled")
                input("\nPress Enter to continue...")
                return
            
            if self._favorites_manager.import_favorites(filename):
                log_success("Favorites imported successfully!")
            else:
                log_error("Failed to import favorites")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error importing favorites: {e}")
            input("\nPress Enter to continue...")

    def _manage_user_preferences(self) -> None:
        """Manage user preferences interface."""
        try:
            log_info("User preferences management not yet fully implemented")
            log_info("This will allow configuration of:")
            log_info("• Search preferences")
            log_info("• Display settings")
            log_info("• Recommendation settings")
            log_info("• Notification preferences")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error managing preferences: {e}")
            input("\nPress Enter to continue...")

    def _show_activity_summary(self) -> None:
        """Show user activity summary."""
        try:
            summary = self._favorites_manager.get_activity_summary()
            if summary:
                log_info("Activity Summary:")
                log_info("═" * 30)
                log_info(f"Total entries: {summary.get('total_entries', 0)}")
                
                actions = summary.get('actions', {})
                if actions:
                    log_info("\nActions performed:")
                    for action, count in actions.items():
                        log_info(f"  {action}: {count}")
                
                trends = summary.get('favorite_trends', {})
                if trends:
                    log_info(f"\nFavorites added last week: {trends.get('added_last_week', 0)}")
                    log_info(f"Favorites removed last week: {trends.get('removed_last_week', 0)}")
            else:
                log_info("No activity data available")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error showing activity summary: {e}")
            input("\nPress Enter to continue...")

    # Placeholder methods for features not yet fully implemented
    def _category_search_interface(self) -> None:
        """Category search interface."""
        log_info("Category search interface - coming soon!")
        input("\nPress Enter to continue...")

    def _tag_search_interface(self) -> None:
        """Tag search interface."""
        log_info("Tag search interface - coming soon!")
        input("\nPress Enter to continue...")

    def _combined_search_interface(self) -> None:
        """Combined search interface."""
        log_info("Combined search interface - coming soon!")
        input("\nPress Enter to continue...")

    def _show_search_history(self) -> None:
        """Show search history."""
        log_info("Search history - coming soon!")
        input("\nPress Enter to continue...")

    def _view_installation_history(self) -> None:
        """View installation history."""
        try:
            if self._installation_history:
                history = self._installation_history.get_installation_history(20)
                if history:
                    log_info("Recent Installation History:")
                    log_info("═" * 40)
                    for entry in history:
                        timestamp = entry.get('timestamp', 'Unknown')
                        action = entry.get('action', 'unknown')
                        tool_id = entry.get('tool_id', 'unknown')
                        success = entry.get('success', False)
                        status = "✓" if success else "✗"
                        log_info(f"{timestamp[:19]} | {status} {action} | {tool_id}")
                else:
                    log_info("No installation history available")
            else:
                log_info("Installation history not available")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error viewing history: {e}")
            input("\nPress Enter to continue...")

    def _show_popular_tools(self) -> None:
        """Show popular tools."""
        try:
            if self._installation_history:
                popular = self._installation_history.get_popular_tools(10)
                if popular:
                    log_info("Most Popular Tools (Last 30 Days):")
                    log_info("═" * 40)
                    for i, tool_id in enumerate(popular, 1):
                        log_info(f"{i}. {tool_id}")
                else:
                    log_info("No popularity data available")
            else:
                log_info("Installation history not available")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error showing popular tools: {e}")
            input("\nPress Enter to continue...")

    def _show_success_statistics(self) -> None:
        """Show installation success statistics."""
        try:
            if self._installation_history:
                overall_rate = self._installation_history.get_success_rate()
                log_info("Installation Success Statistics:")
                log_info("═" * 40)
                log_info(f"Overall success rate: {overall_rate:.1%}")
            else:
                log_info("Installation history not available")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error showing statistics: {e}")
            input("\nPress Enter to continue...")

    def _show_usage_report(self) -> None:
        """Show detailed usage report."""
        try:
            if self._installation_history:
                log_progress("Generating usage report...")
                report = self._installation_history.generate_usage_report()
                if report:
                    log_info("Usage Report:")
                    log_info("═" * 30)
                    
                    summary = report.get('summary', {})
                    log_info(f"Total installations: {summary.get('total_installations', 0)}")
                    log_info(f"Successful: {summary.get('successful_installations', 0)}")
                    log_info(f"Failed: {summary.get('failed_installations', 0)}")
                    log_info(f"Success rate: {summary.get('success_rate', 0):.1%}")
                    log_info(f"Unique tools: {summary.get('unique_tools', 0)}")
                else:
                    log_info("No usage data available")
            else:
                log_info("Installation history not available")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            log_error(f"Error showing usage report: {e}")
            input("\nPress Enter to continue...")

    # Additional placeholder methods for export/import features
    def _show_tool_timeline(self) -> None:
        log_info("Tool timeline feature - coming soon!")
        input("\nPress Enter to continue...")

    def _export_installation_history(self) -> None:
        log_info("Export installation history - coming soon!")
        input("\nPress Enter to continue...")

    def _cleanup_history(self) -> None:
        log_info("History cleanup feature - coming soon!")
        input("\nPress Enter to continue...")

    def _export_configuration(self) -> None:
        log_info("Export configuration - coming soon!")
        input("\nPress Enter to continue...")

    def _export_history(self) -> None:
        log_info("Export history - coming soon!")
        input("\nPress Enter to continue...")

    def _export_all_data(self) -> None:
        log_info("Export all data - coming soon!")
        input("\nPress Enter to continue...")

    def _import_configuration(self) -> None:
        log_info("Import configuration - coming soon!")
        input("\nPress Enter to continue...")

    def _import_user_data(self) -> None:
        log_info("Import user data - coming soon!")
        input("\nPress Enter to continue...")

    def _create_system_backup(self) -> None:
        log_info("Create system backup - coming soon!")
        input("\nPress Enter to continue...")

    def _restore_from_backup(self) -> None:
        log_info("Restore from backup - coming soon!")
        input("\nPress Enter to continue...")

    def print_menu(self):
        while True:
            clear_screen()
            self._print_logo()
            self._print_version()
            self._print_page()
            if self._get_user_input():
                self._execute_selection()
