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
import sqlite3
import hashlib
import csv
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Matplotlib not available, analytics charts will be disabled: {e}")
    MATPLOTLIB_AVAILABLE = False

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

class DataLogger:
    """Handles all data logging and historical data storage"""
    
    def __init__(self, db_path="meshpy_data.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                from_node TEXT,
                to_node TEXT,
                message_text TEXT,
                timestamp DATETIME,
                status TEXT,
                hop_count INTEGER,
                rssi REAL,
                snr REAL,
                message_type TEXT,
                channel TEXT
            )
        ''')
        
        # Nodes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                node_name TEXT,
                short_name TEXT,
                hardware_model TEXT,
                firmware_version TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                is_local BOOLEAN DEFAULT 0
            )
        ''')
        
        # Node positions table (for tracking movement)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS node_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                latitude REAL,
                longitude REAL,
                altitude REAL,
                timestamp DATETIME,
                accuracy REAL
            )
        ''')
        
        # Node metrics table (battery, signal strength, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS node_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                timestamp DATETIME,
                battery_level INTEGER,
                voltage REAL,
                current REAL,
                utilization REAL,
                airtime REAL,
                channel_utilization REAL,
                rssi REAL,
                snr REAL
            )
        ''')
        
        # Network topology table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_topology (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node TEXT,
                to_node TEXT,
                hop_count INTEGER,
                rssi REAL,
                snr REAL,
                timestamp DATETIME,
                route_discovered DATETIME
            )
        ''')
        
        # Emergency events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emergency_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                event_type TEXT,
                latitude REAL,
                longitude REAL,
                message TEXT,
                timestamp DATETIME,
                acknowledged BOOLEAN DEFAULT 0
            )
        ''')
        
        # Configuration profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT UNIQUE,
                device_config TEXT,
                created_date DATETIME,
                last_used DATETIME
            )
        ''')
        
        # Connection events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connection_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                device_path TEXT,
                timestamp DATETIME,
                success BOOLEAN,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
        
    def log_message(self, message_data):
        """Log a message to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO messages (message_id, from_node, to_node, message_text, 
                                    timestamp, status, hop_count, rssi, snr, message_type, channel)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_data.get('message_id', ''),
                message_data.get('from_node', ''),
                message_data.get('to_node', ''),
                message_data.get('message_text', ''),
                message_data.get('timestamp', datetime.now()),
                message_data.get('status', 'received'),
                message_data.get('hop_count', 0),
                message_data.get('rssi', None),
                message_data.get('snr', None),
                message_data.get('message_type', 'text'),
                message_data.get('channel', 'primary')
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging message: {e}")
        finally:
            conn.close()
            
    def log_node_update(self, node_data):
        """Log node information update"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            node_id = node_data.get('node_id', '')
            now = datetime.now()
            
            # Update or insert node basic info
            cursor.execute('''
                INSERT OR REPLACE INTO nodes (node_id, node_name, short_name, 
                                            hardware_model, firmware_version, 
                                            first_seen, last_seen, is_local)
                VALUES (?, ?, ?, ?, ?, 
                        COALESCE((SELECT first_seen FROM nodes WHERE node_id = ?), ?),
                        ?, ?)
            ''', (
                node_id,
                node_data.get('node_name', ''),
                node_data.get('short_name', ''),
                node_data.get('hardware_model', ''),
                node_data.get('firmware_version', ''),
                node_id,
                now,
                now,
                node_data.get('is_local', False)
            ))
            
            # Log position if available
            if 'latitude' in node_data and 'longitude' in node_data:
                cursor.execute('''
                    INSERT INTO node_positions (node_id, latitude, longitude, altitude, timestamp, accuracy)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    node_id,
                    node_data['latitude'],
                    node_data['longitude'],
                    node_data.get('altitude', None),
                    now,
                    node_data.get('accuracy', None)
                ))
                
            # Log metrics if available
            if 'battery_level' in node_data or 'rssi' in node_data:
                cursor.execute('''
                    INSERT INTO node_metrics (node_id, timestamp, battery_level, voltage, 
                                            current, utilization, airtime, channel_utilization, 
                                            rssi, snr)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    node_id,
                    now,
                    node_data.get('battery_level', None),
                    node_data.get('voltage', None),
                    node_data.get('current', None),
                    node_data.get('utilization', None),
                    node_data.get('airtime', None),
                    node_data.get('channel_utilization', None),
                    node_data.get('rssi', None),
                    node_data.get('snr', None)
                ))
                
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging node update: {e}")
        finally:
            conn.close()
            
    def log_connection_event(self, event_type, device_path, success, error_message=None):
        """Log connection events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO connection_events (event_type, device_path, timestamp, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (event_type, device_path, datetime.now(), success, error_message))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging connection event: {e}")
        finally:
            conn.close()
            
    def log_emergency_event(self, node_id, event_type, latitude=None, longitude=None, message=""):
        """Log emergency events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO emergency_events (node_id, event_type, latitude, longitude, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (node_id, event_type, latitude, longitude, message, datetime.now()))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging emergency event: {e}")
        finally:
            conn.close()
            
    def get_message_history(self, limit=100, node_filter=None):
        """Get message history with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = '''
                SELECT m.*, n1.node_name as from_name, n2.node_name as to_name
                FROM messages m
                LEFT JOIN nodes n1 ON m.from_node = n1.node_id
                LEFT JOIN nodes n2 ON m.to_node = n2.node_id
            '''
            params = []
            
            if node_filter:
                query += ' WHERE m.from_node = ? OR m.to_node = ?'
                params.extend([node_filter, node_filter])
                
            query += ' ORDER BY m.timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting message history: {e}")
            return []
        finally:
            conn.close()
            
    def get_node_metrics_history(self, node_id, hours=24):
        """Get node metrics history for charts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM node_metrics 
                WHERE node_id = ? AND timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp
            '''.format(hours), (node_id,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting node metrics history: {e}")
            return []
        finally:
            conn.close()
            
    def get_network_statistics(self):
        """Get network statistics for analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Total messages
            cursor.execute('SELECT COUNT(*) FROM messages')
            stats['total_messages'] = cursor.fetchone()[0]
            
            # Active nodes (seen in last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM nodes 
                WHERE last_seen > datetime('now', '-24 hours')
            ''')
            stats['active_nodes'] = cursor.fetchone()[0]
            
            # Messages in last 24 hours
            cursor.execute('''
                SELECT COUNT(*) FROM messages 
                WHERE timestamp > datetime('now', '-24 hours')
            ''')
            stats['messages_24h'] = cursor.fetchone()[0]
            
            # Emergency events
            cursor.execute('''
                SELECT COUNT(*) FROM emergency_events 
                WHERE timestamp > datetime('now', '-24 hours')
            ''')
            stats['emergency_events_24h'] = cursor.fetchone()[0]
            
            return stats
        except Exception as e:
            logger.error(f"Error getting network statistics: {e}")
            return {}
        finally:
            conn.close()
            
    def search_messages(self, search_term, limit=50):
        """Search messages by content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT m.*, n1.node_name as from_name, n2.node_name as to_name
                FROM messages m
                LEFT JOIN nodes n1 ON m.from_node = n1.node_id
                LEFT JOIN nodes n2 ON m.to_node = n2.node_id
                WHERE m.message_text LIKE ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', (f'%{search_term}%', limit))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return []
        finally:
            conn.close()
            
    def export_data(self, table_name, format='csv'):
        """Export data to various formats"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'SELECT * FROM {table_name}')
            data = cursor.fetchall()
            
            # Get column names
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = [row[1] for row in cursor.fetchall()]
            
            if format == 'csv':
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(columns)
                writer.writerows(data)
                return output.getvalue()
            elif format == 'json':
                result = []
                for row in data:
                    result.append(dict(zip(columns, row)))
                return json.dumps(result, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return None
        finally:
            conn.close()

class MeshtasticUI:
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
    
    def __init__(self, root):
        self.root = root
        self.root.title("Meshtastic UI")
        self.root.geometry("1200x800")
        
        # Initialize variables
        self.interface = None
        self.connection_status = "Disconnected"
        self.nodes = {}
        self.message_queue = queue.Queue()
        self.message_status_tracking = {}  # Track message status
        
        # Initialize data logger
        self.data_logger = DataLogger()
        
        # Map-related variables
        self.map_widget = None
        self.coordinate_canvas = None
        self.map_markers = {}
        self.use_real_map = False
        self.internet_available = False
        self.map_layer_var = tk.StringVar(value="OpenStreetMap")
        self.map_layers = {}
        
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
        self.create_network_topology_tab()
        self.create_analytics_tab()
        self.create_emergency_tab()
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
        self.map_viz_frame.rowconfigure(1, weight=1)
        
        # Map layer selection
        self.create_map_layer_controls()
        
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
        
        # Configure initial tile server
        self.apply_map_layer()
        
        # Set initial position based on available location data
        initial_position = self.get_initial_map_position()
        if initial_position:
            lat, lon, source = initial_position
            logger.info(f"Setting initial map position to {lat}, {lon} (source: {source})")
            self.map_widget.set_position(lat, lon)
            # Use higher zoom if we have GPS location
            zoom = 15 if source == "GPS" else 10
            self.map_widget.set_zoom(zoom)
        else:
            # Fall back to San Francisco
            logger.info("No location data available, using San Francisco as default")
            self.map_widget.set_position(37.7749, -122.4194)
            self.map_widget.set_zoom(10)
        
        self.map_widget.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Update frame title with current layer
        self.update_map_frame_title()
        
    def create_map_layer_controls(self):
        """Create map layer selection controls"""
        layer_frame = ttk.Frame(self.map_viz_frame)
        layer_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        layer_frame.columnconfigure(1, weight=1)
        
        # Map layer selection
        ttk.Label(layer_frame, text="Map Layer:").grid(row=0, column=0, padx=(0, 10))
        
        self.map_layer_var = tk.StringVar(value="OpenStreetMap")
        
                 # Define available map layers
        self.map_layers = {
            "OpenStreetMap": {
                "url": "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "max_zoom": 19,
                "attribution": "© OpenStreetMap contributors"
            },
            "📡 Satellite (Esri)": {
                "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                "max_zoom": 19,
                "attribution": "© Esri, Maxar, Earthstar Geographics"
            },
            "🌍 Satellite (Google)": {
                "url": "http://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}",
                "max_zoom": 20,
                "attribution": "© Google"
            },
                         "🗺️ Hybrid (Google)": {
                 "url": "http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}",
                 "max_zoom": 20,
                 "attribution": "© Google"
             },
             "🏞️ Topo (OpenTopo)": {
                "url": "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
                "max_zoom": 17,
                "attribution": "© OpenTopoMap, © OpenStreetMap contributors"
            },
            "☀️ Light Theme": {
                "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
                "max_zoom": 19,
                "attribution": "© CartoDB, © OpenStreetMap contributors"
            },
            "🌙 Dark Theme": {
                "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
                "max_zoom": 19,
                "attribution": "© CartoDB, © OpenStreetMap contributors"
            }
        }
        
        layer_combo = ttk.Combobox(layer_frame, textvariable=self.map_layer_var, 
                                  values=list(self.map_layers.keys()), state="readonly", width=25)
        layer_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        layer_combo.bind('<<ComboboxSelected>>', self.on_layer_changed)
        
        # Refresh button
        ttk.Button(layer_frame, text="🔄", command=self.refresh_map, width=3).grid(row=0, column=2)
        
    def apply_map_layer(self):
        """Apply the selected map layer to the map widget"""
        if not self.map_widget or not hasattr(self, 'map_layers') or not self.map_layers:
            return
            
        try:
            selected_layer = self.map_layer_var.get()
            if selected_layer not in self.map_layers:
                logger.warning(f"Selected layer '{selected_layer}' not found in map_layers")
                return
                
            layer_config = self.map_layers[selected_layer]
            
            # Set the tile server
            self.map_widget.set_tile_server(
                layer_config["url"], 
                max_zoom=layer_config["max_zoom"]
            )
            
            logger.info(f"Applied map layer: {selected_layer}")
            
        except Exception as e:
            logger.error(f"Error applying map layer: {e}")
            # Fall back to OpenStreetMap
            try:
                self.map_widget.set_tile_server(
                    "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", 
                    max_zoom=19
                )
            except Exception as fallback_error:
                logger.error(f"Error applying fallback layer: {fallback_error}")
            
    def on_layer_changed(self, event=None):
        """Handle map layer selection change"""
        if hasattr(self, 'map_widget') and self.map_widget:
            self.apply_map_layer()
            self.update_map_frame_title()
            
            # Store current position and zoom to maintain view
            try:
                current_position = self.map_widget.get_position()
                current_zoom = self.map_widget.get_zoom()
                
                # Small delay to let tiles load, then restore position
                self.root.after(100, lambda: self.restore_map_view(current_position, current_zoom))
                
            except Exception as e:
                logger.debug(f"Could not preserve map view: {e}")
                
    def restore_map_view(self, position, zoom):
        """Restore map position and zoom after layer change"""
        try:
            if position and zoom:
                self.map_widget.set_position(position[0], position[1])
                self.map_widget.set_zoom(zoom)
        except Exception as e:
            logger.debug(f"Could not restore map view: {e}")
            
    def refresh_map(self):
        """Refresh the current map"""
        if hasattr(self, 'map_widget') and self.map_widget:
            try:
                # Store current state
                current_position = self.map_widget.get_position()
                current_zoom = self.map_widget.get_zoom()
                
                # Reapply layer
                self.apply_map_layer()
                
                # Restore state
                self.restore_map_view(current_position, current_zoom)
                
                # Update nodes
                self.update_map_nodes()
                
                logger.info("Map refreshed")
                
            except Exception as e:
                logger.error(f"Error refreshing map: {e}")
                
    def update_map_frame_title(self):
        """Update the map frame title with current layer info"""
        try:
            if self.use_real_map:
                selected_layer = self.map_layer_var.get()
                if selected_layer:
                    title = f"Map Visualization ({selected_layer} - Online)"
                else:
                    title = "Map Visualization (Online)"
            else:
                title = "Map Visualization (Coordinate Plot"
                if not self.internet_available:
                    title += " - Offline"
                elif not MAPVIEW_AVAILABLE:
                    title += " - Map library unavailable"
                title += ")"
            
            self.map_viz_frame.config(text=title)
            
        except Exception as e:
            logger.debug(f"Could not update map frame title: {e}")
        
    def create_coordinate_plot(self):
        """Create simple coordinate plot as fallback"""
        logger.info("Creating coordinate plot fallback")
        
        self.coordinate_canvas = tk.Canvas(self.map_viz_frame, bg="lightgray", width=400, height=400)
        self.coordinate_canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add grid lines
        self.draw_coordinate_grid()
        
        # Add instructions
        self.coordinate_canvas.create_text(200, 50, text="Coordinate Plot\n(No internet/map tiles)", 
                                         justify=tk.CENTER, font=("Arial", 10), fill="darkblue")
        
        # Update frame title
        self.update_map_frame_title()
        
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
        
        # Message search frame
        search_frame = ttk.Frame(chat_content)
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, padx=(0, 10))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', self.on_search_messages)
        
        ttk.Button(search_frame, text="Load History", command=self.load_message_history).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(search_frame, text="Clear Search", command=self.clear_search).grid(row=0, column=3)
        
        # Message input frame
        input_frame = ttk.Frame(chat_content)
        input_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
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
        
    def create_network_topology_tab(self):
        """Create network topology visualization tab"""
        topology_frame = ttk.Frame(self.notebook)
        self.notebook.add(topology_frame, text="Network")
        
        # Configure grid
        topology_frame.columnconfigure(0, weight=1)
        topology_frame.rowconfigure(0, weight=1)
        
        # Create main paned window
        main_paned = ttk.PanedWindow(topology_frame, orient=tk.HORIZONTAL)
        main_paned.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Left panel for network visualization
        left_frame = ttk.LabelFrame(main_paned, text="Network Topology", padding="10")
        main_paned.add(left_frame, weight=3)
        
        # Network canvas
        self.network_canvas = tk.Canvas(left_frame, bg="white", width=600, height=400)
        self.network_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Canvas scrollbars
        h_scrollbar = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.network_canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.network_canvas.configure(xscrollcommand=h_scrollbar.set)
        
        v_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.network_canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.network_canvas.configure(yscrollcommand=v_scrollbar.set)
        
        # Configure canvas grid
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        # Control buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="Refresh Network", command=self.refresh_network_topology).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="Auto Layout", command=self.auto_layout_network).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="Export Network", command=self.export_network_data).grid(row=0, column=2)
        
        # Right panel for network statistics
        right_frame = ttk.LabelFrame(main_paned, text="Network Statistics", padding="10")
        main_paned.add(right_frame, weight=1)
        
        # Network stats
        self.network_stats_frame = ttk.Frame(right_frame)
        self.network_stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Connection details
        ttk.Label(self.network_stats_frame, text="Connection Details:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Network metrics
        self.network_metrics_labels = {}
        metrics = ["Total Nodes", "Active Nodes", "Total Connections", "Average Hop Count", "Network Diameter"]
        
        for i, metric in enumerate(metrics):
            ttk.Label(self.network_stats_frame, text=f"{metric}:").grid(row=i+1, column=0, sticky=tk.W, pady=2)
            label = ttk.Label(self.network_stats_frame, text="0", foreground="blue")
            label.grid(row=i+1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
            self.network_metrics_labels[metric] = label
        
        # Node details section
        ttk.Label(self.network_stats_frame, text="Selected Node:", font=("Arial", 10, "bold")).grid(row=7, column=0, sticky=tk.W, pady=(20, 10))
        
        # Selected node info
        self.selected_node_info = ttk.Frame(self.network_stats_frame)
        self.selected_node_info.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.selected_node_label = ttk.Label(self.selected_node_info, text="Click on a node to see details", foreground="gray")
        self.selected_node_label.grid(row=0, column=0, sticky=tk.W)
        
        # Node connections list
        ttk.Label(self.network_stats_frame, text="Node Connections:", font=("Arial", 10, "bold")).grid(row=9, column=0, sticky=tk.W, pady=(20, 10))
        
        # Connections treeview
        self.connections_tree = ttk.Treeview(self.network_stats_frame, columns=("target", "hops", "rssi", "snr"), show="headings", height=8)
        self.connections_tree.heading("target", text="Target Node")
        self.connections_tree.heading("hops", text="Hops")
        self.connections_tree.heading("rssi", text="RSSI")
        self.connections_tree.heading("snr", text="SNR")
        
        # Configure column widths
        self.connections_tree.column("target", width=100)
        self.connections_tree.column("hops", width=50)
        self.connections_tree.column("rssi", width=60)
        self.connections_tree.column("snr", width=60)
        
        self.connections_tree.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Scrollbar for connections
        conn_scrollbar = ttk.Scrollbar(self.network_stats_frame, orient="vertical", command=self.connections_tree.yview)
        conn_scrollbar.grid(row=10, column=2, sticky=(tk.N, tk.S))
        self.connections_tree.configure(yscrollcommand=conn_scrollbar.set)
        
        # Configure right frame grid
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        self.network_stats_frame.columnconfigure(1, weight=1)
        
        # Network topology data
        self.network_nodes = {}
        self.network_connections = {}
        self.selected_network_node = None
        
        # Bind canvas events
        self.network_canvas.bind("<Button-1>", self.on_network_canvas_click)
        self.network_canvas.bind("<B1-Motion>", self.on_network_canvas_drag)
        self.network_canvas.bind("<ButtonRelease-1>", self.on_network_canvas_release)
        
        # Initialize network display
        self.refresh_network_topology()
        
    def create_emergency_tab(self):
        """Create emergency features tab"""
        emergency_frame = ttk.Frame(self.notebook)
        self.notebook.add(emergency_frame, text="Emergency")
        
        # Configure grid
        emergency_frame.columnconfigure(0, weight=1)
        emergency_frame.rowconfigure(0, weight=1)
        
        # Create scrollable content
        emergency_canvas = tk.Canvas(emergency_frame)
        emergency_scrollbar = ttk.Scrollbar(emergency_frame, orient="vertical", command=emergency_canvas.yview)
        emergency_content = ttk.Frame(emergency_canvas)
        
        emergency_content.bind('<Configure>', lambda e: emergency_canvas.configure(scrollregion=emergency_canvas.bbox("all")))
        
        emergency_canvas.create_window((0, 0), window=emergency_content, anchor="nw")
        emergency_canvas.configure(yscrollcommand=emergency_scrollbar.set)
        
        emergency_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        emergency_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Emergency Beacon Section
        beacon_frame = ttk.LabelFrame(emergency_content, text="Emergency Beacon", padding="10")
        beacon_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        beacon_frame.columnconfigure(1, weight=1)
        
        # Emergency status
        self.emergency_active = False
        self.emergency_status_label = ttk.Label(beacon_frame, text="Emergency beacon inactive", foreground="gray")
        self.emergency_status_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Emergency message
        ttk.Label(beacon_frame, text="Emergency Message:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.emergency_message_var = tk.StringVar(value="EMERGENCY - Need assistance!")
        emergency_msg_entry = ttk.Entry(beacon_frame, textvariable=self.emergency_message_var, width=50)
        emergency_msg_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Emergency buttons
        button_frame = ttk.Frame(beacon_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.emergency_beacon_button = ttk.Button(button_frame, text="🚨 EMERGENCY BEACON", 
                                                 command=self.activate_emergency_beacon)
        self.emergency_beacon_button.grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(button_frame, text="😱 PANIC BUTTON", command=self.activate_panic_button).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="📤 SEND MESSAGE", command=self.send_emergency_message).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(button_frame, text="🟢 CANCEL", command=self.cancel_emergency).grid(row=0, column=3)
        
        # Emergency Contacts Section
        contacts_frame = ttk.LabelFrame(emergency_content, text="Emergency Contacts", padding="10")
        contacts_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        contacts_frame.columnconfigure(0, weight=1)
        
        # Contacts list
        contacts_list_frame = ttk.Frame(contacts_frame)
        contacts_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        contacts_list_frame.columnconfigure(0, weight=1)
        
        self.emergency_contacts_tree = ttk.Treeview(contacts_list_frame, columns=("name", "node_id", "priority"), show="headings", height=6)
        self.emergency_contacts_tree.heading("name", text="Name")
        self.emergency_contacts_tree.heading("node_id", text="Node ID")
        self.emergency_contacts_tree.heading("priority", text="Priority")
        
        self.emergency_contacts_tree.column("name", width=150)
        self.emergency_contacts_tree.column("node_id", width=100)
        self.emergency_contacts_tree.column("priority", width=80)
        
        self.emergency_contacts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Add contact form
        add_contact_frame = ttk.Frame(contacts_frame)
        add_contact_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        add_contact_frame.columnconfigure(1, weight=1)
        
        ttk.Label(add_contact_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.contact_name_var = tk.StringVar()
        ttk.Entry(add_contact_frame, textvariable=self.contact_name_var, width=20).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(add_contact_frame, text="Node ID:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.contact_node_var = tk.StringVar()
        ttk.Entry(add_contact_frame, textvariable=self.contact_node_var, width=20).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(add_contact_frame, text="Priority:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.contact_priority_var = tk.StringVar(value="Normal")
        priority_combo = ttk.Combobox(add_contact_frame, textvariable=self.contact_priority_var, 
                                     values=["High", "Normal", "Low"], state="readonly", width=10)
        priority_combo.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Contact buttons
        contact_buttons = ttk.Frame(contacts_frame)
        contact_buttons.grid(row=2, column=0, pady=10)
        
        ttk.Button(contact_buttons, text="Add Contact", command=self.add_emergency_contact).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(contact_buttons, text="Remove Contact", command=self.remove_emergency_contact).grid(row=0, column=1)
        
        # Medical Information Section
        medical_frame = ttk.LabelFrame(emergency_content, text="Medical Information", padding="10")
        medical_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        medical_frame.columnconfigure(1, weight=1)
        
        # Medical info fields
        self.medical_info_vars = {}
        medical_fields = [
            ("blood_type", "Blood Type"),
            ("allergies", "Allergies"),
            ("medications", "Current Medications"),
            ("medical_conditions", "Medical Conditions"),
            ("emergency_contact", "Emergency Contact"),
            ("insurance", "Insurance Info")
        ]
        
        for i, (field_key, field_label) in enumerate(medical_fields):
            ttk.Label(medical_frame, text=f"{field_label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar()
            self.medical_info_vars[field_key] = var
            ttk.Entry(medical_frame, textvariable=var, width=40).grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Medical buttons
        medical_buttons = ttk.Frame(medical_frame)
        medical_buttons.grid(row=len(medical_fields), column=0, columnspan=2, pady=10)
        
        ttk.Button(medical_buttons, text="Save Medical Info", command=self.save_medical_info).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(medical_buttons, text="Include in Emergency", command=self.include_medical_in_emergency).grid(row=0, column=1)
        
        # Emergency Events History
        events_frame = ttk.LabelFrame(emergency_content, text="Emergency Events", padding="10")
        events_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        events_frame.columnconfigure(0, weight=1)
        
        # Events list
        self.emergency_events_tree = ttk.Treeview(events_frame, columns=("timestamp", "type", "node", "status"), show="headings", height=6)
        self.emergency_events_tree.heading("timestamp", text="Timestamp")
        self.emergency_events_tree.heading("type", text="Type")
        self.emergency_events_tree.heading("node", text="Node")
        self.emergency_events_tree.heading("status", text="Status")
        
        self.emergency_events_tree.column("timestamp", width=150)
        self.emergency_events_tree.column("type", width=100)
        self.emergency_events_tree.column("node", width=100)
        self.emergency_events_tree.column("status", width=80)
        
        self.emergency_events_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Events buttons
        events_buttons = ttk.Frame(events_frame)
        events_buttons.grid(row=1, column=0, pady=10)
        
        ttk.Button(events_buttons, text="Refresh Events", command=self.refresh_emergency_events).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(events_buttons, text="Acknowledge", command=self.acknowledge_emergency_event).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(events_buttons, text="Clear History", command=self.clear_emergency_history).grid(row=0, column=2)
        
        # Initialize emergency system
        self.emergency_contacts = []
        self.load_emergency_contacts()
        self.load_medical_info()
        self.refresh_emergency_events()
        
    def create_analytics_tab(self):
        """Create analytics and charts tab"""
        analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(analytics_frame, text="Analytics")
        
        # Configure grid
        analytics_frame.columnconfigure(0, weight=1)
        analytics_frame.rowconfigure(0, weight=1)
        
        # Create main paned window
        analytics_paned = ttk.PanedWindow(analytics_frame, orient=tk.VERTICAL)
        analytics_paned.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Top section - Network Statistics
        stats_frame = ttk.LabelFrame(analytics_paned, text="Network Statistics", padding="10")
        analytics_paned.add(stats_frame, weight=1)
        
        # Statistics display
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Network overview statistics
        self.analytics_stats_labels = {}
        stats_data = [
            ("Total Messages", "0"),
            ("Active Nodes (24h)", "0"),
            ("Messages (24h)", "0"),
            ("Emergency Events (24h)", "0"),
            ("Avg. Battery Level", "N/A"),
            ("Network Uptime", "N/A")
        ]
        
        for i, (label, value) in enumerate(stats_data):
            row = i // 3
            col = (i % 3) * 2
            
            ttk.Label(stats_grid, text=f"{label}:", font=("Arial", 9, "bold")).grid(row=row, column=col, sticky=tk.W, padx=(0, 10), pady=5)
            label_widget = ttk.Label(stats_grid, text=value, font=("Arial", 9), foreground="blue")
            label_widget.grid(row=row, column=col+1, sticky=tk.W, padx=(0, 20), pady=5)
            self.analytics_stats_labels[label] = label_widget
        
        # Refresh button
        ttk.Button(stats_frame, text="Refresh Stats", command=self.refresh_analytics_stats).grid(row=1, column=0, pady=(10, 0))
        
        # Charts section
        charts_frame = ttk.LabelFrame(analytics_paned, text="Charts & Trends", padding="10")
        analytics_paned.add(charts_frame, weight=3)
        
        if MATPLOTLIB_AVAILABLE:
            # Chart notebook
            self.chart_notebook = ttk.Notebook(charts_frame)
            self.chart_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
            
            # Create chart tabs
            self.create_message_activity_chart()
            self.create_battery_trends_chart()
            self.create_network_health_chart()
            
            # Chart controls
            chart_controls = ttk.Frame(charts_frame)
            chart_controls.grid(row=1, column=0, sticky=(tk.W, tk.E))
            
            ttk.Button(chart_controls, text="Refresh Charts", command=self.refresh_all_charts).grid(row=0, column=0, padx=(0, 10))
            
            # Time range selection
            ttk.Label(chart_controls, text="Time Range:").grid(row=0, column=1, padx=(0, 10))
            self.time_range_var = tk.StringVar(value="24 hours")
            time_range_combo = ttk.Combobox(chart_controls, textvariable=self.time_range_var, 
                                           values=["1 hour", "6 hours", "24 hours", "7 days", "30 days"], 
                                           state="readonly", width=10)
            time_range_combo.grid(row=0, column=2, padx=(0, 10))
            time_range_combo.bind('<<ComboboxSelected>>', self.on_time_range_changed)
            
        else:
            # Fallback message if matplotlib not available
            ttk.Label(charts_frame, text="Charts not available\n(matplotlib not installed)", 
                     font=("Arial", 12), foreground="red").grid(row=0, column=0, padx=50, pady=50)
        
        # Export section
        export_frame = ttk.LabelFrame(analytics_paned, text="Data Export", padding="10")
        analytics_paned.add(export_frame, weight=1)
        
        # Export controls
        export_controls = ttk.Frame(export_frame)
        export_controls.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(export_controls, text="Export Data:").grid(row=0, column=0, padx=(0, 10))
        
        # Export buttons
        export_buttons = [
            ("Messages CSV", lambda: self.export_data_table("messages", "csv")),
            ("Nodes CSV", lambda: self.export_data_table("nodes", "csv")),
            ("Metrics JSON", lambda: self.export_analytics_summary()),
            ("Network Graph", lambda: self.export_network_graph())
        ]
        
        for i, (text, command) in enumerate(export_buttons):
            ttk.Button(export_controls, text=text, command=command).grid(row=0, column=i+1, padx=(0, 10))
        
        # Configure grid weights
        charts_frame.columnconfigure(0, weight=1)
        charts_frame.rowconfigure(0, weight=1)
        export_frame.columnconfigure(0, weight=1)
        
        # Initialize analytics
        self.refresh_analytics_stats()
        if MATPLOTLIB_AVAILABLE:
            self.refresh_all_charts()
            
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
        
        # List of supported regions (from class constant)
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
        
        # Actions frame
        actions_frame = ttk.LabelFrame(config_content, text="Actions", padding="10")
        actions_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # Action buttons
        ttk.Button(actions_frame, text="Reboot Device", command=self.reboot_device).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(actions_frame, text="Factory Reset", command=self.factory_reset).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(actions_frame, text="Get Device Info", command=self.get_device_info).grid(row=0, column=2, padx=5, pady=2)
        
        # Configuration Profiles Section
        profiles_frame = ttk.LabelFrame(config_content, text="Configuration Profiles", padding="10")
        profiles_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
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
        devices_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
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
        
        # Initialize profiles and devices
        self.config_profiles = {}
        self.managed_devices = []
        self.current_profile = "Default"
        self.load_config_profiles()
        self.load_managed_devices()
        self.scan_devices()
        
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
        
        # Subscribe to routing and acknowledgment events
        pub.subscribe(self.on_routing_error, "meshtastic.routing.error")
        pub.subscribe(self.on_ack_received, "meshtastic.ack.received")
        
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
                
                # Log successful connection
                self.data_logger.log_connection_event("connect", param, True)
                
                self.update_status("Connected")
                self.root.after(0, self.on_connect_success)
                
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                # Log failed connection
                self.data_logger.log_connection_event("connect", param, False, str(e))
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
        
    def on_routing_error(self, packet, interface):
        """Handle routing error"""
        self.message_queue.put(('routing_error', packet))
        
    def on_ack_received(self, packet, interface):
        """Handle ACK received"""
        self.message_queue.put(('ack_received', packet))
        
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
        elif msg_type == 'routing_error':
            self.handle_routing_error(data)
        elif msg_type == 'ack_received':
            self.handle_ack_received(data)
            
    def handle_routing_error(self, packet):
        """Handle routing error for message status updates"""
        try:
            # Try to find the original message that failed
            error_id = packet.get('id', None)
            if error_id:
                # Update message status to failed
                self.update_message_status(error_id, 'failed')
                logger.warning(f"Message routing failed for ID: {error_id}")
        except Exception as e:
            logger.error(f"Error handling routing error: {e}")
            
    def handle_ack_received(self, packet):
        """Handle ACK received for message status updates"""
        try:
            # Extract the message ID that was acknowledged
            ack_id = packet.get('id', None)
            if ack_id:
                # Update message status to delivered
                self.update_message_status(ack_id, 'delivered')
                logger.info(f"Message delivered successfully, ID: {ack_id}")
        except Exception as e:
            logger.error(f"Error handling ACK: {e}")
            
    def update_message_status(self, message_id, status):
        """Update message status in tracking and database"""
        try:
            # Update in-memory tracking
            if message_id in self.message_status_tracking:
                self.message_status_tracking[message_id]['status'] = status
                
            # Update in database
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE messages SET status = ? WHERE message_id = ?
            ''', (status, message_id))
            conn.commit()
            conn.close()
            
            # Update display if needed
            self.refresh_message_display()
            
        except Exception as e:
            logger.error(f"Error updating message status: {e}")
            
    def refresh_message_display(self):
        """Refresh the message display with updated status indicators"""
        try:
            # Get recent messages from database
            messages = self.data_logger.get_message_history(limit=50)
            
            # Clear and repopulate display
            self.message_display.config(state=tk.NORMAL)
            self.message_display.delete(1.0, tk.END)
            
            for msg in reversed(messages):  # Reverse to show oldest first
                timestamp = datetime.fromisoformat(msg[5]) if msg[5] else datetime.now()
                timestamp_str = timestamp.strftime("%H:%M:%S")
                
                from_node = msg[2] if msg[2] else 'Unknown'
                to_node = msg[3] if msg[3] else 'Unknown'
                message_text = msg[4] if msg[4] else ''
                status = msg[6] if msg[6] else 'unknown'
                
                # Choose status indicator
                if status == 'delivered':
                    status_indicator = "✓✓"
                elif status == 'sent':
                    status_indicator = "✓"
                elif status == 'failed':
                    status_indicator = "❌"
                else:
                    status_indicator = "?"
                
                # Format display name
                display_from = "You" if from_node == 'LOCAL' else (msg[12] if msg[12] else from_node)
                display_to = msg[13] if msg[13] else to_node
                
                msg_line = f"[{timestamp_str}] {display_from} -> {display_to}: {message_text} {status_indicator}\n"
                
                self.message_display.insert(tk.END, msg_line)
                
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error refreshing message display: {e}")
            
    def display_message(self, packet):
        """Display received message in chat"""
        try:
            # Extract message info
            from_id = packet.get('fromId', 'Unknown')
            to_id = packet.get('toId', 'Unknown')
            timestamp = datetime.now()
            timestamp_str = timestamp.strftime("%H:%M:%S")
            
            # Get message text
            message_text = ""
            if 'decoded' in packet:
                decoded = packet['decoded']
                if 'text' in decoded:
                    message_text = decoded['text']
                elif 'payload' in decoded:
                    message_text = f"[Binary data: {len(decoded['payload'])} bytes]"
            
            # Generate message ID for tracking
            message_id = hashlib.md5(f"{from_id}{to_id}{message_text}{timestamp}".encode()).hexdigest()[:8]
            
            # Log message to database
            message_data = {
                'message_id': message_id,
                'from_node': from_id,
                'to_node': to_id,
                'message_text': message_text,
                'timestamp': timestamp,
                'status': 'received',
                'hop_count': packet.get('hopLimit', 0),
                'rssi': packet.get('rssi', None),
                'snr': packet.get('snr', None),
                'message_type': 'text' if message_text and not message_text.startswith('[Binary') else 'binary'
            }
            self.data_logger.log_message(message_data)
            
            # Format message with status indicator
            status_indicator = "✓" if message_data['status'] == 'received' else "?"
            msg_line = f"[{timestamp_str}] {from_id} -> {to_id}: {message_text} {status_indicator}\n"
            
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
            timestamp = datetime.now()
            timestamp_str = timestamp.strftime("%H:%M:%S")
            
            # Generate message ID for tracking
            message_id = hashlib.md5(f"YOU{dest}{message}{timestamp}".encode()).hexdigest()[:8]
            
            # Log sent message
            message_data = {
                'message_id': message_id,
                'from_node': 'LOCAL',
                'to_node': dest,
                'message_text': message,
                'timestamp': timestamp,
                'status': 'sent',
                'hop_count': 0,
                'message_type': 'text'
            }
            self.data_logger.log_message(message_data)
            
            # Track message status
            self.message_status_tracking[message_id] = {
                'status': 'sent',
                'timestamp': timestamp,
                'want_ack': want_ack
            }
            
            # Display with status indicator
            status_indicator = "📤" if want_ack else "✓"
            msg_line = f"[{timestamp_str}] You -> {dest}: {message} {status_indicator}\n"
            
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
        
    def on_search_messages(self, event=None):
        """Handle message search"""
        search_term = self.search_entry.get().strip()
        if len(search_term) < 2:
            return
            
        # Search messages in database
        search_results = self.data_logger.search_messages(search_term)
        
        # Display search results
        self.message_display.config(state=tk.NORMAL)
        self.message_display.delete(1.0, tk.END)
        
        if search_results:
            self.message_display.insert(tk.END, f"Search results for '{search_term}':\n\n")
            
            for msg in reversed(search_results):
                timestamp = datetime.fromisoformat(msg[5]) if msg[5] else datetime.now()
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                from_node = msg[2] if msg[2] else 'Unknown'
                to_node = msg[3] if msg[3] else 'Unknown'
                message_text = msg[4] if msg[4] else ''
                status = msg[6] if msg[6] else 'unknown'
                
                # Choose status indicator
                if status == 'delivered':
                    status_indicator = "✓✓"
                elif status == 'sent':
                    status_indicator = "✓"
                elif status == 'failed':
                    status_indicator = "❌"
                else:
                    status_indicator = "?"
                
                # Format display name
                display_from = "You" if from_node == 'LOCAL' else (msg[12] if msg[12] else from_node)
                display_to = msg[13] if msg[13] else to_node
                
                msg_line = f"[{timestamp_str}] {display_from} -> {display_to}: {message_text} {status_indicator}\n"
                
                self.message_display.insert(tk.END, msg_line)
        else:
            self.message_display.insert(tk.END, f"No messages found for '{search_term}'")
            
        self.message_display.see(tk.END)
        self.message_display.config(state=tk.DISABLED)
        
    def clear_search(self):
        """Clear search and show recent messages"""
        self.search_entry.delete(0, tk.END)
        self.load_message_history()
        
    def load_message_history(self):
        """Load message history from database"""
        try:
            # Get messages from database
            messages = self.data_logger.get_message_history(limit=100)
            
            # Display messages
            self.message_display.config(state=tk.NORMAL)
            self.message_display.delete(1.0, tk.END)
            
            if messages:
                self.message_display.insert(tk.END, "Message History:\n\n")
                
                for msg in reversed(messages):
                    timestamp = datetime.fromisoformat(msg[5]) if msg[5] else datetime.now()
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    
                    from_node = msg[2] if msg[2] else 'Unknown'
                    to_node = msg[3] if msg[3] else 'Unknown'
                    message_text = msg[4] if msg[4] else ''
                    status = msg[6] if msg[6] else 'unknown'
                    
                    # Choose status indicator
                    if status == 'delivered':
                        status_indicator = "✓✓"
                    elif status == 'sent':
                        status_indicator = "✓"
                    elif status == 'failed':
                        status_indicator = "❌"
                    else:
                        status_indicator = "?"
                    
                    # Format display name
                    display_from = "You" if from_node == 'LOCAL' else (msg[12] if msg[12] else from_node)
                    display_to = msg[13] if msg[13] else to_node
                    
                    msg_line = f"[{timestamp_str}] {display_from} -> {display_to}: {message_text} {status_indicator}\n"
                    
                    self.message_display.insert(tk.END, msg_line)
            else:
                self.message_display.insert(tk.END, "No message history found.")
                
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error loading message history: {e}")
            messagebox.showerror("Error", f"Failed to load message history: {e}")
            
    def refresh_network_topology(self):
        """Refresh the network topology visualization"""
        try:
            # Clear existing network data
            self.network_nodes.clear()
            self.network_connections.clear()
            
            # Add local device if connected
            if self.interface:
                local_position = self.get_local_device_position()
                if local_position:
                    lat, lon, name = local_position
                    self.network_nodes["LOCAL"] = {
                        'name': name,
                        'x': 300,  # Center position
                        'y': 200,
                        'color': 'blue',
                        'size': 20,
                        'is_local': True,
                        'battery': 'N/A',
                        'last_seen': 'Connected'
                    }
                else:
                    self.network_nodes["LOCAL"] = {
                        'name': 'Local Device',
                        'x': 300,
                        'y': 200,
                        'color': 'blue',
                        'size': 20,
                        'is_local': True,
                        'battery': 'N/A',
                        'last_seen': 'Connected'
                    }
            
            # Add remote nodes
            for node_id, node in self.nodes.items():
                user = node.get('user', {})
                device_metrics = node.get('deviceMetrics', {})
                
                name = user.get('longName', f'Node {node_id}')
                battery = device_metrics.get('batteryLevel', 'N/A')
                last_heard = node.get('lastHeard', 'N/A')
                
                # Determine node color based on battery level
                if battery == 'N/A':
                    color = 'gray'
                elif battery > 75:
                    color = 'green'
                elif battery > 25:
                    color = 'orange'
                else:
                    color = 'red'
                
                # Calculate position (arrange in circle around local node)
                angle = (hash(str(node_id)) % 360) * (math.pi / 180)
                radius = 150
                x = 300 + radius * math.cos(angle)
                y = 200 + radius * math.sin(angle)
                
                self.network_nodes[str(node_id)] = {
                    'name': name,
                    'x': x,
                    'y': y,
                    'color': color,
                    'size': 15,
                    'is_local': False,
                    'battery': f"{battery}%" if battery != 'N/A' else 'N/A',
                    'last_seen': datetime.fromtimestamp(last_heard).strftime("%H:%M:%S") if last_heard != 'N/A' else 'N/A'
                }
                
                # Add connection from local to remote node
                if "LOCAL" in self.network_nodes:
                    self.network_connections[f"LOCAL-{node_id}"] = {
                        'from': "LOCAL",
                        'to': str(node_id),
                        'hops': 1,
                        'rssi': node.get('rssi', 'N/A'),
                        'snr': node.get('snr', 'N/A'),
                        'strength': 'good' if node.get('rssi', -100) > -80 else 'poor'
                    }
            
            # Draw the network
            self.draw_network_topology()
            
            # Update statistics
            self.update_network_statistics()
            
        except Exception as e:
            logger.error(f"Error refreshing network topology: {e}")
            
    def draw_network_topology(self):
        """Draw the network topology on canvas"""
        try:
            # Clear canvas
            self.network_canvas.delete("all")
            
            # Draw connections first (so they appear behind nodes)
            for conn_id, conn in self.network_connections.items():
                from_node = self.network_nodes.get(conn['from'])
                to_node = self.network_nodes.get(conn['to'])
                
                if from_node and to_node:
                    # Determine line color based on connection strength
                    if conn['strength'] == 'good':
                        line_color = 'green'
                        line_width = 3
                    else:
                        line_color = 'red'
                        line_width = 2
                    
                    # Draw connection line
                    self.network_canvas.create_line(
                        from_node['x'], from_node['y'],
                        to_node['x'], to_node['y'],
                        fill=line_color,
                        width=line_width,
                        tags=("connection", conn_id)
                    )
                    
                    # Draw hop count label
                    mid_x = (from_node['x'] + to_node['x']) / 2
                    mid_y = (from_node['y'] + to_node['y']) / 2
                    self.network_canvas.create_text(
                        mid_x, mid_y,
                        text=f"H{conn['hops']}",
                        fill="blue",
                        font=("Arial", 8),
                        tags=("hop_label", conn_id)
                    )
            
            # Draw nodes
            for node_id, node in self.network_nodes.items():
                # Draw node circle
                x, y = node['x'], node['y']
                size = node['size']
                
                node_circle = self.network_canvas.create_oval(
                    x - size, y - size,
                    x + size, y + size,
                    fill=node['color'],
                    outline='black',
                    width=2,
                    tags=("node", node_id)
                )
                
                # Draw node label
                self.network_canvas.create_text(
                    x, y + size + 15,
                    text=node['name'][:12],  # Truncate long names
                    font=("Arial", 8),
                    tags=("node_label", node_id)
                )
                
                # Draw battery level for non-local nodes
                if not node['is_local'] and node['battery'] != 'N/A':
                    self.network_canvas.create_text(
                        x, y + size + 25,
                        text=node['battery'],
                        font=("Arial", 7),
                        fill="gray",
                        tags=("battery_label", node_id)
                    )
            
            # Set canvas scroll region
            self.network_canvas.configure(scrollregion=self.network_canvas.bbox("all"))
            
        except Exception as e:
            logger.error(f"Error drawing network topology: {e}")
            
    def update_network_statistics(self):
        """Update network statistics display"""
        try:
            # Calculate network metrics
            total_nodes = len(self.network_nodes)
            active_nodes = sum(1 for node in self.network_nodes.values() if node['is_local'] or node['last_seen'] != 'N/A')
            total_connections = len(self.network_connections)
            
            # Calculate average hop count
            if self.network_connections:
                avg_hops = sum(conn['hops'] for conn in self.network_connections.values()) / len(self.network_connections)
            else:
                avg_hops = 0
            
            # Network diameter (maximum hops between any two nodes)
            network_diameter = max((conn['hops'] for conn in self.network_connections.values()), default=0)
            
            # Update labels
            self.network_metrics_labels["Total Nodes"].config(text=str(total_nodes))
            self.network_metrics_labels["Active Nodes"].config(text=str(active_nodes))
            self.network_metrics_labels["Total Connections"].config(text=str(total_connections))
            self.network_metrics_labels["Average Hop Count"].config(text=f"{avg_hops:.1f}")
            self.network_metrics_labels["Network Diameter"].config(text=str(network_diameter))
            
        except Exception as e:
            logger.error(f"Error updating network statistics: {e}")
            
    def on_network_canvas_click(self, event):
        """Handle network canvas click"""
        try:
            # Find clicked item
            closest_items = self.network_canvas.find_closest(event.x, event.y)
            
            # Check if there are any items on the canvas
            if not closest_items:
                return
                
            item = closest_items[0]
            tags = self.network_canvas.gettags(item)
            
            # Check if it's a node
            for tag in tags:
                if tag.startswith("node") and tag != "node":
                    node_id = tag
                    self.selected_network_node = node_id
                    self.show_node_details(node_id)
                    break
                    
        except Exception as e:
            logger.error(f"Error handling canvas click: {e}")
            
    def on_network_canvas_drag(self, event):
        """Handle network canvas drag"""
        pass  # Placeholder for node dragging functionality
        
    def on_network_canvas_release(self, event):
        """Handle network canvas mouse release"""
        pass  # Placeholder for node dragging functionality
        
    def show_node_details(self, node_id):
        """Show details for selected node"""
        try:
            node = self.network_nodes.get(node_id)
            if not node:
                return
                
            # Clear previous node info
            for widget in self.selected_node_info.winfo_children():
                widget.destroy()
                
            # Display node information
            info_text = f"Node: {node['name']}\n"
            info_text += f"ID: {node_id}\n"
            info_text += f"Battery: {node['battery']}\n"
            info_text += f"Last Seen: {node['last_seen']}\n"
            info_text += f"Type: {'Local Device' if node['is_local'] else 'Remote Node'}"
            
            info_label = ttk.Label(self.selected_node_info, text=info_text, font=("Arial", 9))
            info_label.grid(row=0, column=0, sticky=tk.W)
            
            # Update connections tree
            self.update_connections_tree(node_id)
            
        except Exception as e:
            logger.error(f"Error showing node details: {e}")
            
    def update_connections_tree(self, node_id):
        """Update connections tree for selected node"""
        try:
            # Clear existing items
            for item in self.connections_tree.get_children():
                self.connections_tree.delete(item)
                
            # Find connections for this node
            connections = []
            for conn_id, conn in self.network_connections.items():
                if conn['from'] == node_id or conn['to'] == node_id:
                    target_node = conn['to'] if conn['from'] == node_id else conn['from']
                    target_name = self.network_nodes.get(target_node, {}).get('name', target_node)
                    
                    connections.append({
                        'target': target_name,
                        'hops': conn['hops'],
                        'rssi': conn['rssi'],
                        'snr': conn['snr']
                    })
            
            # Add connections to tree
            for conn in connections:
                self.connections_tree.insert("", tk.END, values=(
                    conn['target'],
                    conn['hops'],
                    conn['rssi'],
                    conn['snr']
                ))
                
        except Exception as e:
            logger.error(f"Error updating connections tree: {e}")
            
    def auto_layout_network(self):
        """Auto-layout network nodes"""
        try:
            # Simple circular layout
            if not self.network_nodes:
                return
                
            nodes = list(self.network_nodes.keys())
            center_x, center_y = 300, 200
            radius = 150
            
            # Place local node in center
            if "LOCAL" in self.network_nodes:
                self.network_nodes["LOCAL"]['x'] = center_x
                self.network_nodes["LOCAL"]['y'] = center_y
                nodes.remove("LOCAL")
            
            # Place other nodes in circle
            for i, node_id in enumerate(nodes):
                angle = (2 * math.pi * i) / len(nodes)
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                self.network_nodes[node_id]['x'] = x
                self.network_nodes[node_id]['y'] = y
            
            # Redraw network
            self.draw_network_topology()
            
        except Exception as e:
            logger.error(f"Error auto-layouting network: {e}")
            
    def export_network_data(self):
        """Export network data"""
        try:
            # Prepare network data for export
            network_data = {
                'nodes': self.network_nodes,
                'connections': self.network_connections,
                'statistics': {
                    'total_nodes': len(self.network_nodes),
                    'total_connections': len(self.network_connections),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Export to JSON
            json_data = json.dumps(network_data, indent=2)
            
            # Save to file
            filename = f"network_topology_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                f.write(json_data)
                
            messagebox.showinfo("Export Complete", f"Network data exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting network data: {e}")
            messagebox.showerror("Error", f"Failed to export network data: {e}")
             
    def create_message_activity_chart(self):
        """Create message activity chart"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        # Create frame for message activity chart
        msg_chart_frame = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(msg_chart_frame, text="Message Activity")
        
        # Create matplotlib figure
        self.msg_activity_figure = Figure(figsize=(8, 4), dpi=100)
        self.msg_activity_ax = self.msg_activity_figure.add_subplot(111)
        
        # Create canvas
        self.msg_activity_canvas = FigureCanvasTkAgg(self.msg_activity_figure, msg_chart_frame)
        self.msg_activity_canvas.draw()
        self.msg_activity_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_battery_trends_chart(self):
        """Create battery trends chart"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        # Create frame for battery trends chart
        battery_chart_frame = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(battery_chart_frame, text="Battery Trends")
        
        # Create matplotlib figure
        self.battery_trends_figure = Figure(figsize=(8, 4), dpi=100)
        self.battery_trends_ax = self.battery_trends_figure.add_subplot(111)
        
        # Create canvas
        self.battery_trends_canvas = FigureCanvasTkAgg(self.battery_trends_figure, battery_chart_frame)
        self.battery_trends_canvas.draw()
        self.battery_trends_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_network_health_chart(self):
        """Create network health chart"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        # Create frame for network health chart
        health_chart_frame = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(health_chart_frame, text="Network Health")
        
        # Create matplotlib figure
        self.network_health_figure = Figure(figsize=(8, 4), dpi=100)
        self.network_health_ax = self.network_health_figure.add_subplot(111)
        
        # Create canvas
        self.network_health_canvas = FigureCanvasTkAgg(self.network_health_figure, health_chart_frame)
        self.network_health_canvas.draw()
        self.network_health_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def refresh_analytics_stats(self):
        """Refresh analytics statistics"""
        try:
            # Get statistics from database
            stats = self.data_logger.get_network_statistics()
            
            # Update labels
            self.analytics_stats_labels["Total Messages"].config(text=str(stats.get('total_messages', 0)))
            self.analytics_stats_labels["Active Nodes (24h)"].config(text=str(stats.get('active_nodes', 0)))
            self.analytics_stats_labels["Messages (24h)"].config(text=str(stats.get('messages_24h', 0)))
            self.analytics_stats_labels["Emergency Events (24h)"].config(text=str(stats.get('emergency_events_24h', 0)))
            
            # Calculate average battery level
            avg_battery = self.calculate_average_battery()
            self.analytics_stats_labels["Avg. Battery Level"].config(text=f"{avg_battery:.1f}%" if avg_battery else "N/A")
            
            # Network uptime (placeholder)
            self.analytics_stats_labels["Network Uptime"].config(text="N/A")
            
        except Exception as e:
            logger.error(f"Error refreshing analytics stats: {e}")
            
    def calculate_average_battery(self):
        """Calculate average battery level of active nodes"""
        try:
            total_battery = 0
            node_count = 0
            
            for node in self.nodes.values():
                device_metrics = node.get('deviceMetrics', {})
                battery = device_metrics.get('batteryLevel', None)
                if battery is not None:
                    total_battery += battery
                    node_count += 1
            
            return total_battery / node_count if node_count > 0 else None
            
        except Exception as e:
            logger.error(f"Error calculating average battery: {e}")
            return None
            
    def refresh_all_charts(self):
        """Refresh all charts"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            self.update_message_activity_chart()
            self.update_battery_trends_chart()
            self.update_network_health_chart()
        except Exception as e:
            logger.error(f"Error refreshing charts: {e}")
            
    def update_message_activity_chart(self):
        """Update message activity chart"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            # Get time range
            time_range = self.time_range_var.get()
            hours = {"1 hour": 1, "6 hours": 6, "24 hours": 24, "7 days": 168, "30 days": 720}[time_range]
            
            # Get message data from database
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour, COUNT(*) as count
                FROM messages 
                WHERE timestamp > datetime('now', '-{} hours')
                GROUP BY hour
                ORDER BY hour
            '''.format(hours))
            
            data = cursor.fetchall()
            conn.close()
            
            if data:
                hours_list = [datetime.fromisoformat(row[0]) for row in data]
                counts = [row[1] for row in data]
                
                # Clear and plot
                self.msg_activity_ax.clear()
                self.msg_activity_ax.plot(hours_list, counts, marker='o', linewidth=2, markersize=4)
                self.msg_activity_ax.set_title('Message Activity Over Time')
                self.msg_activity_ax.set_xlabel('Time')
                self.msg_activity_ax.set_ylabel('Messages per Hour')
                self.msg_activity_ax.grid(True, alpha=0.3)
                
                # Format x-axis
                self.msg_activity_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.msg_activity_ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, hours//12)))
                
                self.msg_activity_figure.autofmt_xdate()
            else:
                self.msg_activity_ax.clear()
                self.msg_activity_ax.text(0.5, 0.5, 'No message data available', 
                                        transform=self.msg_activity_ax.transAxes, 
                                        ha='center', va='center', fontsize=14)
                self.msg_activity_ax.set_title('Message Activity Over Time')
            
            self.msg_activity_canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating message activity chart: {e}")
            
    def update_battery_trends_chart(self):
        """Update battery trends chart"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            # Get time range
            time_range = self.time_range_var.get()
            hours = {"1 hour": 1, "6 hours": 6, "24 hours": 24, "7 days": 168, "30 days": 720}[time_range]
            
            # Get battery data from database
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT nm.timestamp, nm.battery_level, n.node_name
                FROM node_metrics nm
                JOIN nodes n ON nm.node_id = n.node_id
                WHERE nm.timestamp > datetime('now', '-{} hours')
                AND nm.battery_level IS NOT NULL
                ORDER BY nm.timestamp
            '''.format(hours))
            
            data = cursor.fetchall()
            conn.close()
            
            if data:
                # Group by node
                node_data = {}
                for row in data:
                    timestamp = datetime.fromisoformat(row[0])
                    battery = row[1]
                    node_name = row[2] or 'Unknown'
                    
                    if node_name not in node_data:
                        node_data[node_name] = {'times': [], 'batteries': []}
                    
                    node_data[node_name]['times'].append(timestamp)
                    node_data[node_name]['batteries'].append(battery)
                
                # Plot
                self.battery_trends_ax.clear()
                
                for node_name, data_dict in node_data.items():
                    self.battery_trends_ax.plot(data_dict['times'], data_dict['batteries'], 
                                              marker='o', linewidth=2, markersize=3, label=node_name)
                
                self.battery_trends_ax.set_title('Battery Levels Over Time')
                self.battery_trends_ax.set_xlabel('Time')
                self.battery_trends_ax.set_ylabel('Battery Level (%)')
                self.battery_trends_ax.set_ylim(0, 100)
                self.battery_trends_ax.grid(True, alpha=0.3)
                self.battery_trends_ax.legend()
                
                # Format x-axis
                self.battery_trends_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.battery_trends_ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, hours//12)))
                
                self.battery_trends_figure.autofmt_xdate()
            else:
                self.battery_trends_ax.clear()
                self.battery_trends_ax.text(0.5, 0.5, 'No battery data available', 
                                          transform=self.battery_trends_ax.transAxes, 
                                          ha='center', va='center', fontsize=14)
                self.battery_trends_ax.set_title('Battery Levels Over Time')
            
            self.battery_trends_canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating battery trends chart: {e}")
            
    def update_network_health_chart(self):
        """Update network health chart"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            # Create a pie chart of node status
            self.network_health_ax.clear()
            
            # Count nodes by status
            active_nodes = len([n for n in self.nodes.values() if n.get('lastHeard', 0) > time.time() - 3600])
            inactive_nodes = len(self.nodes) - active_nodes
            
            # Count nodes by battery level
            good_battery = len([n for n in self.nodes.values() if n.get('deviceMetrics', {}).get('batteryLevel', 0) > 75])
            medium_battery = len([n for n in self.nodes.values() if 25 < n.get('deviceMetrics', {}).get('batteryLevel', 0) <= 75])
            low_battery = len([n for n in self.nodes.values() if 0 < n.get('deviceMetrics', {}).get('batteryLevel', 0) <= 25])
            
            if self.nodes:
                # Node status pie chart
                status_labels = ['Active', 'Inactive']
                status_sizes = [active_nodes, inactive_nodes]
                status_colors = ['green', 'red']
                
                self.network_health_ax.pie(status_sizes, labels=status_labels, colors=status_colors, 
                                         autopct='%1.1f%%', startangle=90)
                self.network_health_ax.set_title('Network Node Status')
            else:
                self.network_health_ax.text(0.5, 0.5, 'No network data available', 
                                          transform=self.network_health_ax.transAxes, 
                                          ha='center', va='center', fontsize=14)
                self.network_health_ax.set_title('Network Node Status')
            
            self.network_health_canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating network health chart: {e}")
            
    def on_time_range_changed(self, event=None):
        """Handle time range selection change"""
        if MATPLOTLIB_AVAILABLE:
            self.refresh_all_charts()
            
    def export_data_table(self, table_name, format_type):
        """Export data table to file"""
        try:
            data = self.data_logger.export_data(table_name, format_type)
            if data:
                filename = f"{table_name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
                with open(filename, 'w') as f:
                    f.write(data)
                messagebox.showinfo("Export Complete", f"Data exported to {filename}")
            else:
                messagebox.showwarning("Export Failed", "No data to export")
        except Exception as e:
            logger.error(f"Error exporting data table: {e}")
            messagebox.showerror("Error", f"Failed to export data: {e}")
            
    def export_analytics_summary(self):
        """Export analytics summary as JSON"""
        try:
            # Gather analytics data
            stats = self.data_logger.get_network_statistics()
            avg_battery = self.calculate_average_battery()
            
            analytics_data = {
                'summary': stats,
                'average_battery': avg_battery,
                'node_count': len(self.nodes),
                'active_nodes': len([n for n in self.nodes.values() if n.get('lastHeard', 0) > time.time() - 3600]),
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Export to JSON
            filename = f"analytics_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(analytics_data, f, indent=2)
                
            messagebox.showinfo("Export Complete", f"Analytics summary exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting analytics summary: {e}")
            messagebox.showerror("Error", f"Failed to export analytics summary: {e}")
            
    def export_network_graph(self):
        """Export network graph as image"""
        try:
            if not MATPLOTLIB_AVAILABLE:
                messagebox.showwarning("Export Failed", "Matplotlib not available for graph export")
                return
                
            # Create a new figure for export
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Draw network topology
            for conn_id, conn in self.network_connections.items():
                from_node = self.network_nodes.get(conn['from'])
                to_node = self.network_nodes.get(conn['to'])
                
                if from_node and to_node:
                    color = 'green' if conn['strength'] == 'good' else 'red'
                    ax.plot([from_node['x'], to_node['x']], [from_node['y'], to_node['y']], 
                           color=color, linewidth=2, alpha=0.7)
            
            # Draw nodes
            for node_id, node in self.network_nodes.items():
                ax.scatter(node['x'], node['y'], s=node['size']*20, c=node['color'], 
                          edgecolors='black', linewidths=2)
                ax.annotate(node['name'], (node['x'], node['y']), 
                           xytext=(5, 5), textcoords='offset points', fontsize=8)
            
            ax.set_title('Network Topology')
            ax.set_xlabel('X Position')
            ax.set_ylabel('Y Position')
            ax.grid(True, alpha=0.3)
            
            # Save to file
            filename = f"network_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            messagebox.showinfo("Export Complete", f"Network graph exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting network graph: {e}")
            messagebox.showerror("Error", f"Failed to export network graph: {e}")
             
    def update_node_data(self, node):
        """Update node data"""
        if not node:
            return
            
        node_id = node.get('num', 'Unknown')
        self.nodes[node_id] = node
        
        # Extract node data for logging
        user = node.get('user', {})
        position = node.get('position', {})
        device_metrics = node.get('deviceMetrics', {})
        
        # Prepare node data for logging
        node_data = {
            'node_id': str(node_id),
            'node_name': user.get('longName', ''),
            'short_name': user.get('shortName', ''),
            'hardware_model': user.get('hwModel', ''),
            'firmware_version': node.get('firmwareVersion', ''),
            'is_local': False
        }
        
        # Add position data if available
        if 'latitude' in position and 'longitude' in position:
            node_data.update({
                'latitude': position['latitude'],
                'longitude': position['longitude'],
                'altitude': position.get('altitude', None)
            })
        
        # Add metrics if available
        if device_metrics:
            node_data.update({
                'battery_level': device_metrics.get('batteryLevel', None),
                'voltage': device_metrics.get('voltage', None),
                'current': device_metrics.get('current', None),
                'utilization': device_metrics.get('channelUtilization', None),
                'airtime': device_metrics.get('airUtilTx', None)
            })
        
        # Log node update
        self.data_logger.log_node_update(node_data)
        
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
        
        # Update network topology if tab exists
        if hasattr(self, 'network_canvas'):
            self.refresh_network_topology()
        
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
        
    def get_initial_map_position(self):
        """Get initial map position from GPS or IP geolocation"""
        # First try to get GPS location from local device
        local_position = self.get_local_device_position()
        if local_position:
            lat, lon, name = local_position
            return (lat, lon, "GPS")
        
        # If no GPS and we're online, try IP geolocation
        if self.internet_available:
            ip_location = self.get_ip_location()
            if ip_location:
                lat, lon, location_name = ip_location
                return (lat, lon, f"IP ({location_name})")
        
        return None
    
    def get_ip_location(self):
        """Get approximate location from IP address"""
        try:
            logger.info("Attempting to get location from IP address...")
            
            # Try multiple IP geolocation services for reliability
            services = [
                {
                    'url': 'https://ipapi.co/json/',
                    'lat_key': 'latitude',
                    'lon_key': 'longitude',
                    'location_key': 'city'
                },
                {
                    'url': 'http://ip-api.com/json/',
                    'lat_key': 'lat',
                    'lon_key': 'lon',
                    'location_key': 'city'
                },
                {
                    'url': 'https://ipinfo.io/json',
                    'lat_key': 'loc',  # Special handling needed
                    'lon_key': 'loc',  # Special handling needed
                    'location_key': 'city'
                }
            ]
            
            for service in services:
                try:
                    headers = {
                        'User-Agent': 'MeshtasticUI/1.0 (Educational/Research Use)'
                    }
                    response = requests.get(service['url'], headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Special handling for ipinfo.io
                        if service['url'] == 'https://ipinfo.io/json':
                            if 'loc' in data:
                                lat_str, lon_str = data['loc'].split(',')
                                lat, lon = float(lat_str), float(lon_str)
                            else:
                                continue
                        else:
                            # Standard handling for other services
                            if service['lat_key'] in data and service['lon_key'] in data:
                                lat = float(data[service['lat_key']])
                                lon = float(data[service['lon_key']])
                            else:
                                continue
                        
                        # Get location name
                        location_name = data.get(service['location_key'], 'Unknown')
                        
                        # Validate coordinates
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            logger.info(f"Got IP location: {lat}, {lon} ({location_name})")
                            return (lat, lon, location_name)
                        else:
                            logger.warning(f"Invalid coordinates from {service['url']}: {lat}, {lon}")
                            continue
                            
                except requests.exceptions.RequestException as e:
                    logger.debug(f"IP geolocation service {service['url']} failed: {e}")
                    continue
                except (ValueError, KeyError) as e:
                    logger.debug(f"Error parsing response from {service['url']}: {e}")
                    continue
            
            logger.info("All IP geolocation services failed")
            return None
            
        except Exception as e:
            logger.error(f"Error getting IP location: {e}")
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
                        # Map region enum values back to names using class constant
                        region_num = config.lora.region
                        region_name = self.REGION_ENUM_TO_NAME.get(region_num, f"Unknown ({region_num})")
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
                    # Map region names to enum values using class constant
                    if selected_region in self.REGION_NAME_TO_ENUM:
                        config.lora.region = self.REGION_NAME_TO_ENUM[selected_region]
                        
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
        
    def activate_emergency_beacon(self):
        """Activate emergency beacon"""
        try:
            if not self.interface:
                messagebox.showwarning("Warning", "Not connected to device")
                return
            
            if messagebox.askyesno("Confirm Emergency", 
                                 "Are you sure you want to activate the emergency beacon?\n\n" +
                                 "This will broadcast your location and emergency message to all nodes."):
                
                # Get current location
                local_position = self.get_local_device_position()
                if local_position:
                    lat, lon, name = local_position
                    
                    # Create emergency message with location
                    emergency_msg = f"🚨 EMERGENCY BEACON ACTIVATED 🚨\n"
                    emergency_msg += f"Location: {lat:.6f}, {lon:.6f}\n"
                    emergency_msg += f"From: {name}\n"
                    emergency_msg += f"Message: {self.emergency_message_var.get()}\n"
                    emergency_msg += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # Broadcast emergency message
                    self.interface.sendText(emergency_msg, destinationId="^all", wantAck=True)
                    
                    # Log emergency event
                    self.data_logger.log_emergency_event("LOCAL", "beacon", lat, lon, self.emergency_message_var.get())
                    
                    # Update UI
                    self.emergency_active = True
                    self.emergency_status_label.config(text="🚨 EMERGENCY BEACON ACTIVE", foreground="red")
                    self.emergency_beacon_button.config(text="🚨 BEACON ACTIVE", state="disabled")
                    
                    # Send to emergency contacts
                    self.notify_emergency_contacts("EMERGENCY BEACON", emergency_msg)
                    
                    messagebox.showinfo("Emergency Beacon", "Emergency beacon activated!\nLocation broadcasted to all nodes.")
                else:
                    # No GPS available
                    emergency_msg = f"🚨 EMERGENCY BEACON ACTIVATED 🚨\n"
                    emergency_msg += f"From: Local Device\n"
                    emergency_msg += f"Message: {self.emergency_message_var.get()}\n"
                    emergency_msg += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    emergency_msg += f"NOTE: GPS location not available"
                    
                    self.interface.sendText(emergency_msg, destinationId="^all", wantAck=True)
                    
                    # Log emergency event without location
                    self.data_logger.log_emergency_event("LOCAL", "beacon", None, None, self.emergency_message_var.get())
                    
                    # Update UI
                    self.emergency_active = True
                    self.emergency_status_label.config(text="🚨 EMERGENCY BEACON ACTIVE", foreground="red")
                    self.emergency_beacon_button.config(text="🚨 BEACON ACTIVE", state="disabled")
                    
                    messagebox.showinfo("Emergency Beacon", "Emergency beacon activated!\nMessage broadcasted to all nodes.")
                    
        except Exception as e:
            logger.error(f"Error activating emergency beacon: {e}")
            messagebox.showerror("Error", f"Failed to activate emergency beacon: {e}")
            
    def activate_panic_button(self):
        """Activate panic button (silent emergency alert)"""
        try:
            if not self.interface:
                messagebox.showwarning("Warning", "Not connected to device")
                return
            
            if messagebox.askyesno("Confirm Panic Alert", 
                                 "Send silent emergency alert to emergency contacts?"):
                
                # Get current location
                local_position = self.get_local_device_position()
                lat, lon = (None, None)
                if local_position:
                    lat, lon, name = local_position
                
                # Create silent emergency message
                panic_msg = f"🚨 PANIC ALERT 🚨\n"
                panic_msg += f"Silent emergency alert activated\n"
                if lat and lon:
                    panic_msg += f"Location: {lat:.6f}, {lon:.6f}\n"
                panic_msg += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                # Send to emergency contacts only (not broadcast)
                self.notify_emergency_contacts("PANIC ALERT", panic_msg)
                
                # Log emergency event
                self.data_logger.log_emergency_event("LOCAL", "panic", lat, lon, "Silent panic alert")
                
                messagebox.showinfo("Panic Alert", "Silent emergency alert sent to emergency contacts")
                
        except Exception as e:
            logger.error(f"Error activating panic button: {e}")
            messagebox.showerror("Error", f"Failed to activate panic button: {e}")
            
    def send_emergency_message(self):
        """Send emergency message to all contacts"""
        try:
            if not self.interface:
                messagebox.showwarning("Warning", "Not connected to device")
                return
            
            message = self.emergency_message_var.get()
            if not message:
                messagebox.showwarning("Warning", "Please enter an emergency message")
                return
            
            # Send to all emergency contacts
            for contact in self.emergency_contacts:
                try:
                    self.interface.sendText(f"🚨 EMERGENCY: {message}", 
                                          destinationId=contact['node_id'], wantAck=True)
                except Exception as e:
                    logger.error(f"Failed to send emergency message to {contact['name']}: {e}")
            
            # Also broadcast
            self.interface.sendText(f"🚨 EMERGENCY: {message}", destinationId="^all", wantAck=True)
            
            # Log emergency event
            local_position = self.get_local_device_position()
            lat, lon = (None, None)
            if local_position:
                lat, lon, name = local_position
                
            self.data_logger.log_emergency_event("LOCAL", "message", lat, lon, message)
            
            messagebox.showinfo("Emergency Message", "Emergency message sent to all contacts")
            
        except Exception as e:
            logger.error(f"Error sending emergency message: {e}")
            messagebox.showerror("Error", f"Failed to send emergency message: {e}")
            
    def cancel_emergency(self):
        """Cancel emergency state"""
        try:
            if self.emergency_active:
                if messagebox.askyesno("Cancel Emergency", "Cancel emergency beacon?"):
                    
                    # Send cancellation message
                    cancel_msg = "🟢 EMERGENCY CANCELLED - All clear"
                    self.interface.sendText(cancel_msg, destinationId="^all", wantAck=True)
                    
                    # Notify emergency contacts
                    self.notify_emergency_contacts("EMERGENCY CANCELLED", cancel_msg)
                    
                    # Reset UI
                    self.emergency_active = False
                    self.emergency_status_label.config(text="Emergency beacon inactive", foreground="gray")
                    self.emergency_beacon_button.config(text="🚨 EMERGENCY BEACON", state="normal")
                    
                    # Log cancellation
                    self.data_logger.log_emergency_event("LOCAL", "cancelled", None, None, "Emergency cancelled")
                    
                    messagebox.showinfo("Emergency Cancelled", "Emergency state cancelled")
            else:
                messagebox.showinfo("No Emergency", "No active emergency to cancel")
                
        except Exception as e:
            logger.error(f"Error cancelling emergency: {e}")
            messagebox.showerror("Error", f"Failed to cancel emergency: {e}")
            
    def notify_emergency_contacts(self, event_type, message):
        """Notify emergency contacts"""
        try:
            if not self.interface:
                return
                
            # Sort contacts by priority
            sorted_contacts = sorted(self.emergency_contacts, 
                                   key=lambda x: {"High": 0, "Normal": 1, "Low": 2}.get(x['priority'], 1))
            
            for contact in sorted_contacts:
                try:
                    full_message = f"🚨 {event_type} 🚨\n{message}"
                    self.interface.sendText(full_message, destinationId=contact['node_id'], wantAck=True)
                    logger.info(f"Emergency notification sent to {contact['name']} ({contact['node_id']})")
                except Exception as e:
                    logger.error(f"Failed to notify emergency contact {contact['name']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying emergency contacts: {e}")
            
    def add_emergency_contact(self):
        """Add emergency contact"""
        try:
            name = self.contact_name_var.get().strip()
            node_id = self.contact_node_var.get().strip()
            priority = self.contact_priority_var.get()
            
            if not name or not node_id:
                messagebox.showwarning("Warning", "Please enter both name and node ID")
                return
            
            # Check if contact already exists
            for contact in self.emergency_contacts:
                if contact['node_id'] == node_id:
                    messagebox.showwarning("Warning", "Contact with this node ID already exists")
                    return
            
            # Add contact
            contact = {
                'name': name,
                'node_id': node_id,
                'priority': priority
            }
            self.emergency_contacts.append(contact)
            
            # Update display
            self.update_emergency_contacts_display()
            
            # Save to database
            self.save_emergency_contacts()
            
            # Clear input fields
            self.contact_name_var.set("")
            self.contact_node_var.set("")
            self.contact_priority_var.set("Normal")
            
            messagebox.showinfo("Contact Added", f"Emergency contact '{name}' added successfully")
            
        except Exception as e:
            logger.error(f"Error adding emergency contact: {e}")
            messagebox.showerror("Error", f"Failed to add emergency contact: {e}")
            
    def remove_emergency_contact(self):
        """Remove selected emergency contact"""
        try:
            selection = self.emergency_contacts_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a contact to remove")
                return
            
            # Get selected contact
            item = self.emergency_contacts_tree.item(selection[0])
            node_id = item['values'][1]
            
            # Remove from list
            self.emergency_contacts = [c for c in self.emergency_contacts if c['node_id'] != node_id]
            
            # Update display
            self.update_emergency_contacts_display()
            
            # Save to database
            self.save_emergency_contacts()
            
            messagebox.showinfo("Contact Removed", "Emergency contact removed successfully")
            
        except Exception as e:
            logger.error(f"Error removing emergency contact: {e}")
            messagebox.showerror("Error", f"Failed to remove emergency contact: {e}")
            
    def update_emergency_contacts_display(self):
        """Update emergency contacts display"""
        try:
            # Clear existing items
            for item in self.emergency_contacts_tree.get_children():
                self.emergency_contacts_tree.delete(item)
            
            # Add contacts
            for contact in self.emergency_contacts:
                self.emergency_contacts_tree.insert("", tk.END, values=(
                    contact['name'],
                    contact['node_id'],
                    contact['priority']
                ))
                
        except Exception as e:
            logger.error(f"Error updating emergency contacts display: {e}")
            
    def save_emergency_contacts(self):
        """Save emergency contacts to database"""
        try:
            contacts_json = json.dumps(self.emergency_contacts)
            
            # Save to database or file
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO config_profiles (profile_name, device_config, created_date, last_used)
                VALUES (?, ?, ?, ?)
            ''', ("emergency_contacts", contacts_json, datetime.now(), datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving emergency contacts: {e}")
            
    def load_emergency_contacts(self):
        """Load emergency contacts from database"""
        try:
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT device_config FROM config_profiles 
                WHERE profile_name = ?
            ''', ("emergency_contacts",))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                self.emergency_contacts = json.loads(result[0])
                self.update_emergency_contacts_display()
                
        except Exception as e:
            logger.error(f"Error loading emergency contacts: {e}")
            self.emergency_contacts = []
            
    def save_medical_info(self):
        """Save medical information"""
        try:
            medical_info = {}
            for field, var in self.medical_info_vars.items():
                medical_info[field] = var.get()
            
            medical_json = json.dumps(medical_info)
            
            # Save to database
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO config_profiles (profile_name, device_config, created_date, last_used)
                VALUES (?, ?, ?, ?)
            ''', ("medical_info", medical_json, datetime.now(), datetime.now()))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Medical Info", "Medical information saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving medical info: {e}")
            messagebox.showerror("Error", f"Failed to save medical information: {e}")
            
    def load_medical_info(self):
        """Load medical information"""
        try:
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT device_config FROM config_profiles 
                WHERE profile_name = ?
            ''', ("medical_info",))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                medical_info = json.loads(result[0])
                for field, var in self.medical_info_vars.items():
                    var.set(medical_info.get(field, ""))
                    
        except Exception as e:
            logger.error(f"Error loading medical info: {e}")
            
    def include_medical_in_emergency(self):
        """Include medical information in emergency message"""
        try:
            medical_info = []
            for field, var in self.medical_info_vars.items():
                value = var.get().strip()
                if value:
                    field_name = field.replace('_', ' ').title()
                    medical_info.append(f"{field_name}: {value}")
            
            if medical_info:
                medical_text = "\\n".join(medical_info)
                current_msg = self.emergency_message_var.get()
                new_msg = f"{current_msg}\\n\\nMEDICAL INFO:\\n{medical_text}"
                self.emergency_message_var.set(new_msg)
                messagebox.showinfo("Medical Info", "Medical information added to emergency message")
            else:
                messagebox.showwarning("Warning", "No medical information to include")
                
        except Exception as e:
            logger.error(f"Error including medical info in emergency: {e}")
            messagebox.showerror("Error", f"Failed to include medical information: {e}")
            
    def refresh_emergency_events(self):
        """Refresh emergency events display"""
        try:
            # Clear existing items
            for item in self.emergency_events_tree.get_children():
                self.emergency_events_tree.delete(item)
            
            # Get emergency events from database
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, event_type, node_id, acknowledged, message
                FROM emergency_events
                ORDER BY timestamp DESC
                LIMIT 100
            ''')
            
            events = cursor.fetchall()
            conn.close()
            
            # Add events to tree
            for event in events:
                timestamp = datetime.fromisoformat(event[0]).strftime("%Y-%m-%d %H:%M:%S")
                event_type = event[1]
                node_id = event[2]
                acknowledged = event[3]
                status = "Acknowledged" if acknowledged else "Active"
                
                self.emergency_events_tree.insert("", tk.END, values=(
                    timestamp,
                    event_type,
                    node_id,
                    status
                ))
                
        except Exception as e:
            logger.error(f"Error refreshing emergency events: {e}")
            
    def acknowledge_emergency_event(self):
        """Acknowledge selected emergency event"""
        try:
            selection = self.emergency_events_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select an event to acknowledge")
                return
            
            # Get selected event
            item = self.emergency_events_tree.item(selection[0])
            timestamp = item['values'][0]
            
            # Update database
            conn = sqlite3.connect(self.data_logger.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE emergency_events 
                SET acknowledged = 1
                WHERE timestamp = ?
            ''', (timestamp,))
            
            conn.commit()
            conn.close()
            
            # Refresh display
            self.refresh_emergency_events()
            
            messagebox.showinfo("Event Acknowledged", "Emergency event acknowledged")
            
        except Exception as e:
            logger.error(f"Error acknowledging emergency event: {e}")
            messagebox.showerror("Error", f"Failed to acknowledge emergency event: {e}")
            
    def clear_emergency_history(self):
        """Clear emergency events history"""
        try:
            if messagebox.askyesno("Clear History", "Are you sure you want to clear all emergency events history?"):
                conn = sqlite3.connect(self.data_logger.db_path)
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM emergency_events')
                
                conn.commit()
                conn.close()
                
                # Refresh display
                self.refresh_emergency_events()
                
                messagebox.showinfo("History Cleared", "Emergency events history cleared")
                
        except Exception as e:
            logger.error(f"Error clearing emergency history: {e}")
            messagebox.showerror("Error", f"Failed to clear emergency history: {e}")

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
                'connection_type': self.connection_type.get(),
                'connection_param': self.connection_param.get(),
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
            self.connection_type.set(config.get('connection_type', 'Serial'))
            self.connection_param.set(config.get('connection_param', 'auto'))
            
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
            filename = f"meshtastic_profile_{profile_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo("Export Complete", f"Profile exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting config profile: {e}")
            messagebox.showerror("Error", f"Failed to export configuration profile: {e}")
            
    def import_config_profile(self):
        """Import configuration profile from file"""
        try:
            from tkinter import filedialog
            
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
                if profile_name not in ["emergency_contacts", "medical_info"]:  # Skip non-config profiles
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
        # We don't automatically load it, user needs to click Load Profile
        pass
        
    def scan_devices(self):
        """Scan for available Meshtastic devices"""
        try:
            if not MESHTASTIC_AVAILABLE:
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
            # Simple dialog to add device
            from tkinter import simpledialog
            
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
            
            # Update connection settings
            self.connection_type.set(device_type)
            self.connection_param.set(device_path)
            
            # Attempt connection
            self.connect_meshtastic()
            
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
            
            # Update connection settings
            self.connection_type.set(device_type)
            self.connection_param.set(device_path)
            
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

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = MeshtasticUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()