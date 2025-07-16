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
        self.debug_id = id(self)  # Unique ID for debugging
        
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Initializing with padding={padding}, threshold={min_scroll_threshold}")
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Parent: {parent}")
        
        # Configure parent
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Parent grid configured")
        
        # Create container structure
        self._create_container()
        
        # Bind resize events
        self.parent.bind('<Configure>', self._on_parent_configure)
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Resize events bound")
        
    def _create_container(self):
        """Create the responsive container structure"""
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Creating container structure")
        
        # Main container frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Main frame created and gridded")
        
        # Canvas for scrolling (always present)
        self.canvas = tk.Canvas(self.main_frame, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Canvas created and gridded")
        
        # Scrollbar (initially hidden)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Scrollbar created (hidden)")
        
        # Content frame inside canvas
        self.content_frame = ttk.Frame(self.canvas, padding=self.padding)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Content frame created in canvas, window ID: {self.canvas_window}")
        
        # Configure scrolling
        self.content_frame.bind('<Configure>', self._configure_scroll_region)
        self.canvas.bind('<Configure>', self._configure_canvas_window)
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Configure bindings set up")
        
        # Bind mouse wheel events using Enter/Leave approach
        self._bind_mouse_wheel()
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Mouse wheel events bound")
        
    def _bind_mouse_wheel(self):
        """Bind mouse wheel events using Enter/Leave canvas approach (most reliable)"""
        import platform
        
        system = platform.system()
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Setting up mouse wheel for platform: {system}")
        
        def on_mousewheel(event):
            if self.scrollbar_visible:
                # Cross-platform mouse wheel handling
                if system == "Windows":
                    delta = int(-1 * (event.delta / 120))
                    self.canvas.yview_scroll(delta, "units")
                    logger.debug(f"[ResponsiveContainer-{self.debug_id}] Windows scroll delta: {delta}")
                elif system == "Darwin":  # macOS
                    delta = int(-1 * event.delta)
                    self.canvas.yview_scroll(delta, "units")
                    logger.debug(f"[ResponsiveContainer-{self.debug_id}] macOS scroll delta: {delta}")
                else:  # Linux and others
                    if event.num == 4:
                        self.canvas.yview_scroll(-1, "units")
                        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Linux scroll up")
                    elif event.num == 5:
                        self.canvas.yview_scroll(1, "units")
                        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Linux scroll down")
            else:
                logger.debug(f"[ResponsiveContainer-{self.debug_id}] Mouse wheel event ignored - scrollbar not visible")
        
        def bind_to_mousewheel(event):
            """Bind mouse wheel events when mouse enters canvas area"""
            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Mouse entered canvas - binding wheel events")
            if system == "Linux":
                self.canvas.bind_all("<Button-4>", on_mousewheel)
                self.canvas.bind_all("<Button-5>", on_mousewheel)
            else:  # Windows and macOS
                self.canvas.bind_all("<MouseWheel>", on_mousewheel)
                
        def unbind_from_mousewheel(event):
            """Unbind mouse wheel events when mouse leaves canvas area"""
            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Mouse left canvas - unbinding wheel events")
            if system == "Linux":
                self.canvas.unbind_all("<Button-4>")
                self.canvas.unbind_all("<Button-5>")
            else:  # Windows and macOS
                self.canvas.unbind_all("<MouseWheel>")
        
        # Bind Enter/Leave events to canvas
        self.canvas.bind('<Enter>', bind_to_mousewheel)
        self.canvas.bind('<Leave>', unbind_from_mousewheel)
    
    def _on_parent_configure(self, event=None):
        """Handle parent window resize"""
        if event:
            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Parent configure event: {event.width}x{event.height}")
        else:
            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Parent configure event (no event data)")
        
        # Reset retry count on configure events (might be becoming visible)
        self._retry_count = 0
        
        # Use after_idle to ensure all layout updates are complete
        self.parent.after_idle(self._check_scroll_needed)
    
    def on_visibility_change(self):
        """Call this method when the container becomes visible (e.g., tab switch)"""
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Visibility change detected, forcing scroll check")
        
        # Reset retry count
        self._retry_count = 0
        
        # Force geometry update
        try:
            self.parent.update_idletasks()
            self.canvas.update_idletasks()
        except Exception as e:
            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Error updating during visibility change: {e}")
        
        # Schedule scroll check
        self.parent.after(50, self._check_scroll_needed)
    
    def _check_scroll_needed(self):
        """Check if scrolling is needed and show/hide scrollbar accordingly"""
        try:
            # Force update to get accurate measurements
            self.parent.update_idletasks()
            
            # Check if the widget is actually visible/mapped
            try:
                if not self.canvas.winfo_viewable():
                    logger.debug(f"[ResponsiveContainer-{self.debug_id}] Canvas not viewable, skipping check")
                    return
            except Exception:
                # winfo_viewable might fail if widget isn't fully initialized
                pass
            
            # Get canvas height
            canvas_height = self.canvas.winfo_height()
            canvas_width = self.canvas.winfo_width()
            
            # Check if canvas is properly initialized
            if canvas_height <= 1:  
                # Try to get parent size as fallback
                try:
                    parent_height = self.parent.winfo_height()
                    parent_width = self.parent.winfo_width()
                    
                    # If parent has size but canvas doesn't, force geometry update
                    if parent_height > 1:
                        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Parent has size {parent_width}x{parent_height}, forcing canvas update")
                        self.canvas.update()
                        canvas_height = self.canvas.winfo_height()
                        canvas_width = self.canvas.winfo_width()
                        
                        # If still no size, try configuring manually
                        if canvas_height <= 1 and parent_height > 1:
                            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Scheduling retry after canvas update")
                            self.parent.after(200, self._check_scroll_needed)
                            return
                except Exception as e:
                    logger.debug(f"[ResponsiveContainer-{self.debug_id}] Error getting parent size: {e}")
                
                if canvas_height <= 1:
                    # Still not initialized, but don't retry forever
                    retry_count = getattr(self, '_retry_count', 0)
                    if retry_count < 50:  # Max 5 seconds of retries
                        self._retry_count = retry_count + 1
                        if retry_count % 10 == 0:  # Only log every 10 retries
                            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Canvas not initialized yet, retrying (attempt {retry_count + 1}/50)")
                        self.parent.after(100, self._check_scroll_needed)
                    else:
                        logger.warning(f"[ResponsiveContainer-{self.debug_id}] Canvas failed to initialize after 50 retries, giving up")
                    return
            else:
                # Canvas is properly sized, reset retry count
                if hasattr(self, '_retry_count'):
                    self._retry_count = 0
                
            # Get content height
            content_height = self.content_frame.winfo_reqheight()
            content_width = self.content_frame.winfo_reqwidth()
            
            # Determine if scrollbar is needed
            overflow = content_height - canvas_height
            scrollbar_needed = overflow > self.min_scroll_threshold
            
            # Only log when scrollbar state changes or significant events
            if scrollbar_needed and not self.scrollbar_visible:
                logger.info(f"[ResponsiveContainer-{self.debug_id}] Showing scrollbar - overflow: {overflow}px > {self.min_scroll_threshold}px")
                self._show_scrollbar()
            elif not scrollbar_needed and self.scrollbar_visible:
                logger.info(f"[ResponsiveContainer-{self.debug_id}] Hiding scrollbar - overflow: {overflow}px <= {self.min_scroll_threshold}px")
                self._hide_scrollbar()
                
        except Exception as e:
            logger.error(f"[ResponsiveContainer-{self.debug_id}] Error checking scroll: {e}", exc_info=True)
    
    def _show_scrollbar(self):
        """Show the scrollbar"""
        try:
            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Attempting to show scrollbar")
            self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
            self.scrollbar_visible = True
            logger.info(f"[ResponsiveContainer-{self.debug_id}] Scrollbar shown successfully")
            
            # Update canvas window width to account for scrollbar
            self._configure_canvas_window()
            
        except Exception as e:
            logger.error(f"[ResponsiveContainer-{self.debug_id}] Error showing scrollbar: {e}", exc_info=True)
    
    def _hide_scrollbar(self):
        """Hide the scrollbar"""
        try:
            logger.debug(f"[ResponsiveContainer-{self.debug_id}] Attempting to hide scrollbar")
            self.scrollbar.grid_remove()
            self.scrollbar_visible = False
            logger.info(f"[ResponsiveContainer-{self.debug_id}] Scrollbar hidden successfully")
            
            # Update canvas window width to account for no scrollbar
            self._configure_canvas_window()
            
        except Exception as e:
            logger.error(f"[ResponsiveContainer-{self.debug_id}] Error hiding scrollbar: {e}", exc_info=True)
    
    def _configure_scroll_region(self, event=None):
        """Configure the scroll region and check if scrollbar is needed"""
        try:
            bbox = self.canvas.bbox("all")
            self.canvas.configure(scrollregion=bbox)
            
            # Check if scrollbar is needed after content changes
            self.parent.after_idle(self._check_scroll_needed)
            
        except Exception as e:
            logger.error(f"[ResponsiveContainer-{self.debug_id}] Error configuring scroll region: {e}", exc_info=True)
            
    def _configure_canvas_window(self, event=None):
        """Configure the canvas window size"""
        try:
            canvas_width = self.canvas.winfo_width()
            
            if canvas_width > 1:
                # Adjust width based on whether scrollbar is visible
                scrollbar_width = self.scrollbar.winfo_reqwidth() if self.scrollbar_visible else 0
                content_width = canvas_width - scrollbar_width
                
                self.canvas.itemconfig(self.canvas_window, width=content_width)
                
                # Also trigger a scroll check
                self.parent.after_idle(self._check_scroll_needed)
                
        except Exception as e:
            logger.error(f"[ResponsiveContainer-{self.debug_id}] Error configuring canvas window: {e}", exc_info=True)
    
    def get_content_frame(self):
        """Get the frame where content should be added"""
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Returning content frame: {self.content_frame}")
        return self.content_frame
    
    def force_scroll_check(self):
        """Force a scroll check (useful after adding/removing content)"""
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Force scroll check requested")
        self.parent.after_idle(self._check_scroll_needed)
    
    def set_min_scroll_threshold(self, threshold):
        """Update the minimum scroll threshold"""
        old_threshold = self.min_scroll_threshold
        self.min_scroll_threshold = threshold
        logger.debug(f"[ResponsiveContainer-{self.debug_id}] Scroll threshold changed from {old_threshold} to {threshold}")
        self.force_scroll_check()

    def debug_status(self):
        """Print detailed debug status"""
        try:
            canvas_size = f"{self.canvas.winfo_width()}x{self.canvas.winfo_height()}"
            content_size = f"{self.content_frame.winfo_reqwidth()}x{self.content_frame.winfo_reqheight()}"
            logger.info(f"[ResponsiveContainer-{self.debug_id}] DEBUG STATUS:")
            logger.info(f"[ResponsiveContainer-{self.debug_id}]   Canvas size: {canvas_size}")
            logger.info(f"[ResponsiveContainer-{self.debug_id}]   Content size: {content_size}")
            logger.info(f"[ResponsiveContainer-{self.debug_id}]   Scrollbar visible: {self.scrollbar_visible}")
            logger.info(f"[ResponsiveContainer-{self.debug_id}]   Scroll threshold: {self.min_scroll_threshold}")
            logger.info(f"[ResponsiveContainer-{self.debug_id}]   Content children: {len(self.content_frame.winfo_children())}")
        except Exception as e:
            logger.error(f"[ResponsiveContainer-{self.debug_id}] Error getting debug status: {e}")


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
    logger.debug(f"Creating responsive tab for parent: {parent}")
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
    logger.debug(f"Making frame responsive: {frame}")
    
    # Clear the frame first
    children = frame.winfo_children()
    logger.debug(f"Clearing {len(children)} children from frame")
    for child in children:
        child.destroy()
        
    return ResponsiveContainer(frame, padding, min_scroll_threshold) 