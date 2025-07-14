#!/usr/bin/env python3
"""
Test script to verify IP geolocation functionality
"""

import requests
import json

def test_ip_geolocation():
    """Test IP geolocation services"""
    print("Testing IP geolocation services...")
    
    services = [
        {
            'name': 'ipapi.co',
            'url': 'https://ipapi.co/json/',
            'lat_key': 'latitude',
            'lon_key': 'longitude',
            'location_key': 'city'
        },
        {
            'name': 'ip-api.com',
            'url': 'http://ip-api.com/json/',
            'lat_key': 'lat',
            'lon_key': 'lon',
            'location_key': 'city'
        },
        {
            'name': 'ipinfo.io',
            'url': 'https://ipinfo.io/json',
            'lat_key': 'loc',  # Special handling needed
            'lon_key': 'loc',  # Special handling needed
            'location_key': 'city'
        }
    ]
    
    for service in services:
        try:
            print(f"\nTesting {service['name']}...")
            headers = {
                'User-Agent': 'MeshtasticUI/1.0 (Educational/Research Use)'
            }
            response = requests.get(service['url'], headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Raw response: {json.dumps(data, indent=2)}")
                
                # Special handling for ipinfo.io
                if service['name'] == 'ipinfo.io':
                    if 'loc' in data:
                        lat_str, lon_str = data['loc'].split(',')
                        lat, lon = float(lat_str), float(lon_str)
                        print(f"✅ {service['name']}: {lat}, {lon}")
                    else:
                        print(f"❌ {service['name']}: No location data")
                        continue
                else:
                    # Standard handling for other services
                    if service['lat_key'] in data and service['lon_key'] in data:
                        lat = float(data[service['lat_key']])
                        lon = float(data[service['lon_key']])
                        print(f"✅ {service['name']}: {lat}, {lon}")
                    else:
                        print(f"❌ {service['name']}: Missing location keys")
                        continue
                
                # Get location name
                location_name = data.get(service['location_key'], 'Unknown')
                print(f"   Location: {location_name}")
                
                # Validate coordinates
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    print(f"   ✅ Valid coordinates")
                else:
                    print(f"   ❌ Invalid coordinates: {lat}, {lon}")
                    
            else:
                print(f"❌ {service['name']}: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {service['name']}: Network error - {e}")
        except (ValueError, KeyError) as e:
            print(f"❌ {service['name']}: Parse error - {e}")
        except Exception as e:
            print(f"❌ {service['name']}: Unexpected error - {e}")

if __name__ == "__main__":
    test_ip_geolocation() 