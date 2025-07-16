#!/usr/bin/env python3
"""
Icon Generator for Meshtastic UI
Generates all required icon formats from a single source image
"""

import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        from PIL import Image
        print("✓ PIL/Pillow available")
        return True
    except ImportError:
        print("❌ PIL/Pillow not found. Installing...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            from PIL import Image
            print("✓ PIL/Pillow installed successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to install PIL/Pillow: {e}")
            print("Please install manually: pip install Pillow")
            return False

def generate_ico(source_image, output_path):
    """Generate Windows ICO file with multiple sizes"""
    try:
        from PIL import Image
        
        # ICO sizes (Windows standard)
        sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # Open source image
        img = Image.open(source_image)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create list of resized images
        images = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            images.append(resized)
        
        # Save as ICO
        images[0].save(output_path, format='ICO', sizes=[(img.width, img.height) for img in images])
        print(f"✓ Generated Windows ICO: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate ICO: {e}")
        return False

def generate_icns(source_image, output_path):
    """Generate macOS ICNS file"""
    try:
        from PIL import Image
        import tempfile
        import subprocess
        
        # Check if iconutil is available (macOS only)
        try:
            subprocess.run(['iconutil', '--version'], capture_output=True, check=True)
            iconutil_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            iconutil_available = False
        
        if iconutil_available:
            # Use iconutil for proper ICNS generation (macOS only)
            with tempfile.TemporaryDirectory() as temp_dir:
                iconset_dir = os.path.join(temp_dir, 'icon.iconset')
                os.makedirs(iconset_dir)
                
                # Open source image
                img = Image.open(source_image)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # ICNS required sizes
                icns_sizes = [
                    (16, 'icon_16x16.png'),
                    (32, 'icon_16x16@2x.png'),
                    (32, 'icon_32x32.png'), 
                    (64, 'icon_32x32@2x.png'),
                    (128, 'icon_128x128.png'),
                    (256, 'icon_128x128@2x.png'),
                    (256, 'icon_256x256.png'),
                    (512, 'icon_256x256@2x.png'),
                    (512, 'icon_512x512.png'),
                    (1024, 'icon_512x512@2x.png'),
                ]
                
                # Generate all sizes
                for size, filename in icns_sizes:
                    resized = img.resize((size, size), Image.Resampling.LANCZOS)
                    resized.save(os.path.join(iconset_dir, filename), 'PNG')
                
                # Convert to ICNS
                subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', output_path], check=True)
                print(f"✓ Generated macOS ICNS: {output_path}")
                return True
        else:
            # Fallback: Create a simple PNG as ICNS (not ideal but works)
            img = Image.open(source_image)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Use largest size for macOS
            img_1024 = img.resize((1024, 1024), Image.Resampling.LANCZOS)
            
            # Save as PNG with .icns extension (will work in most cases)
            icns_path = output_path.replace('.icns', '.png')
            img_1024.save(icns_path, 'PNG')
            
            # Rename to .icns
            os.rename(icns_path, output_path)
            print(f"✓ Generated macOS ICNS (PNG format): {output_path}")
            print("  Note: For best results on macOS, use iconutil on a Mac")
            return True
            
    except Exception as e:
        print(f"❌ Failed to generate ICNS: {e}")
        return False

def generate_png(source_image, output_path, size=512):
    """Generate PNG icon for Linux"""
    try:
        from PIL import Image
        
        # Check if source and output are the same file
        if os.path.abspath(source_image) == os.path.abspath(output_path):
            print(f"✓ Generated Linux PNG: {output_path} (source file already correct size)")
            return True
        
        # Open source image
        img = Image.open(source_image)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Check if already the right size
        if img.size == (size, size):
            # Just copy with correct format
            img.save(output_path, 'PNG')
            print(f"✓ Generated Linux PNG: {output_path}")
            return True
        
        # Resize to specified size
        img_resized = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save as PNG
        img_resized.save(output_path, 'PNG')
        print(f"✓ Generated Linux PNG: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate PNG: {e}")
        return False

def main():
    """Main function"""
    print("🎨 Meshtastic UI Icon Generator")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Get source image path
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
    else:
        source_path = input("Enter path to source image (PNG recommended, 1024x1024 or larger): ").strip()
    
    # Convert to absolute path to avoid issues
    source_path = os.path.abspath(source_path)
    
    # Validate source image
    if not os.path.exists(source_path):
        print(f"❌ Source image not found: {source_path}")
        sys.exit(1)
    
    try:
        from PIL import Image
        img = Image.open(source_path)
        print(f"✓ Source image: {source_path}")
        print(f"  Size: {img.size}")
        print(f"  Mode: {img.mode}")
        
        # Recommend RGBA mode
        if img.mode != 'RGBA':
            print("  💡 Tip: RGBA mode recommended for transparency support")
            
        # Recommend square aspect ratio
        if img.size[0] != img.size[1]:
            print("  ⚠️  Warning: Non-square image detected. Icons work best with square images.")
            
    except Exception as e:
        print(f"❌ Invalid image file: {e}")
        sys.exit(1)
    
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    
    print(f"\n📁 Output directory: {project_root}")
    print("\nGenerating icons...")
    
    success_count = 0
    
    # Generate Windows ICO
    ico_path = project_root / "icon.ico"
    if generate_ico(source_path, str(ico_path)):
        success_count += 1
    
    # Generate macOS ICNS
    icns_path = project_root / "icon.icns"
    if generate_icns(source_path, str(icns_path)):
        success_count += 1
    
    # Generate Linux PNG
    png_path = project_root / "icon.png"
    
    # Check if output path is the same as source (avoid overwriting source)
    if os.path.abspath(str(png_path)) == source_path:
        print(f"✓ Linux PNG already exists (source file): {png_path}")
        success_count += 1
    else:
        if generate_png(source_path, str(png_path)):
            success_count += 1
    
    print(f"\n🎉 Generated {success_count}/3 icon formats successfully!")
    
    if success_count == 3:
        print("\n✅ All icons generated! You can now build your executable:")
        print("  python setup.py build")
        print("\n📝 Files created:")
        print(f"  • {ico_path} (Windows)")
        print(f"  • {icns_path} (macOS)")
        print(f"  • {png_path} (Linux)")
        
        print("\n🧪 Test the window icon:")
        print("  python main.py")
    else:
        print("\n⚠️  Some icons failed to generate. Check the errors above.")

if __name__ == "__main__":
    main() 