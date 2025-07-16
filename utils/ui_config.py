#!/usr/bin/env python3
"""
UI Configuration Manager for Meshtastic UI
Handles theme preferences, window settings, and other UI configuration
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default UI configuration
DEFAULT_UI_CONFIG = {
    "theme": "darkly",
    "window": {
        "width": 1200,
        "height": 800,
        "maximized": False,
        "remember_size": True
    },
    "interface": {
        "show_tooltips": True,
        "auto_refresh": True,
        "refresh_interval": 5000,  # milliseconds
        "show_debug_info": False,
        "compact_mode": False
    },
    "notifications": {
        "show_connection_status": True,
        "show_message_notifications": True,
        "sound_enabled": False
    },
    "chat": {
        "message_history_limit": 100,
        "auto_scroll": True,
        "show_timestamps": True,
        "show_node_ids": False
    }
}

# Available ttkbootstrap themes
AVAILABLE_THEMES = {
    # Dark themes
    "darkly": {"name": "Darkly", "type": "dark", "description": "Modern dark theme"},
    "superhero": {"name": "Superhero", "type": "dark", "description": "Dark blue theme"},
    "cyborg": {"name": "Cyborg", "type": "dark", "description": "Dark with cyan accents"},
    "solar": {"name": "Solar", "type": "dark", "description": "Dark with orange accents"},
    "vapor": {"name": "Vapor", "type": "dark", "description": "Dark purple theme"},
    
    # Light themes  
    "flatly": {"name": "Flatly", "type": "light", "description": "Clean light theme"},
    "cosmo": {"name": "Cosmo", "type": "light", "description": "Modern light theme"},
    "journal": {"name": "Journal", "type": "light", "description": "Newspaper style"},
    "litera": {"name": "Litera", "type": "light", "description": "Clean typography"},
    "minty": {"name": "Minty", "type": "light", "description": "Fresh green accents"},
}

class UIConfigManager:
    """Manages UI configuration and preferences"""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the UI config manager
        
        Args:
            config_file: Optional custom config file path
        """
        if config_file:
            self.config_file = Path(config_file)
        else:
            # Use application data directory
            try:
                from utils.paths import get_config_dir
                self.config_file = get_config_dir() / "ui_config.json"
            except ImportError:
                # Fallback to local directory
                self.config_file = Path("ui_config.json")
        
        self.config = DEFAULT_UI_CONFIG.copy()
        self.load_config()
        
    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    
                # Merge with defaults (in case new options were added)
                self._merge_config(self.config, saved_config)
                logger.info(f"UI configuration loaded from {self.config_file}")
            else:
                logger.info("No UI configuration file found, using defaults")
                self.save_config()  # Create default config file
                
        except Exception as e:
            logger.error(f"Error loading UI configuration: {e}")
            logger.info("Using default UI configuration")
            
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            logger.debug(f"UI configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error saving UI configuration: {e}")
            
    def _merge_config(self, default: Dict[str, Any], saved: Dict[str, Any]) -> None:
        """Recursively merge saved config with defaults"""
        for key, value in saved.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
                    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g. 'window.width')"""
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """Set configuration value using dot notation"""
        try:
            keys = key.split('.')
            config = self.config
            
            # Navigate to parent
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
                
            # Set value
            config[keys[-1]] = value
            
            if save:
                self.save_config()
                
        except Exception as e:
            logger.error(f"Error setting UI config {key}={value}: {e}")
            
    def get_theme(self) -> str:
        """Get current theme name"""
        return self.get("theme", "darkly")
        
    def set_theme(self, theme: str, save: bool = True) -> None:
        """Set theme and optionally save"""
        if theme in AVAILABLE_THEMES:
            self.set("theme", theme, save)
            logger.info(f"UI theme changed to: {theme}")
        else:
            logger.warning(f"Unknown theme: {theme}")
            
    def get_window_config(self) -> Dict[str, Any]:
        """Get window configuration"""
        return self.get("window", {})
        
    def set_window_config(self, width: int = None, height: int = None, 
                         maximized: bool = None, save: bool = True) -> None:
        """Update window configuration"""
        if width is not None:
            self.set("window.width", width, False)
        if height is not None:
            self.set("window.height", height, False)
        if maximized is not None:
            self.set("window.maximized", maximized, False)
            
        if save:
            self.save_config()
            
    def get_available_themes(self) -> Dict[str, Dict[str, str]]:
        """Get available themes with metadata"""
        return AVAILABLE_THEMES.copy()
        
    def get_theme_info(self, theme: str) -> Dict[str, str]:
        """Get information about a specific theme"""
        return AVAILABLE_THEMES.get(theme, {})
        
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self.config = DEFAULT_UI_CONFIG.copy()
        self.save_config()
        logger.info("UI configuration reset to defaults")
        
    def export_config(self, file_path: str) -> bool:
        """Export configuration to a file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"UI configuration exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting UI configuration: {e}")
            return False
            
    def import_config(self, file_path: str) -> bool:
        """Import configuration from a file"""
        try:
            with open(file_path, 'r') as f:
                imported_config = json.load(f)
                
            # Validate and merge
            self._merge_config(DEFAULT_UI_CONFIG.copy(), imported_config)
            self.config = DEFAULT_UI_CONFIG
            self.save_config()
            
            logger.info(f"UI configuration imported from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error importing UI configuration: {e}")
            return False

# Global UI config instance
_ui_config = None

def get_ui_config() -> UIConfigManager:
    """Get the global UI configuration manager instance"""
    global _ui_config
    if _ui_config is None:
        _ui_config = UIConfigManager()
    return _ui_config 