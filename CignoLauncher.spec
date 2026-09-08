# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/home/baloreg/CignoLauncher-main/main.py'],
    pathex=[],
    binaries=[],
    datas=[('/home/baloreg/CignoLauncher-main/assets', 'assets')],
    hiddenimports=['azure_config', 'minecraft_launcher_lib', 'minecraft_launcher_lib.utils', 'minecraft_launcher_lib.install', 'minecraft_launcher_lib.command', 'minecraft_launcher_lib.microsoft_account', 'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'requests', 'PIL', 'PIL.Image', 'json', 'uuid', 'hashlib', 'account_manager', 'instance_manager', 'instance_dialog', 'login_dialog_pyqt', 'utils'],
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
    name='CignoLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
