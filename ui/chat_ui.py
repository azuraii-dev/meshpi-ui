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
                display_from = "You" if from_node == 'LOCAL' else (msg[12] if len(msg) > 12 and msg[12] else from_node)
                display_to = msg[13] if len(msg) > 13 and msg[13] else to_node
                
                msg_line = f"[{timestamp_str}] {display_from} -> {display_to}: {message_text} {status_indicator}\n"
                
                self.message_display.insert(tk.END, msg_line)
                
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error refreshing message display: {e}")
            
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
                display_from = "You" if from_node == 'LOCAL' else (msg[12] if len(msg) > 12 and msg[12] else from_node)
                display_to = msg[13] if len(msg) > 13 and msg[13] else to_node
                
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