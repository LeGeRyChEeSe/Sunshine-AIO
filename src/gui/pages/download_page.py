"""
Download Page - Selective downloads without installation

This page provides selective download options with Sunshine theme and translations.
"""

import customtkinter as ctk
from .base_page import BasePage
from ..localization.translations import t, add_translation_observer


class DownloadPage(BasePage):
    """Download page for selective downloads without installation"""
    
    def __init__(self, parent, menu_adapter, status_bar, theme):
        self.theme = theme
        super().__init__(parent, menu_adapter, status_bar, theme)
        add_translation_observer(self.refresh_translations)
    
    def _create_widgets(self):
        """Create the download page widgets"""
        super()._create_widgets()
        
        # Create scrollable frame for content
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.frame,
            fg_color=self.theme.colors.bg_secondary if self.theme else None
        )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Page header
        self._create_header()
        
        # Rest of the content...
        self._create_remaining_content()
    
    def _create_header(self):
        """Create page header"""
        header_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 30))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Title with sunshine colors
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=t("downloads.title"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.theme.colors.sunshine_accent if self.theme else "white"
        )
        self.title_label.grid(row=0, column=0, pady=(0, 5))
        
        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            header_frame,
            text=t("downloads.subtitle"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme.colors.text_secondary if self.theme else "gray",
            wraplength=800
        )
        self.subtitle_label.grid(row=1, column=0, pady=(0, 20))
    
    def _create_remaining_content(self):
        
        # Download info section
        self._create_info_section()
        
        # Core Components Section
        self._create_core_components_section()
        
        # Additional Tools Section
        self._create_additional_tools_section()
        
        # Game Management Section
        self._create_game_management_section()
        
        # Download location info
        self._create_location_info()
    
    def _create_info_section(self):
        """Create information section"""
        info_frame = ctk.CTkFrame(self.scroll_frame, fg_color=("#E7F3FF", "#1A2332"))
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        
        info_header = ctk.CTkLabel(
            info_frame,
            text="ℹ️ Download Information",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#0D47A1", "#64B5F6")
        )
        info_header.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        
        info_text = ctk.CTkLabel(
            info_frame,
            text="• Files are downloaded to the 'tools' folder in the application directory\n"
                 "• No automatic installation or configuration is performed\n"
                 "• You can manually install or transfer files as needed\n"
                 "• Perfect for offline installations or custom setups",
            font=ctk.CTkFont(size=11),
            text_color=("#0D47A1", "#64B5F6"),
            justify="left",
            anchor="w"
        )
        info_text.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 15))
    
    def _create_core_components_section(self):
        """Create core components section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "🎮 Core Streaming Components",
            "Essential components for game streaming functionality"
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        # Core components
        core_components = [
            {
                "text": "Sunshine Server",
                "icon": "🌞",
                "action": lambda: self._execute_async(
                    self.menu_adapter.download_sunshine_only,
                    "Sunshine server downloaded successfully",
                    "Failed to download Sunshine"
                ),
                "desc": "Main streaming server application"
            },
            {
                "text": "Virtual Display Driver",
                "icon": "🖥️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.download_vdd_only,
                    "Virtual Display Driver downloaded",
                    "Failed to download VDD"
                ),
                "desc": "Dedicated virtual display for streaming"
            },
            {
                "text": "Sunshine Virtual Monitor",
                "icon": "⚙️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.download_svm_only,
                    "Sunshine Virtual Monitor downloaded",
                    "Failed to download SVM"
                ),
                "desc": "Smart display management scripts"
            }
        ]
        
        for i, component in enumerate(core_components):
            col = i % 2
            row = (i // 2) + 1
            
            # Component frame
            comp_frame = ctk.CTkFrame(section_frame)
            comp_frame.grid(row=row, column=col, sticky="ew", padx=10, pady=5)
            comp_frame.grid_columnconfigure(0, weight=1)
            
            # Component button
            btn = self._create_action_button(
                comp_frame,
                component["text"],
                component["action"],
                "",
                component["icon"],
                280,
                50
            )
            btn.grid(row=0, column=0, padx=15, pady=(15, 5))
            btn.configure(fg_color="#2B8C5B", hover_color="#238A52")
            
            # Description
            desc_label = ctk.CTkLabel(
                comp_frame,
                text=component["desc"],
                font=ctk.CTkFont(size=10),
                text_color="gray",
                wraplength=250
            )
            desc_label.grid(row=1, column=0, pady=(0, 15))
        
        # Add empty frame for odd number of components
        if len(core_components) % 2 == 1:
            empty_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            empty_frame.grid(row=(len(core_components) // 2) + 1, column=1, sticky="ew", padx=10, pady=5)
    
    def _create_additional_tools_section(self):
        """Create additional tools section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "🛠️ Additional Tools",
            "Utility tools that enhance the streaming experience"
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        # Additional tools
        additional_tools = [
            {
                "text": "Multi Monitor Tool",
                "icon": "🖼️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.download_mmt_only,
                    "Multi Monitor Tool downloaded",
                    "Failed to download MMT"
                ),
                "desc": "Monitor configuration utility"
            },
            {
                "text": "VSync Toggle",
                "icon": "🔄",
                "action": lambda: self._execute_async(
                    self.menu_adapter.download_vsync_toggle_only,
                    "VSync Toggle downloaded",
                    "Failed to download VSync Toggle"
                ),
                "desc": "Graphics synchronization control"
            }
        ]
        
        for i, tool in enumerate(additional_tools):
            # Tool frame
            tool_frame = ctk.CTkFrame(section_frame)
            tool_frame.grid(row=1, column=i, sticky="ew", padx=10, pady=5)
            tool_frame.grid_columnconfigure(0, weight=1)
            
            # Tool button
            btn = self._create_action_button(
                tool_frame,
                tool["text"],
                tool["action"],
                "",
                tool["icon"],
                280,
                50
            )
            btn.grid(row=0, column=0, padx=15, pady=(15, 5))
            btn.configure(fg_color="#7209b7", hover_color="#5c077a")
            
            # Description
            desc_label = ctk.CTkLabel(
                tool_frame,
                text=tool["desc"],
                font=ctk.CTkFont(size=10),
                text_color="gray",
                wraplength=250
            )
            desc_label.grid(row=1, column=0, pady=(0, 15))
    
    def _create_game_management_section(self):
        """Create game management section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=4, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "🎯 Game Management",
            "Tools for managing and launching games through streaming"
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        # Game management tools
        game_tools = [
            {
                "text": "Playnite Launcher",
                "icon": "🎯",
                "action": lambda: self._execute_async(
                    self.menu_adapter.download_playnite_only,
                    "Playnite launcher downloaded",
                    "Failed to download Playnite"
                ),
                "desc": "Universal game library manager"
            },
            {
                "text": "Playnite Watcher",
                "icon": "👁️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.download_playnite_watcher_only,
                    "Playnite Watcher downloaded",
                    "Failed to download Playnite Watcher"
                ),
                "desc": "Automatic game detection and streaming integration"
            }
        ]
        
        for i, tool in enumerate(game_tools):
            # Tool frame
            tool_frame = ctk.CTkFrame(section_frame)
            tool_frame.grid(row=1, column=i, sticky="ew", padx=10, pady=5)
            tool_frame.grid_columnconfigure(0, weight=1)
            
            # Tool button
            btn = self._create_action_button(
                tool_frame,
                tool["text"],
                tool["action"],
                "",
                tool["icon"],
                280,
                50
            )
            btn.grid(row=0, column=0, padx=15, pady=(15, 5))
            btn.configure(fg_color="#1f538d", hover_color="#1a4578")
            
            # Description
            desc_label = ctk.CTkLabel(
                tool_frame,
                text=tool["desc"],
                font=ctk.CTkFont(size=10),
                text_color="gray",
                wraplength=250
            )
            desc_label.grid(row=1, column=0, pady=(0, 15))
    
    def _create_location_info(self):
        """Create download location information"""
        location_frame = ctk.CTkFrame(self.scroll_frame, fg_color=("#FFF8E1", "#2D2A1A"))
        location_frame.grid(row=5, column=0, sticky="ew", pady=(0, 20))
        
        location_header = ctk.CTkLabel(
            location_frame,
            text="📁 Download Location",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#F57F17", "#FFD54F")
        )
        location_header.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        
        # Get application info for path display
        app_info = self.menu_adapter.get_app_info()
        tools_path = f"{app_info['base_path']}\\tools"
        
        location_text = ctk.CTkLabel(
            location_frame,
            text=f"All downloads are saved to: {tools_path}\n\n"
                 "Each component is downloaded to its own subfolder within the tools directory. "
                 "You can find the downloaded files there for manual installation or backup.",
            font=ctk.CTkFont(size=11),
            text_color=("#F57F17", "#FFD54F"),
            justify="left",
            anchor="w",
            wraplength=700
        )
        location_text.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 15))
        
        # Quick actions
        actions_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        actions_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 15))
        
        open_folder_btn = self._create_action_button(
            actions_frame,
            "Open Tools Folder",
            lambda: self._open_tools_folder(),
            "",
            "📂",
            150,
            35
        )
        open_folder_btn.grid(row=0, column=0, pady=5)
        open_folder_btn.configure(fg_color="#F57F17", hover_color="#E65100")
    
    def _open_tools_folder(self):
        """Open the tools folder in file explorer"""
        try:
            import subprocess
            import os
            
            app_info = self.menu_adapter.get_app_info()
            tools_path = os.path.join(app_info['base_path'], "tools")
            
            # Create tools folder if it doesn't exist
            os.makedirs(tools_path, exist_ok=True)
            
            # Open in file explorer
            subprocess.run(['explorer', tools_path])
            self.status_bar.show_temporary_message("Tools folder opened", 3, "success")
            
        except Exception as e:
            self.status_bar.show_temporary_message(f"Failed to open folder: {e}", 3, "error")
    
    def refresh_translations(self):
        """Refresh all translations when language changes"""
        if hasattr(self, 'title_label'):
            self.title_label.configure(text=t("downloads.title"))
            self.subtitle_label.configure(text=t("downloads.subtitle"))
    
    def _on_show(self):
        """Called when page is shown"""
        self.status_bar.set_status(t("downloads.title") + " - " + t("downloads.subtitle"))