"""
Configure Page - Advanced configuration and tools

This page provides advanced configuration options and utility tools.
"""

import customtkinter as ctk
from .base_page import BasePage
from ..localization.translations import t, add_translation_observer


class ConfigurePage(BasePage):
    """Configuration page with advanced tools and settings"""
    
    def __init__(self, parent, menu_adapter, status_bar, theme):
        self.theme = theme
        super().__init__(parent, menu_adapter, status_bar, theme)
        add_translation_observer(self.refresh_translations)
    
    def _create_widgets(self):
        """Create the configuration page widgets"""
        super()._create_widgets()
        
        # Create scrollable frame for content
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.frame,
            fg_color=self.theme.colors.bg_secondary
        )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Page header
        self._create_header()
        
        # Configuration section
        self._create_configuration_section()
        
        # Access tools section
        self._create_access_section()
        
        # Notes section
        self._create_notes_section()
    
    def _create_header(self):
        """Create page header"""
        header_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 30))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Title with sunshine colors
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=t("configure.title"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.theme.colors.sunshine_accent
        )
        self.title_label.grid(row=0, column=0, pady=(0, 5))
        
        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            header_frame,
            text=t("configure.subtitle"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme.colors.text_secondary,
            wraplength=800
        )
        self.subtitle_label.grid(row=1, column=0, pady=(0, 20))
    
    def _create_configuration_section(self):
        """Create configuration tools section"""
        config_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.theme.colors.bg_tertiary,
            border_width=2,
            border_color=self.theme.colors.sunshine_secondary
        )
        config_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        config_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Section header
        config_header = ctk.CTkLabel(
            config_frame,
            text=t("configure.sunshine_config"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.colors.sunshine_primary
        )
        config_header.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        
        # Configuration actions
        config_actions = [
            {
                "title_key": "configure.sunshine_config",
                "desc_key": "configure.sunshine_config_desc",
                "icon": "⚙️",
                "action": self._configure_sunshine,
                "color": "primary"
            },
            {
                "title_key": "configure.display_manager",
                "desc_key": "configure.display_manager_desc",
                "icon": "🖥️",
                "action": self._install_display_manager,
                "color": "secondary"
            }
        ]
        
        for i, action in enumerate(config_actions):
            self._create_action_item(config_frame, action, i+1, i%2)
    
    def _create_access_section(self):
        """Create quick access tools section"""
        access_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.theme.colors.bg_tertiary,
            border_width=2,
            border_color=self.theme.colors.sunshine_secondary
        )
        access_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        access_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Section header
        self.access_title = ctk.CTkLabel(
            access_frame,
            text=t("configure.access_tools"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.colors.sunshine_primary
        )
        self.access_title.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 15), sticky="w")
        
        # Access tools
        access_tools = [
            {
                "title_key": "configure.sunshine_settings",
                "desc_key": "configure.sunshine_settings_desc",
                "icon": "🌞",
                "action": self._open_sunshine_settings,
                "color": self.theme.colors.sunshine_primary
            },
            {
                "title_key": "configure.playnite_app",
                "desc_key": "configure.playnite_app_desc",
                "icon": "🎯",
                "action": self._open_playnite,
                "color": self.theme.colors.sunshine_secondary
            },
            {
                "title_key": "configure.vdd_control",
                "desc_key": "configure.vdd_control_desc",
                "icon": "🖥️",
                "action": self._open_vdd_control,
                "color": self.theme.colors.sunshine_bright
            }
        ]
        
        for i, tool in enumerate(access_tools):
            self._create_access_tool(access_frame, tool, i)
    
    def _create_action_item(self, parent, action, row, col):
        """Create a configuration action item"""
        item_frame = ctk.CTkFrame(parent, fg_color=self.theme.colors.bg_hover)
        item_frame.grid(row=row, column=col, sticky="ew", padx=10, pady=5)
        item_frame.grid_columnconfigure(0, weight=1)
        
        # Action button
        action_btn = ctk.CTkButton(
            item_frame,
            text=f"{action['icon']} {t(action['title_key'])}",
            command=action["action"],
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            **self.theme.get_button_colors(action["color"])
        )
        action_btn.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        
        # Description
        desc_label = ctk.CTkLabel(
            item_frame,
            text=t(action["desc_key"]),
            font=ctk.CTkFont(size=10),
            text_color=self.theme.colors.text_muted,
            wraplength=250
        )
        desc_label.grid(row=1, column=0, padx=15, pady=(0, 15))
        
        # Store for translation updates
        setattr(self, f"action_btn_{action['title_key']}", action_btn)
        setattr(self, f"desc_label_{action['title_key']}", desc_label)
    
    def _create_access_tool(self, parent, tool, index):
        """Create an access tool button"""
        tool_frame = ctk.CTkFrame(parent, fg_color=self.theme.colors.bg_hover)
        tool_frame.grid(row=1, column=index, sticky="ew", padx=5, pady=(0, 20))
        tool_frame.grid_columnconfigure(0, weight=1)
        
        # Tool button
        tool_btn = ctk.CTkButton(
            tool_frame,
            text=f"{tool['icon']} {t(tool['title_key'])}",
            command=tool["action"],
            height=55,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=tool["color"],
            hover_color=tool["color"]
        )
        tool_btn.grid(row=0, column=0, padx=10, pady=(15, 5), sticky="ew")
        
        # Description
        desc_label = ctk.CTkLabel(
            tool_frame,
            text=t(tool["desc_key"]),
            font=ctk.CTkFont(size=9),
            text_color=self.theme.colors.text_muted
        )
        desc_label.grid(row=1, column=0, pady=(0, 15))
        
        # Store for translation updates
        setattr(self, f"tool_btn_{tool['title_key']}", tool_btn)
        setattr(self, f"tool_desc_{tool['title_key']}", desc_label)
    
    def _create_notes_section(self):
        """Create important notes section"""
        notes_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.theme.colors.warning,
            corner_radius=8
        )
        notes_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        
        # Notes header
        self.notes_title = ctk.CTkLabel(
            notes_frame,
            text=f"⚠️ {t('configure.notes_title')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme.colors.bg_primary
        )
        self.notes_title.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        
        # Notes content
        notes = [
            "configure.note_requirements",
            "configure.note_vdd",
            "configure.note_sunshine"
        ]
        
        self.note_labels = []
        for i, note_key in enumerate(notes):
            note_label = ctk.CTkLabel(
                notes_frame,
                text=f"• {t(note_key)}",
                font=ctk.CTkFont(size=11),
                text_color=self.theme.colors.bg_primary,
                anchor="w",
                wraplength=700
            )
            note_label.grid(row=i+1, column=0, sticky="ew", padx=30, pady=2)
            self.note_labels.append((note_key, note_label))
        
        # Add padding
        ctk.CTkLabel(notes_frame, text="", fg_color="transparent").grid(row=len(notes)+1, column=0, pady=10)
    
    def _configure_sunshine(self):
        """Configure Sunshine settings"""
        def config_worker():
            try:
                self.status_bar.show_progress(t("configure.sunshine_config"))
                success = self.menu_adapter.configure_sunshine()
                
                if success:
                    self.status_bar.hide_progress(t("configure.config_success"), "success")
                else:
                    self.status_bar.hide_progress(t("configure.config_error"), "error")
            except Exception as e:
                self.status_bar.hide_progress(f"{t('configure.config_error')}: {e}", "error")
        
        thread = threading.Thread(target=config_worker, daemon=True)
        thread.start()
    
    def _install_display_manager(self):
        """Install Windows Display Manager"""
        def install_worker():
            try:
                self.status_bar.show_progress(t("configure.display_manager"))
                success = self.menu_adapter.install_windows_display_manager()
                
                if success:
                    self.status_bar.hide_progress(t("configure.config_success"), "success")
                else:
                    self.status_bar.hide_progress(t("configure.config_error"), "error")
            except Exception as e:
                self.status_bar.hide_progress(f"{t('configure.config_error')}: {e}", "error")
        
        thread = threading.Thread(target=install_worker, daemon=True)
        thread.start()
    
    def _open_sunshine_settings(self):
        """Open Sunshine settings"""
        success = self.menu_adapter.open_sunshine_settings()
        if success:
            self.status_bar.show_temporary_message(
                t("configure.tool_launched", tool=t("configure.sunshine_settings")), 
                3, "success"
            )
        else:
            self.status_bar.show_temporary_message(
                t("configure.tool_error", tool=t("configure.sunshine_settings")), 
                3, "error"
            )
    
    def _open_playnite(self):
        """Open Playnite"""
        success = self.menu_adapter.open_playnite()
        if success:
            self.status_bar.show_temporary_message(
                t("configure.tool_launched", tool=t("configure.playnite_app")), 
                3, "success"
            )
        else:
            self.status_bar.show_temporary_message(
                t("configure.tool_error", tool=t("configure.playnite_app")), 
                3, "error"
            )
    
    def _open_vdd_control(self):
        """Open VDD Control"""
        success = self.menu_adapter.open_vdd_control()
        if success:
            self.status_bar.show_temporary_message(
                t("configure.tool_launched", tool=t("configure.vdd_control")), 
                3, "success"
            )
        else:
            self.status_bar.show_temporary_message(
                t("configure.tool_not_found", tool=t("configure.vdd_control")), 
                3, "error"
            )
    
    def refresh_translations(self):
        """Refresh all translations when language changes"""
        if not hasattr(self, 'title_label'):
            return
        
        # Update headers
        self.title_label.configure(text=t("configure.title"))
        self.subtitle_label.configure(text=t("configure.subtitle"))
        self.access_title.configure(text=t("configure.access_tools"))
        self.notes_title.configure(text=f"⚠️ {t('configure.notes_title')}")
        
        # Update notes
        for note_key, note_label in self.note_labels:
            note_label.configure(text=f"• {t(note_key)}")
    
    def _on_show(self):
        """Called when page is shown"""
        self.status_bar.set_status(t("configure.title") + " - " + t("configure.subtitle"))