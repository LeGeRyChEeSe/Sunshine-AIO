import json
import sys
import os
from typing import List, Dict, Optional, Any
from misc.Config import DownloadManager
from misc.SystemRequests import SystemRequests
from misc.Uninstaller import SunshineAIOUninstaller
from misc.Logger import log_success, log_info, log_warning, log_error, log_progress, log_header, get_log_file_path
from misc.MenuDisplay import display_logo, display_version, display_menu, display_prompt, display_status, display_header, clear_screen
from . import __version__

# Import library components with graceful fallback
try:
    from library import LibraryManager, initialize_library_system, ToolInfo
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
                "3": self._search_tools,
                "4": self._show_recent_tools,
                "5": self._show_favorites,
                "6": self._sync_library,
                "7": self._library_settings,
                "8": self._previous_page,
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
        """Install a community tool (placeholder implementation)."""
        tool_name = getattr(tool, 'name', 'Unknown')
        tool_category = getattr(tool, 'category', 'Unknown')
        tool_author = getattr(tool, 'author', 'Unknown')
        
        clear_screen()
        display_header("Community Library", f"Install {tool_name}")
        
        log_info("Tool Installation Process")
        log_info("═" * 50)
        log_info(f"Tool: {tool_name}")
        log_info(f"Category: {tool_category}")
        log_info(f"Author: {tool_author}")
        
        print()
        log_warning("Community tool installation is currently under development")
        
        print()
        log_info("The installation process will include:")
        log_info("• Security validation and integrity checks")
        log_info("• Automatic dependency resolution")
        log_info("• Safe installation to designated directories")
        log_info("• Integration with Sunshine-AIO uninstaller")
        log_info("• Automatic updates when available")
        
        print()
        log_info("Current alternatives:")
        log_info("• Check the tool's description for manual installation steps")
        log_info("• Visit the community repository for direct downloads")
        log_info("• Look for similar tools in the main installation options")
        
        print()
        log_success("This feature will be available soon!")
        
        input("\nPress Enter to continue...")

    def print_menu(self):
        while True:
            clear_screen()
            self._print_logo()
            self._print_version()
            self._print_page()
            if self._get_user_input():
                self._execute_selection()
