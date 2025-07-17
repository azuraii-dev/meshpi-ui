#!/usr/bin/env python3
"""
Responsive UI utilities for Meshtastic UI
Provides automatic scrolling and responsive containers
"""

import tkinter as tk
import ttkbootstrap as ttk
import logging

logger = logging.getLogger(__name__)

class ResponsiveContainer:
    """
    A responsive container that automatically adds scrolling when content exceeds available height.
    
    This container monitors the content size and viewport size, automatically enabling
    scrolling when needed and adjusting to window resizing.
    
    Uses a simpler approach: content is always in a scrollable canvas, but scrollbar
    is only shown when needed.
    """
    
    def __init__(self, parent, padding="10", min_scroll_threshold=50):
        """
        Initialize responsive container
        
        Args:
            parent: Parent widget
            padding: Padding around content
            min_scroll_threshold: Minimum pixels of overflow before showing scrollbar
        """
        self.parent = parent
        self.padding = padding
        self.min_scroll_threshold = min_scroll_threshold
        self.scrollbar_visible = False
        
        # Configure parent
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        
        # Create container structure
        self._create_container()
        
        # Bind resize events
        self.parent.bind('<Configure>', self._on_parent_configure)
        
    def _create_container(self):
        """Create the responsive container structure"""
        # Main container frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Canvas for scrolling (always present)
        # Configure background to match theme
        bg_color = self._get_theme_bg_color()
        self.canvas = tk.Canvas(self.main_frame, 
                               highlightthickness=0, 
                               bg=bg_color,
                               bd=0,  # Remove border
                               relief='flat')  # Flat relief
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar (initially hidden)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Content frame inside canvas
        self.content_frame = ttk.Frame(self.canvas, padding=self.padding)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        
        # Configure scrolling
        self.content_frame.bind('<Configure>', self._configure_scroll_region)
        self.canvas.bind('<Configure>', self._configure_canvas_window)
        
        # Bind mouse wheel events
        self._bind_mouse_wheel()
        
        # Schedule a theme update after widget is fully initialized
        self.parent.after(100, self._delayed_theme_setup)
    
    def _delayed_theme_setup(self):
        """Set up theme after widget is fully initialized"""
        try:
            self.update_theme()
        except Exception as e:
            logger.debug(f"Error in delayed theme setup: {e}")
    
    def _get_theme_bg_color(self):
        """Get the background color from the current theme"""
        try:
            # Get the background color from a ttk Frame
            style = ttk.Style()
            
            # Try multiple style elements to find background color
            bg_color = None
            
            # First try TFrame background
            bg_color = style.lookup('TFrame', 'background')
            logger.debug(f"TFrame background: {bg_color}")
            
            # Try TNotebook.Tab for better theme integration
            if not bg_color:
                bg_color = style.lookup('TNotebook.Tab', 'background')
                logger.debug(f"TNotebook.Tab background: {bg_color}")
            
            # Try TLabel background
            if not bg_color:
                bg_color = style.lookup('TLabel', 'background')
                logger.debug(f"TLabel background: {bg_color}")
                
            # Try to get from the actual parent widget
            if not bg_color and hasattr(self.parent, 'cget'):
                try:
                    bg_color = self.parent.cget('bg')
                    logger.debug(f"Parent bg: {bg_color}")
                except:
                    pass
            
            # Try to get from the style's theme colors directly
            if not bg_color:
                theme_colors = style.theme_settings(style.theme.name)
                if theme_colors and 'TFrame' in theme_colors:
                    frame_settings = theme_colors['TFrame']
                    if 'background' in frame_settings:
                        bg_color = frame_settings['background']
                        logger.debug(f"Theme TFrame background: {bg_color}")
                        
            # If still no color, use fallback based on theme name
            if not bg_color:
                theme_name = style.theme.name.lower()
                if any(dark in theme_name for dark in ['dark', 'cyborg', 'solar', 'superhero']):
                    bg_color = '#2b3e50'  # Dark theme background
                else:
                    bg_color = '#ffffff'  # Light theme background
                logger.debug(f"Fallback color for theme {theme_name}: {bg_color}")
                    
            return bg_color
            
        except Exception as e:
            logger.debug(f"Could not get theme background color: {e}")
            # Safe fallback color (darkly theme background)
            return '#2b3e50'
        
    def _bind_mouse_wheel(self):
        """Bind mouse wheel events for scrolling using a global approach"""
        def on_mousewheel(event):
            if self.scrollbar_visible:
                # Check if mouse is over our container area
                widget = event.widget
                # Find the root coordinate of the mouse
                try:
                    x_root = event.x_root
                    y_root = event.y_root
                    
                    # Get our main frame's position and size
                    main_x = self.main_frame.winfo_rootx()
                    main_y = self.main_frame.winfo_rooty()
                    main_w = self.main_frame.winfo_width()
                    main_h = self.main_frame.winfo_height()
                    
                    # Check if mouse is within our frame bounds
                    if (main_x <= x_root <= main_x + main_w and 
                        main_y <= y_root <= main_y + main_h):
                        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                        return "break"  # Prevent further event propagation
                except:
                    # Fallback: just scroll if scrollbar is visible
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                    return "break"
                
        def on_mousewheel_linux(event):
            if self.scrollbar_visible:
                try:
                    x_root = event.x_root
                    y_root = event.y_root
                    
                    # Get our main frame's position and size
                    main_x = self.main_frame.winfo_rootx()
                    main_y = self.main_frame.winfo_rooty()
                    main_w = self.main_frame.winfo_width()
                    main_h = self.main_frame.winfo_height()
                    
                    # Check if mouse is within our frame bounds
                    if (main_x <= x_root <= main_x + main_w and 
                        main_y <= y_root <= main_y + main_h):
                        if event.num == 4:
                            self.canvas.yview_scroll(-1, "units")
                        elif event.num == 5:
                            self.canvas.yview_scroll(1, "units")
                        return "break"
                except:
                    # Fallback
                    if event.num == 4:
                        self.canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        self.canvas.yview_scroll(1, "units")
                    return "break"
        
        # Bind to the top-level window to catch all mouse wheel events
        def bind_to_root():
            try:
                root = self.parent.winfo_toplevel()
                if root:
                    root.bind_all("<MouseWheel>", on_mousewheel, add=True)
                    root.bind_all("<Button-4>", on_mousewheel_linux, add=True)
                    root.bind_all("<Button-5>", on_mousewheel_linux, add=True)
                    logger.debug("Global mouse wheel events bound successfully")
            except Exception as e:
                logger.debug(f"Could not bind global mouse wheel events: {e}")
                # Fallback to local binding
                self.main_frame.bind("<MouseWheel>", on_mousewheel, add=True)
                self.main_frame.bind("<Button-4>", on_mousewheel_linux, add=True)
                self.main_frame.bind("<Button-5>", on_mousewheel_linux, add=True)
        
        # Delay binding to ensure window is fully created
        self.parent.after(100, bind_to_root)
    
    def _on_parent_configure(self, event=None):
        """Handle parent window resize"""
        # Use after_idle to ensure all layout updates are complete
        self.parent.after_idle(self._check_scroll_needed)
    
    def _check_scroll_needed(self):
        """Check if scrolling is needed and show/hide scrollbar accordingly"""
        try:
            # Force update to get accurate measurements
            self.parent.update_idletasks()
            
            # Get canvas height
            canvas_height = self.canvas.winfo_height()
            if canvas_height <= 1:  # Not fully initialized yet
                self.parent.after(100, self._check_scroll_needed)
                return
                
            # Get content height
            content_height = self.content_frame.winfo_reqheight()
            
            # Determine if scrollbar is needed
            overflow = content_height - canvas_height
            scrollbar_needed = overflow > self.min_scroll_threshold
            
            if scrollbar_needed and not self.scrollbar_visible:
                self._show_scrollbar()
            elif not scrollbar_needed and self.scrollbar_visible:
                self._hide_scrollbar()
                
        except Exception as e:
            logger.debug(f"Error checking scroll: {e}")
    
    def _show_scrollbar(self):
        """Show the scrollbar"""
        try:
            self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
            self.scrollbar_visible = True
            logger.debug("Scrollbar shown")
        except Exception as e:
            logger.error(f"Error showing scrollbar: {e}")
    
    def _hide_scrollbar(self):
        """Hide the scrollbar"""
        try:
            self.scrollbar.grid_remove()
            self.scrollbar_visible = False
            logger.debug("Scrollbar hidden")
        except Exception as e:
            logger.error(f"Error hiding scrollbar: {e}")
    
    def _configure_scroll_region(self, event=None):
        """Configure the scroll region and check if scrollbar is needed"""
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Check if scrollbar is needed after content changes
            self.parent.after_idle(self._check_scroll_needed)
        except Exception as e:
            logger.debug(f"Error configuring scroll region: {e}")
            
    def _configure_canvas_window(self, event=None):
        """Configure the canvas window size"""
        try:
            canvas_width = self.canvas.winfo_width()
            if canvas_width > 1:
                # Adjust width based on whether scrollbar is visible
                scrollbar_width = self.scrollbar.winfo_reqwidth() if self.scrollbar_visible else 0
                content_width = canvas_width - scrollbar_width
                self.canvas.itemconfig(self.canvas_window, width=content_width)
        except Exception as e:
            logger.debug(f"Error configuring canvas window: {e}")
    
    def get_content_frame(self):
        """Get the frame where content should be added"""
        return self.content_frame
    
    def force_scroll_check(self):
        """Force a scroll check (useful after adding/removing content)"""
        self.parent.after_idle(self._check_scroll_needed)
    
    def set_min_scroll_threshold(self, threshold):
        """Update the minimum scroll threshold"""
        self.min_scroll_threshold = threshold
        self.force_scroll_check()
    
    def update_theme(self):
        """Update canvas background to match current theme"""
        try:
            # Get the new background color
            bg_color = self._get_theme_bg_color()
            old_color = self.canvas.cget('bg')
            
            logger.info(f"Updating canvas theme: {old_color} -> {bg_color}")
            
            # Configure the canvas background
            self.canvas.configure(bg=bg_color)
            
            # Force multiple update cycles to ensure the change takes effect
            self.canvas.update_idletasks()
            self.canvas.update()
            
            # Force a redraw by triggering a configure event
            self.canvas.event_generate('<Configure>')
            
            # Schedule a quick follow-up to ensure it sticks
            self.parent.after(20, lambda: self._force_canvas_redraw(bg_color))
                    
            logger.info(f"Canvas background updated to {bg_color}")
        except Exception as e:
            logger.error(f"Error updating theme: {e}")
    
    def _force_canvas_redraw(self, bg_color):
        """Force canvas to redraw with new background color"""
        try:
            # Set the background again
            self.canvas.configure(bg=bg_color)
            
            # Get current scroll region and reset it to force redraw
            current_scroll = self.canvas.cget('scrollregion')
            if current_scroll:
                self.canvas.configure(scrollregion='')
                self.canvas.update_idletasks()
                self.canvas.configure(scrollregion=current_scroll)
            
            logger.debug(f"Forced canvas redraw with color {bg_color}")
        except Exception as e:
            logger.debug(f"Error in forced canvas redraw: {e}")


def create_responsive_tab(parent, padding="10", min_scroll_threshold=50):
    """
    Convenience function to create a responsive tab container
    
    Args:
        parent: Parent widget (typically a tab frame)
        padding: Padding around content
        min_scroll_threshold: Minimum overflow before showing scrollbar
        
    Returns:
        ResponsiveContainer instance
    """
    return ResponsiveContainer(parent, padding, min_scroll_threshold)


def make_frame_responsive(frame, padding="5", min_scroll_threshold=30):
    """
    Convert an existing frame to be responsive
    
    Args:
        frame: Existing frame to make responsive
        padding: Padding around content  
        min_scroll_threshold: Minimum overflow before showing scrollbar
        
    Returns:
        ResponsiveContainer instance
    """
    # Clear the frame first
    for child in frame.winfo_children():
        child.destroy()
        
    return ResponsiveContainer(frame, padding, min_scroll_threshold) 