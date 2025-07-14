#!/usr/bin/env python3
"""
Optimized Database Manager for Meshtastic UI
Features: Connection pooling, indexes, batch operations, and automatic cleanup
"""

import sqlite3
import threading
import queue
import json
import time
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class DataLogger:
    """Optimized database manager with connection pooling and performance enhancements"""
    
    def __init__(self, db_path="database/meshpy_data.db", pool_size=5):
        self.db_path = db_path
        self.pool_size = pool_size
        self.connection_pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        
        # Initialize database and connection pool
        self.init_database()
        self.init_connection_pool()
        
        # Batch processing
        self.batch_queue = queue.Queue()
        self.batch_size = 50
        self.batch_timeout = 5.0  # seconds
        self.start_batch_processor()
        
    def init_database(self):
        """Initialize the SQLite database with optimized schema and indexes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrent access
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA cache_size=10000')
        cursor.execute('PRAGMA temp_store=MEMORY')
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
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
                node_id TEXT UNIQUE,
                node_name TEXT,
                short_name TEXT,
                hardware_model TEXT,
                firmware_version TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                is_local BOOLEAN DEFAULT 0
            )
        ''')
        
        # Node positions table
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
        
        # Node metrics table
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
        
        # Create optimized indexes
        self.create_indexes(cursor)
        
        conn.commit()
        conn.close()
        logger.info(f"Optimized database initialized: {self.db_path}")
        
    def create_indexes(self, cursor):
        """Create indexes for better query performance"""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_messages_from_node ON messages(from_node)',
            'CREATE INDEX IF NOT EXISTS idx_messages_to_node ON messages(to_node)',
            'CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)',
            'CREATE INDEX IF NOT EXISTS idx_nodes_node_id ON nodes(node_id)',
            'CREATE INDEX IF NOT EXISTS idx_nodes_last_seen ON nodes(last_seen)',
            'CREATE INDEX IF NOT EXISTS idx_node_positions_node_id ON node_positions(node_id)',
            'CREATE INDEX IF NOT EXISTS idx_node_positions_timestamp ON node_positions(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_node_metrics_node_id ON node_metrics(node_id)',
            'CREATE INDEX IF NOT EXISTS idx_node_metrics_timestamp ON node_metrics(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_emergency_events_timestamp ON emergency_events(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_emergency_events_acknowledged ON emergency_events(acknowledged)',
            'CREATE INDEX IF NOT EXISTS idx_connection_events_timestamp ON connection_events(timestamp)',
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            
    def init_connection_pool(self):
        """Initialize connection pool for efficient database access"""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute('PRAGMA journal_mode=WAL')
            self.connection_pool.put(conn)
            
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            conn = self.connection_pool.get(timeout=10)
            yield conn
        except queue.Empty:
            # If pool is empty, create a temporary connection
            conn = sqlite3.connect(self.db_path)
            yield conn
        finally:
            if conn:
                try:
                    self.connection_pool.put_nowait(conn)
                except queue.Full:
                    # If pool is full, close the connection
                    conn.close()
                    
    def start_batch_processor(self):
        """Start background thread for batch processing"""
        def process_batches():
            batch = []
            last_flush = time.time()
            
            while True:
                try:
                    # Get item with timeout
                    item = self.batch_queue.get(timeout=1.0)
                    batch.append(item)
                    
                    # Process batch if it's full or timeout reached
                    if len(batch) >= self.batch_size or (time.time() - last_flush) > self.batch_timeout:
                        if batch:
                            self._process_batch(batch)
                            batch.clear()
                            last_flush = time.time()
                            
                except queue.Empty:
                    # Timeout - process any pending items
                    if batch:
                        self._process_batch(batch)
                        batch.clear()
                        last_flush = time.time()
                        
        thread = threading.Thread(target=process_batches, daemon=True)
        thread.start()
        
    def _process_batch(self, batch):
        """Process a batch of database operations"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Group operations by type
                messages = []
                node_updates = []
                metrics = []
                positions = []
                
                for operation in batch:
                    op_type = operation['type']
                    data = operation['data']
                    
                    if op_type == 'log_message':
                        messages.append(data)
                    elif op_type == 'log_node_update':
                        node_updates.append(data)
                    elif op_type == 'log_metrics':
                        metrics.append(data)
                    elif op_type == 'log_position':
                        positions.append(data)
                
                # Batch insert messages
                if messages:
                    cursor.executemany('''
                        INSERT OR REPLACE INTO messages 
                        (message_id, from_node, to_node, message_text, timestamp, status, 
                         hop_count, rssi, snr, message_type, channel)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', messages)
                
                # Batch update nodes
                if node_updates:
                    cursor.executemany('''
                        INSERT OR REPLACE INTO nodes 
                        (node_id, node_name, short_name, hardware_model, firmware_version, 
                         first_seen, last_seen, is_local)
                        VALUES (?, ?, ?, ?, ?, 
                                COALESCE((SELECT first_seen FROM nodes WHERE node_id = ?), ?),
                                ?, ?)
                    ''', node_updates)
                
                # Batch insert metrics
                if metrics:
                    cursor.executemany('''
                        INSERT INTO node_metrics 
                        (node_id, timestamp, battery_level, voltage, current, utilization, 
                         airtime, channel_utilization, rssi, snr)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', metrics)
                
                # Batch insert positions
                if positions:
                    cursor.executemany('''
                        INSERT INTO node_positions 
                        (node_id, latitude, longitude, altitude, timestamp, accuracy)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', positions)
                
                conn.commit()
                logger.debug(f"Processed batch: {len(messages)} messages, {len(node_updates)} nodes")
                
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            
    def queue_message(self, message_data):
        """Queue a message for batch processing"""
        operation = {
            'type': 'log_message',
            'data': (
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
            )
        }
        try:
            self.batch_queue.put_nowait(operation)
        except queue.Full:
            logger.warning("Batch queue full, processing immediately")
            self._process_single_operation(operation)
            
    def log_message(self, message_data):
        """Log a message (wrapper for queue_message for UI compatibility)"""
        self.queue_message(message_data)
        
    def log_emergency_event(self, source, event_type, lat, lon, message):
        """Log an emergency event"""
        operation = {
            'type': 'log_emergency_event',
            'data': (
                source,
                event_type,
                lat,
                lon,
                message,
                datetime.now()
            )
        }
        try:
            self.batch_queue.put_nowait(operation)
        except queue.Full:
            logger.warning("Batch queue full, processing emergency event immediately")
            self._process_single_operation(operation)
            
    def queue_node_update(self, node_data):
        """Queue a node update for batch processing"""
        node_id = node_data.get('node_id', '')
        now = datetime.now()
        
        # Queue node basic info
        node_operation = {
            'type': 'log_node_update',
            'data': (
                node_id,
                node_data.get('node_name', ''),
                node_data.get('short_name', ''),
                node_data.get('hardware_model', ''),
                node_data.get('firmware_version', ''),
                node_id,  # For COALESCE check
                now,
                now,
                node_data.get('is_local', False)
            )
        }
        
        try:
            self.batch_queue.put_nowait(node_operation)
        except queue.Full:
            self._process_single_operation(node_operation)
        
        # Queue position if available
        if 'latitude' in node_data and 'longitude' in node_data:
            position_operation = {
                'type': 'log_position',
                'data': (
                    node_id,
                    node_data['latitude'],
                    node_data['longitude'],
                    node_data.get('altitude', None),
                    now,
                    node_data.get('accuracy', None)
                )
            }
            try:
                self.batch_queue.put_nowait(position_operation)
            except queue.Full:
                self._process_single_operation(position_operation)
        
        # Queue metrics if available
        if 'battery_level' in node_data or 'rssi' in node_data:
            metrics_operation = {
                'type': 'log_metrics',
                'data': (
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
                )
            }
            try:
                self.batch_queue.put_nowait(metrics_operation)
            except queue.Full:
                self._process_single_operation(metrics_operation)
                
    def _process_single_operation(self, operation):
        """Process a single operation immediately (fallback)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                op_type = operation['type']
                data = operation['data']
                
                if op_type == 'log_message':
                    cursor.execute('''
                        INSERT OR REPLACE INTO messages 
                        (message_id, from_node, to_node, message_text, timestamp, status, 
                         hop_count, rssi, snr, message_type, channel)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data)
                elif op_type == 'log_node_update':
                    cursor.execute('''
                        INSERT OR REPLACE INTO nodes 
                        (node_id, node_name, short_name, hardware_model, firmware_version, 
                         first_seen, last_seen, is_local)
                        VALUES (?, ?, ?, ?, ?, 
                                COALESCE((SELECT first_seen FROM nodes WHERE node_id = ?), ?),
                                ?, ?)
                    ''', data)
                elif op_type == 'log_metrics':
                    cursor.execute('''
                        INSERT INTO node_metrics 
                        (node_id, timestamp, battery_level, voltage, current, utilization, 
                         airtime, channel_utilization, rssi, snr)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data)
                elif op_type == 'log_position':
                    cursor.execute('''
                        INSERT INTO node_positions 
                        (node_id, latitude, longitude, altitude, timestamp, accuracy)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', data)
                elif op_type == 'log_emergency_event':
                    cursor.execute('''
                        INSERT INTO emergency_events 
                        (node_id, event_type, latitude, longitude, message, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', data)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error processing single operation: {e}")
            
    def get_message_history(self, limit=100, node_filter=None):
        """Get message history with optimized query"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if node_filter:
                    cursor.execute('''
                        SELECT m.*, n1.node_name as from_name, n2.node_name as to_name
                        FROM messages m
                        LEFT JOIN nodes n1 ON m.from_node = n1.node_id
                        LEFT JOIN nodes n2 ON m.to_node = n2.node_id
                        WHERE m.from_node = ? OR m.to_node = ?
                        ORDER BY m.timestamp DESC LIMIT ?
                    ''', (node_filter, node_filter, limit))
                else:
                    cursor.execute('''
                        SELECT m.*, n1.node_name as from_name, n2.node_name as to_name
                        FROM messages m
                        LEFT JOIN nodes n1 ON m.from_node = n1.node_id
                        LEFT JOIN nodes n2 ON m.to_node = n2.node_id
                        ORDER BY m.timestamp DESC LIMIT ?
                    ''', (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting message history: {e}")
            return []
            
    def search_messages(self, search_term, limit=50):
        """Search messages with optimized full-text search"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
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
            
    def get_network_statistics(self):
        """Get network statistics with optimized queries"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                stats = {}
                
                # Use optimized queries with indexes
                cursor.execute('SELECT COUNT(*) FROM messages')
                stats['total_messages'] = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM nodes 
                    WHERE last_seen > datetime('now', '-24 hours')
                ''')
                stats['active_nodes'] = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM messages 
                    WHERE timestamp > datetime('now', '-24 hours')
                ''')
                stats['messages_24h'] = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM emergency_events 
                    WHERE timestamp > datetime('now', '-24 hours')
                ''')
                stats['emergency_events_24h'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting network statistics: {e}")
            return {}
            
    def cleanup_old_data(self, days_to_keep=30):
        """Clean up old data to prevent database bloat"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clean up old messages
                cursor.execute('DELETE FROM messages WHERE timestamp < ?', (cutoff_date,))
                messages_deleted = cursor.rowcount
                
                # Clean up old node positions
                cursor.execute('DELETE FROM node_positions WHERE timestamp < ?', (cutoff_date,))
                positions_deleted = cursor.rowcount
                
                # Clean up old node metrics
                cursor.execute('DELETE FROM node_metrics WHERE timestamp < ?', (cutoff_date,))
                metrics_deleted = cursor.rowcount
                
                # Clean up old connection events
                cursor.execute('DELETE FROM connection_events WHERE timestamp < ?', (cutoff_date,))
                events_deleted = cursor.rowcount
                
                conn.commit()
                
                # Vacuum to reclaim space
                cursor.execute('VACUUM')
                
                logger.info(f"Cleaned up old data: {messages_deleted} messages, "
                          f"{positions_deleted} positions, {metrics_deleted} metrics, "
                          f"{events_deleted} events")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            
    def close(self):
        """Close all connections in the pool"""
        while not self.connection_pool.empty():
            try:
                conn = self.connection_pool.get_nowait()
                conn.close()
            except queue.Empty:
                break 