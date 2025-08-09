"""
Uninstall Page - Component management and removal

This page provides uninstallation and component management equivalent to CLI Menu Page 3.
"""

import customtkinter as ctk
from .base_page import BasePage
import threading


class UninstallPage(BasePage):
    """Uninstall page for managing and removing components"""
    
    def __init__(self, parent, menu_adapter, status_bar):
        super().__init__(parent, menu_adapter, status_bar)
        self.installed_components = []
        self.refresh_needed = True
    
    def _create_widgets(self):
        """Create the uninstall page widgets"""
        super()._create_widgets()
        
        # Create scrollable frame for content
        self.scroll_frame = ctk.CTkScrollableFrame(self.frame)
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Page header
        header = self._create_section_header(
            self.scroll_frame,
            "🗑️ Component Management",
            "View installation status, generate reports, and remove installed components. "
            "Use this page to manage or completely remove Sunshine-AIO components."
        )
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # Control buttons section
        self._create_control_section()
        
        # Component list section
        self._create_component_list_section()
        
        # Danger zone
        self._create_danger_zone()
    
    def _create_control_section(self):
        """Create control buttons section"""
        control_frame = ctk.CTkFrame(self.scroll_frame)
        control_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        control_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Section header
        header = self._create_section_header(
            control_frame,
            "📊 Installation Overview",
            "Get detailed information about installed components and system status"
        )
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=20, pady=(20, 10))
        
        # Control buttons
        report_btn = self._create_action_button(
            control_frame,
            "View Report",
            lambda: self._show_uninstall_report(),
            "",
            "📋",
            180,
            50
        )
        report_btn.grid(row=1, column=0, padx=10, pady=(0, 20))
        report_btn.configure(fg_color="#1f538d", hover_color="#1a4578")
        
        refresh_btn = self._create_action_button(
            control_frame,
            "Refresh List",
            lambda: self._refresh_components(),
            "",
            "🔄",
            180,
            50
        )
        refresh_btn.grid(row=1, column=1, padx=10, pady=(0, 20))
        refresh_btn.configure(fg_color="#2B8C5B", hover_color="#238A52")
        
        # Status indicator
        self.status_indicator = ctk.CTkLabel(
            control_frame,
            text="🔍 Loading...",
            font=ctk.CTkFont(size=12),
            anchor="center"
        )
        self.status_indicator.grid(row=1, column=2, padx=10, pady=(0, 20))
    
    def _create_component_list_section(self):
        """Create component list section"""
        # This will be populated dynamically
        self.component_section = ctk.CTkFrame(self.scroll_frame)
        self.component_section.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        self.component_section.grid_columnconfigure(0, weight=1)
        
        # Placeholder content
        self._create_placeholder_content()
    
    def _create_placeholder_content(self):
        """Create placeholder content while loading"""
        placeholder_label = ctk.CTkLabel(
            self.component_section,
            text="🔍 Loading installed components...\nClick 'Refresh List' to scan for installations",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        placeholder_label.grid(row=0, column=0, padx=20, pady=40)
    
    def _create_danger_zone(self):
        """Create danger zone for complete removal"""
        danger_frame = ctk.CTkFrame(self.scroll_frame, fg_color=("#FFEBEE", "#2C1A1A"))
        danger_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        
        # Section header
        danger_header = ctk.CTkLabel(
            danger_frame,
            text="⚠️ Danger Zone",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#D32F2F", "#EF5350")
        )
        danger_header.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        
        danger_desc = ctk.CTkLabel(
            danger_frame,
            text="Complete removal of all Sunshine-AIO components. This action cannot be undone.",
            font=ctk.CTkFont(size=12),
            text_color=("#D32F2F", "#EF5350"),
            wraplength=600
        )
        danger_desc.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 15))
        
        # Uninstall all button
        uninstall_all_btn = self._create_action_button(
            danger_frame,
            "Uninstall ALL Components",
            lambda: self._confirm_uninstall_all(),
            "",
            "💀",
            300,
            50
        )
        uninstall_all_btn.grid(row=2, column=0, padx=20, pady=(0, 20))
        uninstall_all_btn.configure(fg_color="#D32F2F", hover_color="#B71C1C")
        
        # Warning text
        warning_text = ctk.CTkLabel(
            danger_frame,
            text="⚠️ This will remove ALL installed components, configurations, and associated files",
            font=ctk.CTkFont(size=10),
            text_color=("#D32F2F", "#EF5350")
        )
        warning_text.grid(row=3, column=0, padx=20, pady=(0, 15))
    
    def _show_uninstall_report(self):
        """Show detailed uninstall report in a popup window"""
        def get_report():
            try:
                report = self.menu_adapter.get_uninstall_report()
                self._display_report_window(report)
            except Exception as e:
                self.status_bar.show_temporary_message(f"Error generating report: {e}", 5, "error")
        
        # Run in background thread
        thread = threading.Thread(target=get_report, daemon=True)
        thread.start()
        self.status_bar.set_status("Generating installation report...")
    
    def _display_report_window(self, report_text: str):
        """Display report in a new window"""
        # Create report window
        report_window = ctk.CTkToplevel(self.frame)
        report_window.title("Installation Report - Sunshine-AIO")
        report_window.geometry("800x600")
        report_window.transient(self.frame.winfo_toplevel())
        
        # Make window modal
        report_window.grab_set()
        
        # Create text widget for report
        text_frame = ctk.CTkFrame(report_window)
        text_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        report_window.grid_rowconfigure(0, weight=1)
        report_window.grid_columnconfigure(0, weight=1)
        
        # Report content
        report_textbox = ctk.CTkTextbox(text_frame, wrap="word")
        report_textbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        report_textbox.insert("0.0", report_text)
        report_textbox.configure(state="disabled")  # Make read-only
        
        # Close button
        close_btn = ctk.CTkButton(
            text_frame,
            text="Close",
            command=report_window.destroy,
            width=100
        )
        close_btn.grid(row=1, column=0, pady=10)
        
        self.status_bar.set_status("Installation report displayed")
    
    def _refresh_components(self):
        """Refresh the list of installed components"""
        def refresh_worker():
            try:
                self.status_bar.set_status("Scanning for installed components...")
                self.installed_components = self.menu_adapter.get_installed_components()
                
                # Update UI on main thread
                self.frame.after(0, self._update_component_list)
                
            except Exception as e:
                self.frame.after(0, lambda: self.status_bar.show_temporary_message(
                    f"Error scanning components: {e}", 5, "error"
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
                text="✅ No Sunshine-AIO components currently installed\n\n"
                     "If you believe this is incorrect, try:\n"
                     "• Running the application as administrator\n"
                     "• Checking if components were installed manually\n"
                     "• Using the 'View Report' button for detailed information",
                font=ctk.CTkFont(size=12),
                text_color="gray",
                justify="center"
            )
            no_components_label.grid(row=0, column=0, padx=20, pady=40)
            
            self.status_indicator.configure(text="✅ No components found")
            self.status_bar.set_status("No installed components detected")
            return
        
        # Create header
        header = self._create_section_header(
            self.component_section,
            f"📦 Installed Components ({len(self.installed_components)})",
            "Select individual components to uninstall or view details"
        )
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        # Create component items
        for i, component in enumerate(self.installed_components):
            self._create_component_item(self.component_section, component, i + 1)
        
        # Update status
        self.status_indicator.configure(text=f"📦 {len(self.installed_components)} components")
        self.status_bar.set_status(f"Found {len(self.installed_components)} installed components")
    
    def _create_component_item(self, parent, component_name: str, row: int):
        """Create a component item widget"""
        item_frame = ctk.CTkFrame(parent)
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
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w")
        
        # Component status
        status_label = ctk.CTkLabel(
            info_frame,
            text="Status: Installed and tracked",
            font=ctk.CTkFont(size=11),
            text_color="green",
            anchor="w"
        )
        status_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        # Action buttons
        button_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, padx=15, pady=10)
        
        uninstall_btn = ctk.CTkButton(
            button_frame,
            text="🗑️ Uninstall",
            command=lambda comp=component_name: self._confirm_uninstall_component(comp),
            width=120,
            height=35,
            fg_color="#D32F2F",
            hover_color="#B71C1C"
        )
        uninstall_btn.grid(row=0, column=0, padx=5)
    
    def _confirm_uninstall_component(self, component_name: str):
        """Confirm and uninstall specific component"""
        if self._show_confirmation_dialog(
            "Confirm Uninstall",
            f"Are you sure you want to uninstall {component_name.replace('_', ' ').title()}?\n\n"
            f"This will remove all files, configurations, and registry entries associated with this component."
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
            "⚠️ DANGER - Confirm Complete Removal",
            "This will completely remove ALL Sunshine-AIO components including:\n\n"
            "• All installed software (Sunshine, VDD, Playnite, etc.)\n"
            "• All configurations and settings\n"
            "• All registry entries and system modifications\n"
            "• All downloaded files\n\n"
            "This action CANNOT be undone!\n\n"
            "Are you absolutely sure you want to proceed?"
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
        self.status_bar.hide_progress(f"{component_name} uninstalled successfully", "success")
        self._refresh_components()  # Refresh the list
    
    def _on_uninstall_failed(self, component_name: str):
        """Handle failed component uninstall"""
        self.status_bar.hide_progress(f"Failed to uninstall {component_name}", "error")
        self._show_error_dialog(
            "Uninstall Failed",
            f"Failed to uninstall {component_name}. Check the application logs for details."
        )
    
    def _on_uninstall_all_success(self):
        """Handle successful complete uninstall"""
        self.status_bar.hide_progress("All components uninstalled successfully", "success")
        self._refresh_components()  # Refresh the list
        self._show_info_dialog(
            "Uninstall Complete",
            "All Sunshine-AIO components have been successfully removed from your system."
        )
    
    def _on_uninstall_all_failed(self):
        """Handle failed complete uninstall"""
        self.status_bar.hide_progress("Complete uninstall failed", "error")
        self._show_error_dialog(
            "Uninstall Failed",
            "The complete uninstall operation failed. Some components may still be installed. "
            "Check the application logs for details and try uninstalling components individually."
        )
    
    def _on_show(self):
        """Called when page is shown"""
        self.status_bar.set_status("Component Management - View and remove installed components")
        
        # Auto-refresh components when page is shown
        if self.refresh_needed:
            self._refresh_components()
            self.refresh_needed = False