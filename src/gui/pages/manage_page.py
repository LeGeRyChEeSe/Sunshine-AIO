"""
Manage Page - Component management and removal

This page provides component management and uninstallation with Sunshine theme.
"""

import customtkinter as ctk
from .base_page import BasePage
from ..localization.translations import t, add_translation_observer
import threading


class ManagePage(BasePage):
    """Management page for viewing and removing components"""
    
    def __init__(self, parent, menu_adapter, status_bar, theme):
        self.theme = theme
        self.installed_components = []
        self.refresh_needed = True
        super().__init__(parent, menu_adapter, status_bar, theme)
        add_translation_observer(self.refresh_translations)
    
    def _create_widgets(self):
        """Create the management page widgets"""
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
        
        # Control buttons section
        self._create_control_section()
        
        # Component list section
        self._create_component_list_section()
        
        # Danger zone
        self._create_danger_zone()
    
    def _create_header(self):
        """Create page header"""
        header_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 30))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Title with sunshine colors
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=t("manage.title"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.theme.colors.sunshine_accent
        )
        self.title_label.grid(row=0, column=0, pady=(0, 5))
        
        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            header_frame,
            text=t("manage.subtitle"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme.colors.text_secondary,
            wraplength=800
        )
        self.subtitle_label.grid(row=1, column=0, pady=(0, 20))
    
    def _create_control_section(self):
        """Create control buttons section"""
        control_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.theme.colors.bg_tertiary,
            border_width=2,
            border_color=self.theme.colors.sunshine_secondary
        )
        control_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        control_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Section header
        self.overview_title = ctk.CTkLabel(
            control_frame,
            text=t("manage.overview"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.colors.sunshine_primary
        )
        self.overview_title.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 5), sticky="w")
        
        self.overview_desc = ctk.CTkLabel(
            control_frame,
            text=t("manage.overview_desc"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme.colors.text_secondary,
            wraplength=600
        )
        self.overview_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 15), sticky="w")
        
        # Control buttons
        self.report_btn = ctk.CTkButton(
            control_frame,
            text=f"📋 {t('manage.view_report')}",
            command=self._show_uninstall_report,
            height=50,
            font=ctk.CTkFont(size=12, weight="bold"),
            **self.theme.get_button_colors("primary")
        )
        self.report_btn.grid(row=2, column=0, padx=10, pady=(0, 20))
        
        self.refresh_btn = ctk.CTkButton(
            control_frame,
            text=f"🔄 {t('manage.refresh_list')}",
            command=self._refresh_components,
            height=50,
            font=ctk.CTkFont(size=12, weight="bold"),
            **self.theme.get_button_colors("secondary")
        )
        self.refresh_btn.grid(row=2, column=1, padx=10, pady=(0, 20))
        
        # Status indicator
        self.status_indicator = ctk.CTkLabel(
            control_frame,
            text=f"🔍 {t('manage.loading')}",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.colors.text_muted,
            anchor="center"
        )
        self.status_indicator.grid(row=2, column=2, padx=10, pady=(0, 20))
    
    def _create_component_list_section(self):
        """Create component list section"""
        # This will be populated dynamically
        self.component_section = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.theme.colors.bg_tertiary
        )
        self.component_section.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        self.component_section.grid_columnconfigure(0, weight=1)
        
        # Placeholder content
        self._create_placeholder_content()
    
    def _create_placeholder_content(self):
        """Create placeholder content while loading"""
        self.placeholder_label = ctk.CTkLabel(
            self.component_section,
            text=f"🔍 {t('manage.loading')}...\\n{t('manage.refresh_list')}",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.colors.text_muted
        )
        self.placeholder_label.grid(row=0, column=0, padx=20, pady=40)
    
    def _create_danger_zone(self):
        """Create danger zone for complete removal"""
        danger_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.theme.colors.error,
            corner_radius=8
        )
        danger_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        
        # Section header
        self.danger_title = ctk.CTkLabel(
            danger_frame,
            text=f"⚠️ {t('manage.danger_zone')}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.colors.text_primary
        )
        self.danger_title.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        
        self.danger_desc = ctk.CTkLabel(
            danger_frame,
            text=t("manage.danger_desc"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme.colors.text_primary,
            wraplength=600
        )
        self.danger_desc.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 15))
        
        # Uninstall all button
        self.uninstall_all_btn = ctk.CTkButton(
            danger_frame,
            text=f"💀 {t('manage.uninstall_all')}",
            command=self._confirm_uninstall_all,
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.theme.colors.bg_primary,
            hover_color=self.theme.colors.bg_hover,
            text_color=self.theme.colors.error
        )
        self.uninstall_all_btn.grid(row=2, column=0, padx=20, pady=(0, 15))
        
        # Warning text
        self.warning_label = ctk.CTkLabel(
            danger_frame,
            text=f"⚠️ {t('manage.uninstall_all_warning')}",
            font=ctk.CTkFont(size=10),
            text_color=self.theme.colors.text_primary
        )
        self.warning_label.grid(row=3, column=0, padx=20, pady=(0, 15))
    
    def _show_uninstall_report(self):
        """Show detailed uninstall report in a popup window"""
        def get_report():
            try:
                self.status_bar.set_status(t("manage.report_displayed"))
                report = self.menu_adapter.get_uninstall_report()
                self._display_report_window(report)
            except Exception as e:
                self.status_bar.show_temporary_message(
                    t("manage.report_error", error=str(e)), 
                    5, "error"
                )
        
        # Run in background thread
        thread = threading.Thread(target=get_report, daemon=True)
        thread.start()
    
    def _display_report_window(self, report_text: str):
        """Display report in a new window"""
        # Create report window
        report_window = ctk.CTkToplevel(self.frame)
        report_window.title(t("manage.report_title"))
        report_window.geometry("800x600")
        report_window.transient(self.frame.winfo_toplevel())
        
        # Apply theme
        report_window.configure(fg_color=self.theme.colors.bg_primary)
        
        # Make window modal
        report_window.grab_set()
        
        # Create text widget for report
        text_frame = ctk.CTkFrame(
            report_window,
            fg_color=self.theme.colors.bg_secondary
        )
        text_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        report_window.grid_rowconfigure(0, weight=1)
        report_window.grid_columnconfigure(0, weight=1)
        
        # Report content
        report_textbox = ctk.CTkTextbox(
            text_frame, 
            wrap="word",
            fg_color=self.theme.colors.bg_tertiary,
            text_color=self.theme.colors.text_primary
        )
        report_textbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        report_textbox.insert("0.0", report_text)
        report_textbox.configure(state="disabled")  # Make read-only
        
        # Close button
        close_btn = ctk.CTkButton(
            text_frame,
            text=t("manage.close"),
            command=report_window.destroy,
            width=100,
            **self.theme.get_button_colors("primary")
        )
        close_btn.grid(row=1, column=0, pady=10)
    
    def _refresh_components(self):
        """Refresh the list of installed components"""
        def refresh_worker():
            try:
                self.status_bar.set_status(t("manage.scanning"))
                self.installed_components = self.menu_adapter.get_installed_components()
                
                # Update UI on main thread
                self.frame.after(0, self._update_component_list)
                
            except Exception as e:
                self.frame.after(0, lambda: self.status_bar.show_temporary_message(
                    t("manage.report_error", error=str(e)), 5, "error"
                ))
        
        thread = threading.Thread(target=refresh_worker, daemon=True)
        thread.start()
    
    def _update_component_list(self):
        """Update the component list UI"""
        # Clear existing content
        for widget in self.component_section.winfo_children():
            widget.destroy()
        
        if not self.installed_components:
            # No components found
            no_components_label = ctk.CTkLabel(
                self.component_section,
                text=f"✅ {t('manage.no_components')}\\n\\n{t('manage.no_components_help')}",
                font=ctk.CTkFont(size=12),
                text_color=self.theme.colors.text_muted,
                justify="center"
            )
            no_components_label.grid(row=0, column=0, padx=20, pady=40)
            
            self.status_indicator.configure(text=f"✅ {t('manage.no_components')}")
            self.status_bar.set_status(t("manage.no_components"))
            return
        
        # Create header
        header_label = ctk.CTkLabel(
            self.component_section,
            text=t("manage.installed_components", count=len(self.installed_components)),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.colors.sunshine_primary
        )
        header_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Create component items
        for i, component in enumerate(self.installed_components):
            self._create_component_item(self.component_section, component, i + 1)
        
        # Update status
        self.status_indicator.configure(
            text=t("manage.components_found", count=len(self.installed_components))
        )
        self.status_bar.set_status(
            t("manage.components_found", count=len(self.installed_components))
        )
    
    def _create_component_item(self, parent, component_name: str, row: int):
        """Create a component item widget"""
        item_frame = ctk.CTkFrame(
            parent,
            fg_color=self.theme.colors.bg_hover
        )
        item_frame.grid(row=row, column=0, sticky="ew", padx=20, pady=5)
        item_frame.grid_columnconfigure(0, weight=1)
        
        # Component info
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        info_frame.grid_columnconfigure(0, weight=1)
        
        # Component name
        name_label = ctk.CTkLabel(
            info_frame,
            text=f"📦 {component_name.title().replace('_', ' ')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme.colors.text_primary,
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w")
        
        # Component status
        status_label = ctk.CTkLabel(
            info_frame,
            text=t("manage.component_status"),
            font=ctk.CTkFont(size=11),
            text_color=self.theme.colors.success,
            anchor="w"
        )
        status_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        # Action buttons
        button_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, padx=15, pady=10)
        
        uninstall_btn = ctk.CTkButton(
            button_frame,
            text=f"🗑️ {t('manage.uninstall')}",
            command=lambda comp=component_name: self._confirm_uninstall_component(comp),
            width=120,
            height=35,
            font=ctk.CTkFont(size=11, weight="bold"),
            **self.theme.get_button_colors("danger")
        )
        uninstall_btn.grid(row=0, column=0, padx=5)
    
    def _confirm_uninstall_component(self, component_name: str):
        """Confirm and uninstall specific component"""
        if self._show_confirmation_dialog(
            t("dialogs.confirm"),
            t("manage.uninstall_confirm", component=component_name.replace('_', ' ').title())
        ):
            self._uninstall_component(component_name)
    
    def _uninstall_component(self, component_name: str):
        """Uninstall specific component"""
        def uninstall_worker():
            success = self.menu_adapter.uninstall_component(component_name)
            
            # Update UI on main thread
            if success:
                self.frame.after(0, lambda: self._on_uninstall_success(component_name))
            else:
                self.frame.after(0, lambda: self._on_uninstall_failed(component_name))
        
        self.status_bar.show_progress(f"Uninstalling {component_name}...")
        thread = threading.Thread(target=uninstall_worker, daemon=True)
        thread.start()
    
    def _confirm_uninstall_all(self):
        """Confirm complete uninstallation"""
        if self._show_confirmation_dialog(
            "⚠️ DANGER",
            t("manage.uninstall_all_confirm")
        ):
            self._uninstall_all_components()
    
    def _uninstall_all_components(self):
        """Uninstall all components"""
        def uninstall_all_worker():
            success = self.menu_adapter.uninstall_all_components()
            
            # Update UI on main thread
            if success:
                self.frame.after(0, self._on_uninstall_all_success)
            else:
                self.frame.after(0, self._on_uninstall_all_failed)
        
        self.status_bar.show_progress("Uninstalling all components...")
        thread = threading.Thread(target=uninstall_all_worker, daemon=True)
        thread.start()
    
    def _on_uninstall_success(self, component_name: str):
        """Handle successful component uninstall"""
        self.status_bar.hide_progress(
            t("manage.uninstall_success", component=component_name), 
            "success"
        )
        self._refresh_components()  # Refresh the list
    
    def _on_uninstall_failed(self, component_name: str):
        """Handle failed component uninstall"""
        self.status_bar.hide_progress(
            t("manage.uninstall_error", component=component_name), 
            "error"
        )
    
    def _on_uninstall_all_success(self):
        """Handle successful complete uninstall"""
        self.status_bar.hide_progress(t("manage.uninstall_all_success"), "success")
        self._refresh_components()  # Refresh the list
        self._show_info_dialog(
            t("dialogs.info_title"),
            t("manage.uninstall_all_success")
        )
    
    def _on_uninstall_all_failed(self):
        """Handle failed complete uninstall"""
        self.status_bar.hide_progress(t("manage.uninstall_all_error"), "error")
    
    def refresh_translations(self):
        """Refresh all translations when language changes"""
        if not hasattr(self, 'title_label'):
            return
        
        # Update headers
        self.title_label.configure(text=t("manage.title"))
        self.subtitle_label.configure(text=t("manage.subtitle"))
        self.overview_title.configure(text=t("manage.overview"))
        self.overview_desc.configure(text=t("manage.overview_desc"))
        self.danger_title.configure(text=f"⚠️ {t('manage.danger_zone')}")
        self.danger_desc.configure(text=t("manage.danger_desc"))
        self.warning_label.configure(text=f"⚠️ {t('manage.uninstall_all_warning')}")
        
        # Update buttons
        self.report_btn.configure(text=f"📋 {t('manage.view_report')}")
        self.refresh_btn.configure(text=f"🔄 {t('manage.refresh_list')}")
        self.uninstall_all_btn.configure(text=f"💀 {t('manage.uninstall_all')}")
    
    def _on_show(self):
        """Called when page is shown"""
        self.status_bar.set_status(t("manage.title") + " - " + t("manage.subtitle"))
        
        # Auto-refresh components when page is shown
        if self.refresh_needed:
            self._refresh_components()
            self.refresh_needed = False