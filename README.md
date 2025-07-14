# Meshtastic UI

A comprehensive Python GUI application for interfacing with Meshtastic mesh networking devices. This application provides a user-friendly interface for managing Meshtastic devices with three main sections: Map visualization, Chat interface, and Configuration panel.

## Features

### 🗺️ Map Section
- **Node Visualization**: View all nodes in the mesh network
- **Node Details**: Display node information including name, ID, distance, battery level, and last heard timestamp
- **Interactive Map**: Placeholder for future map integration showing node positions
- **Real-time Updates**: Automatic updates when nodes join or leave the network

### 💬 Chat Section
- **Message Display**: Scrollable chat window showing all received messages
- **Message Sending**: Send text messages to specific nodes or broadcast to all
- **Destination Selection**: Choose message recipients from discovered nodes
- **Message Controls**: Options for requesting acknowledgments and clearing chat history
- **Real-time Communication**: Instant message display with timestamps

### ⚙️ Configuration Section
- **Device Information**: View device details including firmware version, hardware model, and region
- **Node Settings**: Update device long name and short name
- **Channel Settings**: Configure channel names and pre-shared keys (PSK)
- **Power Management**: Monitor battery levels and power settings
- **Device Actions**: Reboot device, factory reset, and retrieve device metadata

## Installation

### Prerequisites
- Python 3.7 or higher
- tkinter (usually included with Python)
- A Meshtastic device (connected via serial or accessible via TCP/IP)

### Setup

1. **Clone or download the application:**
   ```bash
   # If you have git
   git clone <repository-url>
   cd meshpy-ui
   
   # Or simply download the files to a folder
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install meshtastic
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

## Usage

### Connecting to Your Device

1. **Select Connection Type:**
   - **Serial**: Connect via USB/serial port (most common)
   - **TCP**: Connect via network (requires WiFi-enabled device)

2. **Set Connection Parameters:**
   - **Serial**: Use "auto" for automatic detection, or specify port (e.g., `/dev/ttyUSB0`, `COM3`)
   - **TCP**: Use "auto" for localhost, or specify IP address (e.g., `192.168.1.100`)

3. **Click "Connect"** to establish connection

### Using the Chat Interface

1. **Select Destination:**
   - Choose "Broadcast" to send to all nodes
   - Select specific node from the dropdown menu

2. **Type Your Message:**
   - Enter message in the text field
   - Press Enter or click "Send"

3. **Message Options:**
   - Check "Request ACK" for delivery confirmation
   - Click "Clear Chat" to clear message history

### Configuring Your Device

1. **Update Node Information:**
   - Enter new long name and short name
   - Click "Update Node Info"

2. **Channel Settings:**
   - Configure channel names and PSK
   - Ensure all devices use the same channel settings

3. **Device Management:**
   - Use "Get Device Info" to refresh device information
   - "Reboot Device" for soft restart
   - "Factory Reset" to restore default settings (use with caution)

### Monitoring the Network

1. **View Node List:**
   - Check the Map tab for all discovered nodes
   - Monitor battery levels and connection status

2. **Track Messages:**
   - All messages appear in the Chat tab with timestamps
   - Messages show sender, recipient, and content

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to device
- Ensure device is powered on and connected
- Check USB cable and port
- Verify correct port/IP address
- Try different connection type

**Problem**: Device not detected automatically
- Manually specify the port (e.g., `/dev/ttyUSB0`)
- Check device drivers are installed
- Ensure device is not being used by another application

### Message Issues

**Problem**: Messages not sending
- Verify connection is established
- Check if device is within range of other nodes
- Ensure channel settings match other devices

**Problem**: Not receiving messages
- Check if other devices are using the same channel
- Verify PSK settings match
- Ensure device is not in sleep mode

### Configuration Issues

**Problem**: Settings not updating
- Ensure stable connection to device
- Try reconnecting and retrying
- Check device firmware version compatibility

## Technical Details

### Architecture
- **GUI Framework**: tkinter with ttk themed widgets
- **Threading**: Separate threads for device communication and GUI updates
- **Event System**: Uses pypubsub for handling Meshtastic events
- **Error Handling**: Comprehensive error handling with user-friendly messages

### Supported Interfaces
- **Serial Interface**: Direct USB/serial connection
- **TCP Interface**: Network connection via WiFi
- **Future**: Bluetooth interface support planned

### Dependencies
- `meshtastic`: Python library for Meshtastic communication
- `tkinter`: GUI framework (standard library)
- `pypubsub`: Event system for Meshtastic events
- `threading`: Concurrent processing
- `queue`: Thread-safe message passing

## Contributing

Feel free to contribute to this project by:
- Reporting bugs and issues
- Suggesting new features
- Submitting pull requests
- Improving documentation

## License

This project is open source. Please check the license file for details.

## Support

For support with this application:
1. Check the troubleshooting section above
2. Review the official Meshtastic documentation
3. Visit the Meshtastic community forums
4. Check the GitHub issues page

## Future Enhancements

- **Real Map Integration**: Integration with actual mapping services
- **GPS Tracking**: Display node positions on map
- **Message History**: Persistent message storage
- **Plugin System**: Support for custom plugins
- **Advanced Configuration**: More device configuration options
- **Bluetooth Support**: Direct Bluetooth connection to devices
- **Multi-device Support**: Manage multiple devices simultaneously

---

**Note**: This application requires the Meshtastic Python library and a compatible Meshtastic device. Ensure your device firmware is up to date for best compatibility. 