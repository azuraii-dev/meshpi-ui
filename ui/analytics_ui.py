import tkinter as tk
from tkinter import ttk, messagebox
import json
import sqlite3
import logging
import time
from datetime import datetime

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

class AnalyticsUI:
    def __init__(self, parent, interface_manager, data_logger):
        self.parent = parent
        self.interface_manager = interface_manager
        self.data_logger = data_logger
        
        # Create analytics interface
        self.create_widgets()
        
        # Initialize analytics
        self.refresh_analytics_stats()
        if MATPLOTLIB_AVAILABLE:
            self.refresh_all_charts()
            
    def create_widgets(self):
        """Create analytics and charts tab"""
        # Configure grid
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Create main paned window
        analytics_paned = ttk.PanedWindow(self.parent, orient=tk.VERTICAL)
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
            # Get nodes from interface manager
            nodes = self.interface_manager.get_nodes()
            if not nodes:
                return None
                
            total_battery = 0
            node_count = 0
            
            for node in nodes.values():
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
                
                # Format x-axis based on time range
                if hours <= 6:
                    # For short periods, show hours and minutes
                    self.msg_activity_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    self.msg_activity_ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                elif hours <= 24:
                    # For 1 day, show hours
                    self.msg_activity_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    self.msg_activity_ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
                elif hours <= 168:  # 7 days
                    # For a week, show days
                    self.msg_activity_ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                    self.msg_activity_ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                else:  # 30 days
                    # For a month, show dates with fewer ticks
                    self.msg_activity_ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                    self.msg_activity_ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
                
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
                
                # Format x-axis based on time range
                if hours <= 6:
                    # For short periods, show hours and minutes
                    self.battery_trends_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    self.battery_trends_ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                elif hours <= 24:
                    # For 1 day, show hours
                    self.battery_trends_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    self.battery_trends_ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
                elif hours <= 168:  # 7 days
                    # For a week, show days
                    self.battery_trends_ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                    self.battery_trends_ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                else:  # 30 days
                    # For a month, show dates with fewer ticks
                    self.battery_trends_ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                    self.battery_trends_ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
                
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
            # Get nodes from interface manager
            nodes = self.interface_manager.get_nodes()
            
            # Create a pie chart of node status
            self.network_health_ax.clear()
            
            if nodes:
                # Count nodes by status
                current_time = time.time()
                active_nodes = len([n for n in nodes.values() 
                                  if n.get('lastHeard', 0) and n.get('lastHeard', 0) > current_time - 3600])
                inactive_nodes = len(nodes) - active_nodes
                
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
                filename = f"exports/{table_name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
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
            
            # Get nodes count
            nodes = self.interface_manager.get_nodes()
            node_count = len(nodes) if nodes else 0
            active_nodes = len([n for n in nodes.values() if n.get('lastHeard', 0) > time.time() - 3600]) if nodes else 0
            
            analytics_data = {
                'summary': stats,
                'average_battery': avg_battery,
                'node_count': node_count,
                'active_nodes': active_nodes,
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Export to JSON
            filename = f"exports/analytics_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
                
            # Get nodes from interface manager
            nodes = self.interface_manager.get_nodes()
            if not nodes:
                messagebox.showwarning("Export Failed", "No node data available")
                return
                
            # Create a new figure for export
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Simple network visualization
            ax.set_title('Network Topology')
            ax.set_xlabel('Node Index')
            ax.set_ylabel('Battery Level (%)')
            
            # Plot nodes as scatter points
            node_names = []
            battery_levels = []
            
            for node in nodes.values():
                user = node.get('user', {})
                name = user.get('longName', 'Unknown')
                battery = node.get('deviceMetrics', {}).get('batteryLevel', 0)
                
                node_names.append(name)
                battery_levels.append(battery)
                
            if node_names:
                x_positions = range(len(node_names))
                ax.scatter(x_positions, battery_levels, s=100, alpha=0.7)
                ax.set_xticks(x_positions)
                ax.set_xticklabels(node_names, rotation=45, ha='right')
                ax.set_ylim(0, 100)
                ax.grid(True, alpha=0.3)
            
            # Save to file
            filename = f"exports/network_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            messagebox.showinfo("Export Complete", f"Network graph exported to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting network graph: {e}")
            messagebox.showerror("Error", f"Failed to export network graph: {e}")
            
    def update_data(self, nodes=None):
        """Update analytics with new data"""
        self.refresh_analytics_stats()
        if MATPLOTLIB_AVAILABLE:
            self.refresh_all_charts() 