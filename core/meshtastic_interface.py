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
                
                # Validate the connection with a longer timeout for better reliability
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
                self.connection_validated = False
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
                
            # Wait longer for the interface to fully initialize
            time.sleep(1.5)
            
            # Try to get basic device info to ensure connection is working
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Try to access localNode
                    if hasattr(self.interface, 'localNode') and self.interface.localNode:
                        logger.info("Connection validated successfully")
                        return True
                        
                    # If localNode not available, try to get my user
                    if hasattr(self.interface, 'getMyUser'):
                        user = self.interface.getMyUser()
                        if user:
                            logger.info("Connection validated via user info")
                            return True
                            
                except Exception as e:
                    logger.debug(f"Validation attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1.0)  # Wait between retries
                    
            return False
            
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
            local_node = None
            if hasattr(self.interface, 'localNode'):
                local_node = self.interface.localNode
                    
            # Get user info
            user = None
            if hasattr(self.interface, 'getMyUser'):
                try:
                    user = self.interface.getMyUser()
                except Exception as e:
                    logger.debug(f"Could not get user info: {e}")
                    
            # Get node info
            node_info = None
            if hasattr(self.interface, 'getMyNodeInfo'):
                try:
                    node_info = self.interface.getMyNodeInfo()
                except Exception as e:
                    logger.debug(f"Could not get node info: {e}")
                    
            # Get channel settings - try primary channel first
            channel_settings = None
            if hasattr(self.interface, 'getChannelSettings'):
                try:
                    # Try to get primary channel (index 0)
                    channel_settings = self.interface.getChannelSettings(0)
                except Exception as e:
                    logger.debug(f"Could not get channel settings with index 0: {e}")
                    try:
                        # Fallback to default getChannelSettings
                        channel_settings = self.interface.getChannelSettings()
                    except Exception as e2:
                        logger.debug(f"Could not get channel settings: {e2}")
            
            # Helper function to safely get value from object or dict
            def safe_get(obj, key, default=None):
                if obj is None:
                    return default
                if hasattr(obj, key):
                    return getattr(obj, key)
                elif isinstance(obj, dict) and key in obj:
                    return obj[key]
                return default
            
            # Extract and format device information
            # Long name (from user info)
            long_name = safe_get(user, 'longName', 'Unknown')
            device_info['long_name'] = long_name if long_name else 'Unknown'
                
            # Short name (from user info)
            short_name = safe_get(user, 'shortName', 'UNK')
            device_info['short_name'] = short_name if short_name else 'UNK'
                
            # Hardware model (from node info device metadata)
            hardware = None
            if node_info:
                device_metadata = safe_get(node_info, 'deviceMetrics', {})
                if device_metadata:
                    hardware = safe_get(device_metadata, 'hwModel')
                    
            # Also try from user info
            if not hardware and user:
                hardware = safe_get(user, 'hwModel')
                    
            # Try from local node
            if not hardware and local_node:
                hardware = safe_get(local_node, 'hwModel')
                    
            device_info['hardware'] = hardware if hardware else 'Unknown'
                    
            # Firmware version (from node info)
            firmware = None
            if node_info:
                firmware = safe_get(node_info, 'firmwareVersion')
                    
            # Try from local node
            if not firmware and local_node:
                firmware = safe_get(local_node, 'firmwareVersion')
                    
            device_info['firmware'] = firmware if firmware else 'Unknown'
                    
            # Region (from local node config)
            region = None
            if local_node and hasattr(local_node, 'localConfig'):
                try:
                    config = local_node.localConfig
                    if config and hasattr(config, 'lora') and hasattr(config.lora, 'region'):
                        region_num = config.lora.region
                        # Map region enum values back to names
                        region = REGION_ENUM_TO_NAME.get(region_num, f"Unknown ({region_num})")
                except Exception as e:
                    logger.debug(f"Could not get region from local config: {e}")
                    
            device_info['region'] = region if region else 'Unknown'
                    
            # Channel name (from channel settings)
            channel_name = 'Default'
            if channel_settings:
                channel_name = safe_get(channel_settings, 'name', 'Default')
                
            device_info['channel'] = channel_name if channel_name else 'Default'
                
            # Battery level (from node info)
            battery = None
            if node_info:
                node_id = safe_get(node_info, 'num')
                if node_id and node_id in self.nodes:
                    node = self.nodes[node_id]
                    device_metrics = safe_get(node, 'deviceMetrics')
                    if device_metrics:
                        battery = safe_get(device_metrics, 'batteryLevel')
                        
            if battery is not None:
                device_info['battery'] = battery
                        
            # Debug logging to understand what we're getting
            logger.debug(f"User info: {user}")
            logger.debug(f"Node info: {node_info}")
            logger.debug(f"Local node: {local_node}")
            logger.debug(f"Channel settings: {channel_settings}")
            
            logger.info(f"Device info retrieved: {device_info}")
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
        
    def get_gps_status(self):
        """Get detailed GPS status information"""
        if not self.interface or not self.connection_validated:
            return {'status': 'disconnected', 'satellites': 0, 'fix': False}
            
        try:
            if hasattr(self.interface, 'getMyNodeInfo'):
                node_info = self.interface.getMyNodeInfo()
                if node_info and 'position' in node_info:
                    pos = node_info['position']
                    
                    # Check if we have valid coordinates
                    has_coords = ('latitude' in pos and 'longitude' in pos and 
                                pos['latitude'] != 0 and pos['longitude'] != 0)
                    
                    # Get satellite count if available
                    satellites = pos.get('satsInView', 0)
                    
                    # Get GPS time if available (indicates recent fix)
                    gps_time = pos.get('time', 0)
                    
                    # Determine GPS status
                    if has_coords and satellites > 3:
                        status = 'fixed'
                    elif satellites > 0:
                        status = 'searching'
                    else:
                        status = 'no_signal'
                    
                    return {
                        'status': status,
                        'satellites': satellites,
                        'fix': has_coords,
                        'latitude': pos.get('latitude', 0),
                        'longitude': pos.get('longitude', 0),
                        'altitude': pos.get('altitude', 0),
                        'time': gps_time
                    }
            
            # If we can't get position info, assume GPS might be disabled
            return {'status': 'disabled', 'satellites': 0, 'fix': False}
                        
        except Exception as e:
            logger.debug(f"Could not get GPS status: {e}")
            return {'status': 'error', 'satellites': 0, 'fix': False}
        
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
            raise Exception(f"Unsupported region: {region_name}. Available regions: {list(REGION_NAME_TO_ENUM.keys())}")
            
        try:
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'localConfig'):
                config = local_node.localConfig
                
                if hasattr(config, 'lora') and hasattr(config.lora, 'region'):
                    old_region = config.lora.region
                    config.lora.region = REGION_NAME_TO_ENUM[region_name]
                    
                    # Write config and wait for it to be applied
                    local_node.writeConfig("lora")
                    
                    # Allow time for the configuration to be applied
                    time.sleep(2)
                    
                    logger.info(f"Region updated from {old_region} to {region_name} (enum: {REGION_NAME_TO_ENUM[region_name]})")
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
            
    def set_gps_enabled(self, enabled):
        """Enable or disable GPS"""
        if not self.interface or not self.connection_validated:
            raise Exception("Not connected to device")
            
        try:
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'localConfig'):
                config = local_node.localConfig
                
                if hasattr(config, 'position') and hasattr(config.position, 'gps_enabled'):
                    config.position.gps_enabled = enabled
                    local_node.writeConfig("position")
                    logger.info(f"GPS {'enabled' if enabled else 'disabled'}")
                    return True
                else:
                    # Fallback: try alternative method
                    if hasattr(local_node, 'setConfig'):
                        local_node.setConfig(f"position.gps_enabled={enabled}")
                        logger.info(f"GPS {'enabled' if enabled else 'disabled'} (fallback method)")
                        return True
                    else:
                        raise Exception("Unable to access position configuration")
            else:
                raise Exception("Local node configuration not available")
                
        except Exception as e:
            logger.error(f"Error setting GPS enabled status: {e}")
            return False
            
    def set_gps_interval(self, interval):
        """Set GPS update interval in seconds"""
        if not self.interface or not self.connection_validated:
            raise Exception("Not connected to device")
            
        try:
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'localConfig'):
                config = local_node.localConfig
                
                if hasattr(config, 'position') and hasattr(config.position, 'gps_update_interval'):
                    config.position.gps_update_interval = interval
                    local_node.writeConfig("position")
                    logger.info(f"GPS update interval set to {interval} seconds")
                    return True
                else:
                    # Fallback: try alternative method
                    if hasattr(local_node, 'setConfig'):
                        local_node.setConfig(f"position.gps_update_interval={interval}")
                        logger.info(f"GPS update interval set to {interval} seconds (fallback method)")
                        return True
                    else:
                        raise Exception("Unable to access position configuration")
            else:
                raise Exception("Local node configuration not available")
                
        except Exception as e:
            logger.error(f"Error setting GPS update interval: {e}")
            return False
            
    def set_gps_broadcast_interval(self, interval):
        """Set GPS broadcast interval in seconds"""
        if not self.interface or not self.connection_validated:
            raise Exception("Not connected to device")
            
        try:
            local_node = self.interface.localNode
            if local_node and hasattr(local_node, 'localConfig'):
                config = local_node.localConfig
                
                if hasattr(config, 'position') and hasattr(config.position, 'position_broadcast_secs'):
                    config.position.position_broadcast_secs = interval
                    local_node.writeConfig("position")
                    logger.info(f"GPS broadcast interval set to {interval} seconds")
                    return True
                else:
                    # Fallback: try alternative method
                    if hasattr(local_node, 'setConfig'):
                        local_node.setConfig(f"position.position_broadcast_secs={interval}")
                        logger.info(f"GPS broadcast interval set to {interval} seconds (fallback method)")
                        return True
                    else:
                        raise Exception("Unable to access position configuration")
            else:
                raise Exception("Local node configuration not available")
                
        except Exception as e:
            logger.error(f"Error setting GPS broadcast interval: {e}")
            return False
            
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