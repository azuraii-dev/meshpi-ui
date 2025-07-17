import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import math
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import tkintermapview
    MAPVIEW_AVAILABLE = True
except ImportError as e:
    logger.warning(f"tkintermapview not available, using coordinate plot fallback: {e}")
    MAPVIEW_AVAILABLE = False

class MapUI:
    def __init__(self, parent, interface_manager, data_logger):
        self.parent = parent
        self.interface_manager = interface_manager
        self.data_logger = data_logger
        
        # Map-related variables
        self.map_widget = None
        self.coordinate_canvas = None
        self.map_markers = {}
        self.use_real_map = False
        self.internet_available = False
        self.map_layer_var = tk.StringVar(value="OpenStreetMap")
        self.map_layers = {}
        
        # Initialize UI
        self.create_widgets()
        
        # Check internet connectivity and initialize map
        self.check_internet_connectivity()
        
    def create_widgets(self):
        """Create map visualization tab with real map or coordinate plot fallback"""
        # Configure grid
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Create map content
        map_content = ttk.Frame(self.parent, padding="10")
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
        self.parent.after(1000, self.initialize_map)
        
    def check_internet_connectivity(self):
        """Check if internet is available for map tiles"""
        def check_connectivity():
            try:
                # Try to reach OpenStreetMap with proper headers
                logger.info("Checking internet connectivity to OpenStreetMap...")
                headers = {
                    'User-Agent': 'MeshtasticUI/1.0 (Educational/Research Use)',
                    'Accept': 'image/png,image/*;q=0.8,*/*;q=0.5',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'close'
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
        logger.info("Creating real map (online mode)")
        
        # Create map widget (online mode) with responsive sizing
        self.map_widget = tkintermapview.TkinterMapView(
            self.map_viz_frame,
            width=600,
            height=500,
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
        
        # Add resize binding for responsive map sizing
        self.map_viz_frame.bind('<Configure>', self._on_map_frame_resize)
        
        # Apply performance optimizations
        self.optimize_map_performance()
        
        # Update frame title with current layer
        self.update_map_frame_title()
        
    def create_map_layer_controls(self):
        """Create map layer selection controls"""
        layer_frame = ttk.Frame(self.map_viz_frame)
        layer_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        layer_frame.columnconfigure(1, weight=1)
        
        # Map layer selection
        ttk.Label(layer_frame, text="Map Layer:").grid(row=0, column=0, padx=(0, 10))
        
        # Define available map layers (optimized for performance)
        self.map_layers = {
            "OpenStreetMap": {
                "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                "max_zoom": 19,
                "attribution": "© OpenStreetMap contributors"
            },
            "Satellite (Esri)": {
                "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                "max_zoom": 18,  # Reduced for better performance
                "attribution": "© Esri, Maxar, Earthstar Geographics"
            },
            "Satellite (Google)": {
                "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                "max_zoom": 18,  # Reduced for better performance
                "attribution": "© Google"
            },
            "Hybrid (Google)": {
                "url": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                "max_zoom": 18,  # Reduced for better performance
                "attribution": "© Google"
            },
            "Topo (OpenTopo)": {
                "url": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
                "max_zoom": 16,  # Reduced for better performance
                "attribution": "© OpenTopoMap, © OpenStreetMap contributors"
            },
            "Light Theme": {
                "url": "https://cartodb-basemaps-c.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
                "max_zoom": 18,  # Reduced for better performance
                "attribution": "© CartoDB, © OpenStreetMap contributors"
            },
            "Dark Theme": {
                "url": "https://cartodb-basemaps-c.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
                "max_zoom": 18,  # Reduced for better performance
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
        """Apply the selected map layer to the map widget with improved tile loading"""
        if not self.map_widget or not hasattr(self, 'map_layers') or not self.map_layers:
            return
            
        try:
            selected_layer = self.map_layer_var.get()
            if selected_layer not in self.map_layers:
                logger.warning(f"Selected layer '{selected_layer}' not found in map_layers")
                return
                
            layer_config = self.map_layers[selected_layer]
            
            # Store current state before changing layers
            try:
                current_position = self.map_widget.get_position()
                current_zoom = getattr(self.map_widget, 'zoom', 10)
            except:
                current_position = None
                current_zoom = 10
            
            # Set the tile server with error handling
            self.map_widget.set_tile_server(
                layer_config["url"], 
                max_zoom=layer_config["max_zoom"]
            )
            
            # Force a refresh to clear old tiles
            if hasattr(self.map_widget, 'refresh'):
                self.map_widget.refresh()
            
            # Restore position if we had one
            if current_position:
                try:
                    self.map_widget.set_position(current_position[0], current_position[1])
                    self.map_widget.set_zoom(current_zoom)
                except:
                    pass
            
            logger.info(f"Applied map layer: {selected_layer}")
            
        except Exception as e:
            logger.error(f"Error applying map layer: {e}")
            # Fall back to OpenStreetMap
            try:
                self.map_widget.set_tile_server(
                    "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", 
                    max_zoom=19
                )
                logger.info("Fallback to OpenStreetMap applied")
            except Exception as fallback_error:
                logger.error(f"Error applying fallback layer: {fallback_error}")
                
    def on_layer_changed(self, event=None):
        """Handle map layer selection change with improved tile loading"""
        if not hasattr(self, 'map_widget') or not self.map_widget:
            return
            
        # Prevent rapid layer switching
        if hasattr(self, '_layer_switch_pending') and self._layer_switch_pending:
            return
            
        self._layer_switch_pending = True
        
        try:
            # Apply new layer (this now handles position preservation internally)
            self.apply_map_layer()
            self.update_map_frame_title()
            
            # Allow sufficient time for tiles to load and render
            self.parent.after(500, self._layer_switch_complete)
            
        except Exception as e:
            logger.error(f"Error in layer change: {e}")
            self._layer_switch_pending = False
    
    def _layer_switch_complete(self):
        """Mark layer switch as complete"""
        self._layer_switch_pending = False
    
    def _on_map_frame_resize(self, event=None):
        """Handle map frame resize for responsive sizing"""
        if not hasattr(self, 'map_widget') or not self.map_widget:
            return
            
        try:
            # Get the frame size
            frame_width = self.map_viz_frame.winfo_width()
            frame_height = self.map_viz_frame.winfo_height()
            
            # Only resize if we have valid dimensions
            if frame_width > 100 and frame_height > 100:
                # Account for controls and padding
                map_width = max(400, frame_width - 20)
                map_height = max(300, frame_height - 80)  # Leave space for controls
                
                # Update map widget size
                self.map_widget.configure(width=map_width, height=map_height)
                
        except Exception as e:
            logger.debug(f"Error resizing map: {e}")
    
    def optimize_map_performance(self):
        """Apply performance optimizations to the map widget"""
        if not hasattr(self, 'map_widget') or not self.map_widget:
            return
            
        try:
            # Set reasonable tile cache size if available
            if hasattr(self.map_widget, 'set_tile_cache_size'):
                self.map_widget.set_tile_cache_size(100)  # Cache 100 tiles
                
            # Disable unnecessary features for better performance
            if hasattr(self.map_widget, 'set_double_click_zoom'):
                self.map_widget.set_double_click_zoom(True)
                
        except Exception as e:
            logger.debug(f"Could not apply performance optimizations: {e}")
                
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
                # Try different zoom methods - get_zoom() may not exist in this version
                try:
                    current_zoom = self.map_widget.get_zoom()
                except AttributeError:
                    # Fallback: use zoom property or default zoom
                    current_zoom = getattr(self.map_widget, 'zoom', 10)
                
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
        
        self.coordinate_canvas = tk.Canvas(self.map_viz_frame, bg="lightgray", width=600, height=500)
        self.coordinate_canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add grid lines
        self.draw_coordinate_grid()
        
        # Add instructions
        self.coordinate_canvas.create_text(200, 50, text="Coordinate Plot\n(No internet/map tiles)", 
                                         justify=tk.CENTER, font=("Arial", 10), fill="#6B46C1")
        
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
            canvas.create_line(i, 0, i, height, fill="#E5E7EB", width=1, tags="grid")
        for i in range(0, height, 50):
            canvas.create_line(0, i, width, i, fill="#E5E7EB", width=1, tags="grid")
            
        # Draw center lines
        canvas.create_line(width//2, 0, width//2, height, fill="#6B46C1", width=2, tags="grid")
        canvas.create_line(0, height//2, width, height//2, fill="#6B46C1", width=2, tags="grid")
        
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
        
    def get_local_device_position(self):
        """Get the GPS position of the local device if available"""
        if not self.interface_manager.is_connected():
            return None
            
        try:
            # Use interface manager's get_local_position method
            position = self.interface_manager.get_local_position()
            if position:
                lat, lon, name = position
                return (lat, lon, name)
            return None
                    
        except Exception as e:
            logger.debug(f"Could not get local device position: {e}")
            
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
        
    def update_nodes_display(self, nodes):
        """Update nodes tree display and map"""
        # Clear existing items
        for item in self.nodes_tree.get_children():
            self.nodes_tree.delete(item)
            
        # Get local node position for distance calculations
        local_position = None
        if self.interface_manager.is_connected():
            try:
                position = self.interface_manager.get_local_position()
                if position:
                    lat, lon, name = position
                    local_position = (lat, lon)
            except Exception as e:
                logger.debug(f"Could not get local position: {e}")
                
        # Add local device first (if connected and has GPS)
        local_device_position = self.get_local_device_position()
        if local_device_position:
            try:
                lat, lon, name = local_device_position
                
                # Get battery info for local device
                battery = "N/A"
                if self.interface_manager.interface and hasattr(self.interface_manager.interface, 'getMyNodeInfo'):
                    try:
                        node_info = self.interface_manager.interface.getMyNodeInfo()
                        if node_info and 'deviceMetrics' in node_info:
                            device_metrics = node_info['deviceMetrics']
                            if 'batteryLevel' in device_metrics:
                                battery = f"{device_metrics['batteryLevel']}%"
                    except Exception as e:
                        logger.debug(f"Could not get local device battery: {e}")
                
                # Add local device to tree
                self.nodes_tree.insert("", tk.END, values=(f"{name} (You)", "LOCAL", "0m", battery, "Connected"))
                
            except Exception as e:
                logger.error(f"Error adding local device to display: {e}")
        
        # Add remote nodes
        for node_id, node in nodes.items():
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
                
        # Update map with nodes
        self.update_map_nodes(nodes)
        
    def update_map_nodes(self, nodes=None):
        """Update nodes on the map"""
        try:
            if self.use_real_map and self.map_widget:
                self.update_real_map_nodes(nodes)
            elif self.coordinate_canvas:
                self.update_coordinate_plot_nodes(nodes)
        except Exception as e:
            logger.error(f"Error updating map nodes: {e}")
            
    def update_real_map_nodes(self, nodes):
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
            positioned_nodes.append((lat, lon, f"{name} (You)", "#6B46C1"))
        
        # Add remote nodes
        if nodes:
            for node_id, node in nodes.items():
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
                
    def update_coordinate_plot_nodes(self, nodes):
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
            positioned_nodes.append((lat, lon, f"{name} (You)", "#6B46C1"))
        
        # Add remote nodes
        if nodes:
            for node_id, node in nodes.items():
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
            radius = 10 if color == "#6B46C1" else 8  # Make local device marker slightly larger
            outline_width = 3 if color == "#6B46C1" else 2  # Make local device outline thicker
            self.coordinate_canvas.create_oval(x - radius, y - radius, x + radius, y + radius, 
                                             fill=color, outline="black", width=outline_width, tags="node")
            
            # Add label
            self.coordinate_canvas.create_text(x, y - radius - 10, text=name, 
                                             font=("Arial", 8), fill="black", tags="node") 