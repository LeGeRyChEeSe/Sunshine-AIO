"""
GUI Entry Point for Sunshine-AIO

This is the main entry point for the graphical user interface version of Sunshine-AIO.
It provides a modern, user-friendly interface while using all existing business logic.
"""

import os
import sys
import tkinter.messagebox as msgbox

# Add src directory to path for imports
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

def main():
    """Main entry point for GUI application"""
    try:
        # Check if CustomTkinter is available
        try:
            import customtkinter as ctk
        except ImportError:
            msgbox.showerror(
                "Missing Dependency",
                "CustomTkinter is required for the GUI interface.\n\n"
                "Please install it using:\n"
                "pip install customtkinter\n\n"
                "Or install all requirements:\n"
                "pip install -r requirements.txt"
            )
            return 1
        
        # Import and start GUI
        from gui.main_window import SunshineAIOMainWindow
        
        # Set up application metadata
        from misc.AppMetadata import setup_console, get_app_name, get_app_version
        setup_console()
        
        # Initialize and run GUI
        app = SunshineAIOMainWindow()
        app.run()
        return 0
        
    except ImportError as e:
        msgbox.showerror(
            "Import Error",
            f"Failed to import required modules: {e}\n\n"
            "Please ensure all dependencies are installed:\n"
            "pip install -r requirements.txt"
        )
        return 1
        
    except Exception as e:
        msgbox.showerror(
            "Critical Error",
            f"Failed to start GUI application: {e}\n\n"
            "Please check the console for more details or try running the CLI version."
        )
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)