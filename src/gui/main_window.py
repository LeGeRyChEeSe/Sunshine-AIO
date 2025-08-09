"""
Main GUI Window for Sunshine-AIO

This module provides the main window interface that replicates the functionality
of the original CLI menu system with a modern, user-friendly GUI with Sunshine theme.
"""

import customtkinter as ctk
import os
import sys
from typing import Optional

# Import business logic adapters
from .adapters.menu_adapter import MenuAdapter
from .pages.install_page import InstallPage
from .pages.configure_page import ConfigurePage  
from .pages.download_page import DownloadPage
from .pages.manage_page import ManagePage
from .components.status_bar import StatusBar
from .localization.translations import get_translation_manager, t, add_translation_observer, Language
from .theme.sunshine_theme import get_sunshine_theme, apply_sunshine_theme

# Apply Sunshine theme
apply_sunshine_theme()


class SunshineAIOMainWindow:
    """Main application window with Sunshine theme and translations"""
    
    def __init__(self):
        self.window = ctk.CTk() 
        self.menu_adapter: Optional[MenuAdapter] = None
        self.current_page = "install"
        self.theme = get_sunshine_theme()
        self.translation_manager = get_translation_manager()
        
        # Page instances
        self.pages = {}
        
        # Language selector
        self.language_selector = None
        
        self._setup_window()
        self._initialize_menu_adapter()
        self._setup_translation_observer()
        self._create_widgets()
        self._show_page("install")
    
    def _setup_window(self):
        """Configure the main window with Sunshine theme"""
        self.window.title(t("app.title"))
        self.window.geometry("1200x800")
        self.window.minsize(1000, 700)
        
        # Apply theme colors
        self.window.configure(fg_color=self.theme.colors.bg_primary)
        
        # Center window on screen
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Load and set icon if available
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "ressources", "sunshine-aio.ico")
            if os.path.exists(icon_path):
                self.window.iconbitmap(icon_path)
        except Exception:
            pass  # Continue without icon if not available
    
    def _setup_translation_observer(self):
        """Setup translation change observer"""
        add_translation_observer(self._on_language_changed)
    
    def _on_language_changed(self):
        """Handle language change"""
        self.window.title(t("app.title"))
        self._update_navigation_labels()
        self._update_current_page()
    
    def _initialize_menu_adapter(self):
        """Initialize the menu adapter for business logic"""
        try:
            base_path = os.path.join(os.path.dirname(__file__), "..")
            self.menu_adapter = MenuAdapter(base_path)
        except Exception as e:
            self._show_error(f"Failed to initialize application: {e}")
    
    def _create_widgets(self):
        """Create the main window widgets with Sunshine theme"""
        # Create main container with theme colors
        self.main_frame = ctk.CTkFrame(self.window, fg_color=self.theme.colors.bg_secondary)
        self.main_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        
        # Configure grid weights
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=0)  # Sidebar
        self.window.grid_columnconfigure(1, weight=1)  # Content
        
        # Create sidebar navigation
        self._create_sidebar()
        
        # Create content area
        self._create_content_area()
        
        # Create status bar
        self.status_bar = StatusBar(self.window, self.theme)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        
        # Initialize pages
        self._initialize_pages()
    
    def _create_sidebar(self):
        """Create the navigation sidebar with Sunshine theme"""
        self.sidebar = ctk.CTkFrame(
            self.main_frame, 
            width=280,
            fg_color=self.theme.colors.sidebar_bg
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.sidebar.grid_propagate(False)
        
        # App title and logo with sunshine colors
        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 20))
        
        self.title_label = ctk.CTkLabel(
            title_frame, 
            text="🌞 Sunshine-AIO",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.theme.colors.sunshine_accent
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.subtitle_label = ctk.CTkLabel(
            title_frame,
            text=t("app.subtitle"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme.colors.text_secondary
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(0, 5))
        
        # Language selector
        self._create_language_selector(title_frame)
        
        # Navigation buttons with new structure
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        nav_frame.grid_columnconfigure(0, weight=1)
        
        self.nav_buttons = {}
        self.nav_labels = {}
        nav_items = [
            ("install", "🚀", "navigation.install", "navigation.install_desc"),
            ("configure", "⚙️", "navigation.configure", "navigation.configure_desc"),
            ("downloads", "📥", "navigation.downloads", "navigation.downloads_desc"),
            ("manage", "🗑️", "navigation.manage", "navigation.manage_desc")
        ]
        
        for i, (page_id, icon, title_key, desc_key) in enumerate(nav_items):
            # Button container
            btn_container = ctk.CTkFrame(nav_frame, fg_color="transparent")
            btn_container.grid(row=i, column=0, sticky="ew", pady=5)
            btn_container.grid_columnconfigure(0, weight=1)
            
            # Navigation button
            btn = ctk.CTkButton(
                btn_container,
                text=f"{icon} {t(title_key)}",
                command=lambda p=page_id: self._show_page(p),
                height=55,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
                **self.theme.get_button_colors("primary")
            )
            btn.grid(row=0, column=0, sticky="ew")
            self.nav_buttons[page_id] = btn
            
            # Description label
            desc_label = ctk.CTkLabel(
                btn_container,
                text=t(desc_key),
                font=ctk.CTkFont(size=10),
                text_color=self.theme.colors.text_muted,
                anchor="w"
            )
            desc_label.grid(row=1, column=0, sticky="ew", padx=15, pady=(2, 0))
            self.nav_labels[f"{page_id}_desc"] = desc_label
        
        # Exit button at bottom with danger color
        self.exit_btn = ctk.CTkButton(
            self.sidebar,
            text=f"❌ {t('app.exit')}",
            command=self._on_exit,
            height=45,
            font=ctk.CTkFont(size=12, weight="bold"),
            **self.theme.get_button_colors("danger")
        )
        self.exit_btn.grid(row=2, column=0, sticky="ew", padx=10, pady=(20, 10))
    
    def _create_language_selector(self, parent):
        """Create language selector"""
        lang_frame = ctk.CTkFrame(parent, fg_color="transparent")
        lang_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        
        # Language label  
        lang_label = ctk.CTkLabel(
            lang_frame,
            text=t("settings.language"),
            font=ctk.CTkFont(size=10),
            text_color=self.theme.colors.text_muted
        )
        lang_label.grid(row=0, column=0, sticky="w")
        
        # Language dropdown
        languages = ["English", "Français"]
        language_values = [Language.ENGLISH, Language.FRENCH]
        
        # CTkOptionMenu has limited styling options
        self.language_selector = ctk.CTkOptionMenu(
            lang_frame,
            values=languages,
            command=self._on_language_selected,
            width=120,
            height=28,
            font=ctk.CTkFont(size=10),
            fg_color=self.theme.colors.sunshine_secondary,
            button_color=self.theme.colors.sunshine_primary,
            button_hover_color=self.theme.colors.sunshine_bright
        )
        self.language_selector.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        # Set current language
        current_lang = self.translation_manager.get_current_language()
        if current_lang == Language.FRENCH:
            self.language_selector.set("Français")
        else:
            self.language_selector.set("English")
    
    def _on_language_selected(self, choice):
        """Handle language selection"""
        if choice == "Français":
            self.translation_manager.set_language(Language.FRENCH)
        else:
            self.translation_manager.set_language(Language.ENGLISH)
    
    def _create_content_area(self):
        """Create the main content area"""
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Configure main frame grid
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=0)
        self.main_frame.grid_columnconfigure(1, weight=1)
    
    def _initialize_pages(self):
        """Initialize all page instances with new structure"""
        if not self.menu_adapter:
            return
            
        self.pages = {
            "install": InstallPage(self.content_frame, self.menu_adapter, self.status_bar, self.theme),
            "configure": ConfigurePage(self.content_frame, self.menu_adapter, self.status_bar, self.theme),
            "downloads": DownloadPage(self.content_frame, self.menu_adapter, self.status_bar, self.theme),
            "manage": ManagePage(self.content_frame, self.menu_adapter, self.status_bar, self.theme)
        }
    
    def _show_page(self, page_id: str):
        """Show the specified page with theme colors"""
        if page_id not in self.pages:
            return
        
        # Hide current page
        if self.current_page in self.pages:
            self.pages[self.current_page].hide()
        
        # Update navigation button states with theme colors
        for btn_id, btn in self.nav_buttons.items():
            if btn_id == page_id:
                btn.configure(fg_color=self.theme.colors.sidebar_active)
            else:
                btn.configure(**self.theme.get_button_colors("primary"))
        
        # Show new page
        self.pages[page_id].show()
        self.current_page = page_id
        
        # Update status bar with translated text
        page_status = {
            "install": t("install.title"),
            "configure": t("configure.title"),
            "downloads": t("downloads.title"),
            "manage": t("manage.title")
        }
        self.status_bar.set_status(f"{t('app.ready')} - {page_status.get(page_id, page_id)}")
    
    def _update_navigation_labels(self):
        """Update navigation labels when language changes"""
        nav_items = [
            ("install", "🚀", "navigation.install", "navigation.install_desc"),
            ("configure", "⚙️", "navigation.configure", "navigation.configure_desc"), 
            ("downloads", "📥", "navigation.downloads", "navigation.downloads_desc"),
            ("manage", "🗑️", "navigation.manage", "navigation.manage_desc")
        ]
        
        for page_id, icon, title_key, desc_key in nav_items:
            if page_id in self.nav_buttons:
                self.nav_buttons[page_id].configure(text=f"{icon} {t(title_key)}")
            if f"{page_id}_desc" in self.nav_labels:
                self.nav_labels[f"{page_id}_desc"].configure(text=t(desc_key))
        
        # Update other labels
        self.subtitle_label.configure(text=t("app.subtitle"))
        self.exit_btn.configure(text=f"❌ {t('app.exit')}")
    
    def _update_current_page(self):
        """Update current page when language changes"""
        if self.current_page in self.pages:
            self.pages[self.current_page].refresh_translations()
    
    def _show_error(self, message: str):
        """Show error dialog"""
        import tkinter.messagebox as msgbox
        msgbox.showerror("Error", message)
    
    def _on_exit(self):
        """Handle application exit"""
        self.window.quit()
        self.window.destroy()
    
    def run(self):
        """Start the GUI application"""
        self.window.mainloop()


def main():
    """Entry point for GUI application"""
    try:
        app = SunshineAIOMainWindow()
        app.run()
    except Exception as e:
        import tkinter.messagebox as msgbox
        msgbox.showerror("Critical Error", f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()