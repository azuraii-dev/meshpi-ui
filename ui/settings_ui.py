#!/usr/bin/env python3
"""
UI Settings Tab for Meshtastic UI
Provides interface for changing themes, window settings, and other UI preferences
"""

import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox, filedialog
import logging
from typing import Optional, Callable

# Import the responsive UI utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.responsive_ui import create_responsive_tab

logger = logging.getLogger(__name__)

class SettingsUI:
    def __init__(self, parent, ui_config=None, theme_change_callback: Optional[Callable] = None):
        self.parent = parent
        self.ui_config = ui_config
        self.theme_change_callback = theme_change_callback
        
        # UI variables
        self.theme_var = tk.StringVar()
        self.auto_refresh_var = tk.BooleanVar()
        self.refresh_interval_var = tk.IntVar()
        self.show_tooltips_var = tk.BooleanVar()
        self.compact_mode_var = tk.BooleanVar()
        self.show_debug_var = tk.BooleanVar()
        self.remember_size_var = tk.BooleanVar()
        self.show_connection_status_var = tk.BooleanVar()
        self.show_message_notifications_var = tk.BooleanVar()
        self.sound_enabled_var = tk.BooleanVar()
        self.message_history_limit_var = tk.IntVar()
        self.auto_scroll_var = tk.BooleanVar()
        self.show_timestamps_var = tk.BooleanVar()
        self.show_node_ids_var = tk.BooleanVar()
        
        # Load current settings
        self.load_settings()
        
        # Create the settings interface
        self.create_widgets()
        
        # Bind to setting changes
        self.setup_change_handlers()
        
    def load_settings(self):
        """Load current settings from configuration"""
        if not self.ui_config:
            return
            
        try:
            # Load theme
            current_theme = self.ui_config.get_theme()
            self.theme_var.set(current_theme)
            
            # Load interface settings
            self.auto_refresh_var.set(self.ui_config.get('interface.auto_refresh', True))
            self.refresh_interval_var.set(self.ui_config.get('interface.refresh_interval', 5000))
            self.show_tooltips_var.set(self.ui_config.get('interface.show_tooltips', True))
            self.compact_mode_var.set(self.ui_config.get('interface.compact_mode', False))
            self.show_debug_var.set(self.ui_config.get('interface.show_debug_info', False))
            
            # Load window settings
            self.remember_size_var.set(self.ui_config.get('window.remember_size', True))
            
            # Load notification settings
            self.show_connection_status_var.set(self.ui_config.get('notifications.show_connection_status', True))
            self.show_message_notifications_var.set(self.ui_config.get('notifications.show_message_notifications', True))
            self.sound_enabled_var.set(self.ui_config.get('notifications.sound_enabled', False))
            
            # Load chat settings
            self.message_history_limit_var.set(self.ui_config.get('chat.message_history_limit', 100))
            self.auto_scroll_var.set(self.ui_config.get('chat.auto_scroll', True))
            self.show_timestamps_var.set(self.ui_config.get('chat.show_timestamps', True))
            self.show_node_ids_var.set(self.ui_config.get('chat.show_node_ids', False))
            
        except Exception as e:
            logger.error(f"Error loading UI settings: {e}")
            
    def create_widgets(self):
        """Create the settings interface with responsive container"""
        # Create responsive container
        self.responsive_container = create_responsive_tab(self.parent, padding="10")
        main_frame = self.responsive_container.get_content_frame()
        main_frame.columnconfigure(0, weight=1)
        
        # Theme Settings Section
        self.create_theme_section(main_frame, 0)
        
        # Interface Settings Section
        self.create_interface_section(main_frame, 1)
        
        # Window Settings Section
        self.create_window_section(main_frame, 2)
        
        # Notification Settings Section
        self.create_notification_section(main_frame, 3)
        
        # Chat Settings Section
        self.create_chat_section(main_frame, 4)
        
        # Action Buttons
        self.create_action_buttons(main_frame, 5)
        
        # Force scroll check after content is created
        self.parent.after_idle(self.responsive_container.force_scroll_check)
        
    def create_theme_section(self, parent, row):
        """Create theme selection section"""
        theme_frame = ttk.LabelFrame(parent, text="Theme Settings", padding="10")
        theme_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        theme_frame.columnconfigure(1, weight=1)
        
        # Theme selection
        ttk.Label(theme_frame, text="Current Theme:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        if self.ui_config:
            available_themes = list(self.ui_config.get_available_themes().keys())
        else:
            available_themes = ["darkly", "flatly", "cosmo"]
            
        self.theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                       values=available_themes, state="readonly")
        self.theme_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 10), pady=2)
        
        # Theme preview button
        preview_btn = ttk.Button(theme_frame, text="Preview Theme", 
                               command=self.preview_theme, bootstyle="info-outline")
        preview_btn.grid(row=0, column=2, padx=(10, 0), pady=2)
        
        # Theme description
        self.theme_description = ttk.Label(theme_frame, text="Select a theme to see description")
        self.theme_description.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
    def create_interface_section(self, parent, row):
        """Create interface settings section"""
        interface_frame = ttk.LabelFrame(parent, text="Interface Settings", padding="10")
        interface_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        interface_frame.columnconfigure(1, weight=1)
        
        # Auto refresh
        ttk.Checkbutton(interface_frame, text="Auto-refresh data", 
                       variable=self.auto_refresh_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Refresh interval
        ttk.Label(interface_frame, text="Refresh interval (ms):").grid(row=1, column=0, sticky=tk.W, pady=2)
        interval_spinbox = ttk.Spinbox(interface_frame, from_=1000, to=30000, increment=1000,
                                      textvariable=self.refresh_interval_var, width=10)
        interval_spinbox.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Other interface options
        ttk.Checkbutton(interface_frame, text="Show tooltips", 
                       variable=self.show_tooltips_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(interface_frame, text="Compact mode", 
                       variable=self.compact_mode_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(interface_frame, text="Show debug information", 
                       variable=self.show_debug_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        
    def create_window_section(self, parent, row):
        """Create window settings section"""
        window_frame = ttk.LabelFrame(parent, text="Window Settings", padding="10")
        window_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Window options
        ttk.Checkbutton(window_frame, text="Remember window size", 
                       variable=self.remember_size_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        
    def create_notification_section(self, parent, row):
        """Create notification settings section"""
        notif_frame = ttk.LabelFrame(parent, text="Notification Settings", padding="10")
        notif_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Notification options
        ttk.Checkbutton(notif_frame, text="Show connection status notifications", 
                       variable=self.show_connection_status_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(notif_frame, text="Show message notifications", 
                       variable=self.show_message_notifications_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(notif_frame, text="Enable sound notifications", 
                       variable=self.sound_enabled_var).grid(row=2, column=0, sticky=tk.W, pady=2)
        
    def create_chat_section(self, parent, row):
        """Create chat settings section"""
        chat_frame = ttk.LabelFrame(parent, text="Chat Settings", padding="10")
        chat_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        chat_frame.columnconfigure(1, weight=1)
        
        # Message history limit
        ttk.Label(chat_frame, text="Message history limit:").grid(row=0, column=0, sticky=tk.W, pady=2)
        history_spinbox = ttk.Spinbox(chat_frame, from_=10, to=1000, increment=10,
                                     textvariable=self.message_history_limit_var, width=10)
        history_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Chat options
        ttk.Checkbutton(chat_frame, text="Auto-scroll to new messages", 
                       variable=self.auto_scroll_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(chat_frame, text="Show timestamps", 
                       variable=self.show_timestamps_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(chat_frame, text="Show node IDs in chat", 
                       variable=self.show_node_ids_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
    def create_action_buttons(self, parent, row):
        """Create action buttons section"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, pady=(20, 0))
        
        ttk.Button(button_frame, text="Apply Settings", command=self.apply_settings, 
                  bootstyle="success").grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_settings, 
                  bootstyle="warning").grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(button_frame, text="Export Settings", command=self.export_settings, 
                  bootstyle="info-outline").grid(row=0, column=2, padx=(0, 10))
        
        ttk.Button(button_frame, text="Import Settings", command=self.import_settings, 
                  bootstyle="secondary-outline").grid(row=0, column=3)
        
    def setup_change_handlers(self):
        """Setup handlers for immediate setting changes"""
        # Theme changes - handle both old and new tkinter API
        try:
            # Try new API first (Python 3.8+)
            self.theme_var.trace_add('write', self.on_theme_change)
        except AttributeError:
            # Fall back to old API (Python < 3.8)
            self.theme_var.trace('w', self.on_theme_change)
        
    def on_theme_change(self, *args):
        """Handle theme selection change"""
        try:
            if self.ui_config:
                theme_name = self.theme_var.get()
                theme_info = self.ui_config.get_theme_info(theme_name)
                if theme_info:
                    description = f"{theme_info.get('description', '')} ({theme_info.get('type', 'unknown')} theme)"
                    self.theme_description.config(text=description)
        except Exception as e:
            logger.debug(f"Error updating theme description: {e}")
                
    def preview_theme(self):
        """Preview the selected theme"""
        if not self.ui_config:
            messagebox.showwarning("Warning", "UI configuration not available")
            return
            
        theme_name = self.theme_var.get()
        if not theme_name:
            messagebox.showwarning("Warning", "Please select a theme to preview")
            return
            
        try:
            # Apply theme immediately with improved error handling
            if self.theme_change_callback:
                # Apply theme without manipulating combobox state to avoid widget errors
                self.theme_change_callback(theme_name)
            else:
                messagebox.showinfo("Preview", f"Theme '{theme_name}' would be applied.\nRestart to see changes.")
                
        except Exception as e:
            logger.error(f"Error previewing theme: {e}")
            messagebox.showerror("Error", f"Failed to preview theme: {e}")
            
    def _apply_theme_safely(self, theme_name):
        """Apply theme safely with proper error handling"""
        try:
            self.theme_change_callback(theme_name)
        except Exception as e:
            logger.error(f"Error applying theme safely: {e}")
            
    def apply_settings(self):
        """Apply all settings"""
        if not self.ui_config:
            messagebox.showwarning("Warning", "UI configuration not available")
            return
            
        try:
            # Apply theme
            theme_name = self.theme_var.get()
            if theme_name:
                self.ui_config.set_theme(theme_name, save=False)
                
            # Apply interface settings
            self.ui_config.set('interface.auto_refresh', self.auto_refresh_var.get(), save=False)
            self.ui_config.set('interface.refresh_interval', self.refresh_interval_var.get(), save=False)
            self.ui_config.set('interface.show_tooltips', self.show_tooltips_var.get(), save=False)
            self.ui_config.set('interface.compact_mode', self.compact_mode_var.get(), save=False)
            self.ui_config.set('interface.show_debug_info', self.show_debug_var.get(), save=False)
            
            # Apply window settings
            self.ui_config.set('window.remember_size', self.remember_size_var.get(), save=False)
            
            # Apply notification settings
            self.ui_config.set('notifications.show_connection_status', self.show_connection_status_var.get(), save=False)
            self.ui_config.set('notifications.show_message_notifications', self.show_message_notifications_var.get(), save=False)
            self.ui_config.set('notifications.sound_enabled', self.sound_enabled_var.get(), save=False)
            
            # Apply chat settings
            self.ui_config.set('chat.message_history_limit', self.message_history_limit_var.get(), save=False)
            self.ui_config.set('chat.auto_scroll', self.auto_scroll_var.get(), save=False)
            self.ui_config.set('chat.show_timestamps', self.show_timestamps_var.get(), save=False)
            self.ui_config.set('chat.show_node_ids', self.show_node_ids_var.get(), save=False)
            
            # Save all changes
            self.ui_config.save_config()
            
            # Apply theme if callback is available
            if self.theme_change_callback and theme_name:
                self._apply_theme_safely(theme_name)
                
            messagebox.showinfo("Settings Applied", "Settings have been applied successfully!")
            
        except Exception as e:
            logger.error(f"Error applying settings: {e}")
            messagebox.showerror("Error", f"Failed to apply settings: {e}")
            
    def reset_settings(self):
        """Reset all settings to defaults"""
        result = messagebox.askyesno("Reset Settings", 
                                   "Are you sure you want to reset all settings to defaults?\n\n"
                                   "This action cannot be undone.")
        
        if result:
            try:
                if self.ui_config:
                    self.ui_config.reset_to_defaults()
                    self.load_settings()  # Reload the UI with defaults
                    messagebox.showinfo("Reset Complete", "Settings have been reset to defaults.")
                    
            except Exception as e:
                logger.error(f"Error resetting settings: {e}")
                messagebox.showerror("Error", f"Failed to reset settings: {e}")
                
    def export_settings(self):
        """Export current settings to a file"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Export UI Settings",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename and self.ui_config:
                self.ui_config.export_config(filename)
                messagebox.showinfo("Export Complete", f"Settings exported to:\n{filename}")
                
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            messagebox.showerror("Export Error", f"Failed to export settings: {e}")
            
    def import_settings(self):
        """Import settings from a file"""
        try:
            filename = filedialog.askopenfilename(
                title="Import UI Settings",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename and self.ui_config:
                self.ui_config.import_config(filename)
                self.load_settings()  # Reload the UI with imported settings
                messagebox.showinfo("Import Complete", f"Settings imported from:\n{filename}")
                
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            messagebox.showerror("Import Error", f"Failed to import settings: {e}") 