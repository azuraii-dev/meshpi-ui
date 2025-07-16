#!/usr/bin/env python3
"""
Test script to try modern themes with the existing Meshtastic UI
This shows how easy it is to modernize the existing tkinter code
"""

import sys
import os

# Add the current directory to path so we can import from the main app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *

# Test different themes
AVAILABLE_THEMES = [
    'darkly',     # Dark theme
    'solar',      # Dark with orange accents  
    'superhero',  # Dark blue
    'cyborg',     # Dark with cyan accents
    'vapor',      # Light purple
    'flatly',     # Clean light theme
    'cosmo',      # Modern light theme
    'journal',    # Newspaper style
]

class ModernThemeTest:
    def __init__(self):
        # Create the main window with a modern theme
        self.root = ttk_boot.Window(themename="darkly")  # Try different themes!
        self.root.title("Meshtastic UI - Modern Theme Test")
        self.root.geometry("800x600")
        
        self.current_theme = "darkly"
        self.setup_ui()
        
    def setup_ui(self):
        """Setup a simple UI that mirrors your main app structure"""
        
        # Main frame (same as your app)
        main_frame = ttk_boot.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Theme selector
        theme_frame = ttk_boot.LabelFrame(main_frame, text="Theme Selector", padding="10")
        theme_frame.pack(fill="x", pady=(0, 10))
        
        ttk_boot.Label(theme_frame, text="Choose Theme:").pack(side="left", padx=(0, 10))
        
        self.theme_var = tk.StringVar(value=self.current_theme)
        theme_combo = ttk_boot.Combobox(theme_frame, textvariable=self.theme_var, 
                                       values=AVAILABLE_THEMES, state="readonly")
        theme_combo.pack(side="left", padx=(0, 10))
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # Connection frame (mirrors your main.py)
        conn_frame = ttk_boot.LabelFrame(main_frame, text="Connection", padding="10")
        conn_frame.pack(fill="x", pady=(0, 10))
        
        # Connection controls (same layout as your app)
        controls = ttk_boot.Frame(conn_frame)
        controls.pack(fill="x")
        
        ttk_boot.Label(controls, text="Connection Type:").pack(side="left", padx=(0, 10))
        
        self.conn_type = tk.StringVar(value="Serial")
        conn_combo = ttk_boot.Combobox(controls, textvariable=self.conn_type,
                                      values=["Serial", "TCP"], state="readonly", width=10)
        conn_combo.pack(side="left", padx=(0, 10))
        
        ttk_boot.Label(controls, text="Port/IP:").pack(side="left", padx=(0, 10))
        
        self.conn_param = tk.StringVar(value="auto")
        param_entry = ttk_boot.Entry(controls, textvariable=self.conn_param, width=20)
        param_entry.pack(side="left", padx=(0, 10))
        
        # Buttons with modern styling
        btn_frame = ttk_boot.Frame(controls)
        btn_frame.pack(side="left", padx=(10, 0))
        
        connect_btn = ttk_boot.Button(btn_frame, text="Connect", bootstyle="success")
        connect_btn.pack(side="left", padx=(0, 5))
        
        disconnect_btn = ttk_boot.Button(btn_frame, text="Disconnect", bootstyle="danger")
        disconnect_btn.pack(side="left")
        
        # Status indicators with colors
        status_frame = ttk_boot.Frame(conn_frame)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ttk_boot.Label(status_frame, text="Status: Disconnected", 
                                          bootstyle="danger")
        self.status_label.pack(side="left")
        
        self.gps_label = ttk_boot.Label(status_frame, text="GPS: N/A", 
                                       bootstyle="secondary")
        self.gps_label.pack(side="right")
        
        # Notebook tabs (same structure as your app)
        self.notebook = ttk_boot.Notebook(main_frame, bootstyle="dark")
        self.notebook.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create sample tabs
        self.create_sample_tabs()
        
        # Info panel
        info_frame = ttk_boot.LabelFrame(main_frame, text="Theme Information", padding="10")
        info_frame.pack(fill="x")
        
        info_text = f"""
🎨 Current Theme: {self.current_theme}
✨ This is your existing UI with modern themes applied!
🔄 Try different themes from the dropdown above
📝 Your existing tkinter/ttk code works with minimal changes
        """.strip()
        
        ttk_boot.Label(info_frame, text=info_text, justify="left").pack(anchor="w")
        
    def create_sample_tabs(self):
        """Create sample tabs that mirror your main app"""
        
        # Map tab
        map_frame = ttk_boot.Frame(self.notebook)
        self.notebook.add(map_frame, text="🗺️ Map")
        
        map_content = ttk_boot.LabelFrame(map_frame, text="Map Visualization", padding="10")
        map_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk_boot.Label(map_content, text="Your map UI would go here", 
                      font=("Arial", 14)).pack(expand=True)
        
        # Chat tab  
        chat_frame = ttk_boot.Frame(self.notebook)
        self.notebook.add(chat_frame, text="💬 Chat")
        
        chat_content = ttk_boot.LabelFrame(chat_frame, text="Mesh Chat", padding="10")
        chat_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Sample chat controls
        msg_frame = ttk_boot.Frame(chat_content)
        msg_frame.pack(fill="x", side="bottom", pady=(10, 0))
        
        msg_entry = ttk_boot.Entry(msg_frame)
        msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        msg_entry.insert(0, "Type a message...")  # Add placeholder text this way
        
        send_btn = ttk_boot.Button(msg_frame, text="Send", bootstyle="primary")
        send_btn.pack(side="right")
        
        # Emergency tab
        emergency_frame = ttk_boot.Frame(self.notebook)
        self.notebook.add(emergency_frame, text="🚨 Emergency")
        
        emergency_content = ttk_boot.LabelFrame(emergency_frame, text="Emergency Features", padding="10")
        emergency_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Emergency button with danger styling
        emergency_btn = ttk_boot.Button(emergency_content, text="🚨 EMERGENCY BEACON", 
                                       bootstyle="danger-outline", width=30)
        emergency_btn.pack(pady=20)
        
        # Config tab
        config_frame = ttk_boot.Frame(self.notebook)
        self.notebook.add(config_frame, text="⚙️ Config")
        
        config_content = ttk_boot.LabelFrame(config_frame, text="Device Configuration", padding="10")
        config_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk_boot.Label(config_content, text="Configuration options would go here", 
                      font=("Arial", 14)).pack(expand=True)
        
    def change_theme(self, event=None):
        """Change the theme dynamically"""
        new_theme = self.theme_var.get()
        self.current_theme = new_theme
        
        # Apply new theme
        self.root.style.theme_use(new_theme)
        
        # Update info text
        for child in self.root.winfo_children():
            self.update_info_text(child)
            
    def update_info_text(self, widget):
        """Update the info text with current theme"""
        # This is a simple way to find and update the info text
        # In a real app, you'd keep a reference to the specific widget
        try:
            for child in widget.winfo_children():
                if hasattr(child, 'configure') and 'text' in child.configure():
                    current_text = child.cget('text')
                    if "Current Theme:" in current_text:
                        new_text = f"""
🎨 Current Theme: {self.current_theme}
✨ This is your existing UI with modern themes applied!
🔄 Try different themes from the dropdown above
📝 Your existing tkinter/ttk code works with minimal changes
                        """.strip()
                        child.configure(text=new_text)
                        return
                self.update_info_text(child)
        except:
            pass
            
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    print("🎨 Starting Modern Theme Test...")
    print("Try different themes from the dropdown!")
    print("This shows how your existing UI could look with minimal changes.")
    print("-" * 60)
    
    app = ModernThemeTest()
    app.run() 