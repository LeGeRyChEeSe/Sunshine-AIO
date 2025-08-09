"""
Base Page Class

Provides common functionality for all GUI pages with Sunshine theme support.
"""

import customtkinter as ctk
from typing import Optional, Callable
from ..adapters.menu_adapter import MenuAdapter
from ..components.status_bar import StatusBar
import threading


class BasePage:
    """Base class for all GUI pages with theme support"""
    
    def __init__(self, parent: ctk.CTkFrame, menu_adapter: MenuAdapter, status_bar: StatusBar, theme=None):
        self.parent = parent
        self.menu_adapter = menu_adapter
        self.status_bar = status_bar
        self.theme = theme
        self.frame: Optional[ctk.CTkFrame] = None
        self._is_visible = False
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create page widgets - to be implemented by subclasses"""
        self.frame = ctk.CTkFrame(self.parent)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
    
    def show(self):
        """Show this page"""
        if self.frame:
            self.frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            self._is_visible = True
            self._on_show()
    
    def hide(self):
        """Hide this page"""
        if self.frame:
            self.frame.grid_remove()
            self._is_visible = False
            self._on_hide()
    
    def _on_show(self):
        """Called when page is shown - can be overridden by subclasses"""
        pass
    
    def _on_hide(self):
        """Called when page is hidden - can be overridden by subclasses"""
        pass
    
    def refresh_translations(self):
        """Refresh translations - can be overridden by subclasses"""
        pass
    
    def _execute_async(self, action: Callable, success_message: str = "Operation completed", 
                      error_message: str = "Operation failed"):
        """Execute an action asynchronously with progress indication"""
        def progress_callback(message: str):
            self.status_bar.set_status(message)
        
        def worker():
            try:
                self.status_bar.show_progress("Processing...")
                result = action(progress_callback)
                
                if result:
                    self.status_bar.hide_progress(success_message, "success")
                else:
                    self.status_bar.hide_progress(error_message, "error")
                    
            except Exception as e:
                self.status_bar.hide_progress(f"Error: {e}", "error")
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def _create_action_button(self, parent, text: str, command: Callable,
                            description: str = "", icon: str = "", width: int = 200, height: int = 50) -> ctk.CTkButton:
        """Create a styled action button"""
        display_text = f"{icon} {text}" if icon else text
        
        button = ctk.CTkButton(
            parent,
            text=display_text,
            command=command,
            width=width,
            height=height,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8
        )
        
        return button
    
    def _create_section_header(self, parent, title: str, description: str = "") -> ctk.CTkFrame:
        """Create a section header with title and description"""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        
        title_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w"
        )
        title_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
        
        if description:
            desc_label = ctk.CTkLabel(
                header_frame,
                text=description,
                font=ctk.CTkFont(size=12),
                text_color="gray",
                anchor="w",
                wraplength=600
            )
            desc_label.grid(row=1, column=0, sticky="w", padx=5, pady=(0, 10))
        
        return header_frame
    
    def _show_confirmation_dialog(self, title: str, message: str) -> bool:
        """Show confirmation dialog and return user choice"""
        import tkinter.messagebox as msgbox
        return msgbox.askyesno(title, message)
    
    def _show_info_dialog(self, title: str, message: str):
        """Show information dialog"""
        import tkinter.messagebox as msgbox
        msgbox.showinfo(title, message)
    
    def _show_error_dialog(self, title: str, message: str):
        """Show error dialog"""
        import tkinter.messagebox as msgbox
        msgbox.showerror(title, message)