"""
Main Page - Primary installation options

This page provides the main installation options equivalent to CLI Menu Page 0.
"""

import customtkinter as ctk
from .base_page import BasePage


class MainPage(BasePage):
    """Main page with primary installation options"""
    
    def _create_widgets(self):
        """Create the main page widgets"""
        super()._create_widgets()
        
        # Create scrollable frame for content
        self.scroll_frame = ctk.CTkScrollableFrame(self.frame)
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Page header
        header = self._create_section_header(
            self.scroll_frame,
            "🌞 Main Installation Menu",
            "Choose from complete installation options or install components individually. "
            "All installations include automatic configuration and setup."
        )
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # Complete Installation Section
        self._create_complete_section()
        
        # Individual Components Section
        self._create_individual_section()
        
        # Quick Access Section
        self._create_quick_access_section()
    
    def _create_complete_section(self):
        """Create complete installation section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "🚀 Complete Installation",
            "Install all components at once for the full gaming streaming experience"
        )
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        # Complete installation button
        complete_btn = self._create_action_button(
            section_frame,
            "Install Everything",
            lambda: self._execute_async(
                self.menu_adapter.install_everything,
                "All components installed successfully!",
                "Complete installation failed"
            ),
            "Installs Sunshine, VDD, SVM, Playnite, and Playnite Watcher",
            "🌟",
            400,
            60
        )
        complete_btn.grid(row=1, column=0, pady=(0, 20))
        complete_btn.configure(fg_color="#2B8C5B", hover_color="#238A52")
        
        # Features list
        features_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        features_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        features = [
            "✅ Sunshine streaming server with auto-configuration",
            "✅ Virtual Display Driver for dedicated streaming display",
            "✅ Sunshine Virtual Monitor with smart display management",
            "✅ Playnite universal game launcher",
            "✅ Playnite Watcher for automatic game detection"
        ]
        
        for i, feature in enumerate(features):
            feature_label = ctk.CTkLabel(
                features_frame,
                text=feature,
                font=ctk.CTkFont(size=12),
                anchor="w"
            )
            feature_label.grid(row=i, column=0, sticky="w", pady=2)
    
    def _create_individual_section(self):
        """Create individual components section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "🔧 Individual Components",
            "Install and configure components one by one for custom setups"
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        # Component buttons grid
        components = [
            {
                "text": "Sunshine Server",
                "icon": "🎮",
                "action": lambda: self._execute_async(
                    self.menu_adapter.install_sunshine,
                    "Sunshine installed and configured!",
                    "Sunshine installation failed"
                ),
                "desc": "Core streaming server"
            },
            {
                "text": "Virtual Display Driver",
                "icon": "🖥️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.install_vdd,
                    "Virtual Display Driver installed!",
                    "VDD installation failed"
                ),
                "desc": "Dedicated streaming display"
            },
            {
                "text": "Sunshine Virtual Monitor",
                "icon": "⚙️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.install_svm,
                    "Sunshine Virtual Monitor configured!",
                    "SVM installation failed"
                ),
                "desc": "Smart display management"
            },
            {
                "text": "Playnite Launcher",
                "icon": "🎯",
                "action": lambda: self._execute_async(
                    self.menu_adapter.install_playnite,
                    "Playnite installed successfully!",
                    "Playnite installation failed"
                ),
                "desc": "Universal game launcher"
            },
            {
                "text": "Playnite Watcher",
                "icon": "👁️",
                "action": lambda: self._execute_async(
                    self.menu_adapter.install_playnite_watcher,
                    "Playnite Watcher configured!",
                    "Playnite Watcher setup failed"
                ),
                "desc": "Auto game detection"
            }
        ]
        
        for i, component in enumerate(components):
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
                component["desc"],
                component["icon"],
                280,
                50
            )
            btn.grid(row=0, column=0, padx=15, pady=(15, 5))
            
            # Description
            desc_label = ctk.CTkLabel(
                comp_frame,
                text=component["desc"],
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            desc_label.grid(row=1, column=0, pady=(0, 15))
        
        # Add empty frame for odd number of components
        if len(components) % 2 == 1:
            empty_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            empty_frame.grid(row=(len(components) // 2) + 1, column=1, sticky="ew", padx=10, pady=5)
    
    def _create_quick_access_section(self):
        """Create quick access section"""
        section_frame = ctk.CTkFrame(self.scroll_frame)
        section_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        section_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Section header
        header = self._create_section_header(
            section_frame,
            "⚡ Quick Access",
            "Direct access to commonly used functions"
        )
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=20, pady=(20, 10))
        
        # Quick access buttons
        quick_actions = [
            {
                "text": "Extra Tools",
                "icon": "🛠️",
                "action": lambda: self._show_info_dialog("Navigation", "Use the sidebar to navigate to Extra Tools"),
                "color": "#1f538d"
            },
            {
                "text": "Downloads Only",
                "icon": "📥",
                "action": lambda: self._show_info_dialog("Navigation", "Use the sidebar to navigate to Downloads"),
                "color": "#7209b7"
            },
            {
                "text": "Uninstall Tools",
                "icon": "🗑️",
                "action": lambda: self._show_info_dialog("Navigation", "Use the sidebar to navigate to Uninstall"),
                "color": "#a02e2e"
            }
        ]
        
        for i, action in enumerate(quick_actions):
            btn = self._create_action_button(
                section_frame,
                action["text"],
                action["action"],
                "",
                action["icon"],
                200,
                45
            )
            btn.grid(row=1, column=i, padx=10, pady=(0, 20))
            btn.configure(fg_color=action["color"], hover_color=action["color"])
    
    def _on_show(self):
        """Called when page is shown"""
        self.status_bar.set_status("Main Menu - Select installation options")
        
        # Check admin privileges
        if self.menu_adapter.check_admin_privileges():
            self.status_bar.set_admin_status(True)
        else:
            self.status_bar.set_admin_status(False)
            self.status_bar.show_temporary_message(
                "⚠️ Admin privileges recommended for installations", 
                5, 
                "warning"
            )