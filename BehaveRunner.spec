# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

# Define datas: (Source, Dest)
datas = [
    ('app.py', '.'), 
    ('execution_manager.py', '.'), 
    ('requirements.txt', '.'), 
    ('packages.txt', '.'),
    ('pwa_injector.py', '.'),
    ('static/manifest.json', 'static') # Ensure static/manifest.json exists in source
]

# Copy metadata for dependencies
datas += copy_metadata('streamlit')
datas += collect_data_files('streamlit') # <--- REQUIRED for static assets
datas += copy_metadata('tqdm')
datas += copy_metadata('regex')
datas += copy_metadata('requests')
datas += copy_metadata('packaging')
datas += copy_metadata('filelock')
datas += copy_metadata('numpy')
datas += copy_metadata('tokenizers')


a = Analysis(
    ['run_desktop.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['streamlit', 'streamlit.web.cli', 'streamlit.runtime.scriptrunner.magic_funcs', 'tkinter', 'tkinter.filedialog'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BehaveRunner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Set to False if you want to hide the console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BehaveRunner',
)
