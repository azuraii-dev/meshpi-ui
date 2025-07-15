import tkinter as tk
from tkinter import ttk, messagebox
import json
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EmergencyUI:
    def __init__(self, parent, interface_manager, data_logger):
        self.parent = parent
        self.interface_manager = interface_manager
        self.data_logger = data_logger
        
        # Emergency state
        self.emergency_active = False
        self.emergency_contacts = []
        self.medical_info_vars = {}
        
        # Create emergency interface
        self.create_widgets()
        
        # Load data
        self.load_emergency_contacts()
        self.load_medical_info()
        self.refresh_emergency_events()
        
        # Refresh available nodes
        self.refresh_available_nodes()
        
    def create_widgets(self):
        """Create emergency features tab with dual-pane layout"""
        # Configure main grid
        self.parent.columnconfigure(0, weight=1)
        self.parent.columnconfigure(1, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Create left and right panes
        left_pane = ttk.Frame(self.parent, padding="5")
        left_pane.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_pane.columnconfigure(0, weight=1)
        left_pane.rowconfigure(1, weight=1)  # Make contacts section expandable
        
        right_pane = ttk.Frame(self.parent, padding="5")
        right_pane.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_pane.columnconfigure(0, weight=1)
        right_pane.rowconfigure(1, weight=1)  # Make events section expandable
        
        # === LEFT PANE ===
        
        # Emergency Beacon Section
        beacon_frame = ttk.LabelFrame(left_pane, text="Emergency Beacon", padding="10")
        beacon_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        beacon_frame.columnconfigure(1, weight=1)
        
        # Emergency status
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
        
        # Emergency Contacts Section (Left Pane)
        contacts_frame = ttk.LabelFrame(left_pane, text="Emergency Contacts", padding="10")
        contacts_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        contacts_frame.columnconfigure(0, weight=1)
        contacts_frame.rowconfigure(0, weight=1)  # Make the treeview expandable
        
        # Contacts list
        contacts_list_frame = ttk.Frame(contacts_frame)
        contacts_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        contacts_list_frame.columnconfigure(0, weight=1)
        contacts_list_frame.rowconfigure(0, weight=1)
        
        self.emergency_contacts_tree = ttk.Treeview(contacts_list_frame, columns=("name", "node_id", "priority"), show="headings", height=8)
        self.emergency_contacts_tree.heading("name", text="Name")
        self.emergency_contacts_tree.heading("node_id", text="Node ID")
        self.emergency_contacts_tree.heading("priority", text="Priority")
        
        self.emergency_contacts_tree.column("name", width=120)
        self.emergency_contacts_tree.column("node_id", width=80)
        self.emergency_contacts_tree.column("priority", width=70)
        
        self.emergency_contacts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add contact form
        add_contact_frame = ttk.Frame(contacts_frame)
        add_contact_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        add_contact_frame.columnconfigure(1, weight=1)
        
        ttk.Label(add_contact_frame, text="Select Node:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Node selection frame
        node_select_frame = ttk.Frame(add_contact_frame)
        node_select_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        node_select_frame.columnconfigure(0, weight=1)
        
        self.available_nodes_var = tk.StringVar()
        self.available_nodes_combo = ttk.Combobox(node_select_frame, textvariable=self.available_nodes_var, 
                                                 state="readonly", width=25)
        self.available_nodes_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.available_nodes_combo.bind('<<ComboboxSelected>>', self.on_node_selected)
        
        ttk.Button(node_select_frame, text="Refresh", command=self.refresh_available_nodes, width=8).grid(row=0, column=1)
        
        ttk.Label(add_contact_frame, text="Contact Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.contact_name_var = tk.StringVar()
        ttk.Entry(add_contact_frame, textvariable=self.contact_name_var, width=20).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(add_contact_frame, text="Node ID:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.contact_node_var = tk.StringVar()
        node_id_entry = ttk.Entry(add_contact_frame, textvariable=self.contact_node_var, width=20, state="readonly")
        node_id_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(add_contact_frame, text="Priority:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.contact_priority_var = tk.StringVar(value="Normal")
        priority_combo = ttk.Combobox(add_contact_frame, textvariable=self.contact_priority_var, 
                                     values=["High", "Normal", "Low"], state="readonly", width=10)
        priority_combo.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Help text
        help_text = ttk.Label(add_contact_frame, 
                             text="Select a node from the dropdown above. Nodes appear as you receive messages from them.",
                             foreground="gray", font=("Arial", 8))
        help_text.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Contact buttons
        contact_buttons = ttk.Frame(contacts_frame)
        contact_buttons.grid(row=2, column=0, pady=10)
        
        ttk.Button(contact_buttons, text="Add Contact", command=self.add_emergency_contact).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(contact_buttons, text="Remove Contact", command=self.remove_emergency_contact).grid(row=0, column=1)
        
        # === RIGHT PANE ===
        
        # Medical Information Section (Right Pane)
        medical_frame = ttk.LabelFrame(right_pane, text="Medical Information", padding="10")
        medical_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        medical_frame.columnconfigure(1, weight=1)
        
        # Medical info fields - organized in a more compact layout
        medical_fields = [
            ("blood_type", "Blood Type"),
            ("allergies", "Allergies"),
            ("medications", "Current Medications"),
            ("medical_conditions", "Medical Conditions"),
            ("emergency_contact", "Emergency Contact"),
            ("insurance", "Insurance Info")
        ]
        
        for i, (field_key, field_label) in enumerate(medical_fields):
            ttk.Label(medical_frame, text=f"{field_label}:").grid(row=i, column=0, sticky=tk.W, pady=1)
            var = tk.StringVar()
            self.medical_info_vars[field_key] = var
            ttk.Entry(medical_frame, textvariable=var, width=30).grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=1)
        
        # Medical buttons
        medical_buttons = ttk.Frame(medical_frame)
        medical_buttons.grid(row=len(medical_fields), column=0, columnspan=2, pady=8)
        
        ttk.Button(medical_buttons, text="Save Medical Info", command=self.save_medical_info).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(medical_buttons, text="Include in Emergency", command=self.include_medical_in_emergency).grid(row=0, column=1)
        
        # Emergency Events History (Right Pane)
        events_frame = ttk.LabelFrame(right_pane, text="Emergency Events", padding="10")
        events_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        events_frame.columnconfigure(0, weight=1)
        events_frame.rowconfigure(0, weight=1)  # Make the treeview expandable
        
        # Events list
        events_list_frame = ttk.Frame(events_frame)
        events_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        events_list_frame.columnconfigure(0, weight=1)
        events_list_frame.rowconfigure(0, weight=1)
        
        self.emergency_events_tree = ttk.Treeview(events_list_frame, columns=("timestamp", "type", "node", "status"), show="headings", height=8)
        self.emergency_events_tree.heading("timestamp", text="Timestamp")
        self.emergency_events_tree.heading("type", text="Type")
        self.emergency_events_tree.heading("node", text="Node")
        self.emergency_events_tree.heading("status", text="Status")
        
        self.emergency_events_tree.column("timestamp", width=120)
        self.emergency_events_tree.column("type", width=80)
        self.emergency_events_tree.column("node", width=80)
        self.emergency_events_tree.column("status", width=70)
        
        self.emergency_events_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Events buttons
        events_buttons = ttk.Frame(events_frame)
        events_buttons.grid(row=1, column=0, pady=8)
        
        ttk.Button(events_buttons, text="Refresh Events", command=self.refresh_emergency_events).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(events_buttons, text="Acknowledge", command=self.acknowledge_emergency_event).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(events_buttons, text="Clear History", command=self.clear_emergency_history).grid(row=0, column=2)
        
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
        
    def activate_emergency_beacon(self):
        """Activate emergency beacon"""
        try:
            if not self.interface_manager.is_connected():
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
                    self.interface_manager.send_message(emergency_msg, destination="^all", want_ack=True)
                    
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
                    
                    self.interface_manager.send_message(emergency_msg, destination="^all", want_ack=True)
                    
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
            if not self.interface_manager.is_connected():
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
            if not self.interface_manager.is_connected():
                messagebox.showwarning("Warning", "Not connected to device")
                return
            
            message = self.emergency_message_var.get()
            if not message:
                messagebox.showwarning("Warning", "Please enter an emergency message")
                return
            
            # Send to all emergency contacts
            for contact in self.emergency_contacts:
                try:
                    self.interface_manager.send_message(f"🚨 EMERGENCY: {message}", 
                                                      destination=contact['node_id'], want_ack=True)
                except Exception as e:
                    logger.error(f"Failed to send emergency message to {contact['name']}: {e}")
            
            # Also broadcast
            self.interface_manager.send_message(f"🚨 EMERGENCY: {message}", destination="^all", want_ack=True)
            
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
                    
                    if self.interface_manager.is_connected():
                        # Send cancellation message
                        cancel_msg = "🟢 EMERGENCY CANCELLED - All clear"
                        self.interface_manager.send_message(cancel_msg, destination="^all", want_ack=True)
                        
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
            if not self.interface_manager.is_connected():
                return
                
            # Sort contacts by priority
            sorted_contacts = sorted(self.emergency_contacts, 
                                   key=lambda x: {"High": 0, "Normal": 1, "Low": 2}.get(x['priority'], 1))
            
            for contact in sorted_contacts:
                try:
                    full_message = f"🚨 {event_type} 🚨\n{message}"
                    self.interface_manager.send_message(full_message, destination=contact['node_id'], want_ack=True)
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
            
            # Save to database
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
    
    def refresh_available_nodes(self):
        """Refresh the list of available nodes for emergency contacts"""
        try:
            if not self.interface_manager.is_connected():
                self.available_nodes_combo['values'] = ["No nodes available - Please connect to device"]
                return
            
            # Get available nodes from interface manager
            nodes = self.interface_manager.get_nodes()
            
            if not nodes:
                self.available_nodes_combo['values'] = ["No nodes found - Try sending/receiving messages first"]
                return
            
            # Format nodes for display: "NodeName (NodeID)"
            node_options = []
            for node_id, node_data in nodes.items():
                try:
                    # Get node name from user data
                    if 'user' in node_data and node_data['user']:
                        user_data = node_data['user']
                        if 'longName' in user_data and user_data['longName']:
                            node_name = user_data['longName']
                        elif 'shortName' in user_data and user_data['shortName']:
                            node_name = user_data['shortName']
                        else:
                            node_name = f"Node {node_id}"
                    else:
                        node_name = f"Node {node_id}"
                    
                    # Format as "Name (ID)"
                    display_text = f"{node_name} ({node_id})"
                    node_options.append(display_text)
                    
                except Exception as e:
                    logger.debug(f"Error processing node {node_id}: {e}")
                    # Fallback to just node ID
                    node_options.append(f"Node {node_id} ({node_id})")
            
            # Sort the options
            node_options.sort()
            
            # Update combobox
            self.available_nodes_combo['values'] = node_options
            
            logger.info(f"Refreshed available nodes: {len(node_options)} nodes found")
            
        except Exception as e:
            logger.error(f"Error refreshing available nodes: {e}")
            self.available_nodes_combo['values'] = ["Error loading nodes - Check connection"]
    
    def on_node_selected(self, event=None):
        """Handle node selection from dropdown"""
        try:
            selected = self.available_nodes_var.get()
            if not selected or "(" not in selected:
                return
            
            # Extract node ID from "NodeName (NodeID)" format
            node_id = selected.split("(")[-1].rstrip(")")
            
            # Extract node name
            node_name = selected.split(" (")[0]
            
            # Auto-fill the contact name and node ID fields
            self.contact_name_var.set(node_name)
            self.contact_node_var.set(node_id)
            
            logger.debug(f"Selected node: {node_name} with ID: {node_id}")
            
        except Exception as e:
            logger.error(f"Error handling node selection: {e}") 