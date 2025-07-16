# -*- mode: python ; coding: utf-8 -*-
import sys
import os

# Windows-specific PyInstaller spec with enhanced icon handling

block_cipher = None

# Use absolute paths for Windows
icon_path = os.path.abspath('icon.ico')
print(f"Using icon: {icon_path}")

# Verify icon exists
if not os.path.exists(icon_path):
    print("ERROR: Icon file not found!")
    icon_path = None
else:
    icon_size = os.path.getsize(icon_path)
    print(f"Icon size: {icon_size} bytes")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('database', 'database'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'requests',
        'sqlite3',
        'threading',
        'queue',
        'json',
        'datetime',
        'logging',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MeshtasticUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,  # Use absolute path
    version='version_info.txt',  # Include version info
) 