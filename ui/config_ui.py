import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigUI:
    # Region mapping constants - Meshtastic LoRa region enum values
    REGION_NAME_TO_ENUM = {
        "ANZ": 7,       # Australia/New Zealand
        "CN": 8,        # China
        "EU_433": 2,    # Europe 433MHz
        "EU_868": 3,    # Europe 868MHz
        "IN": 9,        # India
        "JP": 10,       # Japan
        "KR": 11,       # Korea
        "MY_433": 12,   # Malaysia 433MHz
        "MY_919": 13,   # Malaysia 919MHz
        "NZ_865": 14,   # New Zealand 865MHz
        "RU": 15,       # Russia
        "SG_923": 16,   # Singapore
        "TH": 17,       # Thailand
        "TW": 18,       # Taiwan
        "UA_433": 19,   # Ukraine 433MHz
        "UA_868": 20,   # Ukraine 868MHz
        "US": 1         # United States
    }
    
    # Reverse mapping for reading current region from device
    REGION_ENUM_TO_NAME = {v: k for k, v in REGION_NAME_TO_ENUM.items()}
    
    def __init__(self, parent, interface_manager, data_logger):
        self.parent = parent
        self.interface_manager = interface_manager
        self.data_logger = data_logger
        
        # Configuration data
        self.config_profiles = {}
        self.managed_devices = []
        self.current_profile = "Default"
        
        # Create configuration interface
        self.create_widgets()
        
        # Initialize data
        self.load_config_profiles()
        self.load_managed_devices()
        
    def create_widgets(self):
        """Create configuration tab"""
        # Configure grid
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Create scrollable content with better performance
        config_canvas = tk.Canvas(self.parent, highlightthickness=0)
        config_scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=config_canvas.yview)
        config_content = ttk.Frame(config_canvas)
        
        # Optimize scrolling performance
        def on_canvas_configure(event):
            config_canvas.configure(scrollregion=config_canvas.bbox("all"))
        
        def on_mousewheel(event):
            config_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        config_content.bind('<Configure>', on_canvas_configure)
        config_canvas.bind("<MouseWheel>", on_mousewheel)
        
        config_canvas.create_window((0, 0), window=config_content, anchor="nw")
        config_canvas.configure(yscrollcommand=config_scrollbar.set)
        
        config_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        config_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Device information
        device_frame = ttk.LabelFrame(config_content, text="Device Information", padding="10")
        device_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        device_frame.columnconfigure(1, weight=1)
        
        # Device info labels
        self.device_info_labels = {}
        info_fields = ["Long Name", "Short Name", "Hardware", "Firmware", "Region", "Channel"]
        
        for i, field in enumerate(info_fields):
            ttk.Label(device_frame, text=f"{field}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            label = ttk.Label(device_frame, text="N/A", foreground="gray")
            label.grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=2)
            self.device_info_labels[field] = label
        
        # Node settings
        node_frame = ttk.LabelFrame(config_content, text="Node Settings", padding="10")
        node_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        node_frame.columnconfigure(1, weight=1)
        
        # Long name
        ttk.Label(node_frame, text="Long Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.long_name_var = tk.StringVar()
        ttk.Entry(node_frame, textvariable=self.long_name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Short name
        ttk.Label(node_frame, text="Short Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.short_name_var = tk.StringVar()
        ttk.Entry(node_frame, textvariable=self.short_name_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Update button
        ttk.Button(node_frame, text="Update Node Info", command=self.update_node_info).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Region settings
        region_frame = ttk.LabelFrame(config_content, text="Region Settings", padding="10")
        region_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        region_frame.columnconfigure(1, weight=1)
        
        # Region selection
        ttk.Label(region_frame, text="Region:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.region_var = tk.StringVar()
        
        # List of supported regions
        self.regions = list(self.REGION_NAME_TO_ENUM.keys())
        
        region_combo = ttk.Combobox(region_frame, textvariable=self.region_var, 
                                   values=self.regions, state="readonly", width=10)
        region_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Region info label
        self.region_info_label = ttk.Label(region_frame, text="Select region for regulatory compliance", 
                                          foreground="gray", font=("Arial", 8))
        self.region_info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Update region button
        ttk.Button(region_frame, text="Update Region", command=self.update_region).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Channel settings
        channel_frame = ttk.LabelFrame(config_content, text="Channel Settings", padding="10")
        channel_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        channel_frame.columnconfigure(1, weight=1)
        
        # Channel name
        ttk.Label(channel_frame, text="Channel Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.channel_name_var = tk.StringVar()
        ttk.Entry(channel_frame, textvariable=self.channel_name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # PSK
        ttk.Label(channel_frame, text="PSK:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.psk_var = tk.StringVar()
        ttk.Entry(channel_frame, textvariable=self.psk_var, width=30, show="*").grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Power settings
        power_frame = ttk.LabelFrame(config_content, text="Power Settings", padding="10")
        power_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # Battery level display
        ttk.Label(power_frame, text="Battery Level:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.battery_label = ttk.Label(power_frame, text="N/A", foreground="gray")
        self.battery_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # GPS settings
        gps_frame = ttk.LabelFrame(config_content, text="GPS Settings", padding="10")
        gps_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        gps_frame.columnconfigure(1, weight=1)
        
        # GPS status display
        ttk.Label(gps_frame, text="GPS Status:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.gps_status_display = ttk.Label(gps_frame, text="N/A", foreground="gray")
        self.gps_status_display.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # GPS enabled checkbox
        ttk.Label(gps_frame, text="GPS Enabled:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.gps_enabled_var = tk.BooleanVar()
        gps_enabled_check = ttk.Checkbutton(gps_frame, variable=self.gps_enabled_var, command=self.toggle_gps)
        gps_enabled_check.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # GPS update interval
        ttk.Label(gps_frame, text="Update Interval (sec):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.gps_interval_var = tk.StringVar(value="30")
        interval_frame = ttk.Frame(gps_frame)
        interval_frame.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        interval_entry = ttk.Entry(interval_frame, textvariable=self.gps_interval_var, width=10)
        interval_entry.grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(interval_frame, text="Update", command=self.update_gps_interval).grid(row=0, column=1)
        
        # GPS broadcast interval
        ttk.Label(gps_frame, text="Broadcast Interval (sec):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.gps_broadcast_var = tk.StringVar(value="900")
        broadcast_frame = ttk.Frame(gps_frame)
        broadcast_frame.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        broadcast_entry = ttk.Entry(broadcast_frame, textvariable=self.gps_broadcast_var, width=10)
        broadcast_entry.grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(broadcast_frame, text="Update", command=self.update_gps_broadcast).grid(row=0, column=1)
        
        # GPS info label
        gps_info_label = ttk.Label(gps_frame, 
                                  text="Update: How often GPS reads position\nBroadcast: How often position is shared with mesh", 
                                  foreground="gray", font=("Arial", 8))
        gps_info_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(config_content, text="Actions", padding="10")
        actions_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # Action buttons
        ttk.Button(actions_frame, text="Reboot Device", command=self.reboot_device).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(actions_frame, text="Factory Reset", command=self.factory_reset).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(actions_frame, text="Get Device Info", command=self.get_device_info).grid(row=0, column=2, padx=5, pady=2)
        
        # Configuration Profiles Section
        profiles_frame = ttk.LabelFrame(config_content, text="Configuration Profiles", padding="10")
        profiles_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        profiles_frame.columnconfigure(1, weight=1)
        
        # Current profile display
        ttk.Label(profiles_frame, text="Current Profile:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.current_profile_label = ttk.Label(profiles_frame, text="Default", foreground="blue")
        self.current_profile_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Profile selection
        ttk.Label(profiles_frame, text="Select Profile:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profiles_frame, textvariable=self.profile_var, state="readonly", width=20)
        self.profile_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_selected)
        
        # Profile name input
        ttk.Label(profiles_frame, text="Profile Name:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.profile_name_var = tk.StringVar()
        ttk.Entry(profiles_frame, textvariable=self.profile_name_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Profile buttons
        profile_buttons = ttk.Frame(profiles_frame)
        profile_buttons.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(profile_buttons, text="Save Profile", command=self.save_config_profile).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(profile_buttons, text="Load Profile", command=self.load_config_profile).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(profile_buttons, text="Delete Profile", command=self.delete_config_profile).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(profile_buttons, text="Export Profile", command=self.export_config_profile).grid(row=0, column=3, padx=(0, 10))
        ttk.Button(profile_buttons, text="Import Profile", command=self.import_config_profile).grid(row=0, column=4)
        
        # Multi-Device Management Section
        devices_frame = ttk.LabelFrame(config_content, text="Multi-Device Management", padding="10")
        devices_frame.grid(row=8, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        devices_frame.columnconfigure(0, weight=1)
        devices_frame.rowconfigure(0, weight=1)
        
        # Device list
        device_list_frame = ttk.Frame(devices_frame)
        device_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        device_list_frame.columnconfigure(0, weight=1)
        device_list_frame.rowconfigure(0, weight=1)
        
        self.devices_tree = ttk.Treeview(device_list_frame, columns=("name", "type", "path", "status"), show="headings", height=6)
        self.devices_tree.heading("name", text="Device Name")
        self.devices_tree.heading("type", text="Type")
        self.devices_tree.heading("path", text="Connection")
        self.devices_tree.heading("status", text="Status")
        
        self.devices_tree.column("name", width=150)
        self.devices_tree.column("type", width=80)
        self.devices_tree.column("path", width=120)
        self.devices_tree.column("status", width=80)
        
        self.devices_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Device list scrollbar
        devices_scrollbar = ttk.Scrollbar(device_list_frame, orient="vertical", command=self.devices_tree.yview)
        devices_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.devices_tree.configure(yscrollcommand=devices_scrollbar.set)
        
        # Device management buttons
        device_buttons = ttk.Frame(devices_frame)
        device_buttons.grid(row=1, column=0, pady=(10, 0))
        
        ttk.Button(device_buttons, text="Scan Devices", command=self.scan_devices).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(device_buttons, text="Add Device", command=self.add_device).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(device_buttons, text="Remove Device", command=self.remove_device).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(device_buttons, text="Connect to Device", command=self.connect_to_selected_device).grid(row=0, column=3, padx=(0, 10))
        ttk.Button(device_buttons, text="Set Default", command=self.set_default_device).grid(row=0, column=4)
        
        # Initial device scan
        self.scan_devices()
        
    def get_device_info(self):
        """Get device information"""
        if not self.interface_manager.is_connected():
            return
            
        try:
            # Get device info from interface manager
            device_info = self.interface_manager.get_device_info()
            if device_info:
                # Update device info labels
                self.device_info_labels["Long Name"].config(text=device_info.get('long_name', 'N/A'))
                self.device_info_labels["Short Name"].config(text=device_info.get('short_name', 'N/A'))
                self.device_info_labels["Hardware"].config(text=device_info.get('hardware', 'N/A'))
                self.device_info_labels["Firmware"].config(text=device_info.get('firmware', 'N/A'))
                self.device_info_labels["Region"].config(text=device_info.get('region', 'N/A'))
                self.device_info_labels["Channel"].config(text=device_info.get('channel', 'N/A'))
                
                # Update input fields
                self.long_name_var.set(device_info.get('long_name', ''))
                self.short_name_var.set(device_info.get('short_name', ''))
                
                # Update region dropdown
                if device_info.get('region') in self.regions:
                    self.region_var.set(device_info.get('region'))
                
                # Update channel fields
                self.channel_name_var.set(device_info.get('channel', ''))
                
                # Update battery level
                if 'battery' in device_info:
                    self.battery_label.config(text=f"{device_info['battery']}%")
                
                # Update GPS status display
                self.update_gps_status_display()
                        
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            
    def update_node_info(self):
        """Update node information"""
        if not self.interface_manager.is_connected():
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        try:
            long_name = self.long_name_var.get().strip()
            short_name = self.short_name_var.get().strip()
            
            if long_name or short_name:
                success = self.interface_manager.update_node_info(long_name, short_name)
                if success:
                    messagebox.showinfo("Success", "Node information updated")
                else:
                    messagebox.showerror("Error", "Failed to update node information")
                    
        except Exception as e:
            logger.error(f"Error updating node info: {e}")
            messagebox.showerror("Error", f"Failed to update node info: {e}")
            
    def update_region(self):
        """Update device region setting"""
        if not self.interface_manager.is_connected():
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        selected_region = self.region_var.get()
        if not selected_region:
            messagebox.showwarning("Warning", "Please select a region")
            return
            
        try:
            success = self.interface_manager.update_region(selected_region)
            if success:
                messagebox.showinfo("Success", f"Region updated to {selected_region}.\n\nDevice will reboot to apply the new region setting.")
                # Update the display
                self.get_device_info()
            else:
                messagebox.showerror("Error", f"Failed to update region to {selected_region}")
                
        except Exception as e:
            logger.error(f"Error updating region: {e}")
            messagebox.showerror("Error", f"Failed to update region: {e}")
            
            # Provide helpful error message for common issues
            if "not connected" in str(e).lower():
                messagebox.showinfo("Help", "Make sure the device is connected and try again.")
            elif "permission" in str(e).lower():
                messagebox.showinfo("Help", "Region update requires a stable connection. Try reconnecting and ensure the device is not in sleep mode.")
            
    def reboot_device(self):
        """Reboot the device"""
        if not self.interface_manager.is_connected():
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to reboot the device?"):
            try:
                success = self.interface_manager.reboot_device()
                if success:
                    messagebox.showinfo("Success", "Device reboot initiated")
                else:
                    messagebox.showerror("Error", "Failed to reboot device")
            except Exception as e:
                logger.error(f"Error rebooting device: {e}")
                messagebox.showerror("Error", f"Failed to reboot device: {e}")
                
    def factory_reset(self):
        """Factory reset the device"""
        if not self.interface_manager.is_connected():
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to factory reset the device? This cannot be undone."):
            try:
                success = self.interface_manager.factory_reset()
                if success:
                    messagebox.showinfo("Success", "Factory reset initiated")
                else:
                    messagebox.showerror("Error", "Failed to factory reset device")
            except Exception as e:
                logger.error(f"Error factory resetting device: {e}")
                messagebox.showerror("Error", f"Failed to factory reset device: {e}")
                
    def save_config_profile(self):
        """Save current configuration as a profile"""
        try:
            profile_name = self.profile_name_var.get().strip()
            if not profile_name:
                messagebox.showwarning("Warning", "Please enter a profile name")
                return
            
            # Gather current configuration
            config = {
                'long_name': self.long_name_var.get(),
                'short_name': self.short_name_var.get(),
                'region': self.region_var.get(),
                'channel_name': self.channel_name_var.get(),
                'psk': self.psk_var.get(),
                'created_date': datetime.now().isoformat(),
                'description': f"Profile created from current settings"
            }
            
            # Save to database
            config_json = json.dumps(config)
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO config_profiles (profile_name, device_config, created_date, last_used)
                VALUES (?, ?, ?, ?)
            ''', (profile_name, config_json, datetime.now(), datetime.now()))
            
            conn.commit()
            conn.close()
            
            # Update profiles list
            self.load_config_profiles()
            self.profile_var.set(profile_name)
            self.current_profile = profile_name
            self.current_profile_label.config(text=profile_name)
            
            messagebox.showinfo("Profile Saved", f"Configuration profile '{profile_name}' saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving config profile: {e}")
            messagebox.showerror("Error", f"Failed to save configuration profile: {e}")
            
    def load_config_profile(self):
        """Load selected configuration profile"""
        try:
            profile_name = self.profile_var.get()
            if not profile_name:
                messagebox.showwarning("Warning", "Please select a profile to load")
                return
            
            if profile_name not in self.config_profiles:
                messagebox.showwarning("Warning", "Selected profile not found")
                return
            
            config = self.config_profiles[profile_name]
            
            # Apply configuration
            self.long_name_var.set(config.get('long_name', ''))
            self.short_name_var.set(config.get('short_name', ''))
            self.region_var.set(config.get('region', ''))
            self.channel_name_var.set(config.get('channel_name', ''))
            self.psk_var.set(config.get('psk', ''))
            
            # Update current profile
            self.current_profile = profile_name
            self.current_profile_label.config(text=profile_name)
            
            # Update last used timestamp
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE config_profiles SET last_used = ? WHERE profile_name = ?
            ''', (datetime.now(), profile_name))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Profile Loaded", f"Configuration profile '{profile_name}' loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading config profile: {e}")
            messagebox.showerror("Error", f"Failed to load configuration profile: {e}")
            
    def delete_config_profile(self):
        """Delete selected configuration profile"""
        try:
            profile_name = self.profile_var.get()
            if not profile_name:
                messagebox.showwarning("Warning", "Please select a profile to delete")
                return
            
            if profile_name == "Default":
                messagebox.showwarning("Warning", "Cannot delete the default profile")
                return
            
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete profile '{profile_name}'?"):
                # Delete from database
                conn = sqlite3.connect(self.data_logger.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM config_profiles WHERE profile_name = ?', (profile_name,))
                conn.commit()
                conn.close()
                
                # Update profiles list
                self.load_config_profiles()
                self.profile_var.set("Default")
                
                messagebox.showinfo("Profile Deleted", f"Configuration profile '{profile_name}' deleted successfully")
                
        except Exception as e:
            logger.error(f"Error deleting config profile: {e}")
            messagebox.showerror("Error", f"Failed to delete configuration profile: {e}")
            
    def export_config_profile(self):
        """Export configuration profile to file"""
        try:
            profile_name = self.profile_var.get()
            if not profile_name:
                messagebox.showwarning("Warning", "Please select a profile to export")
                return
            
            if profile_name not in self.config_profiles:
                messagebox.showwarning("Warning", "Selected profile not found")
                return
            
            config = self.config_profiles[profile_name]
            
            # Add export metadata
            export_data = {
                'profile_name': profile_name,
                'config': config,
                'export_date': datetime.now().isoformat(),
                'exported_by': 'MeshtasticUI'
            }
            
            # Save to file
            filename = f"exports/meshtastic_profile_{profile_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo("Export Complete", f"Profile exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting config profile: {e}")
            messagebox.showerror("Error", f"Failed to export configuration profile: {e}")
            
    def import_config_profile(self):
        """Import configuration profile from file"""
        try:
            # Select file
            filename = filedialog.askopenfilename(
                title="Import Configuration Profile",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not filename:
                return
            
            # Load and validate file
            with open(filename, 'r') as f:
                import_data = json.load(f)
            
            if 'profile_name' not in import_data or 'config' not in import_data:
                messagebox.showerror("Error", "Invalid profile file format")
                return
            
            profile_name = import_data['profile_name']
            config = import_data['config']
            
            # Check if profile already exists
            if profile_name in self.config_profiles:
                if not messagebox.askyesno("Profile Exists", f"Profile '{profile_name}' already exists. Overwrite?"):
                    return
            
            # Save to database
            config_json = json.dumps(config)
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO config_profiles (profile_name, device_config, created_date, last_used)
                VALUES (?, ?, ?, ?)
            ''', (profile_name, config_json, datetime.now(), datetime.now()))
            
            conn.commit()
            conn.close()
            
            # Update profiles list
            self.load_config_profiles()
            self.profile_var.set(profile_name)
            
            messagebox.showinfo("Import Complete", f"Configuration profile '{profile_name}' imported successfully")
            
        except Exception as e:
            logger.error(f"Error importing config profile: {e}")
            messagebox.showerror("Error", f"Failed to import configuration profile: {e}")
            
    def load_config_profiles(self):
        """Load configuration profiles from database"""
        try:
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT profile_name, device_config FROM config_profiles')
            profiles = cursor.fetchall()
            conn.close()
            
            self.config_profiles = {}
            profile_names = ["Default"]
            
            for profile_name, config_json in profiles:
                if profile_name not in ["emergency_contacts", "medical_info", "managed_devices", "default_device"]:
                    try:
                        config = json.loads(config_json)
                        self.config_profiles[profile_name] = config
                        profile_names.append(profile_name)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in profile: {profile_name}")
            
            # Update combo box
            self.profile_combo.configure(values=profile_names)
            
        except Exception as e:
            logger.error(f"Error loading config profiles: {e}")
            
    def on_profile_selected(self, event=None):
        """Handle profile selection"""
        # This method is called when a profile is selected from the combo box
        pass
        
    def scan_devices(self):
        """Scan for available Meshtastic devices"""
        try:
            # Import meshtastic here to avoid circular imports
            try:
                import meshtastic
                import meshtastic.util
            except ImportError:
                messagebox.showwarning("Warning", "Meshtastic library not available")
                return
            
            # Clear existing devices
            for item in self.devices_tree.get_children():
                self.devices_tree.delete(item)
            
            # Add existing managed devices
            for device in self.managed_devices:
                self.devices_tree.insert("", tk.END, values=(
                    device['name'],
                    device['type'],
                    device['path'],
                    device.get('status', 'Unknown')
                ))
            
            # Scan for serial devices
            try:
                ports = meshtastic.util.findPorts(True)
                for port in ports:
                    # Check if this port is already in managed devices
                    existing = any(d['path'] == port for d in self.managed_devices)
                    if not existing:
                        self.devices_tree.insert("", tk.END, values=(
                            f"Meshtastic Device",
                            "Serial",
                            port,
                            "Available"
                        ))
            except Exception as e:
                logger.debug(f"Error scanning serial ports: {e}")
            
            # Add common TCP connections
            tcp_hosts = ["localhost", "192.168.1.1", "meshtastic.local"]
            for host in tcp_hosts:
                existing = any(d['path'] == host and d['type'] == 'TCP' for d in self.managed_devices)
                if not existing:
                    self.devices_tree.insert("", tk.END, values=(
                        f"TCP Device",
                        "TCP",
                        host,
                        "Unknown"
                    ))
            
        except Exception as e:
            logger.error(f"Error scanning devices: {e}")
            messagebox.showerror("Error", f"Failed to scan devices: {e}")
            
    def add_device(self):
        """Add a device to managed devices list"""
        try:
            name = simpledialog.askstring("Add Device", "Enter device name:")
            if not name:
                return
            
            conn_type = simpledialog.askstring("Add Device", "Enter connection type (Serial/TCP):")
            if not conn_type:
                return
            
            path = simpledialog.askstring("Add Device", "Enter device path/IP:")
            if not path:
                return
            
            device = {
                'name': name,
                'type': conn_type,
                'path': path,
                'status': 'Added',
                'added_date': datetime.now().isoformat()
            }
            
            self.managed_devices.append(device)
            self.save_managed_devices()
            self.scan_devices()
            
            messagebox.showinfo("Device Added", f"Device '{name}' added successfully")
            
        except Exception as e:
            logger.error(f"Error adding device: {e}")
            messagebox.showerror("Error", f"Failed to add device: {e}")
            
    def remove_device(self):
        """Remove selected device from managed devices"""
        try:
            selection = self.devices_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a device to remove")
                return
            
            item = self.devices_tree.item(selection[0])
            device_name = item['values'][0]
            device_path = item['values'][2]
            
            # Remove from managed devices
            self.managed_devices = [d for d in self.managed_devices 
                                   if not (d['name'] == device_name and d['path'] == device_path)]
            
            self.save_managed_devices()
            self.scan_devices()
            
            messagebox.showinfo("Device Removed", f"Device '{device_name}' removed successfully")
            
        except Exception as e:
            logger.error(f"Error removing device: {e}")
            messagebox.showerror("Error", f"Failed to remove device: {e}")
            
    def connect_to_selected_device(self):
        """Connect to selected device"""
        try:
            selection = self.devices_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a device to connect to")
                return
            
            item = self.devices_tree.item(selection[0])
            device_type = item['values'][1]
            device_path = item['values'][2]
            
            # Notify the interface manager to connect
            self.interface_manager.connect_to_device(device_type, device_path)
            
        except Exception as e:
            logger.error(f"Error connecting to selected device: {e}")
            messagebox.showerror("Error", f"Failed to connect to selected device: {e}")
            
    def set_default_device(self):
        """Set selected device as default"""
        try:
            selection = self.devices_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a device to set as default")
                return
            
            item = self.devices_tree.item(selection[0])
            device_name = item['values'][0]
            device_type = item['values'][1]
            device_path = item['values'][2]
            
            # Save as default in a profile
            default_config = {
                'connection_type': device_type,
                'connection_param': device_path,
                'device_name': device_name,
                'set_as_default': True,
                'created_date': datetime.now().isoformat()
            }
            
            config_json = json.dumps(default_config)
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO config_profiles (profile_name, device_config, created_date, last_used)
                VALUES (?, ?, ?, ?)
            ''', ("default_device", config_json, datetime.now(), datetime.now()))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Default Device", f"Device '{device_name}' set as default")
            
        except Exception as e:
            logger.error(f"Error setting default device: {e}")
            messagebox.showerror("Error", f"Failed to set default device: {e}")
            
    def save_managed_devices(self):
        """Save managed devices to database"""
        try:
            devices_json = json.dumps(self.managed_devices)
            
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO config_profiles (profile_name, device_config, created_date, last_used)
                VALUES (?, ?, ?, ?)
            ''', ("managed_devices", devices_json, datetime.now(), datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving managed devices: {e}")
            
    def load_managed_devices(self):
        """Load managed devices from database"""
        try:
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT device_config FROM config_profiles 
                WHERE profile_name = ?
            ''', ("managed_devices",))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                self.managed_devices = json.loads(result[0])
            else:
                self.managed_devices = []
                
        except Exception as e:
            logger.error(f"Error loading managed devices: {e}")
            self.managed_devices = []
            
    def toggle_gps(self):
        """Toggle GPS enabled/disabled"""
        if not self.interface_manager.is_connected():
            messagebox.showwarning("Warning", "Please connect to a device first")
            self.gps_enabled_var.set(False)  # Reset checkbox
            return
            
        try:
            enabled = self.gps_enabled_var.get()
            
            # Send GPS enable/disable command to device
            success = self.interface_manager.set_gps_enabled(enabled)
            
            if success:
                status = "enabled" if enabled else "disabled"
                messagebox.showinfo("GPS Settings", f"GPS {status} successfully")
                self.update_gps_status_display()
            else:
                messagebox.showerror("Error", f"Failed to {'enable' if enabled else 'disable'} GPS")
                self.gps_enabled_var.set(not enabled)  # Reset checkbox
                
        except Exception as e:
            logger.error(f"Error toggling GPS: {e}")
            messagebox.showerror("Error", f"Failed to toggle GPS: {e}")
            self.gps_enabled_var.set(not self.gps_enabled_var.get())  # Reset checkbox
            
    def update_gps_interval(self):
        """Update GPS update interval"""
        if not self.interface_manager.is_connected():
            messagebox.showwarning("Warning", "Please connect to a device first")
            return
            
        try:
            interval = int(self.gps_interval_var.get())
            if interval < 1 or interval > 3600:
                messagebox.showwarning("Warning", "GPS update interval must be between 1 and 3600 seconds")
                return
                
            # Send GPS interval command to device
            success = self.interface_manager.set_gps_interval(interval)
            
            if success:
                messagebox.showinfo("GPS Settings", f"GPS update interval set to {interval} seconds")
                self.update_gps_status_display()
            else:
                messagebox.showerror("Error", "Failed to update GPS interval")
                
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid number for GPS interval")
        except Exception as e:
            logger.error(f"Error updating GPS interval: {e}")
            messagebox.showerror("Error", f"Failed to update GPS interval: {e}")
            
    def update_gps_broadcast(self):
        """Update GPS broadcast interval"""
        if not self.interface_manager.is_connected():
            messagebox.showwarning("Warning", "Please connect to a device first")
            return
            
        try:
            interval = int(self.gps_broadcast_var.get())
            if interval < 30 or interval > 86400:  # 30 seconds to 24 hours
                messagebox.showwarning("Warning", "GPS broadcast interval must be between 30 and 86400 seconds")
                return
                
            # Send GPS broadcast interval command to device
            success = self.interface_manager.set_gps_broadcast_interval(interval)
            
            if success:
                messagebox.showinfo("GPS Settings", f"GPS broadcast interval set to {interval} seconds")
                self.update_gps_status_display()
            else:
                messagebox.showerror("Error", "Failed to update GPS broadcast interval")
                
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid number for GPS broadcast interval")
        except Exception as e:
            logger.error(f"Error updating GPS broadcast interval: {e}")
            messagebox.showerror("Error", f"Failed to update GPS broadcast interval: {e}")
            
    def update_gps_status_display(self):
        """Update GPS status display"""
        if not self.interface_manager.is_connected():
            self.gps_status_display.config(text="N/A", foreground="gray")
            self.gps_enabled_var.set(False)
            return
            
        try:
            # Get GPS status from interface manager
            gps_status = self.interface_manager.get_gps_status()
            
            if gps_status:
                status = gps_status.get('status', 'unknown')
                satellites = gps_status.get('satellites', 0)
                fix = gps_status.get('fix', False)
                
                if status == 'fixed':
                    self.gps_status_display.config(text=f"Fixed ({satellites} sats)", foreground="green")
                    self.gps_enabled_var.set(True)
                elif status == 'searching':
                    self.gps_status_display.config(text=f"Searching ({satellites} sats)", foreground="orange")
                    self.gps_enabled_var.set(True)
                elif status == 'no_signal':
                    self.gps_status_display.config(text="No Signal", foreground="red")
                    self.gps_enabled_var.set(True)
                elif status == 'disabled':
                    self.gps_status_display.config(text="Disabled", foreground="gray")
                    self.gps_enabled_var.set(False)
                else:
                    self.gps_status_display.config(text="Unknown", foreground="gray")
                    self.gps_enabled_var.set(False)
            else:
                self.gps_status_display.config(text="N/A", foreground="gray")
                self.gps_enabled_var.set(False)
                
        except Exception as e:
            logger.debug(f"Error updating GPS status display: {e}")
            self.gps_status_display.config(text="Error", foreground="red") 