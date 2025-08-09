"""
Extra Tools Page - Advanced configuration and tools

This page provides advanced tools and configuration options equivalent to CLI Menu Page 1.
"""

import customtkinter as ctk
from .base_page import BasePage


class ExtraPage(BasePage):
    """Extra tools page with advanced configuration options"""
    
    def _create_widgets(self):
        """Create the extra tools page widgets"""
        super()._create_widgets()
        
        # Create scrollable frame for content
        self.scroll_frame = ctk.CTkScrollableFrame(self.frame)
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Page header
        header = self._create_section_header(
            self.scroll_frame,
            "⚙️ Extra Tools & Configuration",
            "Advanced tools for power users and troubleshooting. "
            "Download without installation, configure existing installations, and access utility tools."
        )
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # Download Tools Section
        self._create_download_section()
        
        # Configuration Section
        self._create_configuration_section()
        
        # Access Tools Section
        self._create_access_section()
    
    def _create_download_section(self):
        """Create download tools section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "📥 Download Tools",
            "Download components without installing them for manual setup or backup"
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        # Download all button
        download_all_btn = self._create_action_button(
            section_frame,
            "Download Everything (No Install)",
            lambda: self._execute_async(
                self.menu_adapter.download_everything_no_install,
                "All components downloaded to tools folder",
                "Download operation failed"
            ),
            "Downloads all components to 'tools' folder without installing",
            "📦",
            500,
            50
        )
        download_all_btn.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        download_all_btn.configure(fg_color="#7209b7", hover_color="#5c077a")
        
        # Selective download button
        selective_btn = self._create_action_button(
            section_frame,
            "Selective Downloads",
            lambda: self._show_info_dialog("Navigation", "Use the 'Downloads' page from the sidebar for selective downloads"),
            "Choose specific components to download",
            "🎯",
            240,
            45
        )
        selective_btn.grid(row=2, column=0, padx=(0, 5), pady=(0, 20))
        
        # Info label
        info_label = ctk.CTkLabel(
            section_frame,
            text="💡 Downloaded files are saved in the 'tools' folder\nfor manual installation or backup purposes",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        info_label.grid(row=2, column=1, padx=(5, 0), pady=(0, 20))
    
    def _create_configuration_section(self):
        """Create configuration section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "🔧 Configuration & Setup",
            "Configure existing installations and install required system components"
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        # Configuration buttons
        config_actions = [
            {
                "text": "Configure Sunshine",
                "icon": "⚙️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.configure_sunshine,
                    "Sunshine configuration updated successfully",
                    "Sunshine configuration failed"
                ),
                "desc": "Update Sunshine settings and virtual monitor integration"
            },
            {
                "text": "Install Windows Display Manager",
                "icon": "🖥️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.install_windows_display_manager,
                    "Windows Display Manager PowerShell module installed",
                    "Windows Display Manager installation failed"
                ),
                "desc": "Required PowerShell module for display management"
            }
        ]
        
        for i, action in enumerate(config_actions):
            # Action frame
            action_frame = ctk.CTkFrame(section_frame)
            action_frame.grid(row=i+1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
            action_frame.grid_columnconfigure(0, weight=1)
            
            # Action button
            btn = self._create_action_button(
                action_frame,
                action["text"],
                action["action"],
                action["desc"],
                action["icon"],
                400,
                45
            )
            btn.grid(row=0, column=0, padx=15, pady=(15, 5))
            
            # Description
            desc_label = ctk.CTkLabel(
                action_frame,
                text=action["desc"],
                font=ctk.CTkFont(size=10),
                text_color="gray",
                wraplength=400
            )
            desc_label.grid(row=1, column=0, pady=(0, 15))
    
    def _create_access_section(self):
        """Create access tools section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "🚀 Quick Access Tools",
            "Direct access to installed applications and control panels"
        )
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=20, pady=(20, 10))
        
        # Access tools
        access_tools = [
            {
                "text": "Sunshine Settings",
                "icon": "🌞",
                "action": lambda: self._open_sunshine_settings(),
                "desc": "Web interface",
                "color": "#2B8C5B"
            },
            {
                "text": "Playnite",
                "icon": "🎯",
                "action": lambda: self._open_playnite(),
                "desc": "Game launcher",
                "color": "#1f538d"
            },
            {
                "text": "VDD Control",
                "icon": "🖥️",
                "action": lambda: self._open_vdd_control(),
                "desc": "Display driver",
                "color": "#7209b7"
            }
        ]
        
        for i, tool in enumerate(access_tools):
            # Tool frame
            tool_frame = ctk.CTkFrame(section_frame)
            tool_frame.grid(row=1, column=i, sticky="ew", padx=5, pady=(0, 20))
            tool_frame.grid_columnconfigure(0, weight=1)
            
            # Tool button
            btn = self._create_action_button(
                tool_frame,
                tool["text"],
                tool["action"],
                "",
                tool["icon"],
                180,
                50
            )
            btn.grid(row=0, column=0, padx=10, pady=(15, 5))
            btn.configure(fg_color=tool["color"], hover_color=tool["color"])
            
            # Description
            desc_label = ctk.CTkLabel(
                tool_frame,
                text=tool["desc"],
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            desc_label.grid(row=1, column=0, pady=(0, 15))
        
        # Warning section
        warning_frame = ctk.CTkFrame(self.scroll_frame, fg_color=("#FFF3CD", "#332D1A"))
        warning_frame.grid(row=4, column=0, sticky="ew", pady=(0, 20))
        
        warning_header = ctk.CTkLabel(
            warning_frame,
            text="⚠️ Important Notes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#856404", "#FFEAA7")
        )
        warning_header.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        
        warning_text = ctk.CTkLabel(
            warning_frame,
            text="• Some tools may require the corresponding software to be installed first\n"
                 "• VDD Control requires Virtual Display Driver to be installed\n"
                 "• Sunshine Settings requires Sunshine server to be running",
            font=ctk.CTkFont(size=11),
            text_color=("#856404", "#FFEAA7"),
            justify="left",
            anchor="w"
        )
        warning_text.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 15))
    
    def _open_sunshine_settings(self):
        """Open Sunshine settings"""
        success = self.menu_adapter.open_sunshine_settings()
        if success:
            self.status_bar.show_temporary_message("Sunshine settings opened in browser", 3, "success")
        else:
            self.status_bar.show_temporary_message("Failed to open Sunshine settings", 3, "error")
    
    def _open_playnite(self):
        """Open Playnite"""
        success = self.menu_adapter.open_playnite()
        if success:
            self.status_bar.show_temporary_message("Playnite launched", 3, "success")
        else:
            self.status_bar.show_temporary_message("Failed to launch Playnite", 3, "error")
    
    def _open_vdd_control(self):
        """Open VDD Control"""
        success = self.menu_adapter.open_vdd_control()
        if success:
            self.status_bar.show_temporary_message("VDD Control launched", 3, "success")
        else:
            self.status_bar.show_temporary_message("VDD Control not found - install VDD first", 3, "error")
    
    def _on_show(self):
        """Called when page is shown"""
        self.status_bar.set_status("Extra Tools - Advanced configuration and utilities")