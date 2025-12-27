# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Login Monitor PRO
Build command: pyinstaller login_monitor.spec --clean
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# Project paths
PROJECT_DIR = '/Users/cyvigilant/tool/login-monitor'

# ============================================================================
# HIDDEN IMPORTS - Critical for PyObjC and other dynamic imports
# ============================================================================

hidden_imports = [
    # PyObjC Framework imports (macOS specific)
    'objc',
    'objc._objc',
    'Quartz',
    'Quartz.CoreGraphics',
    'Quartz.QuartzCore',
    'CoreLocation',
    'Foundation',
    'AppKit',
    'Cocoa',

    # OpenCV hidden imports
    'cv2',
    'numpy',
    'numpy.core._methods',
    'numpy.lib.format',

    # Face recognition (optional - may not be installed)
    'dlib',
    'face_recognition',
    'face_recognition.api',

    # Audio
    'pyaudio',
    'wave',

    # Cryptography
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'cryptography.hazmat.backends.openssl',

    # Flask and web
    'flask',
    'flask.json',
    'jinja2',
    'werkzeug',
    'markupsafe',

    # Telegram
    'telegram',
    'telegram.ext',
    'httpx',
    'anyio',

    # Google APIs (optional)
    'google.auth',
    'google.oauth2',
    'google_auth_oauthlib',
    'googleapiclient',
    'googleapiclient.discovery',

    # pynput
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',

    # Standard library often missed
    'sqlite3',
    'email.mime.multipart',
    'email.mime.text',
    'email.mime.image',
    'email.mime.audio',
    'urllib.request',
    'urllib.error',
    'json',
    'uuid',
    'hashlib',
    'base64',
    'smtplib',
    'threading',
    'collections',
    'typing',
    're',
    'socket',
    'platform',

    # Local modules
    'pro_monitor',
    'activity_monitor',
    'telegram_bot',
    'screen_watcher',
]

# Try to collect PyObjC submodules
try:
    hidden_imports += collect_submodules('objc')
except Exception:
    pass

try:
    hidden_imports += collect_submodules('Quartz')
except Exception:
    pass

try:
    hidden_imports += collect_submodules('CoreLocation')
except Exception:
    pass

try:
    hidden_imports += collect_submodules('Foundation')
except Exception:
    pass

# ============================================================================
# DATA FILES
# ============================================================================

datas = []

# Try to collect face_recognition models if available
try:
    import face_recognition_models
    models_path = os.path.dirname(face_recognition_models.__file__)
    datas.append((models_path, 'face_recognition_models'))
except ImportError:
    pass

# ============================================================================
# BINARIES - Native libraries
# ============================================================================

binaries = []

# Collect OpenCV binaries
try:
    binaries += collect_dynamic_libs('cv2')
except Exception:
    pass

# ============================================================================
# ANALYSIS - Define each entry point
# ============================================================================

# Screen Watcher (main monitoring daemon)
screen_watcher_a = Analysis(
    [os.path.join(PROJECT_DIR, 'screen_watcher.py')],
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PIL.ImageTk',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Pro Monitor (triggered by screen_watcher)
pro_monitor_a = Analysis(
    [os.path.join(PROJECT_DIR, 'pro_monitor.py')],
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Command Listener (replaces Telegram Bot - polls Supabase for commands)
command_listener_a = Analysis(
    [os.path.join(PROJECT_DIR, 'command_listener.py')],
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports + ['supabase_client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Setup Tool (GUI)
setup_a = Analysis(
    [os.path.join(PROJECT_DIR, 'setup_gui.py')],
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Launcher (main entry point - auto-setup and start services)
launcher_a = Analysis(
    [os.path.join(PROJECT_DIR, 'launcher.py')],
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ============================================================================
# MERGE - Combine analyses to share common modules
# ============================================================================

MERGE(
    (screen_watcher_a, 'screen_watcher', 'screen_watcher'),
    (pro_monitor_a, 'pro_monitor', 'pro_monitor'),
    (command_listener_a, 'command_listener', 'command_listener'),
    (setup_a, 'setup', 'setup'),
    (launcher_a, 'launcher', 'launcher'),
)

# ============================================================================
# PYZ - Create bytecode archives
# ============================================================================

screen_watcher_pyz = PYZ(
    screen_watcher_a.pure,
    screen_watcher_a.zipped_data,
    cipher=block_cipher
)

pro_monitor_pyz = PYZ(
    pro_monitor_a.pure,
    pro_monitor_a.zipped_data,
    cipher=block_cipher
)

command_listener_pyz = PYZ(
    command_listener_a.pure,
    command_listener_a.zipped_data,
    cipher=block_cipher
)

setup_pyz = PYZ(
    setup_a.pure,
    setup_a.zipped_data,
    cipher=block_cipher
)

launcher_pyz = PYZ(
    launcher_a.pure,
    launcher_a.zipped_data,
    cipher=block_cipher
)

# ============================================================================
# EXE - Create executables
# ============================================================================

screen_watcher_exe = EXE(
    screen_watcher_pyz,
    screen_watcher_a.scripts,
    [],
    exclude_binaries=True,
    name='screen_watcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

pro_monitor_exe = EXE(
    pro_monitor_pyz,
    pro_monitor_a.scripts,
    [],
    exclude_binaries=True,
    name='pro_monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

command_listener_exe = EXE(
    command_listener_pyz,
    command_listener_a.scripts,
    [],
    exclude_binaries=True,
    name='command_listener',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

setup_exe = EXE(
    setup_pyz,
    setup_a.scripts,
    [],
    exclude_binaries=True,
    name='Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI mode - no console needed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

launcher_exe = EXE(
    launcher_pyz,
    launcher_a.scripts,
    [],
    exclude_binaries=True,
    name='LoginMonitorPRO',  # Main app name - runs when double-clicked
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI mode - no console needed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ============================================================================
# COLLECT - Gather all files
# ============================================================================

coll = COLLECT(
    screen_watcher_exe,
    screen_watcher_a.binaries,
    screen_watcher_a.zipfiles,
    screen_watcher_a.datas,
    pro_monitor_exe,
    pro_monitor_a.binaries,
    pro_monitor_a.zipfiles,
    pro_monitor_a.datas,
    command_listener_exe,
    command_listener_a.binaries,
    command_listener_a.zipfiles,
    command_listener_a.datas,
    setup_exe,
    setup_a.binaries,
    setup_a.zipfiles,
    setup_a.datas,
    launcher_exe,
    launcher_a.binaries,
    launcher_a.zipfiles,
    launcher_a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LoginMonitorPRO',
)

# ============================================================================
# BUNDLE - Create macOS .app bundle
# ============================================================================

app = BUNDLE(
    coll,
    name='LoginMonitorPRO.app',
    icon=None,
    bundle_identifier='com.loginmonitor.pro',
    info_plist={
        'CFBundleName': 'LoginMonitorPRO',
        'CFBundleDisplayName': 'Login Monitor PRO',
        'CFBundleExecutable': 'LoginMonitorPRO',  # Launcher is main entry point
        'CFBundleIdentifier': 'com.loginmonitor.pro',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.15',
        'LSUIElement': False,  # Show in Dock during setup, then hide
        'NSHighResolutionCapable': True,
        'NSCameraUsageDescription': 'Login Monitor needs camera access to capture photos on login events.',
        'NSLocationWhenInUseUsageDescription': 'Login Monitor needs location access for anti-theft tracking.',
        'NSLocationAlwaysAndWhenInUseUsageDescription': 'Login Monitor needs location access for anti-theft tracking.',
        'NSMicrophoneUsageDescription': 'Login Monitor needs microphone access to record audio.',
        'NSAppleEventsUsageDescription': 'Login Monitor needs to control system events.',
    },
)
