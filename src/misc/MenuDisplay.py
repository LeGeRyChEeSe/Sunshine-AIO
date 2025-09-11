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

    # ===== PHASE 4: ADVANCED DISPLAY FUNCTIONS =====

    def display_search_interface(self, query: str, suggestions: List[str]) -> str:
        """Display interactive search interface with suggestions."""
        try:
            content = []
            content.append(f"Search Query: {query}")
            
            if suggestions:
                content.append("")
                content.append("Suggestions:")
                for i, suggestion in enumerate(suggestions[:5], 1):
                    content.append(f"  {i}. {suggestion}")
                content.append("")
                content.append("Press 1-5 to use suggestion, or Enter to search")
            else:
                content.append("")
                content.append("Press Enter to search...")
            
            box = self._create_box(content, "Advanced Search")
            return self._center_text(box, self.terminal_width)
            
        except Exception as e:
            return f"Error displaying search interface: {e}"

    def display_tool_comparison(self, tools: List[Dict]) -> None:
        """Display side-by-side tool comparison table."""
        try:
            if not tools or len(tools) < 2:
                self.display_status_message("Need at least 2 tools for comparison", "warning")
                return
            
            # Limit to 3 tools for readability
            tools = tools[:3]
            
            print(self._center_text("═" * self.menu_width, self.terminal_width))
            print(self._center_text("TOOL COMPARISON", self.terminal_width))
            print(self._center_text("═" * self.menu_width, self.terminal_width))
            print()
            
            # Create comparison table
            attributes = ['Name', 'Category', 'Version', 'Author', 'Trust Score', 'Size']
            
            # Calculate column widths
            col_width = (self.menu_width - len(tools) - 1) // (len(tools) + 1)
            
            # Header row
            header_row = "│" + "Attribute".ljust(col_width) + "│"
            for tool in tools:
                tool_name = tool.get('name', 'Unknown')[:col_width-1]
                header_row += tool_name.ljust(col_width) + "│"
            
            print(self._center_text(header_row, self.terminal_width))
            print(self._center_text("├" + "─" * col_width + "┼" + ("─" * col_width + "┼") * len(tools), self.terminal_width))
            
            # Data rows
            for attr in attributes:
                attr_key = attr.lower().replace(' ', '_')
                row = "│" + attr.ljust(col_width) + "│"
                
                for tool in tools:
                    value = str(tool.get(attr_key, 'N/A'))[:col_width-1]
                    row += value.ljust(col_width) + "│"
                
                print(self._center_text(row, self.terminal_width))
            
            print(self._center_text("└" + "─" * col_width + "┴" + ("─" * col_width + "┴") * len(tools), self.terminal_width))
            print()
            
        except Exception as e:
            self.display_status_message(f"Error displaying comparison: {e}", "error")

    def display_installation_progress(self, tool_name: str, progress: float) -> None:
        """Display installation progress with visual progress bar."""
        try:
            # Clear current line and display progress
            progress_width = 40
            filled_width = int(progress * progress_width)
            
            bar = "█" * filled_width + "▒" * (progress_width - filled_width)
            progress_text = f"Installing {tool_name}: [{bar}] {progress:.1%}"
            
            print(f"\r{self._center_text(progress_text, self.terminal_width)}", end="", flush=True)
            
            if progress >= 1.0:
                print()  # New line when complete
                
        except Exception as e:
            print(f"\rProgress display error: {e}")

    def display_statistics_dashboard(self, stats: Dict) -> None:
        """Display comprehensive statistics dashboard."""
        try:
            content = []
            content.append("LIBRARY STATISTICS DASHBOARD")
            content.append("═" * 40)
            content.append("")
            
            # Basic statistics
            content.append("📊 Overview:")
            content.append(f"  Total Tools: {stats.get('total_tools', 0)}")
            content.append(f"  Categories: {stats.get('total_categories', 0)}")
            content.append(f"  Tags: {stats.get('total_tags', 0)}")
            content.append("")
            
            # User statistics
            if 'user_stats' in stats:
                user_stats = stats['user_stats']
                content.append("👤 User Activity:")
                content.append(f"  Favorites: {user_stats.get('favorites_count', 0)}")
                content.append(f"  Installations: {user_stats.get('installations', 0)}")
                content.append(f"  Success Rate: {user_stats.get('success_rate', 0):.1%}")
                content.append("")
            
            # Popular categories
            if 'top_categories' in stats:
                content.append("📂 Top Categories:")
                for category, count in stats['top_categories'][:5]:
                    content.append(f"  {category}: {count} tools")
                content.append("")
            
            # Recent activity
            if 'recent_activity' in stats:
                content.append("🕒 Recent Activity:")
                for activity in stats['recent_activity'][:3]:
                    content.append(f"  {activity.get('action', 'Unknown')}: {activity.get('tool', 'N/A')}")
            
            box = self._create_box(content, "Statistics Dashboard")
            print(self._center_text(box, self.terminal_width))
            print()
            
        except Exception as e:
            self.display_status_message(f"Error displaying statistics: {e}", "error")

    def display_filter_interface(self, active_filters: Dict) -> None:
        """Display current filter status and options."""
        try:
            content = []
            content.append("ACTIVE FILTERS")
            content.append("─" * 20)
            
            if active_filters:
                for filter_name, filter_value in active_filters.items():
                    filter_display = filter_name.replace('_', ' ').title()
                    if isinstance(filter_value, list):
                        value_display = ', '.join(str(v) for v in filter_value)
                    else:
                        value_display = str(filter_value)
                    content.append(f"🔍 {filter_display}: {value_display}")
            else:
                content.append("No filters applied")
            
            content.append("")
            content.append("Available Filter Options:")
            content.append("1. Size Filter")
            content.append("2. Platform Filter") 
            content.append("3. Trust Score Filter")
            content.append("4. Category Filter")
            content.append("5. Tag Filter")
            content.append("6. Last Updated Filter")
            
            box = self._create_box(content, "Filter Configuration")
            print(self._center_text(box, self.terminal_width))
            print()
            
        except Exception as e:
            self.display_status_message(f"Error displaying filters: {e}", "error")

    def display_favorites_list(self, favorites: List[Dict], title: str = "Favorite Tools") -> None:
        """Display list of favorite tools with enhanced formatting."""
        try:
            content = []
            
            if not favorites:
                content.append("No favorite tools yet")
                content.append("")
                content.append("💡 Tip: Browse the library and add tools to favorites!")
            else:
                content.append(f"You have {len(favorites)} favorite tools:")
                content.append("")
                
                for i, tool in enumerate(favorites, 1):
                    tool_name = tool.get('name', 'Unknown')
                    tool_category = tool.get('category', 'General')
                    star_rating = "⭐" * min(int(tool.get('trust_score', 5) / 2), 5)
                    
                    content.append(f"{i:2d}. {tool_name}")
                    content.append(f"    📁 {tool_category} {star_rating}")
                    if i < len(favorites):
                        content.append("")
            
            box = self._create_box(content, title)
            print(self._center_text(box, self.terminal_width))
            print()
            
        except Exception as e:
            self.display_status_message(f"Error displaying favorites: {e}", "error")

    def display_installation_history(self, history: List[Dict], title: str = "Installation History") -> None:
        """Display installation history with status indicators."""
        try:
            content = []
            
            if not history:
                content.append("No installation history available")
            else:
                content.append(f"Recent installations ({len(history)} entries):")
                content.append("")
                
                for entry in history[:10]:  # Show last 10 entries
                    timestamp = entry.get('timestamp', 'Unknown')[:16]  # YYYY-MM-DD HH:MM
                    tool_name = entry.get('tool_id', 'Unknown')
                    success = entry.get('success', False)
                    action = entry.get('action', 'install')
                    
                    status_icon = "✅" if success else "❌"
                    action_icon = "📥" if action == 'installation' else "🗑️"
                    
                    content.append(f"{timestamp} {action_icon} {status_icon} {tool_name}")
            
            box = self._create_box(content, title)
            print(self._center_text(box, self.terminal_width))
            print()
            
        except Exception as e:
            self.display_status_message(f"Error displaying history: {e}", "error")

    def display_tool_details_enhanced(self, tool: Dict) -> None:
        """Display detailed tool information with rich formatting."""
        try:
            content = []
            
            # Header with tool name and key info
            tool_name = tool.get('name', 'Unknown Tool')
            tool_version = tool.get('version', '1.0.0')
            content.append(f"🔧 {tool_name} v{tool_version}")
            content.append("═" * len(f"{tool_name} v{tool_version}"))
            content.append("")
            
            # Basic information
            content.append("📋 Information:")
            content.append(f"  Category: {tool.get('category', 'General')}")
            content.append(f"  Author: {tool.get('author', 'Unknown')}")
            content.append(f"  Size: {self._format_file_size(tool.get('size', 0))}")
            
            # Trust score with visual indicator
            trust_score = tool.get('trust_score', 5.0)
            stars = "⭐" * int(trust_score / 2)
            content.append(f"  Trust Score: {trust_score}/10 {stars}")
            
            # Platforms
            platforms = tool.get('platforms', ['Windows'])
            if isinstance(platforms, str):
                platforms = [platforms]
            platform_icons = {'windows': '🪟', 'linux': '🐧', 'mac': '🍎'}
            platform_display = ' '.join([platform_icons.get(p.lower(), '💻') for p in platforms])
            content.append(f"  Platforms: {platform_display} {', '.join(platforms)}")
            
            content.append("")
            
            # Description
            description = tool.get('description', 'No description available')
            content.append("📝 Description:")
            # Word wrap description
            words = description.split()
            line = ""
            for word in words:
                if len(line + word) > self.menu_width - 8:
                    content.append(f"  {line.strip()}")
                    line = word + " "
                else:
                    line += word + " "
            if line.strip():
                content.append(f"  {line.strip()}")
            
            content.append("")
            
            # Tags
            tags = tool.get('tags', [])
            if tags:
                if isinstance(tags, str):
                    tags = [tags]
                content.append(f"🏷️  Tags: {', '.join(tags)}")
                content.append("")
            
            # Installation status
            content.append("⚙️  Actions Available:")
            content.append("  [I] Install Tool")
            content.append("  [F] Add to Favorites")
            content.append("  [D] Download Only")
            content.append("  [C] Compare with Others")
            
            box = self._create_box(content, "Tool Details")
            print(self._center_text(box, self.terminal_width))
            print()
            
        except Exception as e:
            self.display_status_message(f"Error displaying tool details: {e}", "error")

    def display_recommendations(self, recommendations: List[Dict], title: str = "Recommended for You") -> None:
        """Display personalized tool recommendations."""
        try:
            content = []
            
            if not recommendations:
                content.append("🤖 No recommendations available yet")
                content.append("")
                content.append("💡 Tips to get recommendations:")
                content.append("  • Add tools to favorites")
                content.append("  • Install some tools")
                content.append("  • Browse different categories")
            else:
                content.append(f"🎯 {len(recommendations)} tools recommended for you:")
                content.append("")
                
                for i, tool in enumerate(recommendations[:5], 1):
                    tool_name = tool.get('name', 'Unknown')
                    category = tool.get('category', 'General')
                    trust_score = tool.get('trust_score', 5.0)
                    
                    # Simple recommendation score visualization
                    score_stars = "⭐" * min(int(trust_score / 2), 5)
                    
                    content.append(f"{i}. 🔧 {tool_name}")
                    content.append(f"   📁 {category} {score_stars}")
                    
                    if i < len(recommendations):
                        content.append("")
            
            box = self._create_box(content, title)
            print(self._center_text(box, self.terminal_width))
            print()
            
        except Exception as e:
            self.display_status_message(f"Error displaying recommendations: {e}", "error")

    def display_export_import_status(self, operation: str, file_path: str, success: bool, details: str = "") -> None:
        """Display export/import operation status."""
        try:
            operation_icons = {
                'export': '📤',
                'import': '📥',
                'backup': '💾',
                'restore': '♻️'
            }
            
            icon = operation_icons.get(operation.lower(), '📋')
            status_icon = "✅" if success else "❌"
            status_text = "SUCCESS" if success else "FAILED"
            
            content = []
            content.append(f"{icon} {operation.upper()} {status_text} {status_icon}")
            content.append("─" * 30)
            content.append(f"File: {os.path.basename(file_path)}")
            content.append(f"Path: {file_path}")
            
            if details:
                content.append("")
                content.append(f"Details: {details}")
            
            if success:
                content.append("")
                content.append("✨ Operation completed successfully!")
            else:
                content.append("")
                content.append("⚠️  Please check the error message above")
            
            box = self._create_box(content, f"{operation.title()} Status")
            print(self._center_text(box, self.terminal_width))
            print()
            
        except Exception as e:
            self.display_status_message(f"Error displaying {operation} status: {e}", "error")

    def _format_file_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        try:
            if size == 0:
                return "Unknown"
            
            units = ['B', 'KB', 'MB', 'GB', 'TB']
            size_float = float(size)
            
            for unit in units:
                if size_float < 1024.0:
                    if unit == 'B':
                        return f"{int(size_float)} {unit}"
                    else:
                        return f"{size_float:.1f} {unit}"
                size_float /= 1024.0
            
            return f"{size_float:.1f} PB"
            
        except Exception:
            return "Unknown"


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


# ===== PHASE 4: ADVANCED DISPLAY CONVENIENCE FUNCTIONS =====

def display_search_interface(query: str, suggestions: List[str]) -> str:
    """Display interactive search interface with suggestions"""
    return menu_display.display_search_interface(query, suggestions)


def display_tool_comparison(tools: List[Dict]) -> None:
    """Display side-by-side tool comparison table"""
    menu_display.display_tool_comparison(tools)


def display_installation_progress(tool_name: str, progress: float) -> None:
    """Display installation progress with visual progress bar"""
    menu_display.display_installation_progress(tool_name, progress)


def display_statistics_dashboard(stats: Dict) -> None:
    """Display comprehensive statistics dashboard"""
    menu_display.display_statistics_dashboard(stats)


def display_filter_interface(active_filters: Dict) -> None:
    """Display current filter status and options"""
    menu_display.display_filter_interface(active_filters)


def display_favorites_list(favorites: List[Dict], title: str = "Favorite Tools") -> None:
    """Display list of favorite tools with enhanced formatting"""
    menu_display.display_favorites_list(favorites, title)


def display_installation_history(history: List[Dict], title: str = "Installation History") -> None:
    """Display installation history with status indicators"""
    menu_display.display_installation_history(history, title)


def display_tool_details_enhanced(tool: Dict) -> None:
    """Display detailed tool information with rich formatting"""
    menu_display.display_tool_details_enhanced(tool)


def display_recommendations(recommendations: List[Dict], title: str = "Recommended for You") -> None:
    """Display personalized tool recommendations"""
    menu_display.display_recommendations(recommendations, title)


def display_export_import_status(operation: str, file_path: str, success: bool, details: str = "") -> None:
    """Display export/import operation status"""
    menu_display.display_export_import_status(operation, file_path, success, details)