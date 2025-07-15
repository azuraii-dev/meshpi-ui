import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatUI:
    def __init__(self, parent, interface_manager, data_logger):
        self.parent = parent
        self.interface_manager = interface_manager
        self.data_logger = data_logger
        self.message_status_tracking = {}  # Track message status
        self.displayed_message_ids = set()  # Track displayed messages to prevent duplicates
        
        # Create chat interface
        self.create_widgets()
        
    def create_widgets(self):
        """Create chat interface tab"""
        # Configure grid
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Create chat content
        chat_content = ttk.Frame(self.parent, padding="10")
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
        self.dest_combo = ttk.Combobox(dest_frame, textvariable=self.destination, 
                                      values=["Broadcast"], state="readonly")
        self.dest_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
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
    
    def resolve_node_name(self, node_id):
        """Convert node ID to readable name"""
        if not node_id or node_id in ['Unknown', 'LOCAL']:
            return node_id
            
        # Handle special cases
        if node_id == '^all':
            return 'Broadcast'
        if node_id.startswith('You') or node_id == 'LOCAL':
            return 'You'
        
        try:
            # Get nodes from interface manager
            if self.interface_manager.is_connected():
                nodes = self.interface_manager.get_nodes()
                
                for nid, node_data in nodes.items():
                    # Check if this is the node we're looking for
                    if str(nid) == str(node_id) or str(nid).lstrip('!') == str(node_id).lstrip('!'):
                        # Try to get a readable name
                        if 'user' in node_data and node_data['user']:
                            user_data = node_data['user']
                            if 'longName' in user_data and user_data['longName']:
                                return user_data['longName']
                            elif 'shortName' in user_data and user_data['shortName']:
                                return user_data['shortName']
                
            # If no name found, return a cleaned up node ID
            clean_id = str(node_id).lstrip('!')
            if len(clean_id) > 8:
                return f"Node {clean_id[-8:]}"  # Last 8 chars
            return f"Node {clean_id}"
            
        except Exception as e:
            logger.debug(f"Error resolving node name for {node_id}: {e}")
            return str(node_id)
    
    def categorize_binary_message(self, packet):
        """Categorize binary messages and decide if they should be shown"""
        try:
            if 'decoded' not in packet:
                return None, False
                
            decoded = packet['decoded']
            
            # Check portnum to determine message type
            portnum = decoded.get('portnum', 'UNKNOWN')
            
            # Messages we want to hide (telemetry, routing, etc.)
            hidden_types = [
                'TELEMETRY_APP',
                'POSITION_APP', 
                'NODEINFO_APP',
                'ROUTING_APP',
                'ADMIN_APP',
                'DETECTION_SENSOR_APP',
                'TRACEROUTE_APP'
            ]
            
            # Messages we want to show with descriptions
            if portnum == 'TEXT_MESSAGE_APP':
                return None, True  # Regular text message
            elif portnum == 'PRIVATE_APP':
                return "[APP] Private app message", True
            elif portnum == 'ATAK_PLUGIN':
                return "[ATAK] Location data", True
            elif portnum == 'SERIAL_APP':
                return "[SERIAL] Serial data", True
            elif portnum == 'STORE_FORWARD_APP':
                return "[SF] Store & forward", True
            elif portnum == 'RANGE_TEST_APP':
                return "[RANGE] Range test", True
            elif portnum == 'AUDIO_APP':
                return "[AUDIO] Audio message", True
            elif portnum in hidden_types:
                return None, False  # Don't show these
            else:
                # Unknown binary message type
                payload_size = len(decoded.get('payload', b''))
                return f"📊 Data message ({payload_size} bytes)", True
                
        except Exception as e:
            logger.debug(f"Error categorizing binary message: {e}")
            return "📊 Binary data", True
        
    def display_message(self, packet):
        """Display received message in chat with improved formatting"""
        try:
            # Extract message info
            from_id = packet.get('fromId', 'Unknown')
            to_id = packet.get('toId', 'Unknown')
            timestamp = datetime.now()
            timestamp_str = timestamp.strftime("%H:%M:%S")
            
            # Generate basic message ID for duplicate detection
            basic_content = f"{from_id}{to_id}{timestamp.strftime('%H:%M:%S')}"
            
            # Handle text vs binary messages
            message_text = ""
            message_type = 'text'
            should_display = True
            
            if 'decoded' in packet:
                decoded = packet['decoded']
                if 'text' in decoded:
                    message_text = decoded['text']
                    message_type = 'text'
                else:
                    # Handle binary messages
                    binary_description, should_display = self.categorize_binary_message(packet)
                    if should_display and binary_description:
                        message_text = binary_description
                        message_type = 'binary'
                    elif not should_display:
                        # Skip telemetry and other noise
                        return
                    else:
                        # Fallback for unknown binary
                        payload_size = len(decoded.get('payload', b''))
                        message_text = f"📊 Binary data ({payload_size} bytes)"
                        message_type = 'binary'
            
            # Generate complete message ID for duplicate detection
            message_id = hashlib.md5(f"{from_id}{to_id}{message_text}{timestamp_str}".encode()).hexdigest()[:8]
            
            # Check for duplicates
            if message_id in self.displayed_message_ids:
                logger.debug(f"Skipping duplicate message: {message_id}")
                return
            
            # Add to displayed messages set
            self.displayed_message_ids.add(message_id)
            
            # Resolve names for display
            from_name = self.resolve_node_name(from_id)
            to_name = self.resolve_node_name(to_id)
            
            # Log message to database (with original IDs for compatibility)
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
                'message_type': message_type,
                'from_name': from_name,  # Store resolved names for future use
                'to_name': to_name
            }
            self.data_logger.log_message(message_data)
            
            # Format message with status indicator and better formatting
            if message_type == 'text':
                status_indicator = "[MSG]"
            else:
                status_indicator = "[DATA]"
            
            # Color coding based on message type
            if to_name == 'Broadcast':
                # Public message
                msg_line = f"[{timestamp_str}] {from_name} → All: {message_text} {status_indicator}\n"
            else:
                # Direct message
                msg_line = f"[{timestamp_str}] {from_name} → {to_name}: {message_text} {status_indicator}\n"
            
            # Add to display
            self.message_display.config(state=tk.NORMAL)
            self.message_display.insert(tk.END, msg_line)
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error displaying message: {e}")
            
    def send_message(self):
        """Send message through Meshtastic"""
        if not self.interface_manager.is_connected():
            messagebox.showwarning("Warning", "Not connected to device")
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
                
            self.interface_manager.send_message(message, destination=dest, want_ack=want_ack)
            
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
            
            # Display with improved formatting
            dest_name = self.resolve_node_name(dest)
            status_indicator = "[SENT]" if want_ack else "[OK]"
            
            if dest_name == 'Broadcast':
                msg_line = f"[{timestamp_str}] You → All: {message} {status_indicator}\n"
            else:
                msg_line = f"[{timestamp_str}] You → {dest_name}: {message} {status_indicator}\n"
            
            # Check for duplicates and add to tracking
            simple_msg_id = hashlib.md5(f"YOU{dest}{message}{timestamp_str}".encode()).hexdigest()[:8]
            if simple_msg_id not in self.displayed_message_ids:
                self.displayed_message_ids.add(simple_msg_id)
                
                self.message_display.config(state=tk.NORMAL)
                self.message_display.insert(tk.END, msg_line)
                self.message_display.see(tk.END)
                self.message_display.config(state=tk.DISABLED)
            
            # Clear input
            self.message_entry.delete(0, tk.END)
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            messagebox.showerror("Error", f"Failed to send message: {e}")
            
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
                    status_indicator = "[DELIV]"
                elif status == 'sent':
                    status_indicator = "[SENT]"
                elif status == 'failed':
                    status_indicator = "[ERR]"
                else:
                    status_indicator = "[?]"
                
                # Format display name with improved resolution
                if from_node == 'LOCAL':
                    display_from = "You"
                else:
                    # Try to use stored names first (backward compatibility)
                    display_from = msg[12] if len(msg) > 12 and msg[12] else self.resolve_node_name(from_node)
                
                # Handle destination names
                if to_node == '^all':
                    display_to = "All"
                else:
                    display_to = msg[13] if len(msg) > 13 and msg[13] else self.resolve_node_name(to_node)
                
                # Better message formatting
                if display_to == "All":
                    msg_line = f"[{timestamp_str}] {display_from} → All: {message_text} {status_indicator}\n"
                else:
                    msg_line = f"[{timestamp_str}] {display_from} → {display_to}: {message_text} {status_indicator}\n"
                
                self.message_display.insert(tk.END, msg_line)
                
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error refreshing message display: {e}")
            
    def clear_chat(self):
        """Clear chat display and reset duplicate tracking"""
        self.message_display.config(state=tk.NORMAL)
        self.message_display.delete(1.0, tk.END)
        self.message_display.config(state=tk.DISABLED)
        
        # Clear duplicate tracking when chat is cleared
        self.displayed_message_ids.clear()
        
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
                    status_indicator = "[DELIV]"
                elif status == 'sent':
                    status_indicator = "[SENT]"
                elif status == 'failed':
                    status_indicator = "[ERR]"
                else:
                    status_indicator = "[?]"
                
                # Format display name with improved resolution
                if from_node == 'LOCAL':
                    display_from = "You"
                else:
                    # Try to use stored names first (backward compatibility)
                    display_from = msg[12] if len(msg) > 12 and msg[12] else self.resolve_node_name(from_node)
                
                # Handle destination names
                if to_node == '^all':
                    display_to = "All"
                else:
                    display_to = msg[13] if len(msg) > 13 and msg[13] else self.resolve_node_name(to_node)
                
                # Better message formatting
                if display_to == "All":
                    msg_line = f"[{timestamp_str}] {display_from} → All: {message_text} {status_indicator}\n"
                else:
                    msg_line = f"[{timestamp_str}] {display_from} → {display_to}: {message_text} {status_indicator}\n"
                
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
                        status_indicator = "[DELIV]"
                    elif status == 'sent':
                        status_indicator = "[SENT]"
                    elif status == 'failed':
                        status_indicator = "[ERR]"
                    else:
                        status_indicator = "[?]"
                    
                    # Format display name
                    display_from = "You" if from_node == 'LOCAL' else (msg[12] if len(msg) > 12 and msg[12] else from_node)
                    display_to = msg[13] if len(msg) > 13 and msg[13] else to_node
                    
                    msg_line = f"[{timestamp_str}] {display_from} -> {display_to}: {message_text} {status_indicator}\n"
                    
                    self.message_display.insert(tk.END, msg_line)
            else:
                self.message_display.insert(tk.END, "No message history found.")
                
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error loading message history: {e}")
            messagebox.showerror("Error", f"Failed to load message history: {e}")
            
    def update_destinations(self, nodes):
        """Update destination combo with available nodes"""
        destinations = ["Broadcast"]
        for node in nodes.values():
            user = node.get('user', {})
            if 'longName' in user:
                destinations.append(user['longName'])
                
        self.dest_combo.configure(values=destinations)
        
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