"""
Install Page - Modern installation with checkboxes and dynamic button

This page provides a modern installation interface with component selection
and a dynamic install button that changes based on selection.
"""

import customtkinter as ctk
from .base_page import BasePage
from ..localization.translations import t, add_translation_observer
import threading


class InstallPage(BasePage):
    """Installation page with checkbox selection and dynamic button"""
    
    def __init__(self, parent, menu_adapter, status_bar, theme):
        self.theme = theme
        self.component_checkboxes = {}
        self.component_vars = {}
        self.install_button = None
        self.components_info = [
            {
                "id": "sunshine",
                "name_key": "install.sunshine",
                "desc_key": "install.sunshine_desc",
                "icon": "🌞",
                "color": "core",
                "action": menu_adapter.install_sunshine
            },
            {
                "id": "vdd", 
                "name_key": "install.vdd",
                "desc_key": "install.vdd_desc",
                "icon": "🖥️",
                "color": "core",
                "action": menu_adapter.install_vdd
            },
            {
                "id": "svm",
                "name_key": "install.svm", 
                "desc_key": "install.svm_desc",
                "icon": "⚙️",
                "color": "tools",
                "action": menu_adapter.install_svm
            },
            {
                "id": "playnite",
                "name_key": "install.playnite",
                "desc_key": "install.playnite_desc", 
                "icon": "🎯",
                "color": "games",
                "action": menu_adapter.install_playnite
            },
            {
                "id": "playnite_watcher",
                "name_key": "install.playnite_watcher",
                "desc_key": "install.playnite_watcher_desc",
                "icon": "👁️", 
                "color": "games",
                "action": menu_adapter.install_playnite_watcher
            }
        ]
        
        super().__init__(parent, menu_adapter, status_bar, theme)
        add_translation_observer(self.refresh_translations)
    
    def _create_widgets(self):
        """Create the installation page widgets"""
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
        
        # Component selection section
        self._create_component_selection()
        
        # Installation features info
        self._create_features_info()
        
        # Dynamic install button
        self._create_install_button()
        
        # Initialize all checkboxes as checked
        self._select_all_components()
    
    def _create_header(self):
        """Create page header"""
        header_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 30))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Title with sunshine colors
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=t("install.title"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.theme.colors.sunshine_accent
        )
        self.title_label.grid(row=0, column=0, pady=(0, 5))
        
        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            header_frame,
            text=t("install.subtitle"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme.colors.text_secondary,
            wraplength=800
        )
        self.subtitle_label.grid(row=1, column=0, pady=(0, 20))
    
    def _create_component_selection(self):
        """Create component selection with checkboxes"""
        selection_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.theme.colors.bg_tertiary,
            border_width=2,
            border_color=self.theme.colors.sunshine_secondary
        )
        selection_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        selection_frame.grid_columnconfigure(0, weight=1)
        
        # Selection header
        selection_header = ctk.CTkFrame(selection_frame, fg_color="transparent")
        selection_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        selection_header.grid_columnconfigure(0, weight=1)
        selection_header.grid_columnconfigure(1, weight=0)
        
        self.selection_title = ctk.CTkLabel(
            selection_header,
            text=t("install.select_components"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.colors.sunshine_primary,
            anchor="w"
        )
        self.selection_title.grid(row=0, column=0, sticky="w")
        
        # Select All / Deselect All buttons
        self.select_all_btn = ctk.CTkButton(
            selection_header,
            text="✓ All",
            command=self._select_all_components,
            width=60,
            height=30,
            font=ctk.CTkFont(size=10),
            **self.theme.get_button_colors("secondary")
        )
        self.select_all_btn.grid(row=0, column=1, padx=(10, 5))
        
        self.deselect_all_btn = ctk.CTkButton(
            selection_header,
            text="✗ None", 
            command=self._deselect_all_components,
            width=60,
            height=30,
            font=ctk.CTkFont(size=10),
            **self.theme.get_button_colors("warning")
        )
        self.deselect_all_btn.grid(row=0, column=2)
        
        # Component checkboxes grid
        components_grid = ctk.CTkFrame(selection_frame, fg_color="transparent")
        components_grid.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        components_grid.grid_columnconfigure((0, 1), weight=1)
        
        for i, component in enumerate(self.components_info):
            row = i // 2
            col = i % 2
            
            self._create_component_checkbox(components_grid, component, row, col)
    
    def _create_component_checkbox(self, parent, component, row, col):
        """Create a component checkbox item"""
        # Component frame
        comp_frame = ctk.CTkFrame(
            parent,
            fg_color=self.theme.colors.bg_hover,
            corner_radius=8
        )
        comp_frame.grid(row=row, column=col, sticky="ew", padx=5, pady=5)
        comp_frame.grid_columnconfigure(1, weight=1)
        
        # Component variable
        var = ctk.BooleanVar(value=True)
        self.component_vars[component["id"]] = var
        var.trace_add("write", self._on_selection_changed)
        
        # Checkbox
        checkbox = ctk.CTkCheckBox(
            comp_frame,
            text="",
            variable=var,
            width=24,
            height=24,
            checkbox_width=20,
            checkbox_height=20,
            **{
                "fg_color": self.theme.colors.sunshine_primary,
                "hover_color": self.theme.colors.sunshine_secondary,
                "checkmark_color": self.theme.colors.text_primary
            }
        )
        checkbox.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="n")
        self.component_checkboxes[component["id"]] = checkbox
        
        # Component info
        info_frame = ctk.CTkFrame(comp_frame, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="ew", padx=(0, 15), pady=15)
        info_frame.grid_columnconfigure(0, weight=1)
        
        # Component name with icon
        name_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        name_frame.grid(row=0, column=0, sticky="ew")
        
        name_label = ctk.CTkLabel(
            name_frame,
            text=f"{component['icon']} {t(component['name_key'])}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme.colors.text_primary,
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w")
        
        # Component description
        desc_label = ctk.CTkLabel(
            info_frame,
            text=t(component["desc_key"]),
            font=ctk.CTkFont(size=11),
            text_color=self.theme.colors.text_secondary,
            anchor="w",
            wraplength=300
        )
        desc_label.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        # Store labels for translation updates
        setattr(self, f"{component['id']}_name_label", name_label)
        setattr(self, f"{component['id']}_desc_label", desc_label)
    
    def _create_features_info(self):
        """Create installation features information"""
        features_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=self.theme.colors.bg_tertiary
        )
        features_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        
        # Features header
        self.features_title = ctk.CTkLabel(
            features_frame,
            text=t("install.features_title"),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.colors.sunshine_secondary
        )
        self.features_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Features list
        features = [
            "install.feature_auto_config",
            "install.feature_admin_check", 
            "install.feature_progress",
            "install.feature_error_handling"
        ]
        
        for i, feature_key in enumerate(features):
            feature_label = ctk.CTkLabel(
                features_frame,
                text=f"✓ {t(feature_key)}",
                font=ctk.CTkFont(size=12),
                text_color=self.theme.colors.text_primary,
                anchor="w"
            )
            feature_label.grid(row=i+1, column=0, sticky="w", padx=30, pady=3)
        
        # Add padding at bottom
        ctk.CTkLabel(features_frame, text="").grid(row=len(features)+1, column=0, pady=10)
    
    def _create_install_button(self):
        """Create dynamic install button"""
        button_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", pady=(0, 30))
        button_frame.grid_columnconfigure(0, weight=1)
        
        self.install_button = ctk.CTkButton(
            button_frame,
            text=t("install.install_all", count=len(self.components_info)),
            command=self._on_install_clicked,
            height=60,
            font=ctk.CTkFont(size=16, weight="bold"),
            **self.theme.get_button_colors("install_all")
        )
        self.install_button.grid(row=0, column=0, padx=20)
        
        # Progress frame (hidden initially)
        self.progress_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.colors.text_secondary
        )
        self.progress_label.grid(row=0, column=0, pady=(0, 5))
        
        # Update button state initially
        self._update_install_button()
    
    def _select_all_components(self):
        """Select all components"""
        for var in self.component_vars.values():
            var.set(True)
    
    def _deselect_all_components(self):
        """Deselect all components"""
        for var in self.component_vars.values():
            var.set(False)
    
    def _on_selection_changed(self, *args):
        """Handle component selection change"""
        self._update_install_button()
    
    def _update_install_button(self):
        """Update install button based on selection"""
        if not hasattr(self, 'install_button') or not self.install_button:
            return
            
        selected_count = sum(1 for var in self.component_vars.values() if var.get())
        total_count = len(self.component_vars)
        
        if selected_count == 0:
            # No components selected - disable button
            self.install_button.configure(
                text=t("install.install_button_disabled"),
                state="disabled",
                **self.theme.get_button_colors("disabled")
            )
        elif selected_count == total_count:
            # All components selected - "Install All" button
            self.install_button.configure(
                text=t("install.install_all", count=total_count),
                state="normal",
                **self.theme.get_button_colors("install_all")
            )
        else:
            # Some components selected - "Install Selected" button
            self.install_button.configure(
                text=t("install.install_selected", count=selected_count),
                state="normal",
                **self.theme.get_button_colors("install_selected")
            )
    
    def _on_install_clicked(self):
        """Handle install button click"""
        selected_components = [
            comp for comp in self.components_info 
            if self.component_vars[comp["id"]].get()
        ]
        
        if not selected_components:
            return
        
        # Start installation in background thread
        def install_worker():
            success_count = 0
            total_count = len(selected_components)
            
            try:
                # Show progress
                self._show_progress()
                
                for i, component in enumerate(selected_components):
                    # Update progress
                    self._update_progress(
                        t("install.installing", component=t(component["name_key"])),
                        i / total_count
                    )
                    
                    try:
                        # Install component without console interaction
                        success = self._install_component_silently(component)
                        if success:
                            success_count += 1
                            self.status_bar.set_status(
                                t("install.install_success", component=t(component["name_key"])),
                                "success"
                            )
                        else:
                            self.status_bar.set_status(
                                t("install.install_error", component=t(component["name_key"])),
                                "error"
                            )
                    except Exception as e:
                        self.status_bar.set_status(
                            t("install.install_error", component=t(component["name_key"])),
                            "error"
                        )
                
                # Final status
                if success_count == total_count:
                    final_message = t("install.install_complete")
                    message_type = "success"
                else:
                    final_message = t("install.install_partial")
                    message_type = "warning"
                
                self._hide_progress(final_message, message_type)
                
            except Exception as e:
                self._hide_progress(f"Installation failed: {e}", "error")
        
        thread = threading.Thread(target=install_worker, daemon=True)
        thread.start()
    
    def _install_component_silently(self, component):
        """Install component without console interaction"""
        try:
            # Create a silent progress callback
            def progress_callback(message):
                self._update_progress(message, None)
            
            # Call the component's install action
            return component["action"](progress_callback)
        except Exception:
            return False
    
    def _show_progress(self):
        """Show installation progress"""
        self.install_button.grid_remove() 
        self.progress_frame.grid(row=0, column=0, padx=20)
        
        # Create progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=400,
            height=20,
            fg_color=self.theme.colors.bg_hover,
            progress_color=self.theme.colors.sunshine_primary
        )
        self.progress_bar.grid(row=1, column=0, pady=(0, 10))
        self.progress_bar.set(0)
    
    def _update_progress(self, message, progress):
        """Update installation progress"""
        if hasattr(self, 'progress_label'):
            self.progress_label.configure(text=message)
        if hasattr(self, 'progress_bar') and progress is not None:
            self.progress_bar.set(progress)
    
    def _hide_progress(self, message, message_type):
        """Hide progress and show final message"""
        if hasattr(self, 'progress_frame'):
            self.progress_frame.grid_remove()
        self.install_button.grid(row=0, column=0, padx=20)
        
        self.status_bar.set_status(message, message_type)
    
    def refresh_translations(self):
        """Refresh all translations when language changes"""
        if not hasattr(self, 'title_label'):
            return
        
        # Update headers
        self.title_label.configure(text=t("install.title"))
        self.subtitle_label.configure(text=t("install.subtitle"))
        self.selection_title.configure(text=t("install.select_components"))
        self.features_title.configure(text=t("install.features_title"))
        
        # Update component labels
        for component in self.components_info:
            name_label = getattr(self, f"{component['id']}_name_label", None)
            desc_label = getattr(self, f"{component['id']}_desc_label", None)
            
            if name_label:
                name_label.configure(text=f"{component['icon']} {t(component['name_key'])}")
            if desc_label:
                desc_label.configure(text=t(component["desc_key"]))
        
        # Update button
        self._update_install_button()
    
    def _on_show(self):
        """Called when page is shown"""
        self.status_bar.set_status(t("install.title") + " - " + t("install.subtitle"))
        
        # Check admin privileges
        if self.menu_adapter.check_admin_privileges():
            self.status_bar.set_admin_status(True)
        else:
            self.status_bar.set_admin_status(False)
            self.status_bar.show_temporary_message(
                t("app.admin_required"), 
                5, 
                "warning"
            )