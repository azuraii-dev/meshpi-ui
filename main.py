#!/usr/bin/env python3
"""
Meshtastic UI - A comprehensive interface for Meshtastic mesh networking
Features: Map view, Chat interface, and Configuration panel
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import queue
import json
from datetime import datetime
import logging
import requests
import os
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import meshtastic
    import meshtastic.serial_interface
    import meshtastic.tcp_interface
    import meshtastic.util
    from pubsub import pub
    MESHTASTIC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Meshtastic library not available: {e}")
    MESHTASTIC_AVAILABLE = False

try:
    import tkintermapview
    MAPVIEW_AVAILABLE = True
except ImportError as e:
    logger.warning(f"tkintermapview not available, using coordinate plot fallback: {e}")
    MAPVIEW_AVAILABLE = False

class MeshtasticUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Meshtastic UI")
        self.root.geometry("1200x800")
        
        # Initialize variables
        self.interface = None
        self.connection_status = "Disconnected"
        self.nodes = {}
        self.message_queue = queue.Queue()
        
        # Map-related variables
        self.map_widget = None
        self.coordinate_canvas = None
        self.map_markers = {}
        self.use_real_map = False
        self.internet_available = False
        
        # Setup UI
        self.create_widgets()
        self.setup_meshtastic_events()
        
        # Start message processing thread
        self.start_message_thread()
        
        # Update status periodically
        self.update_status()
        
        # Check internet connectivity and initialize map
        self.check_internet_connectivity()
        
    def check_internet_connectivity(self):
        """Check if internet is available for map tiles"""
        def check_connectivity():
            try:
                # Try to reach OpenStreetMap with proper headers
                logger.info("Checking internet connectivity to OpenStreetMap...")
                headers = {
                    'User-Agent': 'MeshtasticUI/1.0 (Educational/Research Use)'
                }
                # Try a simple tile request instead of the main page
                response = requests.get("https://tile.openstreetmap.org/0/0/0.png", 
                                      headers=headers, timeout=10)
                logger.info(f"Response status code: {response.status_code}")
                self.internet_available = response.status_code == 200
                logger.info(f"Internet connectivity: {'Available' if self.internet_available else 'Unavailable'}")
            except Exception as e:
                self.internet_available = False
                logger.info(f"No internet connectivity: {e}")
                
            # Determine map type to use
            self.use_real_map = MAPVIEW_AVAILABLE and self.internet_available
            logger.info(f"Using {'real map' if self.use_real_map else 'coordinate plot'}")
            
        threading.Thread(target=check_connectivity, daemon=True).start()
            
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS coordinates in kilometers"""
        if None in (lat1, lon1, lat2, lon2):
            return None
            
        # Haversine formula
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    def create_widgets(self):
        """Create the main UI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
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
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
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
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_meshtastic)
        self.connect_btn.grid(row=0, column=4, padx=(0, 10))
        
        self.disconnect_btn = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect_meshtastic, state="disabled")
        self.disconnect_btn.grid(row=0, column=5)
        
        # Status indicator
        self.status_label = ttk.Label(conn_frame, text="Status: Disconnected", foreground="red")
        self.status_label.grid(row=0, column=6, padx=(20, 0))
        
    def create_main_content(self, parent):
        """Create the main tabbed interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create tabs
        self.create_map_tab()
        self.create_chat_tab()
        self.create_config_tab()
        
    def create_map_tab(self):
        """Create map visualization tab with real map or coordinate plot fallback"""
        map_frame = ttk.Frame(self.notebook)
        self.notebook.add(map_frame, text="Map")
        
        # Configure grid
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(0, weight=1)
        
        # Create map content
        map_content = ttk.Frame(map_frame, padding="10")
        map_content.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        map_content.columnconfigure(1, weight=1)
        map_content.rowconfigure(1, weight=1)
        
        # Nodes list
        ttk.Label(map_content, text="Nodes in Mesh:").grid(row=0, column=0, sticky=tk.W)
        
        # Node list frame
        nodes_frame = ttk.Frame(map_content)
        nodes_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        nodes_frame.columnconfigure(0, weight=1)
        nodes_frame.rowconfigure(0, weight=1)
        
        # Nodes treeview
        self.nodes_tree = ttk.Treeview(nodes_frame, columns=("name", "id", "distance", "battery", "last_heard"), show="headings")
        self.nodes_tree.heading("name", text="Name")
        self.nodes_tree.heading("id", text="ID")
        self.nodes_tree.heading("distance", text="Distance")
        self.nodes_tree.heading("battery", text="Battery")
        self.nodes_tree.heading("last_heard", text="Last Heard")
        
        # Configure column widths
        self.nodes_tree.column("name", width=100)
        self.nodes_tree.column("id", width=100)
        self.nodes_tree.column("distance", width=80)
        self.nodes_tree.column("battery", width=80)
        self.nodes_tree.column("last_heard", width=120)
        
        self.nodes_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for nodes
        nodes_scrollbar = ttk.Scrollbar(nodes_frame, orient="vertical", command=self.nodes_tree.yview)
        nodes_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.nodes_tree.configure(yscrollcommand=nodes_scrollbar.set)
        
        # Map visualization area
        self.map_viz_frame = ttk.LabelFrame(map_content, text="Map Visualization", padding="10")
        self.map_viz_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.map_viz_frame.columnconfigure(0, weight=1)
        self.map_viz_frame.rowconfigure(0, weight=1)
        
        # Initialize map after a short delay to allow connectivity check to complete
        self.root.after(1000, self.initialize_map)
        
    def initialize_map(self):
        """Initialize either real map or coordinate plot based on availability"""
        try:
            if self.use_real_map:
                self.create_real_map()
            else:
                self.create_coordinate_plot()
        except Exception as e:
            logger.error(f"Error initializing map: {e}")
            # Fallback to coordinate plot if real map fails
            if self.use_real_map:
                logger.info("Falling back to coordinate plot")
                self.use_real_map = False
                self.create_coordinate_plot()
                
    def create_real_map(self):
        """Create real map using tkintermapview"""
        logger.info("Creating real map (online mode - caching not available in current tkintermapview version)")
        
        # Create map widget (online mode)
        self.map_widget = tkintermapview.TkinterMapView(
            self.map_viz_frame,
            width=400,
            height=400,
            corner_radius=0
        )
        
        # Configure tile caching for offline use
        self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=19)
        
        # Set initial position (will be updated when nodes are found)
        self.map_widget.set_position(37.7749, -122.4194)  # San Francisco as default
        self.map_widget.set_zoom(10)
        
        self.map_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Update frame title  
        self.map_viz_frame.config(text="Map Visualization (OpenStreetMap - Online Only)")
        
    def create_coordinate_plot(self):
        """Create simple coordinate plot as fallback"""
        logger.info("Creating coordinate plot fallback")
        
        self.coordinate_canvas = tk.Canvas(self.map_viz_frame, bg="lightgray", width=400, height=400)
        self.coordinate_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add grid lines
        self.draw_coordinate_grid()
        
        # Add instructions
        self.coordinate_canvas.create_text(200, 50, text="Coordinate Plot\n(No internet/map tiles)", 
                                         justify=tk.CENTER, font=("Arial", 10), fill="darkblue")
        
        # Update frame title
        title = "Map Visualization (Coordinate Plot"
        if not self.internet_available:
            title += " - Offline"
        elif not MAPVIEW_AVAILABLE:
            title += " - Map library unavailable"
        title += ")"
        self.map_viz_frame.config(text=title)
        
    def draw_coordinate_grid(self):
        """Draw grid lines on coordinate plot"""
        if not self.coordinate_canvas:
            return
            
        canvas = self.coordinate_canvas
        width = 400
        height = 400
        
        # Clear existing grid
        canvas.delete("grid")
        
        # Draw grid lines
        for i in range(0, width, 50):
            canvas.create_line(i, 0, i, height, fill="lightblue", width=1, tags="grid")
        for i in range(0, height, 50):
            canvas.create_line(0, i, width, i, fill="lightblue", width=1, tags="grid")
            
        # Draw center lines
        canvas.create_line(width//2, 0, width//2, height, fill="blue", width=2, tags="grid")
        canvas.create_line(0, height//2, width, height//2, fill="blue", width=2, tags="grid")

    def create_chat_tab(self):
        """Create chat interface tab"""
        chat_frame = ttk.Frame(self.notebook)
        self.notebook.add(chat_frame, text="Chat")
        
        # Configure grid
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)
        
        # Create chat content
        chat_content = ttk.Frame(chat_frame, padding="10")
        chat_content.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        chat_content.columnconfigure(0, weight=1)
        chat_content.rowconfigure(0, weight=1)
        
        # Message display area
        self.message_display = scrolledtext.ScrolledText(chat_content, wrap=tk.WORD, height=20)
        self.message_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.message_display.config(state=tk.DISABLED)
        
        # Message input frame
        input_frame = ttk.Frame(chat_content)
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        input_frame.columnconfigure(0, weight=1)
        
        # Destination selection
        dest_frame = ttk.Frame(input_frame)
        dest_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        dest_frame.columnconfigure(1, weight=1)
        
        ttk.Label(dest_frame, text="To:").grid(row=0, column=0, padx=(0, 10))
        
        self.destination = tk.StringVar(value="Broadcast")
        dest_combo = ttk.Combobox(dest_frame, textvariable=self.destination, 
                                 values=["Broadcast"], state="readonly")
        dest_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Message input
        msg_frame = ttk.Frame(input_frame)
        msg_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        msg_frame.columnconfigure(0, weight=1)
        
        self.message_entry = ttk.Entry(msg_frame, font=("Arial", 12))
        self.message_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        
        self.send_btn = ttk.Button(msg_frame, text="Send", command=self.send_message)
        self.send_btn.grid(row=0, column=1)
        
        # Message controls
        controls_frame = ttk.Frame(input_frame)
        controls_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.want_ack = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_frame, text="Request ACK", variable=self.want_ack).grid(row=0, column=0)
        
        ttk.Button(controls_frame, text="Clear Chat", command=self.clear_chat).grid(row=0, column=1, padx=(10, 0))
        
    def create_config_tab(self):
        """Create configuration tab"""
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Config")
        
        # Configure grid
        config_frame.columnconfigure(0, weight=1)
        config_frame.rowconfigure(0, weight=1)
        
        # Create scrollable content
        config_canvas = tk.Canvas(config_frame)
        config_scrollbar = ttk.Scrollbar(config_frame, orient="vertical", command=config_canvas.yview)
        config_content = ttk.Frame(config_canvas)
        
        config_content.bind('<Configure>', lambda e: config_canvas.configure(scrollregion=config_canvas.bbox("all")))
        
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
        self.regions = [
            "ANZ",      # Australia/New Zealand
            "CN",       # China
            "EU_433",   # Europe 433MHz
            "EU_868",   # Europe 868MHz
            "IN",       # India
            "JP",       # Japan
            "KR",       # Korea
            "MY_433",   # Malaysia 433MHz
            "MY_919",   # Malaysia 919MHz
            "NZ_865",   # New Zealand 865MHz
            "RU",       # Russia
            "SG_923",   # Singapore
            "TH",       # Thailand
            "TW",       # Taiwan
            "UA_433",   # Ukraine 433MHz
            "UA_868",   # Ukraine 868MHz
            "US"        # United States
        ]
        
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
        
        # Actions frame
        actions_frame = ttk.LabelFrame(config_content, text="Actions", padding="10")
        actions_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # Action buttons
        ttk.Button(actions_frame, text="Reboot Device", command=self.reboot_device).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(actions_frame, text="Factory Reset", command=self.factory_reset).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(actions_frame, text="Get Device Info", command=self.get_device_info).grid(row=0, column=2, padx=5, pady=2)
        
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(1, weight=1)
        
        # Status elements
        self.status_text = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_text).grid(row=0, column=0, sticky=tk.W)
        
        # Node count
        self.node_count_text = tk.StringVar(value="Nodes: 0")
        ttk.Label(status_frame, textvariable=self.node_count_text).grid(row=0, column=1, sticky=tk.E)
        
    def setup_meshtastic_events(self):
        """Setup Meshtastic event handlers"""
        if not MESHTASTIC_AVAILABLE:
            return
            
        # Subscribe to Meshtastic events
        pub.subscribe(self.on_receive_message, "meshtastic.receive")
        pub.subscribe(self.on_connection_established, "meshtastic.connection.established")
        pub.subscribe(self.on_connection_lost, "meshtastic.connection.lost")
        pub.subscribe(self.on_node_updated, "meshtastic.node.updated")
        
    def connect_meshtastic(self):
        """Connect to Meshtastic device"""
        if not MESHTASTIC_AVAILABLE:
            messagebox.showerror("Error", "Meshtastic library not available")
            return
            
        def connect_thread():
            try:
                self.update_status("Connecting...")
                self.status_label.config(text="Status: Connecting...", foreground="orange")
                
                conn_type = self.connection_type.get()
                param = self.connection_param.get()
                
                if conn_type == "Serial":
                    # Check for available ports first
                    if param.lower() == "auto":
                        ports = meshtastic.util.findPorts(True)
                        if not ports:
                            raise Exception("No Meshtastic devices found on serial ports.\n\nPlease check:\n• Device is connected via USB\n• Device is powered on\n• USB cable supports data transfer\n• Device drivers are installed")
                        self.interface = meshtastic.serial_interface.SerialInterface()
                    else:
                        try:
                            self.interface = meshtastic.serial_interface.SerialInterface(devPath=param)
                        except Exception as serial_error:
                            raise Exception(f"Failed to connect to serial device '{param}'.\n\nPlease check:\n• Device path is correct\n• Device is connected and powered on\n• You have permission to access the device\n• Device is not in use by another application\n\nOriginal error: {serial_error}")
                elif conn_type == "TCP":
                    if param.lower() == "auto":
                        param = "localhost"
                    try:
                        self.interface = meshtastic.tcp_interface.TCPInterface(hostname=param)
                    except Exception as tcp_error:
                        raise Exception(f"Failed to connect to TCP host '{param}'.\n\nPlease check:\n• Host is reachable\n• Port 4403 is open\n• Meshtastic device has network module enabled\n• IP address/hostname is correct\n\nOriginal error: {tcp_error}")
                
                # Validate the connection by checking if we can access basic properties
                if not self.validate_connection():
                    raise Exception("Connection established but device is not responding properly.\n\nThis could indicate:\n• Device is not a Meshtastic device\n• Device firmware is incompatible\n• Device is not fully initialized\n\nTry disconnecting and reconnecting the device.")
                
                self.update_status("Connected")
                self.root.after(0, self.on_connect_success)
                
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                self.update_status("Connection failed")
                error_message = str(e)
                self.root.after(0, lambda: self.on_connect_failed(error_message))
                
        threading.Thread(target=connect_thread, daemon=True).start()
        
    def validate_connection(self):
        """Validate that the connection is working properly"""
        try:
            # For serial connections, check if the interface has a proper stream
            if hasattr(self.interface, 'stream') and self.interface.stream is None:
                return False
                
            # Try to access basic interface properties to ensure it's properly initialized
            if not hasattr(self.interface, 'localNode'):
                return False
                
            # Wait a moment for the interface to initialize
            time.sleep(0.5)
            
            # Try to send a heartbeat to test the connection
            if hasattr(self.interface, 'sendHeartbeat'):
                self.interface.sendHeartbeat()
                
            return True
            
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False
        
    def disconnect_meshtastic(self):
        """Disconnect from Meshtastic device"""
        if self.interface:
            try:
                # Check if the interface has a proper close method and stream
                if hasattr(self.interface, 'close') and hasattr(self.interface, 'stream'):
                    self.interface.close()
                self.interface = None
                self.update_status("Disconnected")
                self.on_disconnect()
            except Exception as e:
                logger.error(f"Disconnect error: {e}")
                # Force cleanup even if close fails
                self.interface = None
                self.update_status("Disconnected")
                self.on_disconnect()
                
    def on_connect_success(self):
        """Handle successful connection"""
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.status_label.config(text="Status: Connected", foreground="green")
        
        # Update device info
        self.get_device_info()
        
    def on_connect_failed(self, error_message):
        """Handle failed connection"""
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.status_label.config(text="Status: Connection Failed", foreground="red")
        messagebox.showerror("Connection Error", error_message)
        
    def on_disconnect(self):
        """Handle disconnection"""
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.status_label.config(text="Status: Disconnected", foreground="red")
        
        # Clear data
        self.nodes.clear()
        self.update_nodes_display()
        
    def on_receive_message(self, packet, interface):
        """Handle received message"""
        self.message_queue.put(('message', packet))
        
    def on_connection_established(self, interface):
        """Handle connection established"""
        self.message_queue.put(('connection_established', None))
        
    def on_connection_lost(self, interface):
        """Handle connection lost"""
        self.message_queue.put(('connection_lost', None))
        
    def on_node_updated(self, node, interface):
        """Handle node update"""
        self.message_queue.put(('node_updated', node))
        
    def start_message_thread(self):
        """Start thread to process messages"""
        def process_messages():
            while True:
                try:
                    msg_type, data = self.message_queue.get(timeout=0.1)
                    self.root.after(0, self.handle_message, msg_type, data)
                except queue.Empty:
                    continue
                    
        threading.Thread(target=process_messages, daemon=True).start()
        
    def handle_message(self, msg_type, data):
        """Handle messages in main thread"""
        if msg_type == 'message':
            self.display_message(data)
        elif msg_type == 'node_updated':
            self.update_node_data(data)
        elif msg_type == 'connection_established':
            self.update_status("Connection established")
        elif msg_type == 'connection_lost':
            self.update_status("Connection lost")
            
    def display_message(self, packet):
        """Display received message in chat"""
        try:
            # Extract message info
            from_id = packet.get('fromId', 'Unknown')
            to_id = packet.get('toId', 'Unknown')
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Get message text
            message_text = ""
            if 'decoded' in packet:
                decoded = packet['decoded']
                if 'text' in decoded:
                    message_text = decoded['text']
                elif 'payload' in decoded:
                    message_text = f"[Binary data: {len(decoded['payload'])} bytes]"
                    
            # Format message
            msg_line = f"[{timestamp}] {from_id} -> {to_id}: {message_text}\n"
            
            # Add to display
            self.message_display.config(state=tk.NORMAL)
            self.message_display.insert(tk.END, msg_line)
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error displaying message: {e}")
            
    def send_message(self):
        """Send message through Meshtastic"""
        if not self.interface:
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        # Validate that the interface has the required methods
        if not hasattr(self.interface, 'sendText'):
            messagebox.showwarning("Warning", "Interface not properly initialized")
            return
            
        message = self.message_entry.get().strip()
        if not message:
            return
            
        try:
            # Send message
            dest = self.destination.get()
            want_ack = self.want_ack.get()
            
            if dest == "Broadcast":
                dest = "^all"
                
            self.interface.sendText(message, destinationId=dest, wantAck=want_ack)
            
            # Display sent message
            timestamp = datetime.now().strftime("%H:%M:%S")
            msg_line = f"[{timestamp}] You -> {dest}: {message}\n"
            
            self.message_display.config(state=tk.NORMAL)
            self.message_display.insert(tk.END, msg_line)
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
            
            # Clear input
            self.message_entry.delete(0, tk.END)
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            messagebox.showerror("Error", f"Failed to send message: {e}")
            
    def clear_chat(self):
        """Clear chat display"""
        self.message_display.config(state=tk.NORMAL)
        self.message_display.delete(1.0, tk.END)
        self.message_display.config(state=tk.DISABLED)
        
    def update_node_data(self, node):
        """Update node data"""
        if not node:
            return
            
        node_id = node.get('num', 'Unknown')
        self.nodes[node_id] = node
        self.update_nodes_display()
        
    def update_nodes_display(self):
        """Update nodes tree display and map"""
        # Clear existing items
        for item in self.nodes_tree.get_children():
            self.nodes_tree.delete(item)
            
        # Get local node position for distance calculations
        local_position = None
        if self.interface and hasattr(self.interface, 'localNode'):
            try:
                local_node_info = self.interface.getMyNodeInfo()
                if local_node_info and 'position' in local_node_info:
                    pos = local_node_info['position']
                    if 'latitude' in pos and 'longitude' in pos:
                        local_position = (pos['latitude'], pos['longitude'])
            except Exception as e:
                logger.debug(f"Could not get local position: {e}")
            
        # Add local device first (if connected and has GPS)
        local_device_position = self.get_local_device_position()
        if local_device_position:
            try:
                lat, lon, name = local_device_position
                
                # Get battery info for local device
                battery = "N/A"
                if self.interface and hasattr(self.interface, 'getMyNodeInfo'):
                    try:
                        node_info = self.interface.getMyNodeInfo()
                        if node_info and 'deviceMetrics' in node_info:
                            device_metrics = node_info['deviceMetrics']
                            if 'batteryLevel' in device_metrics:
                                battery = f"{device_metrics['batteryLevel']}%"
                    except Exception as e:
                        logger.debug(f"Could not get local device battery: {e}")
                
                # Add local device to tree
                self.nodes_tree.insert("", tk.END, values=(f"📍 {name} (You)", "LOCAL", "0m", battery, "Connected"))
                
            except Exception as e:
                logger.error(f"Error adding local device to display: {e}")
        
        # Add remote nodes
        for node_id, node in self.nodes.items():
            try:
                # Extract node info
                user = node.get('user', {})
                name = user.get('longName', 'Unknown')
                short_name = user.get('shortName', 'N/A')
                
                # Position info and distance calculation
                position = node.get('position', {})
                distance = "N/A"
                
                if 'latitude' in position and 'longitude' in position and local_position:
                    node_lat = position['latitude']
                    node_lon = position['longitude']
                    dist_km = self.calculate_distance(local_position[0], local_position[1], node_lat, node_lon)
                    if dist_km is not None:
                        if dist_km < 1:
                            distance = f"{dist_km * 1000:.0f}m"
                        else:
                            distance = f"{dist_km:.1f}km"
                
                # Battery info
                device_metrics = node.get('deviceMetrics', {})
                battery = device_metrics.get('batteryLevel', 'N/A')
                if battery != 'N/A':
                    battery = f"{battery}%"
                    
                # Last heard
                last_heard = node.get('lastHeard', 'N/A')
                if last_heard != 'N/A':
                    last_heard = datetime.fromtimestamp(last_heard).strftime("%H:%M:%S")
                    
                # Add to tree
                self.nodes_tree.insert("", tk.END, values=(name, short_name, distance, battery, last_heard))
                
            except Exception as e:
                logger.error(f"Error updating node display: {e}")
                
        # Update node count (include local device if it has GPS)
        total_nodes = len(self.nodes)
        if self.get_local_device_position():
            total_nodes += 1
        self.node_count_text.set(f"Nodes: {total_nodes}")
        
        # Update map with nodes
        self.update_map_nodes()
        
        # Update destination combo
        destinations = ["Broadcast"]
        for node in self.nodes.values():
            user = node.get('user', {})
            if 'longName' in user:
                destinations.append(user['longName'])
                
        # Update destination combo values
        dest_widget = None
        for child in self.root.winfo_children():
            if hasattr(child, 'winfo_children'):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, ttk.Combobox) and grandchild.get() in ["Broadcast"] + list(self.nodes.keys()):
                        dest_widget = grandchild
                        break
                        
        if dest_widget:
            dest_widget.configure(values=destinations)
            
    def get_local_device_position(self):
        """Get the GPS position of the local device if available"""
        if not self.interface or not hasattr(self.interface, 'localNode'):
            return None
            
        try:
            # Get local node information
            local_node_info = self.interface.getMyNodeInfo()
            if local_node_info and 'position' in local_node_info:
                pos = local_node_info['position']
                if 'latitude' in pos and 'longitude' in pos:
                    lat = pos['latitude']
                    lon = pos['longitude']
                    
                    # Get device name
                    name = "Local Device"
                    if hasattr(self.interface, 'getMyUser'):
                        user = self.interface.getMyUser()
                        if user and 'longName' in user:
                            name = user['longName']
                    
                    return (lat, lon, name)
                    
        except Exception as e:
            logger.debug(f"Could not get local device position: {e}")
            
        return None
            
    def update_map_nodes(self):
        """Update nodes on the map"""
        try:
            if self.use_real_map and self.map_widget:
                self.update_real_map_nodes()
            elif self.coordinate_canvas:
                self.update_coordinate_plot_nodes()
        except Exception as e:
            logger.error(f"Error updating map nodes: {e}")
            
    def update_real_map_nodes(self):
        """Update nodes on real map"""
        if not self.map_widget:
            return
            
        # Clear existing markers
        for marker in self.map_markers.values():
            try:
                marker.delete()
            except:
                pass
        self.map_markers.clear()
        
        # Get nodes with position data
        positioned_nodes = []
        
        # Add local device first (if GPS available)
        local_position = self.get_local_device_position()
        if local_position:
            lat, lon, name = local_position
            positioned_nodes.append((lat, lon, f"📍 {name} (You)", "blue"))
        
        # Add remote nodes
        for node_id, node in self.nodes.items():
            position = node.get('position', {})
            if 'latitude' in position and 'longitude' in position:
                user = node.get('user', {})
                name = user.get('longName', f'Node {node_id}')
                lat = position['latitude']
                lon = position['longitude']
                
                # Determine marker color based on battery or connection status
                battery = node.get('deviceMetrics', {}).get('batteryLevel', 0)
                if battery > 75:
                    marker_color = "green"
                elif battery > 25:
                    marker_color = "orange"
                else:
                    marker_color = "red"
                
                positioned_nodes.append((lat, lon, name, marker_color))
                
        # Add markers for positioned nodes
        for lat, lon, name, color in positioned_nodes:
            try:
                marker = self.map_widget.set_marker(lat, lon, text=name, marker_color_circle=color, marker_color_outside=color)
                self.map_markers[name] = marker
            except Exception as e:
                logger.debug(f"Could not add marker for {name}: {e}")
                
        # Auto-fit map to show all nodes
        if positioned_nodes:
            try:
                # Calculate bounds
                lats = [pos[0] for pos in positioned_nodes]
                lons = [pos[1] for pos in positioned_nodes]
                
                center_lat = sum(lats) / len(lats)
                center_lon = sum(lons) / len(lons)
                
                # Set position and zoom to fit all nodes
                self.map_widget.set_position(center_lat, center_lon)
                
                # Calculate appropriate zoom level
                lat_range = max(lats) - min(lats)
                lon_range = max(lons) - min(lons)
                max_range = max(lat_range, lon_range)
                
                if max_range > 1:
                    zoom = 8
                elif max_range > 0.1:
                    zoom = 12
                elif max_range > 0.01:
                    zoom = 15
                else:
                    zoom = 17
                    
                self.map_widget.set_zoom(zoom)
                
            except Exception as e:
                logger.debug(f"Could not auto-fit map: {e}")
                
    def update_coordinate_plot_nodes(self):
        """Update nodes on coordinate plot"""
        if not self.coordinate_canvas:
            return
            
        # Clear existing node markers
        self.coordinate_canvas.delete("node")
        
        # Get nodes with position data
        positioned_nodes = []
        
        # Add local device first (if GPS available)
        local_position = self.get_local_device_position()
        if local_position:
            lat, lon, name = local_position
            positioned_nodes.append((lat, lon, "YOU", "blue"))
        
        # Add remote nodes
        for node_id, node in self.nodes.items():
            position = node.get('position', {})
            if 'latitude' in position and 'longitude' in position:
                user = node.get('user', {})
                name = user.get('shortName', f'N{node_id}')[:4]  # Short name for space
                lat = position['latitude']
                lon = position['longitude']
                
                # Determine marker color based on battery
                battery = node.get('deviceMetrics', {}).get('batteryLevel', 0)
                if battery > 75:
                    color = "green"
                elif battery > 25:
                    color = "orange"
                else:
                    color = "red"
                
                positioned_nodes.append((lat, lon, name, color))
                
        if not positioned_nodes:
            # Show message if no positioned nodes
            self.coordinate_canvas.create_text(200, 200, text="No nodes with GPS data", 
                                             justify=tk.CENTER, font=("Arial", 12), fill="gray", tags="node")
            return
            
        # Calculate coordinate bounds and scale
        lats = [pos[0] for pos in positioned_nodes]
        lons = [pos[1] for pos in positioned_nodes]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Add padding
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        padding = max(lat_range, lon_range) * 0.1
        
        min_lat -= padding
        max_lat += padding
        min_lon -= padding
        max_lon += padding
        
        # Map coordinates to canvas
        canvas_width = 400
        canvas_height = 400
        margin = 30
        
        for lat, lon, name, color in positioned_nodes:
            # Scale to canvas coordinates
            if max_lat != min_lat:
                y = margin + (max_lat - lat) / (max_lat - min_lat) * (canvas_height - 2 * margin)
            else:
                y = canvas_height // 2
                
            if max_lon != min_lon:
                x = margin + (lon - min_lon) / (max_lon - min_lon) * (canvas_width - 2 * margin)
            else:
                x = canvas_width // 2
            
            # Draw node marker
            radius = 10 if color == "blue" else 8  # Make local device marker slightly larger
            outline_width = 3 if color == "blue" else 2  # Make local device outline thicker
            self.coordinate_canvas.create_oval(x - radius, y - radius, x + radius, y + radius, 
                                             fill=color, outline="black", width=outline_width, tags="node")
            
            # Add label
            self.coordinate_canvas.create_text(x, y - radius - 10, text=name, 
                                             font=("Arial", 8), fill="black", tags="node")
            
    def get_device_info(self):
        """Get device information"""
        if not self.interface:
            return
            
        try:
            # Validate that the interface has the required attributes
            if not hasattr(self.interface, 'localNode'):
                logger.warning("Interface doesn't have localNode attribute")
                return
                
            # Get local node info
            local_node = self.interface.localNode
            if local_node:
                # Update device info labels
                if hasattr(self.interface, 'getMyUser'):
                    user = self.interface.getMyUser()
                    if user:
                        self.device_info_labels["Long Name"].config(text=user.get('longName', 'N/A'))
                        self.device_info_labels["Short Name"].config(text=user.get('shortName', 'N/A'))
                        self.long_name_var.set(user.get('longName', ''))
                        self.short_name_var.set(user.get('shortName', ''))
                        
                # Get device metadata
                if hasattr(self.interface, 'getMyNodeInfo'):
                    node_info = self.interface.getMyNodeInfo()
                    if node_info:
                        # Hardware info
                        device_metadata = node_info.get('deviceMetrics', {})
                        if 'hwModel' in device_metadata:
                            self.device_info_labels["Hardware"].config(text=device_metadata['hwModel'])
                        
                        # Firmware version
                        if 'firmwareVersion' in node_info:
                            self.device_info_labels["Firmware"].config(text=node_info['firmwareVersion'])
                        
                        # Battery level
                        if 'batteryLevel' in device_metadata:
                            battery_level = device_metadata['batteryLevel']
                            self.battery_label.config(text=f"{battery_level}%")
                            
                # Get region information
                if hasattr(local_node, 'localConfig'):
                    config = local_node.localConfig
                    if hasattr(config, 'lora') and hasattr(config.lora, 'region'):
                        # Map region enum values back to names
                        region_map = {
                            1: "US",        # US
                            2: "EU_433",    # EU_433
                            3: "EU_868",    # EU_868
                            7: "ANZ",       # ANZ
                            8: "CN",        # CN
                            9: "IN",        # IN
                            10: "JP",       # JP
                            11: "KR",       # KR
                            12: "MY_433",   # MY_433
                            13: "MY_919",   # MY_919
                            14: "NZ_865",   # NZ_865
                            15: "RU",       # RU
                            16: "SG_923",   # SG_923
                            17: "TH",       # TH
                            18: "TW",       # TW
                            19: "UA_433",   # UA_433
                            20: "UA_868",   # UA_868
                        }
                        
                        region_num = config.lora.region
                        region_name = region_map.get(region_num, f"Unknown ({region_num})")
                        self.device_info_labels["Region"].config(text=region_name)
                        
                        # Update the region dropdown selection
                        if region_name in self.regions:
                            self.region_var.set(region_name)
                            
                # Get channel information
                if hasattr(self.interface, 'getChannelSettings'):
                    try:
                        channel_settings = self.interface.getChannelSettings()
                        if channel_settings:
                            # Update channel info
                            channel_name = channel_settings.get('name', 'Primary')
                            self.device_info_labels["Channel"].config(text=channel_name)
                            self.channel_name_var.set(channel_name)
                            
                            # Update PSK if available
                            if 'psk' in channel_settings:
                                # PSK is usually displayed as base64 or hex
                                psk_display = "***" if channel_settings['psk'] else "None"
                                self.psk_var.set(psk_display)
                    except Exception as e:
                        logger.debug(f"Could not get channel settings: {e}")
                        
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            
    def update_node_info(self):
        """Update node information"""
        if not self.interface:
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        # Validate that the interface has the required attributes
        if not hasattr(self.interface, 'localNode'):
            messagebox.showwarning("Warning", "Interface not properly initialized")
            return
            
        try:
            long_name = self.long_name_var.get().strip()
            short_name = self.short_name_var.get().strip()
            
            if long_name or short_name:
                local_node = self.interface.localNode
                if local_node and hasattr(local_node, 'setOwner'):
                    local_node.setOwner(long_name=long_name, short_name=short_name)
                    messagebox.showinfo("Success", "Node information updated")
                else:
                    messagebox.showwarning("Warning", "Local node not available or not properly initialized")
                    
        except Exception as e:
            logger.error(f"Error updating node info: {e}")
            messagebox.showerror("Error", f"Failed to update node info: {e}")
            
    def update_region(self):
        """Update device region setting"""
        if not self.interface:
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        # Validate that the interface has the required attributes
        if not hasattr(self.interface, 'localNode'):
            messagebox.showwarning("Warning", "Interface not properly initialized")
            return
            
        selected_region = self.region_var.get()
        if not selected_region:
            messagebox.showwarning("Warning", "Please select a region")
            return
            
        try:
            # Get the local node config
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'localConfig'):
                # Create a new config object with the region setting
                config = local_node.localConfig
                
                # Update the region in the config
                # The region is stored in the LoRa config
                if hasattr(config, 'lora') and hasattr(config.lora, 'region'):
                    # Map our region names to the protobuf enum values
                    region_map = {
                        "ANZ": 7,       # ANZ
                        "CN": 8,        # CN
                        "EU_433": 2,    # EU_433
                        "EU_868": 3,    # EU_868
                        "IN": 9,        # IN
                        "JP": 10,       # JP
                        "KR": 11,       # KR
                        "MY_433": 12,   # MY_433
                        "MY_919": 13,   # MY_919
                        "NZ_865": 14,   # NZ_865
                        "RU": 15,       # RU
                        "SG_923": 16,   # SG_923
                        "TH": 17,       # TH
                        "TW": 18,       # TW
                        "UA_433": 19,   # UA_433
                        "UA_868": 20,   # UA_868
                        "US": 1         # US
                    }
                    
                    if selected_region in region_map:
                        config.lora.region = region_map[selected_region]
                        
                        # Write the config back to the device
                        local_node.writeConfig("lora")
                        
                        messagebox.showinfo("Success", f"Region updated to {selected_region}.\n\nDevice will reboot to apply the new region setting.")
                        
                        # Update the display
                        self.get_device_info()
                        
                    else:
                        messagebox.showerror("Error", f"Unsupported region: {selected_region}")
                        
                else:
                    messagebox.showerror("Error", "Unable to access LoRa configuration")
                    
            else:
                messagebox.showwarning("Warning", "Local node configuration not available")
                
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
        if not self.interface:
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        # Validate that the interface has the required attributes
        if not hasattr(self.interface, 'localNode'):
            messagebox.showwarning("Warning", "Interface not properly initialized")
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to reboot the device?"):
            try:
                local_node = self.interface.localNode
                if local_node and hasattr(local_node, 'reboot'):
                    local_node.reboot()
                    messagebox.showinfo("Success", "Device reboot initiated")
                else:
                    messagebox.showwarning("Warning", "Local node not available or not properly initialized")
            except Exception as e:
                logger.error(f"Error rebooting device: {e}")
                messagebox.showerror("Error", f"Failed to reboot device: {e}")
                
    def factory_reset(self):
        """Factory reset the device"""
        if not self.interface:
            messagebox.showwarning("Warning", "Not connected to device")
            return
            
        # Validate that the interface has the required attributes
        if not hasattr(self.interface, 'localNode'):
            messagebox.showwarning("Warning", "Interface not properly initialized")
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to factory reset the device? This cannot be undone."):
            try:
                local_node = self.interface.localNode
                if local_node and hasattr(local_node, 'factoryReset'):
                    local_node.factoryReset()
                    messagebox.showinfo("Success", "Factory reset initiated")
                else:
                    messagebox.showwarning("Warning", "Local node not available or not properly initialized")
            except Exception as e:
                logger.error(f"Error factory resetting device: {e}")
                messagebox.showerror("Error", f"Failed to factory reset device: {e}")
                
    def update_status(self, status=None):
        """Update status display"""
        if status:
            self.status_text.set(status)
            
        # Schedule next update
        self.root.after(5000, self.update_status)

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = MeshtasticUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()