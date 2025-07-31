import os
import datetime
import traceback
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
    
    def __init__(self, enable_colors: bool = True, log_file: Optional[str] = None):
        self.enable_colors = enable_colors and self._supports_color()
        
        # Auto-generate log file name if not provided
        if log_file is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("logs", exist_ok=True)
            self.log_file = f"logs/sunshine_aio_{timestamp}.log"
        else:
            self.log_file = log_file
        
        # Initialize log file with session header
        self._initialize_log_file()
        
    def _supports_color(self) -> bool:
        """Check if the terminal supports ANSI color codes"""
        return (
            hasattr(os, 'isatty') and os.isatty(1) or 
            os.environ.get('TERM') in ('xterm', 'xterm-color', 'xterm-256color') or
            os.environ.get('COLORTERM') in ('truecolor', '24bit') or
            'ANSICON' in os.environ
        )
    
    def _initialize_log_file(self):
        """Initialize log file with session header"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"SUNSHINE-AIO EXECUTION LOG\n")
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
    
    def separator(self, char: str = "-", width: int = 50):
        """Print a separator line"""
        if self.enable_colors:
            print(f"\033[90m{char * width}{LogLevel.RESET.value}")
        else:
            print(char * width)
    
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


# Global logger instance
logger = Logger()


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