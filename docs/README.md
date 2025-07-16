# meshpi UI - Cross-Platform Meshtastic Interface

A comprehensive, cross-platform interface for Meshtastic mesh networking devices with advanced features including real-time chat, network topology visualization, analytics, emergency features, and device configuration.

## 🚀 Quick Start

### One-Command Setup (All Platforms)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/meshpi-ui.git
   cd meshpi-ui
   ```

2. **Run the setup script**:
   ```bash
   python setup.py
   ```

3. **Launch the application**:
   - **Windows**: Double-click `run.bat` or run `run.bat` from command line
   - **macOS/Linux**: Run `./run.sh` from terminal

That's it! The setup script automatically:
- ✅ Detects your operating system
- ✅ Creates a virtual environment
- ✅ Installs all required dependencies
- ✅ Creates platform-specific run scripts
- ✅ Sets up the database directory

### Manual Setup (If Needed)

If you prefer manual setup:

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 📋 Requirements

- **Python 3.8 or higher**
- **USB drivers** for your Meshtastic device (if using serial connection)
- **Internet connection** (for map tiles and initial setup)

## Features

### Core Features
- **Real-time Chat**: Message exchange with delivery status tracking
- **Interactive Map**: GPS-based node visualization with multiple map layers
- **Network Topology**: Visual network graph with signal strength indicators
- **Analytics Dashboard**: Charts and metrics for network health monitoring
- **Emergency System**: Beacon, panic button, and emergency contacts
- **Device Configuration**: Complete device setup and profile management

### Advanced Features
- **Data Logging**: SQLite-based persistent storage for all network data
- **Message Status Tracking**: Sent/delivered/failed indicators with ACK support
- **Profile Management**: Save/load device configurations
- **Multi-Device Support**: Manage multiple Meshtastic devices
- **Data Export**: Export network data in CSV/JSON/GPX formats
- **Offline Support**: Works without internet connection

## Directory Structure

The application follows a clean, organized structure:

```
meshpi-ui/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore rules
├── core/                  # Core system components
│   ├── __init__.py
│   └── meshtastic_interface.py    # Device communication layer
├── data/                  # Data management
│   ├── __init__.py
│   └── database.py                # SQLite data persistence
├── ui/                    # User interface modules
│   ├── __init__.py
│   ├── map_ui.py                  # Map visualization
│   ├── chat_ui.py                 # Chat interface
│   ├── network_ui.py              # Network topology
│   ├── analytics_ui.py            # Analytics dashboard
│   ├── emergency_ui.py            # Emergency features
│   └── config_ui.py               # Device configuration
├── utils/                 # Utility modules
│   ├── __init__.py
│   ├── constants.py               # App constants
│   ├── networking.py              # Network utilities
│   └── gps.py                     # GPS utilities
├── database/              # SQLite database files
│   └── meshpi_data.db             # Main database (auto-created)
├── exports/               # Export files (auto-created)
│   ├── *.csv                      # Data exports
│   ├── *.json                     # Configuration exports
│   └── *.png                      # Graph exports
├── legacy/                # Legacy code
│   └── main.py                    # Original monolithic version
├── docs/                  # Documentation
│   ├── README.md                  # This file
│   └── OPTIMIZATION_SUMMARY.md    # Performance analysis
└── scripts/               # Utility scripts
    └── test_connection.py         # Connection testing
```

## Module Descriptions

### Core Module
- **MeshtasticInterface**: Handles all device communication, connection management, and message routing with proper error handling and connection validation

### Data Module
- **DataLogger**: Provides SQLite-based persistence for messages, nodes, metrics, and events with efficient querying and data export capabilities

### UI Modules
- **MapUI**: Interactive map with GPS positioning, multiple tile layers, and node visualization
- **ChatUI**: Real-time messaging with history, search, and message status tracking
- **NetworkUI**: Network topology visualization with interactive node graphs
- **AnalyticsUI**: Charts and statistics for network monitoring and health analysis
- **EmergencyUI**: Emergency beacon, panic button, contact management, and medical information
- **ConfigUI**: Complete device configuration including:
  - Device information display
  - Node settings (name, region, channels)
  - Configuration profiles (save/load/export/import)
  - Multi-device management
  - Device actions (reboot, factory reset)

### Utils Module
- **Constants**: Application-wide constants and configuration
- **Networking**: Network utilities and IP geolocation
- **GPS**: GPS coordinate calculations and utilities

## Configuration Features

The ConfigUI module provides comprehensive device configuration:

### Device Information
- Real-time display of device status
- Hardware and firmware information
- Battery level monitoring
- Region and channel information

### Node Settings
- Update device long and short names
- Configure device identification

### Region Settings
- Support for all Meshtastic regions:
  - US, EU_433, EU_868, CN, JP, ANZ, KR, TW, RU, IN
  - MY_433, MY_919, NZ_865, SG_923, TH, UA_433, UA_868
- Regulatory compliance information
- Automatic device reboot after region change

### Channel Settings
- Channel name configuration
- PSK (Pre-Shared Key) management
- Channel security settings

### Configuration Profiles
- Save current device configuration as named profiles
- Load saved profiles to quickly configure devices
- Export/import profiles for backup and sharing
- Profile versioning and metadata

### Multi-Device Management
- Automatic device discovery and scanning
- Add/remove devices from managed list
- Connect to different devices easily
- Set default device for auto-connection

### Device Actions
- Safe device reboot
- Factory reset with confirmation
- Real-time device information refresh

## Performance Optimizations

### Database Optimizations
- **Connection Pooling**: Efficient database connection management
- **Indexed Queries**: Optimized database indexes for fast lookups
- **Batch Operations**: Bulk database operations for improved performance
- **Connection Caching**: Reuse database connections

### UI Optimizations
- **Event-Driven Updates**: React to actual events instead of polling
- **Selective Refreshing**: Update only changed components
- **Async Operations**: Non-blocking UI operations
- **Memory Management**: Proper cleanup of resources

### Network Optimizations
- **Efficient Message Routing**: Optimized message handling
- **Connection Validation**: Proper connection state management
- **Error Recovery**: Robust error handling and recovery

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/meshpi-ui.git
cd meshpi-ui

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Requirements

- Python 3.7+
- tkinter (usually included with Python)
- meshtastic Python library
- sqlite3 (included with Python)
- requests (for IP geolocation)
- matplotlib (for analytics charts)
- tkintermapview (for interactive maps)

## Usage

### Basic Usage
1. Connect your Meshtastic device via USB or configure TCP connection
2. Launch the application: `python main.py`
3. Select connection type and port/IP
4. Click "Connect" to establish connection
5. Use the various tabs to access different features

### Configuration Workflow
1. Go to the "Config" tab after connecting
2. Review current device information
3. Update node settings as needed
4. Set appropriate region for your location
5. Configure channels and security settings
6. Save configuration as a profile for future use

### Profile Management
1. Create profiles for different use cases
2. Export profiles for backup or sharing
3. Import profiles from other devices
4. Switch between profiles easily

## Contributing

This modular architecture makes it easy to contribute:

1. **Add new UI features**: Create new modules in `ui/`
2. **Extend data handling**: Modify `data/database.py`
3. **Add utilities**: Create new modules in `utils/`
4. **Improve core functionality**: Enhance `core/meshtastic_interface.py`

## License

MIT License - see LICENSE file for details

## Changelog

### v2.0.0 (Modular Architecture)
- Complete rewrite with modular architecture
- Separated UI components into individual modules
- Improved performance and maintainability
- Added comprehensive configuration management
- Enhanced error handling and logging
- Better separation of concerns

### v1.0.0 (Legacy Monolithic)
- Initial release with all features in single file
- Basic functionality for all components
- Performance limitations due to monolithic design 