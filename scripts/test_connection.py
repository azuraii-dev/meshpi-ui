#!/usr/bin/env python3
"""
Test script to validate Meshtastic connection detection
"""

import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import meshtastic
    import meshtastic.serial_interface
    import meshtastic.util
    MESHTASTIC_AVAILABLE = True
except ImportError as e:
    logger.error(f"Meshtastic library not available: {e}")
    MESHTASTIC_AVAILABLE = False
    sys.exit(1)

def test_serial_connection():
    """Test serial connection detection"""
    print("Testing serial connection...")
    
    # Check for available ports
    print("Looking for available serial ports...")
    ports = meshtastic.util.findPorts(True)
    print(f"Found ports: {ports}")
    
    if not ports:
        print("❌ No Meshtastic devices found on serial ports")
        return False
    
    try:
        print("Attempting to create SerialInterface...")
        interface = meshtastic.serial_interface.SerialInterface()
        
        # Validate the interface
        print("Validating interface...")
        
        # Check if the interface has a proper stream
        if not hasattr(interface, 'stream') or interface.stream is None:
            print("❌ Interface doesn't have a valid stream")
            return False
            
        # Check if it has localNode
        if not hasattr(interface, 'localNode'):
            print("❌ Interface doesn't have localNode attribute")
            return False
            
        print("✅ Interface created successfully")
        
        # Clean up
        if hasattr(interface, 'close'):
            interface.close()
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to create interface: {e}")
        return False

def test_without_device():
    """Test behavior when no device is connected"""
    print("\nTesting behavior without device...")
    
    # Simulate what happens when no device is found
    try:
        # This should fail gracefully
        interface = meshtastic.serial_interface.SerialInterface(devPath="/dev/nonexistent")
        print("❌ Should have failed but didn't")
        return False
    except Exception as e:
        print(f"✅ Correctly failed with: {e}")
        return True

def main():
    """Main test function"""
    print("Meshtastic Connection Validation Test")
    print("=" * 40)
    
    if not MESHTASTIC_AVAILABLE:
        print("❌ Meshtastic library not available")
        return
        
    # Test serial connection
    serial_ok = test_serial_connection()
    
    # Test without device
    no_device_ok = test_without_device()
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Serial connection test: {'✅ PASS' if serial_ok else '❌ FAIL'}")
    print(f"No device test: {'✅ PASS' if no_device_ok else '❌ FAIL'}")
    
    if not serial_ok:
        print("\nNote: Serial connection test failure is expected if no Meshtastic device is connected")

if __name__ == "__main__":
    main() 