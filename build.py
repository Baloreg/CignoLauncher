#!/usr/bin/env python3
"""
Script di Build Multi-Piattaforma per CignoLauncher.
Supporta: Windows (.exe), Linux (ELF standalone), macOS (.app / zip).
Uso: python3 build.py [--onefile]
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

APP_NAME = "CignoLauncher"
PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
ICON_PATH = PROJECT_ROOT / "assets" / "window_icon.ico"

def print_banner(msg):
    print("=" * 60)
    print(f" {msg}")
    print("=" * 60)

def ensure_pyinstaller():
    try:
        import PyInstaller
        print(f"✓ PyInstaller rilevato (v{PyInstaller.__version__})")
    except ImportError:
        print("Installazione di PyInstaller in corso...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"])

def build():
    print_banner(f"Avvio compilazione {APP_NAME} per {platform.system()} ({platform.machine()})")
    ensure_pyinstaller()

    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build"

    # Opzioni di base di PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",              # Nessuna finestra console DOS
        "--clean",
        "--noconfirm",
    ]

    # Includi assets
    assets_dir = PROJECT_ROOT / "assets"
    if assets_dir.exists():
        sep = ";" if sys.platform == "win32" else ":"
        cmd.extend(["--add-data", f"{assets_dir}{sep}assets"])

    # Icona specifica piattaforma
    if sys.platform == "win32" and ICON_PATH.exists():
        cmd.extend(["--icon", str(ICON_PATH)])
    elif sys.platform == "darwin":
        icns_path = assets_dir / "window_icon.icns"
        if icns_path.exists():
            cmd.extend(["--icon", str(icns_path)])
        elif ICON_PATH.exists():
            cmd.extend(["--icon", str(ICON_PATH)])

    # Hidden imports critici per PyQt6 e minecraft-launcher-lib
    hidden_imports = [
        "minecraft_launcher_lib",
        "minecraft_launcher_lib.utils",
        "minecraft_launcher_lib.install",
        "minecraft_launcher_lib.command",
        "minecraft_launcher_lib.microsoft_account",
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "requests",
        "PIL",
        "PIL.Image",
        "json",
        "uuid",
        "hashlib",
        "account_manager",
        "instance_manager",
        "instance_dialog",
        "login_dialog_pyqt",
        "utils"
    ]

    for mod in hidden_imports:
        cmd.extend(["--hidden-import", mod])

    # Unico file eseguibile (onedir per default su macOS app, onefile su Windows/Linux se richiesto)
    if "--onefile" in sys.argv or sys.platform == "win32":
        cmd.append("--onefile")

    cmd.append(str(MAIN_SCRIPT))

    print(f"Esecuzione comando:\n{' '.join(map(str, cmd))}\n")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print_banner("❌ Errore durante la compilazione!")
        sys.exit(result.returncode)

    print_banner(f"✓ Compilazione completata con successo!")
    print(f"Gli eseguibili sono disponibili nella cartella: {dist_dir}")

    # Lista file generati
    if dist_dir.exists():
        for file_path in sorted(dist_dir.iterdir()):
            size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.is_file() else 0
            if size_mb > 0:
                print(f" - {file_path.name} ({size_mb:.2f} MB)")
            else:
                print(f" - {file_path.name}/ (directory)")

if __name__ == "__main__":
    build()
