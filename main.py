#!/usr/bin/env python3
"""
Meshtastic UI - A comprehensive interface for Meshtastic mesh networking
Features: Map view, Chat interface, Network topology, Analytics, Emergency, and Configuration
"""

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import logging
import threading
import time
import queue
import os
import sys
import platform

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our modules
from core.meshtastic_interface import MeshtasticInterface
from data.database import DataLogger
from ui.map_ui import MapUI
from ui.chat_ui import ChatUI
from ui.network_ui import NetworkUI

from ui.emergency_ui import EmergencyUI
from ui.config_ui import ConfigUI
from ui.settings_ui import SettingsUI

# Import path utilities for data location info
try:
    from utils.paths import get_runtime_info, is_executable
    SHOW_DATA_PATHS = True
except ImportError:
    SHOW_DATA_PATHS = False

# Import UI configuration
try:
    from utils.ui_config import get_ui_config
    UI_CONFIG_AVAILABLE = True
except ImportError:
    UI_CONFIG_AVAILABLE = False
    logger.warning("UI configuration not available")

class MeshtasticApp:
    """Main application class for Meshtastic UI"""
    
    def __init__(self, root):
        self.root = root
        
        # Load UI configuration
        if UI_CONFIG_AVAILABLE:
            self.ui_config = get_ui_config()
            # Apply saved window settings
            window_config = self.ui_config.get_window_config()
            window_size = f"{window_config.get('width', 1200)}x{window_config.get('height', 800)}"
        else:
            self.ui_config = None
            window_size = "1200x800"
        
        # Apply macOS-specific fixes for PyInstaller windowed app issues
        if platform.system() == "Darwin":
            self.apply_macos_fixes()
        
        self.root.title(f"Meshtastic UI")
        self.root.geometry(window_size)
        
        # Set window icon (if available)
        try:
            # Try to load icon from different sources
            icon_paths = [
                "assets/icon.png",  # For development/Linux
                "assets/icon.ico",  # For Windows  
                "assets/icon.icns",  # For macOS
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    # For PNG/ICO files with PIL
                    try:
                        from PIL import Image, ImageTk
                        image = Image.open(icon_path)
                        # Resize to appropriate window icon size
                        image = image.resize((32, 32), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(image)
                        self.root.iconphoto(True, photo)
                        break
                    except ImportError:
                        # Fallback: use ICO directly on Windows
                        if icon_path.endswith('.ico'):
                            self.root.iconbitmap(icon_path)
                            break
        except Exception as e:
            logger.debug(f"Could not set window icon: {e}")
        
        # Show data location info on startup
        if SHOW_DATA_PATHS:
            runtime_info = get_runtime_info()
            if is_executable():
                logger.info("=" * 60)
                logger.info("RUNNING AS EXECUTABLE")
                logger.info("=" * 60)
                logger.info(f"Data will be stored in: {runtime_info['user_data_dir']}")
                logger.info(f"Database location: {runtime_info['database_path']}")
                logger.info(f"Logs location: {runtime_info['logs_dir']}")
                logger.info("=" * 60)
                
                # Also show in title bar for executable mode
                self.root.title(f"Meshtastic UI - Data in {runtime_info['user_data_dir']}")
        
        # Initialize core components
        self.data_logger = DataLogger()
        self.interface_manager = MeshtasticInterface(self.data_logger)
        
        # Event queue for UI updates
        self.ui_event_queue = queue.Queue()
        
        # Initialize UI components
        self.setup_ui()
        
        # Setup event callbacks
        self.setup_event_callbacks()
        
        # Start event processing and periodic updates
        self.start_event_processing()
        self.start_periodic_updates()
        
    def apply_macos_fixes(self):
        """Apply macOS-specific fixes for PyInstaller issues"""
        try:
            # Debug logging for macOS issues
            logger.info("Applying macOS PyInstaller fixes...")
            
            # Schedule window fixes after a short delay to let the app initialize
            self.root.after(100, self.fix_macos_window_display)
            
            # Ensure proper focus handling
            self.root.after(200, lambda: self.root.focus_force())
            
            # Force window to front
            self.root.after(300, lambda: self.root.lift())
            
        except Exception as e:
            logger.warning(f"Could not apply macOS fixes: {e}")
    
    def fix_macos_window_display(self):
        """Fix macOS window display issues commonly seen with PyInstaller"""
        try:
            # This is a known workaround for macOS PyInstaller apps
            # that appear in dock but don't show the window properly
            logger.debug("Applying macOS window display fix...")
            
            # Temporary iconify/deiconify cycle to force proper window display
            self.root.iconify()
            self.root.update()
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            
            logger.debug("macOS window display fix applied")
            
        except Exception as e:
            logger.warning(f"Could not apply window display fix: {e}")
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Create connection frame
        self.create_connection_frame(main_frame)
        
        # Create main content area with notebook tabs
        self.create_main_content(main_frame)
        
        # Create status bar
        self.create_status_bar(main_frame)
        
    def create_connection_frame(self, parent):
        """Create connection controls"""
        conn_frame = ttk.LabelFrame(parent, text="Connection", padding="5")
        conn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Connection type selection
        ttk.Label(conn_frame, text="Connection Type:").grid(row=0, column=0, padx=(0, 10))
        
        self.connection_type = tk.StringVar(value="Serial")
        conn_type_combo = ttk.Combobox(conn_frame, textvariable=self.connection_type, 
                                      values=["Serial", "TCP"], state="readonly", width=10)
        conn_type_combo.grid(row=0, column=1, padx=(0, 10))
        
        # Connection parameters
        ttk.Label(conn_frame, text="Port/IP:").grid(row=0, column=2, padx=(0, 10))
        
        self.connection_param = tk.StringVar(value="auto")
        param_entry = ttk.Entry(conn_frame, textvariable=self.connection_param, width=20)
        param_entry.grid(row=0, column=3, padx=(0, 10))
        
        # Connect/Disconnect buttons
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_device)
        self.connect_btn.grid(row=0, column=4, padx=(0, 10))
        
        self.disconnect_btn = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect_device, state="disabled")
        self.disconnect_btn.grid(row=0, column=5)
        
        # Status indicator
        self.status_label = ttk.Label(conn_frame, text="Status: Disconnected", foreground="red")
        self.status_label.grid(row=0, column=6, padx=(20, 0))
        
        # GPS Status indicator
        self.gps_status_label = ttk.Label(conn_frame, text="GPS: N/A", foreground="gray")
        self.gps_status_label.grid(row=0, column=7, padx=(20, 0))
        
    def create_main_content(self, parent):
        """Create the main tabbed interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create tab frames
        map_frame = ttk.Frame(self.notebook)
        chat_frame = ttk.Frame(self.notebook)
        #network_frame = ttk.Frame(self.notebook)
        #analytics_frame = ttk.Frame(self.notebook)
        emergency_frame = ttk.Frame(self.notebook)
        config_frame = ttk.Frame(self.notebook)
        settings_frame = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(map_frame, text="Map")
        self.notebook.add(chat_frame, text="Chat")
        #self.notebook.add(network_frame, text="Network")
        #self.notebook.add(analytics_frame, text="Analytics")
        self.notebook.add(emergency_frame, text="Emergency")
        self.notebook.add(config_frame, text="Config")
        self.notebook.add(settings_frame, text="Settings")
        
        # Initialize UI modules with the correct parent frames
        self.map_ui = MapUI(map_frame, self.interface_manager, self.data_logger)
        self.chat_ui = ChatUI(chat_frame, self.interface_manager, self.data_logger)
        self.emergency_ui = EmergencyUI(emergency_frame, self.interface_manager, self.data_logger)
        self.config_ui = ConfigUI(config_frame, self.interface_manager, self.data_logger)
        self.settings_ui = SettingsUI(settings_frame, self.ui_config, self.change_theme)
        
        # Set disabled UI components to None for proper handling
        self.network_ui = None
        self.analytics_ui = None
        
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(1, weight=1)
        
        # Status elements
        self.status_text = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_text).grid(row=0, column=0, sticky=tk.W)
        
        # Connection status
        self.connection_status_text = tk.StringVar(value="Disconnected")
        ttk.Label(status_frame, textvariable=self.connection_status_text).grid(row=0, column=1, sticky=tk.E)
        
    def setup_event_callbacks(self):
        """Setup event callbacks for interface manager"""
        # Override the interface manager's handle_message method to also update UI
        original_handle_message = self.interface_manager.handle_message
        
        def handle_message_with_ui_update(msg_type, data):
            # Call original handler
            original_handle_message(msg_type, data)
            
            # Queue UI update
            self.ui_event_queue.put((msg_type, data))
            
        self.interface_manager.handle_message = handle_message_with_ui_update
        
    def start_event_processing(self):
        """Start processing UI events"""
        def process_ui_events():
            try:
                # Process multiple events in one go to reduce frequency
                events_processed = 0
                max_events_per_cycle = 5
                
                while events_processed < max_events_per_cycle:
                    try:
                        msg_type, data = self.ui_event_queue.get(timeout=0.01)
                        
                        # Handle different message types
                        if msg_type == 'message':
                            self.handle_message_received(data)
                        elif msg_type == 'node_updated':
                            self.handle_node_updated(data)
                        elif msg_type == 'connection_established':
                            self.handle_connection_established()
                        elif msg_type == 'connection_lost':
                            self.handle_connection_lost()
                        elif msg_type == 'ack_received':
                            self.handle_ack_received(data)
                        elif msg_type == 'routing_error':
                            self.handle_routing_error(data)
                            
                        events_processed += 1
                        
                    except queue.Empty:
                        break
                    
            except Exception as e:
                logger.error(f"Error processing UI event: {e}")
                
            # Schedule next processing (reduced frequency)
            self.root.after(100, process_ui_events)
            
        # Start processing
        self.root.after(100, process_ui_events)
        
    def handle_message_received(self, packet):
        """Handle received message"""
        try:
            # Update chat UI
            if hasattr(self.chat_ui, 'display_message'):
                self.chat_ui.display_message(packet)
                
        except Exception as e:
            logger.error(f"Error handling received message: {e}")
            
    def handle_node_updated(self, node):
        """Handle node update"""
        try:
            # Update all UI components that need node data
            nodes = self.interface_manager.get_nodes()
            
            if hasattr(self.map_ui, 'update_nodes_display'):
                self.map_ui.update_nodes_display(nodes)
                
            if self.network_ui and hasattr(self.network_ui, 'update_nodes'):
                self.network_ui.update_nodes(nodes)
                
            if hasattr(self.chat_ui, 'update_destinations'):
                self.chat_ui.update_destinations(nodes)
                
        except Exception as e:
            logger.error(f"Error handling node update: {e}")
            
    def handle_connection_established(self):
        """Handle connection established"""
        self.root.after(0, self.on_connect_success)
        
    def handle_connection_lost(self):
        """Handle connection lost"""
        self.root.after(0, self.on_disconnect)
        
    def handle_ack_received(self, packet):
        """Handle ACK received"""
        try:
            if hasattr(self.chat_ui, 'handle_ack_received'):
                self.chat_ui.handle_ack_received(packet)
        except Exception as e:
            logger.error(f"Error handling ACK: {e}")
            
    def handle_routing_error(self, packet):
        """Handle routing error"""
        try:
            if hasattr(self.chat_ui, 'handle_routing_error'):
                self.chat_ui.handle_routing_error(packet)
        except Exception as e:
            logger.error(f"Error handling routing error: {e}")
        
    def connect_device(self):
        """Connect to Meshtastic device"""
        conn_type = self.connection_type.get()
        param = self.connection_param.get()
        
        # Disable connect button during connection attempt
        self.connect_btn.config(state="disabled")
        self.update_connection_status("Connecting...")
        
        def connection_callback(success, message):
            """Callback for connection result"""
            if success:
                self.root.after(0, self.on_connect_success)
            else:
                self.root.after(0, lambda: self.on_connect_failed(message))
                
        # Connect with callback
        self.interface_manager.connect(conn_type, param, connection_callback)
        
    def disconnect_device(self):
        """Disconnect from Meshtastic device"""
        self.interface_manager.disconnect()
        self.on_disconnect()
        
    def on_connect_success(self):
        """Handle successful connection"""
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.status_label.config(text="Status: Connected", foreground="green")
        self.connection_status_text.set("Connected")
        
        # Check GPS status immediately after connection
        self.root.after(1000, self.check_gps_status)  # Check after 1 second delay
        
        # Refresh device info in config tab
        if hasattr(self.config_ui, 'get_device_info'):
            self.root.after(500, self.config_ui.get_device_info)  # Slight delay to ensure connection is stable
        
    def on_connect_failed(self, error_message="Failed to connect to device"):
        """Handle failed connection"""
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.status_label.config(text="Status: Connection Failed", foreground="red")
        self.connection_status_text.set("Connection Failed")
        messagebox.showerror("Connection Error", error_message)
        
    def on_disconnect(self):
        """Handle disconnection"""
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.status_label.config(text="Status: Disconnected", foreground="red")
        self.connection_status_text.set("Disconnected")
        
        # Clear GPS status
        self.gps_status_label.config(text="GPS: N/A", foreground="gray")
        
        # Clear node data in UI components
        if hasattr(self.map_ui, 'update_nodes_display'):
            self.map_ui.update_nodes_display({})
        if self.network_ui and hasattr(self.network_ui, 'update_nodes'):
            self.network_ui.update_nodes({})
        if hasattr(self.chat_ui, 'update_destinations'):
            self.chat_ui.update_destinations({})
        
    def update_connection_status(self, status):
        """Update connection status"""
        self.status_text.set(status)
        
    def check_gps_status(self):
        """Check and update GPS status"""
        if not self.interface_manager.is_connected():
            self.gps_status_label.config(text="GPS: N/A", foreground="gray")
            return
            
        try:
            # Get detailed GPS status from interface manager
            gps_status = self.interface_manager.get_gps_status()
            
            status = gps_status.get('status', 'unknown')
            satellites = gps_status.get('satellites', 0)
            
            if status == 'fixed':
                self.gps_status_label.config(text=f"GPS: Fixed ({satellites} sats)", foreground="green")
            elif status == 'searching':
                self.gps_status_label.config(text=f"GPS: Searching ({satellites} sats)", foreground="orange")
            elif status == 'no_signal':
                self.gps_status_label.config(text="GPS: No Signal", foreground="red")
            elif status == 'disabled':
                self.gps_status_label.config(text="GPS: Disabled", foreground="gray")
            elif status == 'disconnected':
                self.gps_status_label.config(text="GPS: N/A", foreground="gray")
            else:
                self.gps_status_label.config(text="GPS: Error", foreground="red")
                    
        except Exception as e:
            logger.debug(f"Error checking GPS status: {e}")
            self.gps_status_label.config(text="GPS: Error", foreground="red")
        
    def start_periodic_updates(self):
        """Start periodic updates for UI components"""
        # Separate update frequencies for different components
        self.update_counter = 0
        
        def update_loop():
            try:
                # Only update if connected
                if self.interface_manager.is_connected():
                    # Get current nodes from interface manager
                    nodes = self.interface_manager.get_nodes()
                    
                    # Update node count in status (every update)
                    node_count = len(nodes)
                    self.status_text.set(f"Ready - {node_count} nodes")
                    
                    # Update GPS status (every update)
                    self.check_gps_status()
                    
                    # Update analytics data less frequently (every 3rd update = 30 seconds)
                    if self.update_counter % 3 == 0:
                        if self.analytics_ui and hasattr(self.analytics_ui, 'update_data'):
                            self.analytics_ui.update_data(nodes)
                    
                    # Update network topology less frequently (every 2nd update = 20 seconds)
                    if self.update_counter % 2 == 0:
                        if self.network_ui and hasattr(self.network_ui, 'refresh_network_topology'):
                            self.network_ui.refresh_network_topology(nodes)
                    
                    self.update_counter += 1
                    
            except Exception as e:
                logger.error(f"Error in periodic update: {e}")
                
            # Schedule next update
            self.root.after(10000, update_loop)  # Update every 10 seconds
            
        # Start the update loop
        self.root.after(1000, update_loop)  # First update after 1 second
        
    def change_theme(self, theme_name: str):
        """Change the application theme"""
        try:
            if hasattr(self.root, 'style'):
                logger.info(f"Changing theme from {self.root.style.theme.name} to {theme_name}")
                
                # Apply theme with error isolation
                try:
                    # Force focus away from any comboboxes to prevent widget errors
                    self.root.focus_set()
                    
                    # Give a moment for any dropdowns to close
                    self.root.update_idletasks()
                    
                    self.root.style.theme_use(theme_name)
                    logger.info(f"Theme successfully changed to: {theme_name}")
                except Exception as theme_error:
                    # Check if it's the specific combobox error we're seeing
                    if "combobox.popdown" in str(theme_error):
                        logger.warning(f"Combobox dropdown interference during theme change: {theme_error}")
                        # The theme might have still changed despite the error, so continue with updates
                        logger.info("Continuing with canvas updates despite combobox error")
                    else:
                        logger.error(f"Error applying theme {theme_name}: {theme_error}")
                        return  # Don't continue if theme change failed
                
                # Save theme preference immediately
                try:
                    if self.ui_config:
                        self.ui_config.set_theme(theme_name)
                        logger.debug("Theme preference saved")
                except Exception as save_error:
                    logger.error(f"Error saving theme preference: {save_error}")
                
                # Update responsive container backgrounds to match new theme
                # Try immediate update first, then delayed backup
                def update_responsive_containers_immediate():
                    logger.debug("Immediate responsive container theme updates...")
                    try:
                        if hasattr(self, 'settings_ui') and hasattr(self.settings_ui, 'responsive_container'):
                            self.settings_ui.responsive_container.update_theme()
                        if hasattr(self, 'config_ui') and hasattr(self.config_ui, 'responsive_container'):
                            self.config_ui.responsive_container.update_theme()
                        if hasattr(self, 'emergency_ui') and hasattr(self.emergency_ui, 'responsive_container'):
                            self.emergency_ui.responsive_container.update_theme()
                        if hasattr(self, 'chat_ui') and hasattr(self.chat_ui, 'update_theme'):
                            self.chat_ui.update_theme()
                    except Exception as e:
                        logger.debug(f"Immediate update failed: {e}")
                
                def update_responsive_containers():
                    logger.info("Starting responsive container theme updates...")
                    try:
                        if hasattr(self, 'settings_ui') and hasattr(self.settings_ui, 'responsive_container'):
                            logger.info("Updating settings UI responsive container theme")
                            self.settings_ui.responsive_container.update_theme()
                    except Exception as e:
                        logger.error(f"Error updating settings UI theme: {e}")
                    
                    try:
                        if hasattr(self, 'config_ui') and hasattr(self.config_ui, 'responsive_container'):
                            logger.info("Updating config UI responsive container theme")
                            self.config_ui.responsive_container.update_theme()
                    except Exception as e:
                        logger.error(f"Error updating config UI theme: {e}")
                    
                    try:
                        if hasattr(self, 'emergency_ui') and hasattr(self.emergency_ui, 'responsive_container'):
                            logger.info("Updating emergency UI responsive container theme")
                            self.emergency_ui.responsive_container.update_theme()
                    except Exception as e:
                        logger.error(f"Error updating emergency UI theme: {e}")
                    
                    # Also update chat UI in delayed update  
                    try:
                        if hasattr(self, 'chat_ui') and hasattr(self.chat_ui, 'update_theme'):
                            logger.info("Updating chat UI theme")
                            self.chat_ui.update_theme()
                    except Exception as e:
                        logger.error(f"Error updating chat UI theme: {e}")
                    
                    logger.info("Completed responsive container theme updates")
                
                # Try immediate update for fast feedback
                self.root.after_idle(update_responsive_containers_immediate)
                
                # Also update chat UI theme immediately
                try:
                    if hasattr(self, 'chat_ui') and hasattr(self.chat_ui, 'update_theme'):
                        self.chat_ui.update_theme()
                        logger.debug("Updated chat UI theme immediately")
                except Exception as e:
                    logger.error(f"Error updating chat UI theme immediately: {e}")
                
                # Schedule delayed update as backup
                self.root.after(100, update_responsive_containers)
                    
            else:
                logger.warning("Theme change not supported - restart required")
                
        except Exception as e:
            logger.error(f"Error changing theme: {e}")
            # Don't show error popup for theme changes - just log it
    
    def _retry_theme_change(self, theme_name: str):
        """Retry theme change after combobox interference"""
        try:
            logger.info(f"Retrying theme change to: {theme_name}")
            self.root.style.theme_use(theme_name)
            logger.info(f"Theme successfully changed to: {theme_name} (retry)")
            
            # Save theme preference
            if self.ui_config:
                self.ui_config.set_theme(theme_name)
                
            # Update responsive containers
            def update_responsive_containers():
                try:
                    if hasattr(self, 'settings_ui') and hasattr(self.settings_ui, 'responsive_container'):
                        self.settings_ui.responsive_container.update_theme()
                except Exception as e:
                    logger.error(f"Error updating settings UI theme: {e}")
                
                try:
                    if hasattr(self, 'config_ui') and hasattr(self.config_ui, 'responsive_container'):
                        self.config_ui.responsive_container.update_theme()
                except Exception as e:
                    logger.error(f"Error updating config UI theme: {e}")
                
                try:
                    if hasattr(self, 'emergency_ui') and hasattr(self.emergency_ui, 'responsive_container'):
                        self.emergency_ui.responsive_container.update_theme()
                except Exception as e:
                    logger.error(f"Error updating emergency UI theme: {e}")
            
            self.root.after(200, update_responsive_containers)
            
        except Exception as e:
            logger.error(f"Failed to retry theme change: {e}")

def main():
    """Main application entry point"""
    logger.info("Starting Meshtastic UI...")
    
    # Load theme from configuration
    theme_name = "darkly"  # default
    if UI_CONFIG_AVAILABLE:
        try:
            ui_config = get_ui_config()
            theme_name = ui_config.get_theme()
            logger.info(f"Using theme: {theme_name}")
        except Exception as e:
            logger.warning(f"Error loading theme config: {e}")
    
    # Create ttkbootstrap window with theme
    root = ttk.Window(themename=theme_name)
    app = MeshtasticApp(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
    finally:
        # Save window settings on exit
        if UI_CONFIG_AVAILABLE and hasattr(app, 'ui_config') and app.ui_config:
            try:
                # Save current window size if remember_size is enabled
                if app.ui_config.get('window.remember_size', True):
                    width = root.winfo_width()
                    height = root.winfo_height()
                    if width > 100 and height > 100:  # Sanity check
                        app.ui_config.set_window_config(width=width, height=height)
            except Exception as e:
                logger.debug(f"Error saving window settings: {e}")
        
        logger.info("Meshtastic UI shutting down")

if __name__ == "__main__":
    main() 