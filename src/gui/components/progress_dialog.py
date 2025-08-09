"""
Progress Dialog Component

A modal progress dialog for long-running operations.
"""

import customtkinter as ctk
import threading
from typing import Callable, Optional


class ProgressDialog:
    """Modal progress dialog for operations"""
    
    def __init__(self, parent, title: str = "Processing", message: str = "Please wait..."):
        self.parent = parent
        self.dialog = None
        self.progress_bar = None
        self.message_label = None
        self.is_cancelled = False
        
        self._create_dialog(title, message)
    
    def _create_dialog(self, title: str, message: str):
        """Create the progress dialog"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # Content frame
        content_frame = ctk.CTkFrame(self.dialog)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Message label
        self.message_label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=ctk.CTkFont(size=14)
        )
        self.message_label.pack(pady=(10, 20))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(content_frame, width=300)
        self.progress_bar.pack(pady=(0, 20))
        self.progress_bar.set(0)
        
        # Cancel button (optional)
        self.cancel_button = ctk.CTkButton(
            content_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100
        )
        self.cancel_button.pack()
    
    def _on_cancel(self):
        """Handle cancel button click"""
        self.is_cancelled = True
        self.close()
    
    def update_message(self, message: str):
        """Update the progress message"""
        if self.message_label:
            self.message_label.configure(text=message)
            self.dialog.update()
    
    def update_progress(self, value: float):
        """Update progress value (0.0 to 1.0)"""
        if self.progress_bar:
            self.progress_bar.set(value)
            self.dialog.update()
    
    def close(self):
        """Close the dialog"""
        if self.dialog:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None
    
    def show(self):
        """Show the dialog"""
        if self.dialog:
            self.dialog.deiconify()
    
    def hide(self):
        """Hide the dialog"""
        if self.dialog:
            self.dialog.withdraw()