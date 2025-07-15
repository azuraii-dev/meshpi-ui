#!/usr/bin/env python3
"""
Path utilities for Meshtastic UI
Handles data directories properly for both development and executable modes
"""

import os
import sys
import platform
from pathlib import Path

def is_executable():
    """Check if running as PyInstaller executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_executable_dir():
    """Get the directory containing the executable"""
    if is_executable():
        # Running as executable - get the directory containing the .exe/.app
        return Path(sys.executable).parent
    else:
        # Running as script - get the project root directory
        return Path(__file__).parent.parent

def get_user_data_dir():
    """Get the appropriate user data directory for the current OS"""
    app_name = "MeshtasticUI"
    
    system = platform.system()
    
    if system == "Windows":
        # Windows: %APPDATA%\MeshtasticUI
        base_dir = os.environ.get('APPDATA', '')
        if not base_dir:
            base_dir = Path.home() / "AppData" / "Roaming"
        return Path(base_dir) / app_name
    
    elif system == "Darwin":  # macOS
        # macOS: ~/Library/Application Support/MeshtasticUI
        return Path.home() / "Library" / "Application Support" / app_name
    
    else:  # Linux and others
        # Linux: ~/.local/share/MeshtasticUI (XDG standard)
        base_dir = os.environ.get('XDG_DATA_HOME', '')
        if not base_dir:
            base_dir = Path.home() / ".local" / "share"
        return Path(base_dir) / app_name

def get_config_dir():
    """Get the appropriate config directory for the current OS"""
    app_name = "MeshtasticUI"
    
    system = platform.system()
    
    if system == "Windows":
        # Windows: Same as data dir
        return get_user_data_dir()
    
    elif system == "Darwin":  # macOS
        # macOS: ~/Library/Preferences/MeshtasticUI
        return Path.home() / "Library" / "Preferences" / app_name
    
    else:  # Linux and others
        # Linux: ~/.config/MeshtasticUI (XDG standard)
        base_dir = os.environ.get('XDG_CONFIG_HOME', '')
        if not base_dir:
            base_dir = Path.home() / ".config"
        return Path(base_dir) / app_name

def get_data_directory():
    """Get the directory where data files should be stored"""
    if is_executable():
        # Running as executable - use user data directory
        data_dir = get_user_data_dir()
    else:
        # Running as script - use local database directory for development
        data_dir = get_executable_dir() / "database"
    
    # Ensure directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_database_path():
    """Get the full path to the database file"""
    return get_data_directory() / "meshpy_data.db"

def get_logs_directory():
    """Get the directory where log files should be stored"""
    if is_executable():
        # Running as executable - use user data directory
        logs_dir = get_user_data_dir() / "logs"
    else:
        # Running as script - use local logs directory for development
        logs_dir = get_executable_dir() / "logs"
    
    # Ensure directory exists
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

def get_config_file_path():
    """Get the path to the configuration file"""
    if is_executable():
        return get_config_dir() / "config.json"
    else:
        return get_executable_dir() / "config.json"

def ensure_data_directories():
    """Ensure all necessary data directories exist"""
    directories = [
        get_data_directory(),
        get_logs_directory(),
    ]
    
    if is_executable():
        directories.append(get_config_dir())
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    return {
        'data': get_data_directory(),
        'logs': get_logs_directory(),
        'config': get_config_dir() if is_executable() else get_executable_dir(),
        'database': get_database_path(),
    }

def get_runtime_info():
    """Get information about the current runtime environment"""
    return {
        'is_executable': is_executable(),
        'executable_dir': str(get_executable_dir()),
        'user_data_dir': str(get_user_data_dir()),
        'config_dir': str(get_config_dir()),
        'database_path': str(get_database_path()),
        'logs_dir': str(get_logs_directory()),
        'platform': platform.system(),
    } 