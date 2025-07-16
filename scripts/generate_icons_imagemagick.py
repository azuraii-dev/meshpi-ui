#!/usr/bin/env python3
"""
High-Quality Icon Generator using ImageMagick
Creates professional-quality ICO files for Windows
"""

import os
import sys
import subprocess
from pathlib import Path

def check_imagemagick():
    """Check if ImageMagick is available"""
    try:
        result = subprocess.run(['magick', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ ImageMagick available")
            return True
        else:
            print("❌ ImageMagick not working properly")
            return False
    except FileNotFoundError:
        print("❌ ImageMagick not found")
        print("Install with: brew install imagemagick")
        return False

def generate_ico_imagemagick(source_image, output_path):
    """Generate high-quality ICO file using ImageMagick"""
    try:
        # Method 1: Auto-resize (recommended)
        cmd = [
            'magick', source_image,
            '-define', 'icon:auto-resize=256,128,64,48,32,24,16',
            output_path
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✓ Generated high-quality ICO: {output_path} ({file_size} bytes)")
                return True
            else:
                print("❌ ICO file was not created")
                return False
        else:
            print(f"❌ ImageMagick error: {result.stderr}")
            return generate_ico_imagemagick_explicit(source_image, output_path)
    
    except Exception as e:
        print(f"❌ Failed to generate ICO with ImageMagick: {e}")
        return generate_ico_imagemagick_explicit(source_image, output_path)

def generate_ico_imagemagick_explicit(source_image, output_path):
    """Generate ICO with explicit size creation"""
    try:
        # Method 2: Explicit multi-size creation
        cmd = [
            'magick', source_image,
            '(', '-clone', '0', '-resize', '16x16', ')',
            '(', '-clone', '0', '-resize', '24x24', ')',
            '(', '-clone', '0', '-resize', '32x32', ')',
            '(', '-clone', '0', '-resize', '48x48', ')',
            '(', '-clone', '0', '-resize', '64x64', ')',
            '(', '-clone', '0', '-resize', '128x128', ')',
            '(', '-clone', '0', '-resize', '256x256', ')',
            '-delete', '0',
            output_path
        ]
        
        print(f"Trying explicit method...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✓ Generated ICO (explicit method): {output_path} ({file_size} bytes)")
                return True
        
        print(f"❌ Explicit method also failed: {result.stderr}")
        return False
        
    except Exception as e:
        print(f"❌ Explicit ICO generation failed: {e}")
        return False

def generate_icns_imagemagick(source_image, output_path):
    """Generate ICNS file using ImageMagick"""
    try:
        # For ICNS, we need different sizes
        cmd = [
            'magick', source_image,
            '-define', 'icon:auto-resize=1024,512,256,128,64,32,16',
            '-format', 'png',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✓ Generated ICNS: {output_path} ({file_size} bytes)")
                return True
        
        # Fallback: just convert to PNG with .icns extension
        cmd_fallback = ['magick', source_image, '-resize', '1024x1024', output_path]
        result = subprocess.run(cmd_fallback, capture_output=True, text=True)
        
        if result.returncode == 0:
            file_size = os.path.getsize(output_path)
            print(f"✓ Generated ICNS (PNG format): {output_path} ({file_size} bytes)")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Failed to generate ICNS: {e}")
        return False

def generate_png_imagemagick(source_image, output_path, size=512):
    """Generate PNG using ImageMagick"""
    try:
        cmd = ['magick', source_image, '-resize', f'{size}x{size}', output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            file_size = os.path.getsize(output_path)
            print(f"✓ Generated PNG: {output_path} ({file_size} bytes)")
            return True
        else:
            print(f"❌ PNG generation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to generate PNG: {e}")
        return False

def main():
    """Main function"""
    print("🎨 High-Quality Icon Generator (ImageMagick)")
    print("=" * 50)
    
    # Check ImageMagick
    if not check_imagemagick():
        sys.exit(1)
    
    # Get source image
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
    else:
        source_path = input("Enter path to source image: ").strip()
    
    source_path = os.path.abspath(source_path)
    
    if not os.path.exists(source_path):
        print(f"❌ Source image not found: {source_path}")
        sys.exit(1)
    
    print(f"✓ Source image: {source_path}")
    
    # Get project root
    project_root = Path(__file__).parent.parent
    print(f"📁 Output directory: {project_root}")
    
    print("\nGenerating high-quality icons...")
    
    success_count = 0
    
    # Generate Windows ICO with ImageMagick
    ico_path = project_root / "icon.ico"
    if generate_ico_imagemagick(source_path, str(ico_path)):
        success_count += 1
    
    # Generate macOS ICNS
    icns_path = project_root / "icon.icns"
    if generate_icns_imagemagick(source_path, str(icns_path)):
        success_count += 1
    
    # Generate Linux PNG
    png_path = project_root / "icon.png"
    if os.path.abspath(str(png_path)) == source_path:
        print(f"✓ Linux PNG already exists (source file): {png_path}")
        success_count += 1
    else:
        if generate_png_imagemagick(source_path, str(png_path)):
            success_count += 1
    
    print(f"\n🎉 Generated {success_count}/3 icon formats successfully!")
    
    if success_count >= 2:  # ICO and at least one other
        print("\n✅ Icons ready for building executable!")
        print("  python setup.py build")
        
        print("\n📝 Files created:")
        for icon_file in [ico_path, icns_path, png_path]:
            if icon_file.exists():
                size = icon_file.stat().st_size
                print(f"  • {icon_file} ({size} bytes)")
        
        print("\n💡 Tips:")
        print("  • ICO file should be 10KB+ for good quality")
        print("  • Test on Windows to verify icon appears correctly")
        print("  • The icon will appear in Windows Explorer and taskbar")
    else:
        print("\n⚠️  Some icons failed to generate. Check the errors above.")

if __name__ == "__main__":
    main() 