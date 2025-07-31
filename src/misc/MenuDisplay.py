import os
import shutil
from typing import Dict, List
from misc.Logger import log_info, log_header


class MenuDisplay:
    """
    Enhanced menu display system with ASCII art and centered layout
    """
    
    def __init__(self):
        self.terminal_width = self._get_terminal_width()
        # Optimize for readability with proper margins
        self.menu_width = min(76, self.terminal_width - 8)  # Better proportions
    
    def _get_terminal_width(self) -> int:
        """Get terminal width, fallback to 80 if not available"""
        try:
            return shutil.get_terminal_size().columns
        except:
            return 80
    
    def _center_text(self, text: str, width: int = None) -> str:
        """Center text within given width"""
        if width is None:
            width = self.menu_width
        return text.center(width)
    
    def _create_box(self, content: List[str], title: str = None) -> str:
        """Create a bordered box with content"""
        box_width = self.menu_width
        
        # Ensure minimum width
        if box_width < 40:
            box_width = 40
        
        # Top border
        if title and title.strip():
            title_text = f" {title.strip()} "
            remaining_width = box_width - len(title_text) - 2
            if remaining_width > 0:
                left_dashes = remaining_width // 2
                right_dashes = remaining_width - left_dashes
                title_line = f"╭{'─' * left_dashes}{title_text}{'─' * right_dashes}╮"
            else:
                title_line = "╭" + "─" * (box_width - 2) + "╮"
        else:
            title_line = "╭" + "─" * (box_width - 2) + "╮"
        
        # Content lines
        content_lines = []
        for line in content:
            # Handle empty lines
            if not line:
                padded_line = "│" + " " * (box_width - 2) + "│"
            else:
                # Truncate if too long
                if len(line) > box_width - 4:
                    line = line[:box_width - 7] + "..."
                # Pad to exact width
                padded_line = f"│ {line:<{box_width - 4}} │"
            content_lines.append(padded_line)
        
        # Bottom border
        bottom_line = "╰" + "─" * (box_width - 2) + "╯"
        
        return "\n".join([title_line] + content_lines + [bottom_line])
    
    def display_logo(self) -> None:
        """Display the Sunshine-AIO ASCII logo from file"""
        try:
            # Get the path to the logo file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(current_dir, "ressources", "logo_menu.txt")
            
            # Read the logo file
            with open(logo_path, 'r', encoding='utf-8') as file:
                logo_lines = file.read().splitlines()
            
            # Display each line centered
            for line in logo_lines:
                print(self._center_text(line, self.terminal_width))
                
        except FileNotFoundError:
            # Fallback if file not found
            fallback_logo = [
                "    ____                  _     _                 _    ___ ___",
                "   / ___| _   _ _ __  ___| |__ (_)_ __   ___     / \\  |_ _/ _ \\",
                "   \\___ \\| | | | '_ \\/ __| '_ \\| | '_ \\ / _ \\   / _ \\  | | | | |",
                "    ___) | |_| | | | \\__ \\ | | | | | | |  __/  / ___ \\ | | |_| |",
                "   |____/ \\__,_|_| |_|___/_| |_|_|_| |_|\\___| /_/   \\_\\___\\___/",
                ""
            ]
            for line in fallback_logo:
                print(self._center_text(line, self.terminal_width))
        except Exception as e:
            # If any other error, show simple text
            print(self._center_text("SUNSHINE-AIO", self.terminal_width))
    
    def display_version(self, version: str) -> None:
        """Display version information"""
        version_text = f"Version {version}"
        print(self._center_text(version_text, self.terminal_width))
        print()
    
    def display_menu_options(self, options: Dict[str, str], title: str = "Menu Options") -> None:
        """Display menu options in a formatted box"""
        content = []
        
        # Sort options by key, but put '0' (Exit) at the end
        sorted_options = sorted(options.items(), key=lambda x: (x[0] == '0', x[0]))
        
        for key, description in sorted_options:
            if key == '0':
                content.append("")  # Add separator before exit option
                content.append(f"  {key}. {description}")
            else:
                content.append(f"  {key}. {description}")
        
        box = self._create_box(content, title)
        print(self._center_text(box, self.terminal_width))
        print()
    
    def display_input_prompt(self, max_option: int) -> str:
        """Display input prompt and return user input"""
        prompt = f"Please choose an option (0-{max_option}): "
        centered_prompt = self._center_text(prompt, self.terminal_width)
        
        # Calculate the position where input should start
        spaces_before = " " * ((self.terminal_width - len(prompt)) // 2)
        
        return input(f"{spaces_before}{prompt}")
    
    def display_status_message(self, message: str, status_type: str = "info") -> None:
        """Display a status message in a box"""
        icons = {
            "success": "✓",
            "error": "✗", 
            "warning": "⚠",
            "info": "ℹ"
        }
        
        icon = icons.get(status_type, "ℹ")
        formatted_message = f"{icon} {message}"
        
        content = [formatted_message]
        box = self._create_box(content)
        print(self._center_text(box, self.terminal_width))
        print()
    
    def display_header_section(self, title: str, subtitle: str = None) -> None:
        """Display a section header"""
        print("\n")
        header_box = []
        header_box.append(title.upper())
        if subtitle:
            header_box.append("")
            header_box.append(subtitle)
        
        box = self._create_box(header_box, "")
        print(self._center_text(box, self.terminal_width))
        print()
    
    def display_installation_steps(self, steps: List[str], title: str = "Installation Steps") -> None:
        """Display installation steps in a formatted way"""
        content = []
        for i, step in enumerate(steps, 1):
            content.append(f"{i}. {step}")
        
        box = self._create_box(content, title)
        print(self._center_text(box, self.terminal_width))
        print()
    
    def display_footer(self, message: str = None) -> None:
        """Display footer message"""
        if not message:
            message = "Thank you for using Sunshine-AIO!"
        
        print(self._center_text("─" * len(message), self.terminal_width))
        print(self._center_text(message, self.terminal_width))
        print()
    
    def clear_screen(self) -> None:
        """Clear the screen with minimal spacing"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print()  # Single line spacing


# Global display instance
menu_display = MenuDisplay()


# Convenience functions
def display_logo():
    """Display the Sunshine-AIO logo"""
    menu_display.display_logo()


def display_version(version: str):
    """Display version information"""
    menu_display.display_version(version)


def display_menu(options: Dict[str, str], title: str = "Menu Options"):
    """Display menu options"""
    menu_display.display_menu_options(options, title)


def display_prompt(max_option: int) -> str:
    """Display input prompt"""
    return menu_display.display_input_prompt(max_option)


def display_status(message: str, status_type: str = "info"):
    """Display status message"""
    menu_display.display_status_message(message, status_type)


def display_header(title: str, subtitle: str = None):
    """Display section header"""
    menu_display.display_header_section(title, subtitle)


def display_steps(steps: List[str], title: str = "Steps"):
    """Display steps"""
    menu_display.display_installation_steps(steps, title)


def clear_screen():
    """Clear screen"""
    menu_display.clear_screen()