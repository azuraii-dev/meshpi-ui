#!/usr/bin/env python3
"""
GPS and location utilities for Meshtastic UI
"""

import math
import logging

logger = logging.getLogger(__name__)

class GPSUtils:
    """Utilities for GPS and location operations"""
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS coordinates in kilometers using Haversine formula"""
        if None in (lat1, lon1, lat2, lon2):
            return None
            
        try:
            # Haversine formula
            R = 6371  # Earth's radius in kilometers
            
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            
            a = (math.sin(dlat/2) * math.sin(dlat/2) + 
                 math.cos(lat1_rad) * math.cos(lat2_rad) * 
                 math.sin(dlon/2) * math.sin(dlon/2))
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            
            return R * c
            
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return None

    @staticmethod
    def format_distance(distance_km):
        """Format distance for display"""
        if distance_km is None:
            return "N/A"
        
        if distance_km < 1:
            return f"{distance_km * 1000:.0f}m"
        else:
            return f"{distance_km:.1f}km"

    @staticmethod
    def format_coordinates(lat, lon, precision=6):
        """Format coordinates for display"""
        if lat is None or lon is None:
            return "N/A"
        
        try:
            return f"{lat:.{precision}f}, {lon:.{precision}f}"
        except Exception:
            return "Invalid coordinates"

    @staticmethod
    def validate_coordinates(lat, lon):
        """Validate GPS coordinates"""
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            
            if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
                return True, lat_f, lon_f
            else:
                return False, None, None
                
        except (ValueError, TypeError):
            return False, None, None

    @staticmethod
    def get_bearing(lat1, lon1, lat2, lon2):
        """Calculate bearing from point 1 to point 2 in degrees"""
        if None in (lat1, lon1, lat2, lon2):
            return None
            
        try:
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            dlon_rad = math.radians(lon2 - lon1)
            
            y = math.sin(dlon_rad) * math.cos(lat2_rad)
            x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
                 math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
            
            bearing_rad = math.atan2(y, x)
            bearing_deg = math.degrees(bearing_rad)
            
            # Normalize to 0-360 degrees
            return (bearing_deg + 360) % 360
            
        except Exception as e:
            logger.error(f"Error calculating bearing: {e}")
            return None

    @staticmethod
    def get_compass_direction(bearing):
        """Convert bearing to compass direction"""
        if bearing is None:
            return "N/A"
            
        try:
            directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                         "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            
            index = round(bearing / 22.5) % 16
            return directions[index]
            
        except Exception:
            return "N/A"

    @staticmethod
    def calculate_bounding_box(positions, padding_percent=10):
        """Calculate bounding box for a list of positions with padding"""
        if not positions:
            return None
            
        try:
            lats = [pos[0] for pos in positions if pos[0] is not None]
            lons = [pos[1] for pos in positions if pos[1] is not None]
            
            if not lats or not lons:
                return None
                
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
            
            # Add padding
            lat_range = max_lat - min_lat
            lon_range = max_lon - min_lon
            
            lat_padding = lat_range * (padding_percent / 100)
            lon_padding = lon_range * (padding_percent / 100)
            
            return {
                'min_lat': min_lat - lat_padding,
                'max_lat': max_lat + lat_padding,
                'min_lon': min_lon - lon_padding,
                'max_lon': max_lon + lon_padding,
                'center_lat': (min_lat + max_lat) / 2,
                'center_lon': (min_lon + max_lon) / 2
            }
            
        except Exception as e:
            logger.error(f"Error calculating bounding box: {e}")
            return None

    @staticmethod
    def calculate_zoom_level(bounding_box, map_width=400, map_height=400):
        """Calculate appropriate zoom level for a bounding box"""
        if not bounding_box:
            return 10  # Default zoom
            
        try:
            lat_range = bounding_box['max_lat'] - bounding_box['min_lat']
            lon_range = bounding_box['max_lon'] - bounding_box['min_lon']
            
            # Simple heuristic for zoom level based on coordinate range
            max_range = max(lat_range, lon_range)
            
            if max_range > 10:
                return 5
            elif max_range > 5:
                return 7
            elif max_range > 1:
                return 10
            elif max_range > 0.1:
                return 12
            elif max_range > 0.01:
                return 15
            else:
                return 17
                
        except Exception:
            return 10

    @staticmethod
    def convert_to_dms(coordinate, coordinate_type):
        """Convert decimal degrees to degrees, minutes, seconds format"""
        if coordinate is None:
            return "N/A"
            
        try:
            abs_coord = abs(coordinate)
            degrees = int(abs_coord)
            minutes_float = (abs_coord - degrees) * 60
            minutes = int(minutes_float)
            seconds = (minutes_float - minutes) * 60
            
            # Determine direction
            if coordinate_type.lower() == 'latitude':
                direction = 'N' if coordinate >= 0 else 'S'
            else:  # longitude
                direction = 'E' if coordinate >= 0 else 'W'
                
            return f"{degrees}°{minutes}'{seconds:.1f}\"{direction}"
            
        except Exception:
            return "Invalid"

    @staticmethod
    def is_valid_gps_fix(lat, lon, accuracy=None):
        """Determine if GPS coordinates represent a valid fix"""
        # Check basic coordinate validity
        valid, _, _ = GPSUtils.validate_coordinates(lat, lon)
        if not valid:
            return False
            
        # Check for common invalid coordinates
        if lat == 0 and lon == 0:
            return False  # Null Island
            
        # Check accuracy if provided (in meters)
        if accuracy is not None:
            if accuracy > 1000:  # Very poor accuracy
                return False
                
        return True

    @staticmethod
    def calculate_grid_square(lat, lon):
        """Calculate Maidenhead grid square locator"""
        if lat is None or lon is None:
            return "N/A"
            
        try:
            # Adjust longitude and latitude
            adj_lon = lon + 180
            adj_lat = lat + 90
            
            # Calculate grid square
            field_lon = int(adj_lon / 20)
            field_lat = int(adj_lat / 10)
            
            square_lon = int((adj_lon % 20) / 2)
            square_lat = int((adj_lat % 10) / 1)
            
            subsquare_lon = int(((adj_lon % 20) % 2) / (2/24))
            subsquare_lat = int(((adj_lat % 10) % 1) / (1/24))
            
            # Convert to characters
            grid = (chr(ord('A') + field_lon) + 
                   chr(ord('A') + field_lat) +
                   str(square_lon) + str(square_lat) +
                   chr(ord('a') + subsquare_lon) +
                   chr(ord('a') + subsquare_lat))
                   
            return grid
            
        except Exception as e:
            logger.error(f"Error calculating grid square: {e}")
            return "Error" 