# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None

# -----------------------------------------------------------------------------
# 1. Collect Runtime Metadata & Data Files
# -----------------------------------------------------------------------------
# Collect metadata for streamlit so it can find its version/config
datas = []
datas += copy_metadata("streamlit")
datas += copy_metadata("behave")

# Collect internal streamlit static files (frontend)
# usage: collect_data_files(package_name, subdir=None, include_py_files=False)
datas += collect_data_files("streamlit")
datas += collect_data_files("behave")
datas += collect_data_files("altair")

# Add our project specific files
# (Source Path, Destination Path relative to bundle root)
datas += [
    ("app.py", "."),
    ("static", "static"),
    ("execution_manager.py", "."),
    ("pwa_injector.py", "."),
    # Include other helpers if needed
    ("verify_lt_regex.py", "."),
    # If you have configs or templates, add them here:
    # ("configs", "configs"), 
    # ("endpoints.json", "."),
]

# -----------------------------------------------------------------------------
# 2. Analysis
# -----------------------------------------------------------------------------
a = Analysis(
    ['run_desktop.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Core
        "streamlit",
        "streamlit.web.cli",
        "pandas",
        "behave",
        "json",
        "glob",
        "shutil",
        "re",
        "subprocess",
        "importlib.metadata",
        
        # Project modules
        "execution_manager",
        "pwa_injector",
        
        # Missing Streamlit internals
        "streamlit.runtime.scriptrunner.magic_funcs",
        "streamlit.runtime.scriptrunner.script_runner",
        
        # Unused but often needed by Streamlit deps
        "pydeck",
        "altair",
        "watchdog",
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

# -----------------------------------------------------------------------------
# 3. EXE (One File or One Dir)
# -----------------------------------------------------------------------------
# Create a folder-based distribution (onedir) which is usually faster to startup
# and easier to debug than onefile.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='behave_runner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Set to False if you want to hide terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None, # Add path to .ico if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='behave_runner',
)

# Mac OS X .app Bundle
import sys
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='BehaveRunner.app',
        icon=None,
        bundle_identifier=None,
    )
