"""
Sunshine Theme for Sunshine-AIO GUI

Provides warm, vibrant colors inspired by sunshine and solar themes.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ColorPalette:
    """Color palette for the Sunshine theme"""
    
    # Primary sunshine colors
    sunshine_primary: str = "#FF8C00"      # Dark Orange
    sunshine_secondary: str = "#FFB347"    # Light Orange  
    sunshine_accent: str = "#FFD700"       # Gold
    sunshine_bright: str = "#FFA500"       # Orange
    sunshine_warm: str = "#FF6347"         # Tomato
    
    # Background colors
    bg_primary: str = "#1A1A1A"           # Dark background
    bg_secondary: str = "#2D2D2D"         # Lighter dark
    bg_tertiary: str = "#3D3D3D"          # Card backgrounds
    bg_hover: str = "#4D4D4D"             # Hover states
    
    # Text colors
    text_primary: str = "#FFFFFF"         # White text
    text_secondary: str = "#E0E0E0"       # Light gray
    text_muted: str = "#A0A0A0"           # Muted gray
    text_sunshine: str = "#FFD700"        # Gold text
    
    # Status colors
    success: str = "#4CAF50"              # Green
    error: str = "#F44336"                # Red
    warning: str = "#FF9800"              # Amber
    info: str = "#2196F3"                 # Blue
    
    # Component colors
    button_primary: str = "#FF8C00"       # Dark Orange
    button_secondary: str = "#FFB347"     # Light Orange
    button_success: str = "#4CAF50"       # Green
    button_danger: str = "#F44336"        # Red
    button_warning: str = "#FF9800"       # Amber
    
    # Border and accent colors
    border_primary: str = "#FF8C00"       # Dark Orange
    border_secondary: str = "#FFB347"     # Light Orange
    border_muted: str = "#666666"         # Gray
    
    # Sidebar colors
    sidebar_bg: str = "#252525"           # Darker than main bg
    sidebar_active: str = "#FF8C00"       # Orange active
    sidebar_hover: str = "#FFB347"        # Light orange hover


class SunshineTheme:
    """Sunshine theme configuration"""
    
    def __init__(self):
        self.colors = ColorPalette()
        self._setup_customtkinter_theme()
    
    def _setup_customtkinter_theme(self):
        """Configure CustomTkinter with sunshine colors"""
        import customtkinter as ctk
        
        # Set appearance mode to dark to work with our color scheme
        ctk.set_appearance_mode("dark")
        
        # Create custom color theme
        self.ctk_theme = {
            "CTk": {
                "fg_color": [self.colors.bg_primary, self.colors.bg_primary]
            },
            "CTkToplevel": {
                "fg_color": [self.colors.bg_primary, self.colors.bg_primary]
            },
            "CTkFrame": {
                "fg_color": [self.colors.bg_secondary, self.colors.bg_secondary],
                "border_color": [self.colors.border_muted, self.colors.border_muted]
            },
            "CTkButton": {
                "fg_color": [self.colors.button_primary, self.colors.button_primary],
                "hover_color": [self.colors.sunshine_secondary, self.colors.sunshine_secondary],
                "border_color": [self.colors.border_primary, self.colors.border_primary],
                "text_color": [self.colors.text_primary, self.colors.text_primary]
            },
            "CTkLabel": {
                "text_color": [self.colors.text_primary, self.colors.text_primary]
            },
            "CTkEntry": {
                "fg_color": [self.colors.bg_tertiary, self.colors.bg_tertiary],
                "border_color": [self.colors.border_muted, self.colors.border_primary],
                "text_color": [self.colors.text_primary, self.colors.text_primary]
            },
            "CTkCheckBox": {
                "fg_color": [self.colors.button_primary, self.colors.button_primary],
                "hover_color": [self.colors.sunshine_secondary, self.colors.sunshine_secondary],
                "checkmark_color": [self.colors.text_primary, self.colors.text_primary],
                "text_color": [self.colors.text_primary, self.colors.text_primary]
            },
            "CTkSwitch": {
                "fg_color": [self.colors.bg_hover, self.colors.bg_hover],
                "progress_color": [self.colors.button_primary, self.colors.button_primary],
                "button_color": [self.colors.text_primary, self.colors.text_primary],
                "text_color": [self.colors.text_primary, self.colors.text_primary]
            },
            "CTkProgressBar": {
                "fg_color": [self.colors.bg_hover, self.colors.bg_hover],
                "progress_color": [self.colors.button_primary, self.colors.button_primary]
            },
            "CTkScrollbar": {
                "fg_color": [self.colors.bg_secondary, self.colors.bg_secondary],
                "button_color": [self.colors.bg_hover, self.colors.bg_hover],
                "button_hover_color": [self.colors.border_muted, self.colors.border_muted]
            },
            "CTkScrollableFrame": {
                "fg_color": [self.colors.bg_secondary, self.colors.bg_secondary]
            },
            "CTkTextbox": {
                "fg_color": [self.colors.bg_tertiary, self.colors.bg_tertiary],
                "border_color": [self.colors.border_muted, self.colors.border_primary],
                "text_color": [self.colors.text_primary, self.colors.text_primary]
            }
        }
    
    def get_button_colors(self, button_type: str = "primary") -> Dict[str, str]:
        """Get button colors for different types"""
        button_configs = {
            "primary": {
                "fg_color": self.colors.button_primary,
                "hover_color": self.colors.sunshine_secondary,
                "text_color": self.colors.text_primary
            },
            "secondary": {
                "fg_color": self.colors.button_secondary,
                "hover_color": self.colors.sunshine_bright,
                "text_color": self.colors.bg_primary
            },
            "success": {
                "fg_color": self.colors.button_success,
                "hover_color": "#45A049",
                "text_color": self.colors.text_primary
            },
            "danger": {
                "fg_color": self.colors.button_danger,
                "hover_color": "#D32F2F",
                "text_color": self.colors.text_primary
            },
            "warning": {
                "fg_color": self.colors.button_warning,
                "hover_color": "#F57C00",
                "text_color": self.colors.bg_primary
            },
            "install_all": {
                "fg_color": self.colors.sunshine_accent,
                "hover_color": self.colors.sunshine_bright,
                "text_color": self.colors.bg_primary
            },
            "install_selected": {
                "fg_color": self.colors.button_primary,
                "hover_color": self.colors.sunshine_secondary,
                "text_color": self.colors.text_primary
            },
            "disabled": {
                "fg_color": self.colors.bg_hover,
                "hover_color": self.colors.bg_hover,
                "text_color": self.colors.text_muted
            }
        }
        
        return button_configs.get(button_type, button_configs["primary"])
    
    def get_status_color(self, status: str) -> str:
        """Get color for status messages"""
        status_colors = {
            "success": self.colors.success,
            "error": self.colors.error,
            "warning": self.colors.warning,
            "info": self.colors.info,
            "sunshine": self.colors.sunshine_accent
        }
        
        return status_colors.get(status, self.colors.text_primary)
    
    def get_component_colors(self) -> Dict[str, str]:
        """Get colors for different component types"""
        return {
            "core": self.colors.sunshine_primary,      # Core streaming components
            "tools": self.colors.sunshine_secondary,   # Additional tools
            "games": self.colors.sunshine_bright,      # Game management
            "system": self.colors.sunshine_warm        # System utilities
        }


# Global theme instance
_sunshine_theme = None


def get_sunshine_theme() -> SunshineTheme:
    """Get the global sunshine theme instance"""
    global _sunshine_theme
    if _sunshine_theme is None:
        _sunshine_theme = SunshineTheme()
    return _sunshine_theme


def apply_sunshine_theme():
    """Apply the sunshine theme to CustomTkinter"""
    theme = get_sunshine_theme()
    
    import customtkinter as ctk
    # Apply the color theme
    ctk.set_appearance_mode("dark")
    
    # Note: CustomTkinter doesn't support custom themes directly
    # So we'll apply colors individually to components
    return theme