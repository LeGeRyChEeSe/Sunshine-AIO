"""
Status Bar Component

Provides application status and progress information to the user with Sunshine theme.
"""

import customtkinter as ctk
from typing import Optional
import threading
import time


class StatusBar(ctk.CTkFrame):
    """Status bar widget for showing application status and progress"""
    
    def __init__(self, parent, theme=None):
        self.theme = theme
        
        # Apply theme colors if available
        if theme:
            super().__init__(
                parent, 
                height=35,
                fg_color=theme.colors.bg_tertiary,
                border_width=1,
                border_color=theme.colors.border_muted
            )
        else:
            super().__init__(parent, height=35)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        
        # Status label with theme colors
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=theme.colors.text_primary if theme else "white"
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=5)
        
        # Progress bar (hidden by default) with theme colors
        if theme:
            self.progress_bar = ctk.CTkProgressBar(
                self, 
                width=200,
                fg_color=theme.colors.bg_hover,
                progress_color=theme.colors.sunshine_primary
            )
        else:
            self.progress_bar = ctk.CTkProgressBar(self, width=200)
        self.progress_bar.grid(row=0, column=1, padx=5, pady=5)
        self.progress_bar.grid_remove()  # Hide initially
        
        # Admin status indicator with theme colors
        self.admin_label = ctk.CTkLabel(
            self,
            text="👑 Admin",
            font=ctk.CTkFont(size=10),
            text_color=theme.colors.sunshine_accent if theme else "gold",
            width=80
        )
        self.admin_label.grid(row=0, column=2, padx=(5, 10), pady=5)
    
    def set_status(self, message: str, message_type: str = "info"):
        """Set status message with optional type for color coding"""
        if self.theme:
            colors = {
                "info": self.theme.colors.text_primary,
                "success": self.theme.colors.success,
                "warning": self.theme.colors.warning,
                "error": self.theme.colors.error,
                "sunshine": self.theme.colors.sunshine_accent
            }
        else:
            colors = {
                "info": "white",
                "success": "green", 
                "warning": "orange",
                "error": "red",
                "sunshine": "gold"
            }
        
        color = colors.get(message_type, colors["info"])
        self.status_label.configure(text=message, text_color=color)
    
    def show_progress(self, message: str = "Processing..."):
        """Show progress bar with message"""
        self.set_status(message)
        self.progress_bar.grid()
        self.progress_bar.set(0)
    
    def update_progress(self, value: float, message: str = None):
        """Update progress bar value (0.0 to 1.0)"""
        self.progress_bar.set(value)
        if message:
            self.set_status(message)
    
    def hide_progress(self, final_message: str = "Ready", message_type: str = "info"):
        """Hide progress bar and set final message"""
        self.progress_bar.grid_remove()
        self.set_status(final_message, message_type)
    
    def set_admin_status(self, is_admin: bool):
        """Update admin status indicator"""
        if is_admin:
            self.admin_label.configure(text="👑 Admin", text_color="gold")
        else:
            self.admin_label.configure(text="⚠️ User", text_color="orange")
    
    def show_temporary_message(self, message: str, duration: int = 3, message_type: str = "info"):
        """Show a temporary message that disappears after specified duration"""
        self.set_status(message, message_type)
        
        def reset_status():
            time.sleep(duration)
            self.set_status("Ready")
        
        thread = threading.Thread(target=reset_status, daemon=True)
        thread.start()