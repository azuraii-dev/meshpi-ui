#!/usr/bin/env python3
"""
Networking utilities for Meshtastic UI
"""

import requests
import threading
import logging
from .constants import IP_GEOLOCATION_SERVICES

logger = logging.getLogger(__name__)

class NetworkUtils:
    """Utilities for network operations"""
    
    @staticmethod
    def check_internet_connectivity(callback=None):
        """Check if internet is available for map tiles"""
        def check_connectivity():
            try:
                logger.info("Checking internet connectivity to OpenStreetMap...")
                headers = {
                    'User-Agent': 'MeshtasticUI/1.0 (Educational/Research Use)'
                }
                # Try a simple tile request instead of the main page
                response = requests.get("https://tile.openstreetmap.org/0/0/0.png", 
                                      headers=headers, timeout=10)
                logger.info(f"Response status code: {response.status_code}")
                internet_available = response.status_code == 200
                logger.info(f"Internet connectivity: {'Available' if internet_available else 'Unavailable'}")
                
                if callback:
                    callback(internet_available)
                    
                return internet_available
                
            except Exception as e:
                logger.info(f"No internet connectivity: {e}")
                if callback:
                    callback(False)
                return False
                
        if callback:
            # Run asynchronously if callback provided
            threading.Thread(target=check_connectivity, daemon=True).start()
        else:
            # Run synchronously
            return check_connectivity()
    
    @staticmethod
    def get_ip_location():
        """Get approximate location from IP address using multiple services"""
        try:
            logger.info("Attempting to get location from IP address...")
            
            for service in IP_GEOLOCATION_SERVICES:
                try:
                    headers = {
                        'User-Agent': 'MeshtasticUI/1.0 (Educational/Research Use)'
                    }
                    response = requests.get(service['url'], headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Special handling for ipinfo.io
                        if service['url'] == 'https://ipinfo.io/json':
                            if 'loc' in data:
                                lat_str, lon_str = data['loc'].split(',')
                                lat, lon = float(lat_str), float(lon_str)
                            else:
                                continue
                        else:
                            # Standard handling for other services
                            if service['lat_key'] in data and service['lon_key'] in data:
                                lat = float(data[service['lat_key']])
                                lon = float(data[service['lon_key']])
                            else:
                                continue
                        
                        # Get location name
                        location_name = data.get(service['location_key'], 'Unknown')
                        
                        # Validate coordinates
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            logger.info(f"Got IP location: {lat}, {lon} ({location_name})")
                            return (lat, lon, location_name)
                        else:
                            logger.warning(f"Invalid coordinates from {service['url']}: {lat}, {lon}")
                            continue
                            
                except requests.exceptions.RequestException as e:
                    logger.debug(f"IP geolocation service {service['url']} failed: {e}")
                    continue
                except (ValueError, KeyError) as e:
                    logger.debug(f"Error parsing response from {service['url']}: {e}")
                    continue
            
            logger.info("All IP geolocation services failed")
            return None
            
        except Exception as e:
            logger.error(f"Error getting IP location: {e}")
            return None

    @staticmethod
    def get_ip_location_async(callback):
        """Get IP location asynchronously with callback"""
        def get_location():
            result = NetworkUtils.get_ip_location()
            callback(result)
            
        threading.Thread(target=get_location, daemon=True).start()

    @staticmethod
    def test_url_connectivity(url, timeout=5):
        """Test connectivity to a specific URL"""
        try:
            headers = {
                'User-Agent': 'MeshtasticUI/1.0 (Educational/Research Use)'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def download_with_retry(url, max_retries=3, timeout=10):
        """Download content with retry logic"""
        headers = {
            'User-Agent': 'MeshtasticUI/1.0 (Educational/Research Use)'
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}, attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Download failed for {url}, attempt {attempt + 1}: {e}")
                
            if attempt < max_retries - 1:
                # Wait before retry (exponential backoff)
                import time
                time.sleep(2 ** attempt)
                
        return None 