import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NetworkUI:
    def __init__(self, parent, interface_manager, data_logger):
        self.parent = parent
        self.interface_manager = interface_manager
        self.data_logger = data_logger
        
        # Network topology data
        self.network_nodes = {}
        self.network_connections = {}
        self.selected_network_node = None
        
        # Create network interface
        self.create_widgets()
        
        # Initialize network display
        self.refresh_network_topology()
        
    def create_widgets(self):
        """Create network topology visualization tab"""
        # Configure grid
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Create main paned window
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
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
        
        # Bind canvas events
        self.network_canvas.bind("<Button-1>", self.on_network_canvas_click)
        self.network_canvas.bind("<B1-Motion>", self.on_network_canvas_drag)
        self.network_canvas.bind("<ButtonRelease-1>", self.on_network_canvas_release)
        
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
        
    def refresh_network_topology(self, nodes=None):
        """Refresh the network topology visualization"""
        try:
            # Clear existing network data
            self.network_nodes.clear()
            self.network_connections.clear()
            
            # Add local device if connected
            if self.interface_manager.is_connected():
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
            if nodes:
                for node_id, node in nodes.items():
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
            filename = f"exports/network_topology_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                f.write(json_data)
                
            messagebox.showinfo("Export Complete", f"Network data exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting network data: {e}")
            messagebox.showerror("Error", f"Failed to export network data: {e}")
            
    def update_nodes(self, nodes):
        """Update network topology with new node data"""
        self.refresh_network_topology(nodes) 