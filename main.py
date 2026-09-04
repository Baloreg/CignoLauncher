#!/usr/bin/env python3
"""
CignoLauncher - Main Entry Point
Un launcher Minecraft semplice, moderno e leggero basato su PyQt6 e minecraft-launcher-lib.
"""

import sys
from PyQt6.QtWidgets import QApplication
from cignolauncher_pyqt import MinecraftLauncher

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CignoLauncher")
    app.setOrganizationName("Baloreg")
    
    launcher = MinecraftLauncher()
    if not launcher.onboarding_pending:
        launcher.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
