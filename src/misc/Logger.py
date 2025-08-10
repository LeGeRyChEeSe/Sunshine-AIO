import os
import datetime
import traceback
import glob
import sys
from enum import Enum
from typing import Optional


class LogLevel(Enum):
    """Log levels with color codes for console output"""
    SUCCESS = ("\033[92m", "✓")    # Green
    INFO = ("\033[94m", "ℹ")       # Blue  
    WARNING = ("\033[93m", "⚠")    # Yellow
    ERROR = ("\033[91m", "✗")      # Red
    PROGRESS = ("\033[96m", "→")   # Cyan
    HEADER = ("\033[95m", "■")     # Magenta
    RESET = "\033[0m"              # Reset color


class Logger:
    """
    Enhanced logging system with color support for Sunshine-AIO
    
    Features:
    - Color-coded messages for different log levels
    - Icons for better visual identification
    - Consistent formatting across the application
    - Optional file logging capability
    """
    
    def __init__(self, enable_colors: bool = True, log_file: Optional[str] = None, max_log_files: int = 5, log_type: str = "app"):
        self.enable_colors = enable_colors and self._supports_color()
        self.max_log_files = max_log_files
        self.log_type = log_type
        
        # Auto-generate log file name if not provided
        if log_file is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Get project root directory (go up from src/misc/ to project root)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            logs_dir = os.path.join(project_root, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Different log file names based on type
            if log_type == "script":
                self.log_file = os.path.join(logs_dir, f"sunshine_aio_script_{timestamp}.log")
            else:
                # For app type, check if we're running as admin and reuse existing log
                existing_log = self._find_existing_app_log(logs_dir)
                if existing_log and self._is_admin_rerun():
                    self.log_file = existing_log
                    self._append_to_existing = True
                else:
                    self.log_file = os.path.join(logs_dir, f"sunshine_aio_app_{timestamp}.log")
                    self._append_to_existing = False
        else:
            self.log_file = log_file
            self._append_to_existing = False
        
        # Perform log rotation before initializing new log file (only if not appending)
        if not getattr(self, '_append_to_existing', False):
            self._rotate_logs()
        
        # Initialize log file with session header (or append admin section)
        self._initialize_log_file()
        
    def _supports_color(self) -> bool:
        """Check if the terminal supports ANSI color codes"""
        return (
            hasattr(os, 'isatty') and os.isatty(1) or 
            os.environ.get('TERM') in ('xterm', 'xterm-color', 'xterm-256color') or
            os.environ.get('COLORTERM') in ('truecolor', '24bit') or
            'ANSICON' in os.environ
        )
    
    def _find_existing_app_log(self, logs_dir: str) -> Optional[str]:
        """Find the most recent app log file from today"""
        try:
            today = datetime.datetime.now().strftime("%Y%m%d")
            app_log_pattern = os.path.join(logs_dir, f"sunshine_aio_app_{today}_*.log")
            app_logs = glob.glob(app_log_pattern)
            
            if app_logs:
                # Return the most recent app log from today
                app_logs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                return app_logs[0]
            return None
        except Exception:
            return None
    
    def _is_admin_rerun(self) -> bool:
        """Check if this is likely an admin rerun (simple heuristic)"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    
    def _rotate_logs(self):
        """Rotate log files, keeping only the most recent max_log_files"""
        try:
            # Find all existing log files in the correct directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            logs_dir = os.path.join(project_root, "logs")
            log_pattern = os.path.join(logs_dir, "sunshine_aio_*.log")
            log_files = glob.glob(log_pattern)
            
            if len(log_files) >= self.max_log_files:
                # Sort by modification time (oldest first)
                log_files.sort(key=lambda x: os.path.getmtime(x))
                
                # Remove oldest files to keep only (max_log_files - 1) files
                # This leaves room for the new log file that will be created
                files_to_remove = len(log_files) - (self.max_log_files - 1)
                
                for i in range(files_to_remove):
                    try:
                        os.remove(log_files[i])
                        print(f"Removed old log file: {log_files[i]}")
                    except Exception as e:
                        print(f"Warning: Could not remove old log file {log_files[i]}: {e}")
                        
        except Exception as e:
            print(f"Warning: Log rotation failed: {e}")
    
    def _initialize_log_file(self):
        """Initialize log file with session header or append admin section"""
        try:
            if getattr(self, '_append_to_existing', False):
                # Append admin section to existing log
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("ADMIN ELEVATION - CONTINUING SESSION\n")
                    f.write(f"Admin session started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
            else:
                # Create new log file
                mode = 'w' if self.log_type == "app" else 'w'
                with open(self.log_file, mode, encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    if self.log_type == "script":
                        f.write("SUNSHINE-AIO SCRIPT LOG\n")
                    else:
                        f.write("SUNSHINE-AIO APPLICATION LOG\n")
                    f.write(f"Session started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Log file: {self.log_file}\n")
                    f.write("=" * 80 + "\n\n")
        except Exception as e:
            print(f"Warning: Could not initialize log file: {e}")
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp for log entries"""
        return datetime.datetime.now().strftime("%H:%M:%S")
    
    def _format_message(self, level: LogLevel, message: str) -> str:
        """Format message with color and icon"""
        if self.enable_colors:
            color_code, icon = level.value
            return f"{color_code}{icon} {message}{LogLevel.RESET.value}"
        else:
            return f"{level.value[1]} {message}"
    
    def _log(self, level: LogLevel, message: str):
        """Internal logging method"""
        formatted_message = self._format_message(level, message)
        print(formatted_message)
        
        # File logging with timestamp
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = self._get_timestamp()
                    # Clean message without ANSI codes for file
                    clean_message = f"[{timestamp}] {level.value[1]} {message}"
                    f.write(f"{clean_message}\n")
            except Exception as e:
                print(f"Warning: Could not write to log file: {e}")
    
    def success(self, message: str):
        """Log success message"""
        self._log(LogLevel.SUCCESS, message)
    
    def info(self, message: str):
        """Log informational message"""
        self._log(LogLevel.INFO, message)
    
    def warning(self, message: str):
        """Log warning message"""
        self._log(LogLevel.WARNING, message)
    
    def error(self, message: str):
        """Log error message"""
        self._log(LogLevel.ERROR, message)
    
    def progress(self, message: str):
        """Log progress message"""
        self._log(LogLevel.PROGRESS, message)
    
    def header(self, message: str, separator: str = "=", width: int = 70):
        """Log header with separator line"""
        if self.enable_colors:
            color_code, icon = LogLevel.HEADER.value
            print(f"\n{color_code}{separator * width}{LogLevel.RESET.value}")
            print(f"{color_code}{icon} {message.upper()}{LogLevel.RESET.value}")
            print(f"{color_code}{separator * width}{LogLevel.RESET.value}\n")
        else:
            print(f"\n{separator * width}")
            print(f"{LogLevel.HEADER.value[1]} {message.upper()}")
            print(f"{separator * width}\n")
        
        # Log header to file as well
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = self._get_timestamp()
                    f.write(f"\n[{timestamp}] {separator * width}\n")
                    f.write(f"[{timestamp}] {LogLevel.HEADER.value[1]} {message.upper()}\n")
                    f.write(f"[{timestamp}] {separator * width}\n\n")
            except Exception as e:
                print(f"Warning: Could not write header to log file: {e}")
    
    def separator(self, char: str = "-", width: int = 50):
        """Print a separator line"""
        if self.enable_colors:
            print(f"\033[90m{char * width}{LogLevel.RESET.value}")
        else:
            print(char * width)
        
        # Log separator to file as well
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = self._get_timestamp()
                    f.write(f"[{timestamp}] {char * width}\n")
            except Exception as e:
                print(f"Warning: Could not write separator to log file: {e}")
    
    def step(self, step_number: int, total_steps: int, description: str):
        """Log a step in a multi-step process"""
        progress_msg = f"Step {step_number}/{total_steps}: {description}"
        self.progress(progress_msg)
    
    def exception(self, message: str, exc: Exception = None):
        """Log an exception with full traceback"""
        self._log(LogLevel.ERROR, message)
        
        # Log exception details to file
        if self.log_file and exc:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = self._get_timestamp()
                    f.write(f"[{timestamp}] EXCEPTION DETAILS:\n")
                    f.write(f"Exception Type: {type(exc).__name__}\n")
                    f.write(f"Exception Message: {str(exc)}\n")
                    f.write("Traceback:\n")
                    f.write(traceback.format_exc())
                    f.write("-" * 80 + "\n\n")
            except Exception as e:
                print(f"Warning: Could not write exception to log file: {e}")
    
    def section_start(self, section_name: str):
        """Mark the start of a major section"""
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = self._get_timestamp()
                    f.write(f"\n[{timestamp}] ===== SECTION START: {section_name.upper()} =====\n")
            except Exception:
                pass
    
    def section_end(self, section_name: str):
        """Mark the end of a major section"""
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = self._get_timestamp()
                    f.write(f"[{timestamp}] ===== SECTION END: {section_name.upper()} =====\n\n")
            except Exception:
                pass
    
    def get_log_file_path(self) -> str:
        """Get the current log file path"""
        return self.log_file
    
    def log_print(self, message: str):
        """Log a print message to file (for capturing print() calls)"""
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = self._get_timestamp()
                    f.write(f"[{timestamp}] {message}\n")
            except Exception as e:
                pass  # Silent fail to avoid recursion


class LogCapture:
    """Capture print statements and redirect them to log file (system logs only)"""
    
    def __init__(self, logger_instance):
        self.logger = logger_instance
        self.original_stdout = sys.stdout
        # Patterns to filter out (menu/user interface messages)
        self.filter_patterns = [
            "press enter",
            "choose option",
            "select",
            "menu",
            "option",
            "choice",
            "input",
            "═",
            "─",
            "│",
            "┌",
            "┐",
            "└",
            "┘",
            "starting sunshine",
            "application started",
            "application session",
            "print capture",
            "[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]", "[8]", "[9]", "[0]"
        ]
        
    def write(self, message: str):
        # Write to original stdout (console)
        self.original_stdout.write(message)
        
        # Filter out menu/UI messages - only log system operations
        if message.strip() and self._should_log(message.strip()):
            self.logger.log_print(message.strip())
    
    def _should_log(self, message: str) -> bool:
        """Determine if a message should be logged (system operations only)"""
        message_lower = message.lower()
        
        # Skip empty or whitespace-only messages
        if not message.strip():
            return False
            
        # Skip messages containing UI/menu patterns
        for pattern in self.filter_patterns:
            if pattern in message_lower:
                return False
        
        # Only log system operations (installations, downloads, configurations, errors)
        system_keywords = [
            "download", "install", "uninstall", "extract", "configur", 
            "error", "warning", "success", "fail", "complet", "start",
            "driver", "service", "registry", "file", "directory"
        ]
        
        return any(keyword in message_lower for keyword in system_keywords)
    
    def flush(self):
        self.original_stdout.flush()


# Global logger instance (will be initialized as app logger by default)
logger = Logger(log_type="app")

# Global log capture instance
log_capture = None


# Convenience functions for easy usage
def log_success(message: str):
    """Log success message"""
    logger.success(message)


def log_info(message: str):
    """Log informational message"""
    logger.info(message)


def log_warning(message: str):
    """Log warning message"""
    logger.warning(message)


def log_error(message: str):
    """Log error message"""
    logger.error(message)


def log_progress(message: str):
    """Log progress message"""
    logger.progress(message)


def log_header(message: str, separator: str = "=", width: int = 70):
    """Log header with separator line"""
    logger.header(message, separator, width)


def log_separator(char: str = "-", width: int = 50):
    """Print a separator line"""
    logger.separator(char, width)


def log_step(step_number: int, total_steps: int, description: str):
    """Log a step in a multi-step process"""
    logger.step(step_number, total_steps, description)


def log_exception(message: str, exc: Exception = None):
    """Log an exception with full traceback"""
    logger.exception(message, exc)


def log_section_start(section_name: str):
    """Mark the start of a major section"""
    logger.section_start(section_name)


def log_section_end(section_name: str):
    """Mark the end of a major section"""
    logger.section_end(section_name)


def get_log_file_path() -> str:
    """Get the current log file path"""
    return logger.get_log_file_path()


def enable_system_log_capture():
    """Enable capturing of system print statements to log file (no menu/UI)"""
    global log_capture
    if log_capture is None:
        log_capture = LogCapture(logger)
        sys.stdout = log_capture
        log_info("System log capture enabled - tracking system operations only")


def disable_system_log_capture():
    """Disable capturing of system print statements"""
    global log_capture
    if log_capture is not None:
        sys.stdout = log_capture.original_stdout
        log_capture = None
        log_info("System log capture disabled")


def is_system_log_capture_enabled() -> bool:
    """Check if system log capture is currently enabled"""
    return log_capture is not None

# Keep old function names for backwards compatibility
def enable_print_capture():
    """Legacy function - use enable_system_log_capture instead"""
    enable_system_log_capture()

def disable_print_capture():
    """Legacy function - use disable_system_log_capture instead"""
    disable_system_log_capture()

def is_print_capture_enabled() -> bool:
    """Legacy function - use is_system_log_capture_enabled instead"""
    return is_system_log_capture_enabled()


def create_script_logger() -> Logger:
    """Create a dedicated logger for PowerShell script usage"""
    return Logger(log_type="script")


def get_script_log_path() -> str:
    """Get the path for script logging (for PowerShell script integration)"""
    script_logger = create_script_logger()
    return script_logger.get_log_file_path()