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
        print(f"[OK] PyInstaller rilevato (v{PyInstaller.__version__})")
    except ImportError:
        print("Installazione di PyInstaller in corso...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"])

def build():
    print_banner(f"Avvio compilazione {APP_NAME} per {platform.system()} ({platform.machine()})")
    ensure_pyinstaller()

    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build"

    # Opzioni di base di PyInstaller con ottimizzazioni e compressione
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",              # Nessuna finestra console DOS
        "--clean",
        "--noconfirm",
        "--noupx",                 # Disabilitato di default per evitare problemi di corruzione binaria su alcune piattaforme, ma escludiamo moduli pesanti
    ]

    # Moduli pesanti o non necessari da escludere per ridurre le dimensioni
    excluded_modules = [
        "tkinter",
        "unittest",
        "pydoc",
        "xmlrpc",
        "email",
        "http",
        "sqlite3",
        "PyQt6.QtSql",
        "PyQt6.QtTest",
        "PyQt6.QtPdf",
        "PyQt6.QtDesigner",
        "PyQt6.QtHelp",
        "PyQt6.QtNfc",
        "PyQt6.QtSensors",
        "PyQt6.QtSerialPort",
        "PyQt6.QtSvgWidgets",
        "PyQt6.QtTextToSpeech",
        "PyQt6.QtXml",
    ]

    for mod in excluded_modules:
        cmd.extend(["--exclude-module", mod])

    # Includi assets
    assets_dir = PROJECT_ROOT / "assets"
    if assets_dir.exists():
        sep = ";" if sys.platform == "win32" else ":"
        cmd.extend(["--add-data", f"{assets_dir}{sep}assets"])

    # Icona per Windows e macOS (su Linux PyInstaller non supporta embedding diretto di file .ico)
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

    # Unico file eseguibile (onefile su Windows, Linux e macOS)
    cmd.append("--onefile")

    cmd.append(str(MAIN_SCRIPT))

    print(f"Esecuzione comando:\n{' '.join(map(str, cmd))}\n")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print_banner("[ERROR] Errore durante la compilazione!")
        sys.exit(result.returncode)

    print_banner(f"[OK] Compilazione completata con successo!")
    print(f"Gli eseguibili sono disponibili nella cartella: {dist_dir}")

    # Se siamo su Linux, creiamo un tar.gz con lo script di installazione
    if sys.platform.startswith("linux"):
        print_banner("Creazione archivio .tar.gz per Linux con script di installazione...")
        tar_name = dist_dir / "CignoLauncher-Linux-x86_64.tar.gz"
        import tarfile
        with tarfile.open(tar_name, "w:gz") as tar:
            binary_path = dist_dir / APP_NAME
            if binary_path.exists():
                tar.add(binary_path, arcname=APP_NAME)
            install_script = PROJECT_ROOT / "install.sh"
            if install_script.exists():
                tar.add(install_script, arcname="install.sh")
            assets_path = PROJECT_ROOT / "assets"
            if assets_path.exists():
                tar.add(assets_path, arcname="assets")
        print(f"[OK] Archivio Linux creato: {tar_name}")

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
