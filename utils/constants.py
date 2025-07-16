#!/usr/bin/env python3
"""
Constants used throughout the Meshtastic UI application
"""

# Application version
APP_VERSION = "2.0.0"

# Database configuration
DEFAULT_DB_NAME = "database/meshpi_data.db"

# Map configuration
DEFAULT_MAP_ZOOM = 10
GPS_MAP_ZOOM = 15

# Update intervals (in milliseconds)
STATUS_UPDATE_INTERVAL = 5000
PERIODIC_UPDATE_INTERVAL = 10000

# Network configuration
DEFAULT_TCP_PORT = 4403
CONNECTION_TIMEOUT = 10

# Message limits
MAX_MESSAGE_LENGTH = 228
MAX_MESSAGES_DISPLAY = 100

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

# Supported regions list
REGIONS = list(REGION_NAME_TO_ENUM.keys())

# Map layers configuration
MAP_LAYERS = {
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

# Emergency system constants
EMERGENCY_PRIORITIES = ["High", "Normal", "Low"]
EMERGENCY_EVENT_TYPES = ["beacon", "panic", "message", "cancelled"]

# Analytics time ranges
TIME_RANGES = {
    "1 hour": 1,
    "6 hours": 6,
    "24 hours": 24,
    "7 days": 168,
    "30 days": 720
}

# Node colors based on battery level
NODE_COLORS = {
    "high": "green",      # >75% battery
    "medium": "orange",   # 25-75% battery
    "low": "red",         # <25% battery
    "unknown": "gray",    # Unknown battery
    "local": "#6B46C1"    # Local device
}

# Battery level thresholds
BATTERY_HIGH_THRESHOLD = 75
BATTERY_LOW_THRESHOLD = 25

# Message status indicators
MESSAGE_STATUS_ICONS = {
    "sent": "✓",
    "delivered": "✓✓",
    "failed": "[ERR]",
    "received": "✓",
    "unknown": "?"
}

# Default IP geolocation services
IP_GEOLOCATION_SERVICES = [
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

# Default fallback coordinates (San Francisco)
DEFAULT_COORDINATES = (37.7749, -122.4194)

# Network topology constants
NETWORK_CANVAS_SIZE = (600, 400)
NETWORK_NODE_SIZE = 15
NETWORK_LOCAL_NODE_SIZE = 20
NETWORK_CONNECTION_GOOD_RSSI = -80

# Export formats
EXPORT_FORMATS = ["csv", "json", "gpx"]

# Medical information fields
MEDICAL_FIELDS = [
    ("blood_type", "Blood Type"),
    ("allergies", "Allergies"),
    ("medications", "Current Medications"),
    ("medical_conditions", "Medical Conditions"),
    ("emergency_contact", "Emergency Contact"),
    ("insurance", "Insurance Info")
]

# Chart configuration
CHART_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
CHART_DPI = 100
CHART_FIGURE_SIZE = (8, 4)

# Configuration profile constants
DEFAULT_PROFILE_NAME = "Default"
RESERVED_PROFILE_NAMES = ["emergency_contacts", "medical_info", "managed_devices", "default_device"]

# Device scan constants
COMMON_TCP_HOSTS = ["localhost", "192.168.1.1", "meshtastic.local"]
DEVICE_SCAN_TIMEOUT = 5

# UI constants
PADDING = 10
BUTTON_PADDING = 5
FRAME_PADDING = 10

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO' 