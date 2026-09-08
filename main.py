#!/usr/bin/env python3
"""
CignoLauncher - Main Entry Point
Un launcher Minecraft semplice, moderno e leggero basato su PyQt6 e minecraft-launcher-lib.
"""

import sys
import os

# Sopprime gli avvisi di moduli GTK mancanti su distribuzioni Linux
os.environ["NO_AT_BRIDGE"] = "1"
if "GTK_MODULES" in os.environ:
    del os.environ["GTK_MODULES"]

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ModernSplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(360, 220)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Container widget with dark background and rounded corners
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: #18181b;
                border: 1px solid #27272a;
                border-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setSpacing(10)
        
        # Logo
        self.logo_label = QLabel()
        logo_path = resource_path("assets/window_icon.ico")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.logo_label)
        
        # Title
        title_label = QLabel("CignoLauncher")
        title_label.setStyleSheet("color: #f43f5e; font-size: 18px; font-weight: bold; background: transparent; border: none;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title_label)
        
        # Status / Loading text
        self.status_label = QLabel("Avvio in corso...")
        self.status_label.setStyleSheet("color: #a1a1aa; font-size: 13px; background: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.status_label)
        
        main_layout.addWidget(self.container)
        self.setLayout(main_layout)
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def set_status(self, text):
        self.status_label.setText(text)
        QApplication.processEvents()

from cignolauncher_pyqt import MinecraftLauncher

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CignoLauncher")
    app.setOrganizationName("Baloreg")
    
    splash = ModernSplashScreen()
    splash.show()
    app.processEvents()
    
    splash.set_status("Caricamento configurazioni...")
    app.processEvents()
    
    launcher = MinecraftLauncher()
    
    splash.set_status("Preparazione interfaccia...")
    app.processEvents()
    
    if not launcher.onboarding_pending:
        launcher.show()
        
    splash.close()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
