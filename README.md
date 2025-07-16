# Meshtastic UI

A comprehensive cross-platform interface for Meshtastic mesh networking devices with real-time chat, network topology visualization, analytics, emergency features, and device configuration.

## 🚀 Quick Start

### 1. Setup
```bash
git clone https://github.com/your-username/meshpy-ui.git
cd meshpy-ui
python3 setup.py
```

### 2. Run
- **Windows**: `run.bat`
- **macOS/Linux**: `./run.sh`

### 3. Build Executable
```bash
python3 setup.py build
```

## ✨ Features

- 🗺️ **Interactive Maps** - Real-time node positioning with multiple tile layers
- 💬 **Mesh Chat** - Message history, search, and status tracking
- 🌐 **Network Topology** - Visual network graph with signal strength
- 📊 **Analytics** - Battery trends, connectivity charts, and network health
- 🚨 **Emergency** - Beacon broadcasts and panic button with emergency contacts
- ⚙️ **Configuration** - Device settings, profiles, and multi-device management

## 📱 Supported Platforms

- **Windows** 10/11 (x64)
- **macOS** 10.9+ (Intel/Apple Silicon)
- **Linux** (Ubuntu, Debian, Fedora, etc.)

## 🔌 Connection Support

- **Serial** - USB/UART connections (auto-detection)
- **TCP** - Network connections to devices
- **Bluetooth** - Wireless device connections

## 📋 Requirements

- Python 3.8+
- Meshtastic device (any supported hardware)
- Internet connection (for maps and setup)

## 🛠️ Development

```bash
# Manual setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py
```

## 📖 Documentation

See `docs/` folder for detailed documentation and advanced features.

## 🐛 Issues & Support

Please report issues on GitHub or join the Meshtastic Discord community.

---

**Built with ❤️ for the Meshtastic community** 