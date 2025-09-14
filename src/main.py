import os
import sys
from misc.MenuHandler import MenuHandler
from misc.AppMetadata import setup_console, get_app_name, get_app_version
from misc.Logger import log_info, get_log_file_path, enable_print_capture, disable_print_capture

def main():
    """Main application entry point"""
    try:
        # Setup console branding and appearance
        setup_console()
        
        # Initialize application
        base_path = os.path.abspath(os.path.dirname(__file__))
        menu = MenuHandler(base_path)
        
        # Show startup info
        print(f"Starting {get_app_name()} {get_app_version()}...")
        log_info(f"Application started - Log file: {get_log_file_path()}")
        log_info("System logging enabled - tracking installations and configurations only")
        
        # Request admin privileges and start menu
        menu.rerun_as_admin()
        menu.print_menu()
        
    except KeyboardInterrupt:
        log_info("Application interrupted by user")
        print("\nApplication interrupted by user.")
    except Exception as e:
        print(f"Critical error: {e}")
        log_info(f"Critical error: {e}")
        input("Press Enter to exit...")
    finally:
        log_info("Application session ended")

if __name__ == "__main__":
    main()
