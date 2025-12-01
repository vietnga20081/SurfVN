# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Thu thập file cần cho PyQt6
pyqt6_datas = collect_data_files("PyQt6")
pyqt6_hidden = collect_submodules("PyQt6")

# Selenium + Webdriver Manager động import
selenium_hidden = collect_submodules("selenium")
webdriver_hidden = collect_submodules("webdriver_manager")

# Thư viện requests, certifi
requests_hidden = collect_submodules("requests")
certifi_datas = collect_data_files("certifi")

# Gom tất cả hidden imports
hidden_imports = pyqt6_hidden + selenium_hidden + webdriver_hidden + requests_hidden

# Gom tất cả data
datas = pyqt6_datas + certifi_datas


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
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
    a.binaries,
    a.datas,
    [],
    name='SurfVN',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # đổi True nếu muốn debug popup console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,        # macOS signing optional
    entitlements_file=None,
    icon='app_icon.ico',
)
