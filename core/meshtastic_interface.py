#!/usr/bin/env python3
"""
Meshtastic device interface for optimized connectivity and communication
"""

import threading
import queue
import time
import hashlib
import logging
from datetime import datetime

try:
    import meshtastic
    import meshtastic.serial_interface
    import meshtastic.tcp_interface
    import meshtastic.util
    from pubsub import pub
    MESHTASTIC_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Meshtastic library not available: {e}")
    MESHTASTIC_AVAILABLE = False

from utils.constants import REGION_NAME_TO_ENUM, REGION_ENUM_TO_NAME

logger = logging.getLogger(__name__)

class MeshtasticInterface:
    """Optimized Meshtastic device interface with improved performance"""
    
    def __init__(self, database_manager=None):
        self.interface = None
        self.connection_status = "Disconnected"
        self.nodes = {}
        self.message_queue = queue.Queue()
        self.message_status_tracking = {}
        self.database_manager = database_manager
        
        # Connection validation
        self.connection_validated = False
        self.last_heartbeat = None
        
        # Setup event handlers
        self.setup_meshtastic_events()
        
        # Start message processing thread
        self.start_message_thread()
        
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
        
    def connect(self, connection_type="Serial", connection_param="auto", callback=None):
        """Connect to Meshtastic device with improved error handling"""
        if not MESHTASTIC_AVAILABLE:
            error_msg = "Meshtastic library not available"
            if callback:
                callback(False, error_msg)
            return False
            
        def connect_thread():
            try:
                self.connection_status = "Connecting"
                # Make sure connection_param is properly scoped
                actual_connection_param = connection_param
                logger.info(f"Attempting to connect via {connection_type}: {actual_connection_param}")
                
                if connection_type == "Serial":
                    if actual_connection_param.lower() == "auto":
                        # Check for available ports first
                        ports = meshtastic.util.findPorts(True)
                        if not ports:
                            raise Exception("No Meshtastic devices found on serial ports.\n\n"
                                          "Please check:\n• Device is connected via USB\n"
                                          "• Device is powered on\n• USB cable supports data transfer\n"
                                          "• Device drivers are installed")
                        self.interface = meshtastic.serial_interface.SerialInterface()
                    else:
                        try:
                            self.interface = meshtastic.serial_interface.SerialInterface(devPath=actual_connection_param)
                        except Exception as serial_error:
                            raise Exception(f"Failed to connect to serial device '{actual_connection_param}'.\n\n"
                                          f"Please check:\n• Device path is correct\n"
                                          f"• Device is connected and powered on\n"
                                          f"• You have permission to access the device\n"
                                          f"• Device is not in use by another application\n\n"
                                          f"Original error: {serial_error}")
                            
                elif connection_type == "TCP":
                    if actual_connection_param.lower() == "auto":
                        actual_connection_param = "localhost"
                    try:
                        self.interface = meshtastic.tcp_interface.TCPInterface(hostname=actual_connection_param)
                    except Exception as tcp_error:
                        raise Exception(f"Failed to connect to TCP host '{actual_connection_param}'.\n\n"
                                      f"Please check:\n• Host is reachable\n• Port 4403 is open\n"
                                      f"• Meshtastic device has network module enabled\n"
                                      f"• IP address/hostname is correct\n\n"
                                      f"Original error: {tcp_error}")
                
                # Validate the connection
                if not self.validate_connection():
                    raise Exception("Connection established but device is not responding properly.\n\n"
                                  "This could indicate:\n• Device is not a Meshtastic device\n"
                                  "• Device firmware is incompatible\n"
                                  "• Device is not fully initialized\n\n"
                                  "Try disconnecting and reconnecting the device.")
                
                self.connection_status = "Connected"
                self.connection_validated = True
                
                # Log successful connection
                if self.database_manager:
                    self.database_manager.queue_message({
                        'message_type': 'connection_event',
                        'event_type': 'connect',
                        'device_path': actual_connection_param,
                        'success': True,
                        'timestamp': datetime.now()
                    })
                
                logger.info(f"Successfully connected to Meshtastic device")
                if callback:
                    callback(True, "Connected successfully")
                    
            except Exception as e:
                self.connection_status = "Failed"
                error_message = str(e)
                logger.error(f"Connection failed: {error_message}")
                
                # Log failed connection
                if self.database_manager:
                    self.database_manager.queue_message({
                        'message_type': 'connection_event',
                        'event_type': 'connect',
                        'device_path': actual_connection_param,
                        'success': False,
                        'error_message': error_message,
                        'timestamp': datetime.now()
                    })
                
                if callback:
                    callback(False, error_message)
                    
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
                self.last_heartbeat = time.time()
                
            return True
            
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from Meshtastic device"""
        try:
            if self.interface:
                # Check if the interface has a proper close method and stream
                if hasattr(self.interface, 'close') and hasattr(self.interface, 'stream'):
                    self.interface.close()
                self.interface = None
                self.connection_status = "Disconnected"
                self.connection_validated = False
                self.nodes.clear()
                logger.info("Disconnected from Meshtastic device")
                return True
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            # Force cleanup even if close fails
            self.interface = None
            self.connection_status = "Disconnected"
            self.connection_validated = False
            self.nodes.clear()
            return False
            
    def send_message(self, message, destination="^all", want_ack=True):
        """Send message with improved error handling and status tracking"""
        if not self.interface or not self.connection_validated:
            raise Exception("Not connected to device")
            
        if not hasattr(self.interface, 'sendText'):
            raise Exception("Interface not properly initialized")
            
        try:
            # Generate message ID for tracking
            message_id = hashlib.md5(f"LOCAL{destination}{message}{datetime.now()}".encode()).hexdigest()[:8]
            
            # Send message
            self.interface.sendText(message, destinationId=destination, wantAck=want_ack)
            
            # Track message status
            self.message_status_tracking[message_id] = {
                'status': 'sent',
                'timestamp': datetime.now(),
                'want_ack': want_ack,
                'destination': destination
            }
            
            # Log sent message to database
            if self.database_manager:
                message_data = {
                    'message_id': message_id,
                    'from_node': 'LOCAL',
                    'to_node': destination,
                    'message_text': message,
                    'timestamp': datetime.now(),
                    'status': 'sent',
                    'hop_count': 0,
                    'message_type': 'text',
                    'channel': 'primary'
                }
                self.database_manager.queue_message(message_data)
            
            logger.info(f"Message sent successfully: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
            
    def get_device_info(self):
        """Get comprehensive device information"""
        if not self.interface or not self.connection_validated:
            return None
            
        try:
            device_info = {}
            
            # Get local node info
            if hasattr(self.interface, 'localNode'):
                local_node = self.interface.localNode
                if local_node:
                    device_info['local_node'] = local_node
                    
            # Get user info
            if hasattr(self.interface, 'getMyUser'):
                user = self.interface.getMyUser()
                if user:
                    device_info['user'] = user
                    
            # Get node info
            if hasattr(self.interface, 'getMyNodeInfo'):
                node_info = self.interface.getMyNodeInfo()
                if node_info:
                    device_info['node_info'] = node_info
                    
            # Get channel settings
            if hasattr(self.interface, 'getChannelSettings'):
                try:
                    channel_settings = self.interface.getChannelSettings()
                    if channel_settings:
                        device_info['channel_settings'] = channel_settings
                except Exception as e:
                    logger.debug(f"Could not get channel settings: {e}")
                    
            return device_info
            
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return None
            
    def get_local_position(self):
        """Get GPS position of the local device"""
        if not self.interface or not self.connection_validated:
            return None
            
        try:
            if hasattr(self.interface, 'getMyNodeInfo'):
                node_info = self.interface.getMyNodeInfo()
                if node_info and 'position' in node_info:
                    pos = node_info['position']
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
        
    def update_node_info(self, long_name, short_name):
        """Update node information"""
        if not self.interface or not self.connection_validated:
            raise Exception("Not connected to device")
            
        if not hasattr(self.interface, 'localNode'):
            raise Exception("Interface not properly initialized")
            
        try:
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'setOwner'):
                local_node.setOwner(long_name=long_name, short_name=short_name)
                logger.info(f"Node info updated: {long_name} ({short_name})")
                return True
            else:
                raise Exception("Local node not available or not properly initialized")
                
        except Exception as e:
            logger.error(f"Error updating node info: {e}")
            raise
            
    def update_region(self, region_name):
        """Update device region setting"""
        if not self.interface or not self.connection_validated:
            raise Exception("Not connected to device")
            
        if not hasattr(self.interface, 'localNode'):
            raise Exception("Interface not properly initialized")
            
        if region_name not in REGION_NAME_TO_ENUM:
            raise Exception(f"Unsupported region: {region_name}")
            
        try:
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'localConfig'):
                config = local_node.localConfig
                
                if hasattr(config, 'lora') and hasattr(config.lora, 'region'):
                    config.lora.region = REGION_NAME_TO_ENUM[region_name]
                    local_node.writeConfig("lora")
                    logger.info(f"Region updated to {region_name}")
                    return True
                else:
                    raise Exception("Unable to access LoRa configuration")
            else:
                raise Exception("Local node configuration not available")
                
        except Exception as e:
            logger.error(f"Error updating region: {e}")
            raise
            
    def reboot_device(self):
        """Reboot the device"""
        if not self.interface or not self.connection_validated:
            raise Exception("Not connected to device")
            
        if not hasattr(self.interface, 'localNode'):
            raise Exception("Interface not properly initialized")
            
        try:
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'reboot'):
                local_node.reboot()
                logger.info("Device reboot initiated")
                return True
            else:
                raise Exception("Local node not available or not properly initialized")
                
        except Exception as e:
            logger.error(f"Error rebooting device: {e}")
            raise
            
    def factory_reset(self):
        """Factory reset the device"""
        if not self.interface or not self.connection_validated:
            raise Exception("Not connected to device")
            
        if not hasattr(self.interface, 'localNode'):
            raise Exception("Interface not properly initialized")
            
        try:
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'factoryReset'):
                local_node.factoryReset()
                logger.info("Factory reset initiated")
                return True
            else:
                raise Exception("Local node not available or not properly initialized")
                
        except Exception as e:
            logger.error(f"Error factory resetting device: {e}")
            raise
            
    # Event handlers
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
                    self.handle_message(msg_type, data)
                except queue.Empty:
                    continue
                    
        threading.Thread(target=process_messages, daemon=True).start()
        
    def handle_message(self, msg_type, data):
        """Handle messages in processing thread"""
        try:
            if msg_type == 'message':
                self.process_received_message(data)
            elif msg_type == 'node_updated':
                self.process_node_update(data)
            elif msg_type == 'connection_established':
                self.connection_status = "Connected"
                logger.info("Connection established")
            elif msg_type == 'connection_lost':
                self.connection_status = "Disconnected"
                self.connection_validated = False
                logger.warning("Connection lost")
            elif msg_type == 'routing_error':
                self.handle_routing_error(data)
            elif msg_type == 'ack_received':
                self.handle_ack_received(data)
                
        except Exception as e:
            logger.error(f"Error handling message {msg_type}: {e}")
            
    def process_received_message(self, packet):
        """Process received message"""
        try:
            # Extract message info
            from_id = packet.get('fromId', 'Unknown')
            to_id = packet.get('toId', 'Unknown')
            timestamp = datetime.now()
            
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
            if self.database_manager:
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
                self.database_manager.queue_message(message_data)
            
            logger.debug(f"Processed message from {from_id}: {message_text}")
            
        except Exception as e:
            logger.error(f"Error processing received message: {e}")
            
    def process_node_update(self, node):
        """Process node update"""
        try:
            if not node:
                return
                
            node_id = node.get('num', 'Unknown')
            self.nodes[node_id] = node
            
            # Extract node data for logging
            user = node.get('user', {})
            position = node.get('position', {})
            device_metrics = node.get('deviceMetrics', {})
            
            # Prepare node data for database
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
            
            # Log node update to database
            if self.database_manager:
                self.database_manager.queue_node_update(node_data)
            
            logger.debug(f"Processed node update for {node_id}")
            
        except Exception as e:
            logger.error(f"Error processing node update: {e}")
            
    def handle_routing_error(self, packet):
        """Handle routing error for message status updates"""
        try:
            error_id = packet.get('id', None)
            if error_id and error_id in self.message_status_tracking:
                self.message_status_tracking[error_id]['status'] = 'failed'
                logger.warning(f"Message routing failed for ID: {error_id}")
        except Exception as e:
            logger.error(f"Error handling routing error: {e}")
            
    def handle_ack_received(self, packet):
        """Handle ACK received for message status updates"""
        try:
            ack_id = packet.get('id', None)
            if ack_id and ack_id in self.message_status_tracking:
                self.message_status_tracking[ack_id]['status'] = 'delivered'
                logger.info(f"Message delivered successfully, ID: {ack_id}")
        except Exception as e:
            logger.error(f"Error handling ACK: {e}")
            
    def get_connection_status(self):
        """Get current connection status"""
        return self.connection_status
        
    def is_connected(self):
        """Check if connected and validated"""
        return self.interface is not None and self.connection_validated
        
    def get_nodes(self):
        """Get all known nodes"""
        return self.nodes.copy()
        
    def get_message_status(self, message_id):
        """Get status of a specific message"""
        return self.message_status_tracking.get(message_id, {'status': 'unknown'}) 