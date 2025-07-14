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
        
        # Setup UI
        self.create_widgets()
        self.setup_meshtastic_events()
        
        # Start message processing thread
        self.start_message_thread()
        
        # Update status periodically
        self.update_status()
        
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
        """Create map visualization tab"""
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
        
        # Map visualization area (placeholder)
        map_viz_frame = ttk.LabelFrame(map_content, text="Map Visualization", padding="10")
        map_viz_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        map_viz_frame.columnconfigure(0, weight=1)
        map_viz_frame.rowconfigure(0, weight=1)
        
        # Placeholder for map - in a real implementation, you'd use a mapping library
        self.map_canvas = tk.Canvas(map_viz_frame, bg="lightgray", width=400, height=400)
        self.map_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add placeholder text
        self.map_canvas.create_text(200, 200, text="Map Visualization\n(Placeholder)", 
                                   justify=tk.CENTER, font=("Arial", 12))
        
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
        
        # Channel settings
        channel_frame = ttk.LabelFrame(config_content, text="Channel Settings", padding="10")
        channel_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
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
        power_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # Battery level display
        ttk.Label(power_frame, text="Battery Level:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.battery_label = ttk.Label(power_frame, text="N/A", foreground="gray")
        self.battery_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(config_content, text="Actions", padding="10")
        actions_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
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
                self.root.after(0, lambda: messagebox.showerror("Connection Error", error_message))
                
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
        """Update nodes tree display"""
        # Clear existing items
        for item in self.nodes_tree.get_children():
            self.nodes_tree.delete(item)
            
        # Add nodes
        for node_id, node in self.nodes.items():
            try:
                # Extract node info
                user = node.get('user', {})
                name = user.get('longName', 'Unknown')
                short_name = user.get('shortName', 'N/A')
                
                # Position info
                position = node.get('position', {})
                distance = "N/A"
                
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
                
        # Update node count
        self.node_count_text.set(f"Nodes: {len(self.nodes)}")
        
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
                        
                # Hardware info
                if hasattr(local_node, 'localConfig'):
                    # This would be populated with actual device info
                    pass
                    
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