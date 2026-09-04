import sys
import os
import json
import subprocess
import threading
from pathlib import Path
from datetime import datetime

import requests
import minecraft_launcher_lib

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QStackedWidget, QPlainTextEdit,
    QSpinBox, QFrame, QGroupBox, QMessageBox, QSpacerItem, QSizePolicy,
    QComboBox, QCheckBox, QLineEdit, QFileDialog, QSlider, QTabWidget,
    QButtonGroup
)
from PyQt6.QtGui import QIcon, QFont, QTextCursor, QPixmap, QColor
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt, pyqtSlot, QEvent, QSize

from account_manager import AccountManager
from login_dialog_pyqt import LoginDialog, CustomMessageBox
from utils import ImageDownloader, create_steve_avatar, create_app_logo_pixmap

# Helper per percorsi asset
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Windows: nascondi finestra console durante Popen
if sys.platform == 'win32':
    _original_Popen = subprocess.Popen
    def _new_Popen(*args, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        return _original_Popen(*args, **kwargs)
    subprocess.Popen = _new_Popen


class Worker(QObject):
    """Worker generico per eseguire task pesanti (download, installazione) in background."""
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str, str)
    log_message = pyqtSignal(str, str)
    versions_loaded = pyqtSignal(list, str)
    
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.log_message.emit(f"Errore nel thread di lavoro: {e}", "ERROR")
            self.status_update.emit(f"Errore: {e}", "ERROR")
        finally:
            self.finished.emit()


class LogEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self, message):
        super().__init__(self.EVENT_TYPE)
        self.message = message


class GameClosedEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self):
        super().__init__(self.EVENT_TYPE)


class MinecraftLauncher(QMainWindow):
    """Launcher Minecraft moderno multi-versione per CignoLauncher."""
    
    def __init__(self):
        super().__init__()
        self.launcher_name = "CignoLauncher"
        self.launcher_version = "2.0.0"
        
        self.setup_paths()
        self.load_settings()
        self.account_manager = AccountManager(self.launcher_directory)
        
        self.game_process = None
        self.worker_thread = None
        self.worker = None
        
        self.all_versions = []
        self.installed_version_ids = set()
        self.selected_version = self.settings.get("last_version", "")
        
        self.AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "your-client-id")
        self.AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "your-secret-value")
        
        self.setupUi()
        self.apply_modern_stylesheet()
        
        # Carica versioni in background
        self.refresh_version_list(initial=True)
        self.update_account_badge()

    def setup_paths(self):
        """Inizializza i percorsi di gioco e configurazione."""
        if sys.platform == "win32":
            appdata = os.getenv('APPDATA')
            self.launcher_directory = os.path.join(appdata, "CignoLauncher")
        else:
            home = os.path.expanduser("~")
            self.launcher_directory = os.path.join(home, ".cignolauncher")
        
        self.minecraft_directory = os.path.join(self.launcher_directory, "minecraft")
        self.heads_folder = os.path.join(self.launcher_directory, "heads")
        self.settings_file = os.path.join(self.launcher_directory, "settings.json")
        self.versions_cache_file = os.path.join(self.launcher_directory, "versions_cache.json")
        
        for folder in [self.launcher_directory, self.minecraft_directory, self.heads_folder]:
            os.makedirs(folder, exist_ok=True)

    def load_settings(self):
        """Carica le impostazioni da settings.json con valori di default."""
        self.settings = {
            "ram_gb": 4,
            "show_snapshots": False,
            "last_version": "",
            "custom_java": "",
            "jvm_args": "",
            "custom_resolution": False,
            "res_width": 1280,
            "res_height": 720
        }
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.settings.update(saved)
            except Exception as e:
                print(f"Errore lettura impostazioni: {e}")

    def save_settings(self):
        """Salva le impostazioni su settings.json."""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Errore salvataggio impostazioni: {e}")

    def setupUi(self):
        self.setWindowTitle(f"{self.launcher_name} v{self.launcher_version} - Vanilla Edition")
        self.setMinimumSize(960, 640)
        self.resize(1000, 660)

        # Icona finestra
        icon_path = resource_path("assets/window_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon(create_steve_avatar(32)))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- SIDEBAR MODERNA ---
        sidebar_widget = QWidget()
        sidebar_widget.setObjectName("sidebar")
        sidebar_widget.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(12, 18, 12, 14)
        sidebar_layout.setSpacing(8)

        # Brand / Logo Sidebar
        brand_container = QWidget()
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(4, 4, 4, 14)
        brand_layout.setSpacing(10)
        
        logo_icon_label = QLabel()
        logo_icon_label.setPixmap(create_steve_avatar(36))
        
        brand_text_layout = QVBoxLayout()
        brand_text_layout.setSpacing(0)
        app_title = QLabel("CignoLauncher")
        app_title.setObjectName("SidebarTitle")
        app_sub = QLabel("Minecraft Vanilla")
        app_sub.setObjectName("SidebarSub")
        brand_text_layout.addWidget(app_title)
        brand_text_layout.addWidget(app_sub)
        
        brand_layout.addWidget(logo_icon_label)
        brand_layout.addLayout(brand_text_layout)
        sidebar_layout.addWidget(brand_container)

        # Pulsanti di navigazione
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("🚀  Gioca", 0),
            ("👤  Account", 1),
            ("⚙️  Impostazioni", 2),
            ("📋  Console & Log", 3)
        ]

        self.nav_buttons = []
        for text, page_idx in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setObjectName("NavButton")
            btn.setFixedHeight(44)
            sidebar_layout.addWidget(btn)
            self.nav_group.addButton(btn, page_idx)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Widget account in fondo alla sidebar
        self.sidebar_account_frame = QFrame()
        self.sidebar_account_frame.setObjectName("SidebarAccountCard")
        acc_box = QHBoxLayout(self.sidebar_account_frame)
        acc_box.setContentsMargins(8, 8, 8, 8)
        acc_box.setSpacing(10)
        
        self.sidebar_head_label = QLabel()
        self.sidebar_head_label.setFixedSize(36, 36)
        self.sidebar_head_label.setPixmap(create_steve_avatar(36))
        
        user_info_box = QVBoxLayout()
        user_info_box.setSpacing(1)
        self.sidebar_username_label = QLabel("Nessun Account")
        self.sidebar_username_label.setObjectName("SidebarUsername")
        self.sidebar_type_label = QLabel("Clicca per gestire")
        self.sidebar_type_label.setObjectName("SidebarAccountType")
        user_info_box.addWidget(self.sidebar_username_label)
        user_info_box.addWidget(self.sidebar_type_label)
        
        acc_box.addWidget(self.sidebar_head_label)
        acc_box.addLayout(user_info_box)
        
        self.sidebar_account_frame.mousePressEvent = lambda e: self.show_account_dialog()
        sidebar_layout.addWidget(self.sidebar_account_frame)

        main_layout.addWidget(sidebar_widget)

        # --- PAGINE PRINCIPALI ---
        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages, 1)

        self.nav_group.idClicked.connect(self.pages.setCurrentIndex)

        # Inizializza le 4 tab
        self.home_tab = QWidget()
        self.account_tab = QWidget()
        self.settings_tab = QWidget()
        self.log_tab = QWidget()

        self.setup_home_tab()
        self.setup_account_tab()
        self.setup_settings_tab()
        self.setup_log_tab()

        self.pages.addWidget(self.home_tab)
        self.pages.addWidget(self.account_tab)
        self.pages.addWidget(self.settings_tab)
        self.pages.addWidget(self.log_tab)

        # Seleziona la prima tab di default
        self.nav_buttons[0].setChecked(True)

    def setup_home_tab(self):
        """Schermata principale di lancio e selezione versione."""
        layout = QVBoxLayout(self.home_tab)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Header Hero Card
        hero_card = QFrame()
        hero_card.setObjectName("HeroCard")
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(25, 20, 25, 20)
        
        hero_text_box = QVBoxLayout()
        hero_text_box.setSpacing(6)
        hero_title = QLabel("Pronto a esplorare?")
        hero_title.setObjectName("HeroTitle")
        hero_desc = QLabel("Seleziona una versione ufficiale di Minecraft e avvia la tua avventura.")
        hero_desc.setObjectName("HeroDesc")
        hero_text_box.addWidget(hero_title)
        hero_text_box.addWidget(hero_desc)
        
        hero_layout.addLayout(hero_text_box)
        hero_layout.addStretch()
        
        hero_badge = QLabel("Minecraft Vanilla")
        hero_badge.setObjectName("HeroBadge")
        hero_layout.addWidget(hero_badge)
        
        layout.addWidget(hero_card)

        # Card Selezione Versione
        version_card = QFrame()
        version_card.setObjectName("ModernCard")
        v_layout = QVBoxLayout(version_card)
        v_layout.setContentsMargins(25, 20, 25, 20)
        v_layout.setSpacing(15)

        card_header = QLabel("Selettore Versione Minecraft")
        card_header.setObjectName("SectionHeader")
        v_layout.addWidget(card_header)

        select_row = QHBoxLayout()
        select_row.setSpacing(12)

        self.version_combo = QComboBox()
        self.version_combo.setObjectName("VersionComboBox")
        self.version_combo.setMinimumHeight(42)
        self.version_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.version_combo.currentIndexChanged.connect(self.on_version_selected)
        select_row.addWidget(self.version_combo, 1)

        self.refresh_ver_btn = QPushButton("🔄 Aggiorna Lista")
        self.refresh_ver_btn.setObjectName("SecondaryButton")
        self.refresh_ver_btn.setFixedHeight(42)
        self.refresh_ver_btn.clicked.connect(lambda: self.refresh_version_list(force_network=True))
        select_row.addWidget(self.refresh_ver_btn)

        v_layout.addLayout(select_row)

        # Opzioni e Badge di stato versione
        ver_info_row = QHBoxLayout()
        self.version_status_pill = QLabel("Verifica stato versione...")
        self.version_status_pill.setObjectName("StatusPill")
        ver_info_row.addWidget(self.version_status_pill)
        ver_info_row.addStretch()

        self.snapshot_checkbox = QCheckBox("Mostra anche Snapshot e versioni storiche")
        self.snapshot_checkbox.setChecked(self.settings.get("show_snapshots", False))
        self.snapshot_checkbox.toggled.connect(self.on_snapshot_toggled)
        ver_info_row.addWidget(self.snapshot_checkbox)

        v_layout.addLayout(ver_info_row)
        layout.addWidget(version_card)

        layout.addStretch()

        # Bottom Launch Bar
        bottom_card = QFrame()
        bottom_card.setObjectName("ModernCard")
        bottom_layout = QVBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(25, 18, 25, 20)
        bottom_layout.setSpacing(12)

        status_row = QHBoxLayout()
        self.action_status_label = QLabel("Pronto")
        self.action_status_label.setObjectName("ActionStatusLabel")
        self.progress_percentage_label = QLabel("")
        self.progress_percentage_label.setObjectName("ProgressPercentageLabel")
        status_row.addWidget(self.action_status_label)
        status_row.addStretch()
        status_row.addWidget(self.progress_percentage_label)
        bottom_layout.addLayout(status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        bottom_layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.main_action_btn = QPushButton("▶  GIOCA")
        self.main_action_btn.setObjectName("PlayButton")
        self.main_action_btn.setFixedSize(220, 52)
        self.main_action_btn.clicked.connect(self.handle_main_action)
        btn_row.addWidget(self.main_action_btn)
        
        btn_row.addStretch()
        bottom_layout.addLayout(btn_row)

        layout.addWidget(bottom_card)

    def setup_account_tab(self):
        """Schermata di riepilogo e gestione account."""
        layout = QVBoxLayout(self.account_tab)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        header = QLabel("Gestione Account")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        self.account_details_card = QFrame()
        self.account_details_card.setObjectName("ModernCard")
        card_layout = QVBoxLayout(self.account_details_card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(15)

        self.acc_display_widget = QWidget()
        self.acc_display_layout = QHBoxLayout(self.acc_display_widget)
        self.acc_display_layout.setContentsMargins(0, 0, 0, 0)
        self.acc_display_layout.setSpacing(18)

        self.acc_large_head = QLabel()
        self.acc_large_head.setFixedSize(64, 64)
        self.acc_large_head.setPixmap(create_steve_avatar(64))
        self.acc_display_layout.addWidget(self.acc_large_head)

        acc_text_layout = QVBoxLayout()
        acc_text_layout.setSpacing(4)
        self.acc_name_label = QLabel("Nessun account selezionato")
        self.acc_name_label.setObjectName("LargeAccountName")
        self.acc_desc_label = QLabel("Aggiungi o seleziona un account per giocare.")
        self.acc_desc_label.setObjectName("AccountSubtitle")
        acc_text_layout.addWidget(self.acc_name_label)
        acc_text_layout.addWidget(self.acc_desc_label)
        self.acc_display_layout.addLayout(acc_text_layout)
        self.acc_display_layout.addStretch()

        card_layout.addWidget(self.acc_display_widget)

        manage_btn = QPushButton("🔑  Gestisci o Aggiungi Account")
        manage_btn.setObjectName("SecondaryButton")
        manage_btn.setFixedHeight(44)
        manage_btn.clicked.connect(self.show_account_dialog)
        card_layout.addWidget(manage_btn)

        layout.addWidget(self.account_details_card)
        layout.addStretch()

    def setup_settings_tab(self):
        """Schermata impostazioni di gioco (RAM, Java, Risoluzione, Cartella)."""
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        header = QLabel("Impostazioni di Gioco")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        settings_card = QFrame()
        settings_card.setObjectName("ModernCard")
        card_layout = QVBoxLayout(settings_card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(18)

        # 1. RAM Slider & SpinBox
        ram_label = QLabel("Allocazione Memoria RAM (GB)")
        ram_label.setObjectName("SettingTitle")
        card_layout.addWidget(ram_label)

        ram_control_row = QHBoxLayout()
        ram_control_row.setSpacing(15)

        self.ram_slider = QSlider(Qt.Orientation.Horizontal)
        self.ram_slider.setRange(2, 24)
        self.ram_slider.setValue(self.settings.get("ram_gb", 4))
        
        self.ram_spinbox = QSpinBox()
        self.ram_spinbox.setRange(2, 24)
        self.ram_spinbox.setValue(self.settings.get("ram_gb", 4))
        self.ram_spinbox.setSuffix(" GB")
        self.ram_spinbox.setFixedWidth(90)

        self.ram_slider.valueChanged.connect(self.ram_spinbox.setValue)
        self.ram_spinbox.valueChanged.connect(self.ram_slider.setValue)
        self.ram_spinbox.valueChanged.connect(self.on_ram_changed)

        ram_control_row.addWidget(self.ram_slider, 1)
        ram_control_row.addWidget(self.ram_spinbox)
        card_layout.addLayout(ram_control_row)

        ram_hint = QLabel("Consigliati: 4 GB per versioni Vanilla fino a 1.20+, 6-8 GB per carichi elevati.")
        ram_hint.setObjectName("SettingHint")
        card_layout.addWidget(ram_hint)

        # Separatore
        card_layout.addWidget(self.create_separator())

        # 2. Percorso Java
        java_label = QLabel("Eseguibile Java (lascia vuoto per auto-rilevamento)")
        java_label.setObjectName("SettingTitle")
        card_layout.addWidget(java_label)

        java_row = QHBoxLayout()
        self.java_input = QLineEdit(self.settings.get("custom_java", ""))
        self.java_input.setPlaceholderText("Auto-rilevato automaticamente dal runtime Minecraft")
        self.java_input.textChanged.connect(self.on_java_path_changed)
        
        browse_java_btn = QPushButton("Sfoglia...")
        browse_java_btn.setObjectName("SecondaryButton")
        browse_java_btn.clicked.connect(self.browse_java_path)
        
        java_row.addWidget(self.java_input, 1)
        java_row.addWidget(browse_java_btn)
        card_layout.addLayout(java_row)

        # Separatore
        card_layout.addWidget(self.create_separator())

        # 3. Argomenti JVM personalizzati
        jvm_label = QLabel("Argomenti JVM Personalizzati (Avanzate)")
        jvm_label.setObjectName("SettingTitle")
        card_layout.addWidget(jvm_label)

        self.jvm_input = QLineEdit(self.settings.get("jvm_args", ""))
        self.jvm_input.setPlaceholderText("Es. -XX:+UseG1GC -XX:+UnlockExperimentalVMOptions")
        self.jvm_input.textChanged.connect(self.on_jvm_args_changed)
        card_layout.addWidget(self.jvm_input)

        # Separatore
        card_layout.addWidget(self.create_separator())

        # 4. Cartella Minecraft
        dir_label = QLabel("Cartella Dati Minecraft")
        dir_label.setObjectName("SettingTitle")
        card_layout.addWidget(dir_label)

        dir_row = QHBoxLayout()
        dir_path_display = QLabel(self.minecraft_directory)
        dir_path_display.setObjectName("DirPathLabel")
        dir_path_display.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        open_folder_btn = QPushButton("📁  Apri Cartella")
        open_folder_btn.setObjectName("SecondaryButton")
        open_folder_btn.clicked.connect(self.open_minecraft_folder)
        
        dir_row.addWidget(dir_path_display, 1)
        dir_row.addWidget(open_folder_btn)
        card_layout.addLayout(dir_row)

        layout.addWidget(settings_card)
        layout.addStretch()

    def setup_log_tab(self):
        """Schermata console per log in tempo reale di Minecraft e launcher."""
        layout = QVBoxLayout(self.log_tab)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("Console e Log di Gioco")
        title.setObjectName("PageHeader")
        header_row.addWidget(title)
        header_row.addStretch()

        copy_btn = QPushButton("📋  Copia Log")
        copy_btn.setObjectName("SecondaryButton")
        copy_btn.clicked.connect(self.copy_log_to_clipboard)
        
        clear_btn = QPushButton("🗑️  Pulisci")
        clear_btn.setObjectName("SecondaryButton")
        clear_btn.clicked.connect(self.clear_log)
        
        header_row.addWidget(copy_btn)
        header_row.addWidget(clear_btn)
        layout.addLayout(header_row)

        self.log_text = QPlainTextEdit()
        self.log_text.setObjectName("ConsoleView")
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 1)

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #272a34; max-height: 1px;")
        return line

    def apply_modern_stylesheet(self):
        """Applica il design system dark gaming moderno ad alto contrasto."""
        self.setStyleSheet("""
            QWidget {
                background-color: #0f1115;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            QMainWindow {
                background-color: #0f1115;
            }
            QWidget#sidebar {
                background-color: #16181f;
                border-right: 1px solid #232631;
            }
            QLabel#SidebarTitle {
                font-size: 11pt;
                font-weight: 800;
                color: #ffffff;
                letter-spacing: 0.5px;
            }
            QLabel#SidebarSub {
                font-size: 8pt;
                color: #38bdf8;
                font-weight: 600;
            }
            QPushButton#NavButton {
                background-color: transparent;
                color: #94a3b8;
                font-size: 10pt;
                font-weight: 600;
                text-align: left;
                padding-left: 14px;
                border: none;
                border-radius: 8px;
            }
            QPushButton#NavButton:hover {
                background-color: #1f232d;
                color: #f8fafc;
            }
            QPushButton#NavButton:checked {
                background-color: #2563eb;
                color: #ffffff;
            }
            QFrame#SidebarAccountCard {
                background-color: #1a1d26;
                border: 1px solid #282c39;
                border-radius: 8px;
            }
            QFrame#SidebarAccountCard:hover {
                background-color: #222633;
                border: 1px solid #3b82f6;
                cursor: pointer;
            }
            QLabel#SidebarUsername {
                font-weight: 700;
                font-size: 9pt;
                color: #f1f5f9;
            }
            QLabel#SidebarAccountType {
                font-size: 8pt;
                color: #38bdf8;
            }
            QFrame#HeroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #0f172a);
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QLabel#HeroTitle {
                font-size: 18pt;
                font-weight: 800;
                color: #ffffff;
            }
            QLabel#HeroDesc {
                font-size: 10pt;
                color: #94a3b8;
            }
            QLabel#HeroBadge {
                background-color: #0284c7;
                color: white;
                font-size: 8pt;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 12px;
            }
            QFrame#ModernCard {
                background-color: #16181f;
                border: 1px solid #232631;
                border-radius: 12px;
            }
            QLabel#SectionHeader {
                font-size: 12pt;
                font-weight: 700;
                color: #f8fafc;
            }
            QLabel#PageHeader {
                font-size: 16pt;
                font-weight: 800;
                color: #ffffff;
                margin-bottom: 5px;
            }
            QComboBox#VersionComboBox {
                background-color: #1f232d;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 11pt;
                font-weight: 600;
            }
            QComboBox#VersionComboBox:focus {
                border: 1px solid #3b82f6;
            }
            QComboBox#VersionComboBox QAbstractItemView {
                background-color: #1f232d;
                color: #ffffff;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                border: 1px solid #334155;
                padding: 4px;
            }
            QLabel#StatusPill {
                font-size: 9pt;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 6px;
                background-color: #1f232d;
            }
            QCheckBox {
                color: #94a3b8;
                font-size: 9pt;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1f232d;
            }
            QCheckBox::indicator:checked {
                background-color: #3b82f6;
                border: 1px solid #3b82f6;
            }
            QLabel#ActionStatusLabel {
                font-size: 10pt;
                color: #94a3b8;
                font-weight: 500;
            }
            QLabel#ProgressPercentageLabel {
                font-size: 10pt;
                color: #38bdf8;
                font-weight: 700;
            }
            QProgressBar {
                background-color: #1f232d;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 4px;
            }
            QPushButton#PlayButton {
                background-color: #10b981;
                color: #ffffff;
                font-size: 13pt;
                font-weight: 800;
                border: none;
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton#PlayButton:hover {
                background-color: #059669;
            }
            QPushButton#PlayButton:disabled {
                background-color: #272a34;
                color: #64748b;
            }
            QPushButton#SecondaryButton {
                background-color: #1f232d;
                color: #e2e8f0;
                font-size: 10pt;
                font-weight: 600;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #2a303e;
                color: #ffffff;
                border-color: #475569;
            }
            QLabel#LargeAccountName {
                font-size: 14pt;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#AccountSubtitle {
                font-size: 10pt;
                color: #94a3b8;
            }
            QLabel#SettingTitle {
                font-size: 10pt;
                font-weight: 700;
                color: #e2e8f0;
            }
            QLabel#SettingHint {
                font-size: 8pt;
                color: #64748b;
            }
            QLabel#DirPathLabel {
                background-color: #1f232d;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                color: #94a3b8;
                font-family: monospace;
                font-size: 9pt;
            }
            QLineEdit {
                background-color: #1f232d;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            QSpinBox {
                background-color: #1f232d;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                font-size: 10pt;
                font-weight: 700;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1f232d;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #60a5fa;
                border: 2px solid #ffffff;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QPlainTextEdit#ConsoleView {
                background-color: #0c0d10;
                color: #e2e8f0;
                border: 1px solid #232631;
                border-radius: 8px;
                font-family: 'Consolas', 'DejaVu Sans Mono', monospace;
                font-size: 9pt;
                padding: 8px;
            }
        """)

    # --- LOGICA RECUPERO E GESTIONE VERSIONI MINECRAFT ---

    def refresh_version_list(self, force_network=False, initial=False):
        """Recupera la lista delle versioni (da cache o rete) e le versioni installate."""
        self.action_status_label.setText("Caricamento elenco versioni...")
        self.refresh_ver_btn.setEnabled(False)
        
        def task():
            cached_data = None
            if not force_network and os.path.exists(self.versions_cache_file):
                try:
                    with open(self.versions_cache_file, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                except Exception:
                    pass

            if cached_data and isinstance(cached_data, list) and len(cached_data) > 0:
                versions = cached_data
            else:
                try:
                    self.worker.log_message.emit("Connessione a Mojang per recuperare l'elenco versioni...", "INFO")
                    version_manifest = minecraft_launcher_lib.utils.get_version_list()
                    versions = version_manifest.get("versions", [])
                    # Salva in cache
                    try:
                        with open(self.versions_cache_file, "w", encoding="utf-8") as f:
                            json.dump(versions, f)
                    except Exception:
                        pass
                except Exception as e:
                    self.worker.log_message.emit(f"Impossibile contattare Mojang: {e}", "ERROR")
                    versions = cached_data if cached_data else []

            latest_release = ""
            for v in versions:
                if v.get("type") == "release":
                    latest_release = v.get("id")
                    break
            
            self.worker.versions_loaded.emit(versions, latest_release)

        self.run_task(task, on_finish=lambda: self.refresh_ver_btn.setEnabled(True))

    @pyqtSlot(list, str)
    def on_versions_loaded(self, versions, latest_release):
        self.all_versions = versions
        self.update_installed_versions_cache()
        self.populate_version_dropdown()
        self.action_status_label.setText("Pronto per il lancio")

    def update_installed_versions_cache(self):
        """Rileva quali versioni sono attualmente installate nella cartella locale."""
        try:
            installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_directory)
            self.installed_version_ids = {v["id"] for v in installed if "id" in v}
        except Exception as e:
            self.installed_version_ids = set()

    def populate_version_dropdown(self):
        """Riempie il ComboBox con le versioni filtrate in base all'impostazione."""
        self.version_combo.blockSignals(True)
        self.version_combo.clear()

        show_all = self.snapshot_checkbox.isChecked()
        target_version = self.selected_version

        # Se non c'è una versione selezionata, cerca l'ultima installata o l'ultima release
        if not target_version:
            for v in self.all_versions:
                if v.get("id") in self.installed_version_ids:
                    target_version = v.get("id")
                    break
            if not target_version:
                for v in self.all_versions:
                    if v.get("type") == "release":
                        target_version = v.get("id")
                        break

        idx_to_select = 0
        added_count = 0

        for v in self.all_versions:
            v_id = v.get("id")
            v_type = v.get("type", "release")
            
            # Se show_all è False, mostra solo release o versioni già installate localmente
            if not show_all and v_type != "release" and v_id not in self.installed_version_ids:
                continue

            is_inst = v_id in self.installed_version_ids
            status_tag = "✓ Installata" if is_inst else "Download"
            type_tag = "Release" if v_type == "release" else v_type.capitalize()
            
            display_text = f"{v_id}   ({type_tag})  [{status_tag}]"
            self.version_combo.addItem(display_text, v_id)

            if v_id == target_version:
                idx_to_select = added_count

            added_count += 1

        if self.version_combo.count() > 0:
            self.version_combo.setCurrentIndex(idx_to_select)
            self.selected_version = self.version_combo.currentData()
        
        self.version_combo.blockSignals(False)
        self.update_version_status_ui()

    def on_version_selected(self, index):
        v_id = self.version_combo.currentData()
        if v_id:
            self.selected_version = v_id
            self.settings["last_version"] = v_id
            self.save_settings()
            self.update_version_status_ui()

    def on_snapshot_toggled(self, checked):
        self.settings["show_snapshots"] = checked
        self.save_settings()
        self.populate_version_dropdown()

    def update_version_status_ui(self):
        """Aggiorna il pill di stato e il bottone GIOCA / INSTALLA."""
        if not self.selected_version:
            self.version_status_pill.setText("Nessuna versione selezionata")
            self.version_status_pill.setStyleSheet("background-color: #1f232d; color: #94a3b8;")
            self.main_action_btn.setEnabled(False)
            return

        is_installed = self.selected_version in self.installed_version_ids
        
        if is_installed:
            self.version_status_pill.setText(f"✓ {self.selected_version} è installata e pronta")
            self.version_status_pill.setStyleSheet("background-color: #064e3b; color: #34d399; border: 1px solid #059669;")
            self.main_action_btn.setText("▶  GIOCA")
            self.main_action_btn.setStyleSheet("""
                QPushButton#PlayButton {
                    background-color: #10b981;
                    color: #ffffff;
                }
                QPushButton#PlayButton:hover {
                    background-color: #059669;
                }
            """)
            self.main_action_btn.setEnabled(self.game_process is None)
        else:
            self.version_status_pill.setText(f"⬇ {self.selected_version} non è ancora installata")
            self.version_status_pill.setStyleSheet("background-color: #1e3a8a; color: #93c5fd; border: 1px solid #2563eb;")
            self.main_action_btn.setText("⬇  INSTALLA")
            self.main_action_btn.setStyleSheet("""
                QPushButton#PlayButton {
                    background-color: #3b82f6;
                    color: #ffffff;
                }
                QPushButton#PlayButton:hover {
                    background-color: #2563eb;
                }
            """)
            self.main_action_btn.setEnabled(self.game_process is None)

    # --- LOGICA DI INSTALLAZIONE E AVVIO GIOCO ---

    def handle_main_action(self):
        if not self.selected_version:
            return

        is_installed = self.selected_version in self.installed_version_ids
        if is_installed:
            self.launch_game()
        else:
            self.install_selected_version()

    def install_selected_version(self):
        """Scarica e installa la versione Minecraft selezionata tramite callback dettagliati."""
        version_id = self.selected_version
        self.log(f"Avvio installazione di Minecraft {version_id}...", "INFO")
        self.action_status_label.setText(f"Installazione di {version_id} in corso...")
        self.progress_bar.setValue(0)
        self.progress_percentage_label.setText("0%")

        current_max = 0

        def set_status(status_text):
            self.worker.status_update.emit(status_text, "INFO")

        def set_progress(progress_val):
            nonlocal current_max
            if current_max > 0:
                pct = int((progress_val / current_max) * 100)
                self.worker.progress.emit(min(pct, 100))

        def set_max(new_max):
            nonlocal current_max
            current_max = new_max

        callback = {
            "setStatus": set_status,
            "setProgress": set_progress,
            "setMax": set_max
        }

        def install_task():
            minecraft_launcher_lib.install.install_minecraft_version(
                version_id,
                self.minecraft_directory,
                callback=callback
            )
            self.worker.log_message.emit(f"Minecraft {version_id} installato con successo!", "SUCCESS")

        def on_complete():
            self.update_installed_versions_cache()
            self.populate_version_dropdown()
            self.action_status_label.setText("Installazione completata con successo!")
            self.progress_bar.setValue(100)
            self.progress_percentage_label.setText("100%")
            CustomMessageBox("Installazione Completata", f"Minecraft {version_id} è pronto per essere giocato!", "success", self).exec()

        self.run_task(install_task, on_finish=on_complete)

    def launch_game(self):
        """Prepara le opzioni e lancia il processo di Minecraft."""
        if self.worker_thread and self.worker_thread.isRunning():
            CustomMessageBox("Attendi", "Un'operazione di download o installazione è in corso.", "info", self).exec()
            return
            
        if not self.account_manager.current_account:
            CustomMessageBox("Account richiesto", "Seleziona o aggiungi un account prima di avviare il gioco.", "info", self).exec()
            self.show_account_dialog()
            return

        if not self.refresh_current_account_token():
            CustomMessageBox("Sessione Scaduta", "Il tuo token Microsoft è scaduto. Effettua nuovamente l'accesso.", "error", self).exec()
            self.show_account_dialog()
            return

        account_opts = self.account_manager.get_launch_options()
        ram_gb = self.settings.get("ram_gb", 4)
        
        jvm_args = [f"-Xmx{ram_gb}G", f"-Xms{ram_gb}G"]
        custom_args = self.settings.get("jvm_args", "").strip()
        if custom_args:
            jvm_args.extend(custom_args.split())

        options = {
            "username": account_opts["username"],
            "uuid": account_opts["uuid"],
            "token": account_opts["token"],
            "jvmArguments": jvm_args,
            "launcherName": self.launcher_name,
            "launcherVersion": self.launcher_version,
            "gameDirectory": self.minecraft_directory
        }

        custom_java = self.settings.get("custom_java", "").strip()
        if custom_java and os.path.exists(custom_java):
            options["executablePath"] = custom_java

        version_id = self.selected_version
        self.log(f"Generazione comando per Minecraft {version_id} (RAM: {ram_gb}GB)...", "INFO")
        
        try:
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                version_id,
                self.minecraft_directory,
                options
            )
            
            self.log(f"Comando di avvio pronto. Esecuzione del processo...", "SUCCESS")
            self.action_status_label.setText(f"Minecraft {version_id} in esecuzione")
            self.main_action_btn.setEnabled(False)
            self.main_action_btn.setText("■ IN ESECUZIONE")

            # Passa automaticamente alla tab della console
            self.nav_buttons[3].setChecked(True)
            self.pages.setCurrentIndex(3)

            subprocess_args = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
                'text': True,
                'encoding': 'utf-8',
                'errors': 'ignore',
                'cwd': self.minecraft_directory
            }
            if sys.platform == "win32":
                subprocess_args['creationflags'] = subprocess.CREATE_NO_WINDOW

            self.game_process = subprocess.Popen(minecraft_command, **subprocess_args)

            threading.Thread(target=self.monitor_game_process, daemon=True).start()
            threading.Thread(target=self.read_game_output, args=(self.game_process.stdout,), daemon=True).start()

        except Exception as e:
            self.log(f"Errore irreversibile durante l'avvio: {e}", "ERROR")
            CustomMessageBox("Errore di Avvio", f"Impossibile avviare Minecraft {version_id}:\n{e}", "error", self).exec()
            self.update_version_status_ui()

    def read_game_output(self, pipe):
        for line in iter(pipe.readline, ''):
            if line:
                QApplication.postEvent(self, LogEvent(line.strip()))

    def monitor_game_process(self):
        if self.game_process:
            self.game_process.wait()
            QApplication.postEvent(self, GameClosedEvent())

    def event(self, event):
        if event.type() == LogEvent.EVENT_TYPE:
            self.log(event.message, "GAME")
            return True
        if event.type() == GameClosedEvent.EVENT_TYPE:
            self.on_game_closed()
            return True
        return super().event(event)

    def on_game_closed(self):
        self.log("Processo di Minecraft terminato.", "SUCCESS")
        self.game_process = None
        self.action_status_label.setText("Pronto per il lancio")
        self.update_version_status_ui()
        # Torna alla pagina iniziale
        self.nav_buttons[0].setChecked(True)
        self.pages.setCurrentIndex(0)

    # --- GESTIONE ACCOUNT & REFRESH ---

    def show_account_dialog(self):
        dialog = LoginDialog(self, self.account_manager, client_id=self.AZURE_CLIENT_ID, client_secret=self.AZURE_CLIENT_SECRET)
        dialog.exec()
        self.update_account_badge()

    def update_account_badge(self):
        """Aggiorna le informazioni dell'account nella sidebar e nella pagina Account."""
        curr = self.account_manager.current_account
        if curr:
            name = curr.get("username", "Giocatore")
            is_ms = curr.get("type") == "microsoft"
            acc_type_str = "Microsoft Xbox" if is_ms else "Offline"
            
            self.sidebar_username_label.setText(name)
            self.sidebar_type_label.setText(acc_type_str)
            self.acc_name_label.setText(name)
            self.acc_desc_label.setText(f"Account {acc_type_str} attivo ● Pronto per giocare")
            
            if is_ms:
                self.load_head_avatar(curr.get("uuid"))
            else:
                self.sidebar_head_label.setPixmap(create_steve_avatar(36))
                self.acc_large_head.setPixmap(create_steve_avatar(64))
        else:
            self.sidebar_username_label.setText("Nessun Account")
            self.sidebar_type_label.setText("Clicca per accedere")
            self.acc_name_label.setText("Nessun account attivo")
            self.acc_desc_label.setText("Configura un profilo nella tab Account.")
            self.sidebar_head_label.setPixmap(create_steve_avatar(36))
            self.acc_large_head.setPixmap(create_steve_avatar(64))

    def load_head_avatar(self, uuid_str):
        cached_path = os.path.join(self.heads_folder, f"{uuid_str}.png")
        if os.path.exists(cached_path) and os.path.getsize(cached_path) > 0:
            pix = QPixmap(cached_path)
            self.sidebar_head_label.setPixmap(pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.acc_large_head.setPixmap(pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            return

        self.sidebar_head_label.setPixmap(create_steve_avatar(36))
        self.acc_large_head.setPixmap(create_steve_avatar(64))

        def on_loaded(u, pixmap):
            if not pixmap.isNull():
                self.sidebar_head_label.setPixmap(pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.acc_large_head.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        dl_thread = QThread(self)
        worker = ImageDownloader(uuid_str, self.heads_folder)
        worker.moveToThread(dl_thread)
        worker.image_ready.connect(on_loaded)
        dl_thread.started.connect(worker.run)
        worker.finished.connect(dl_thread.quit)
        worker.finished.connect(worker.deleteLater)
        dl_thread.finished.connect(dl_thread.deleteLater)
        dl_thread.start()

    def refresh_current_account_token(self):
        account = self.account_manager.current_account
        if not account or account.get("type") != "microsoft":
            return True
        if not self.account_manager.is_token_expired():
            return True

        self.log("Rinnovo token di accesso Microsoft in corso...", "INFO")
        refresh_token = account.get("refresh_token")
        if not refresh_token:
            return False

        try:
            new_data = minecraft_launcher_lib.microsoft_account.complete_refresh(
                client_id=self.AZURE_CLIENT_ID,
                client_secret=self.AZURE_CLIENT_SECRET,
                redirect_uri="http://localhost:5000/callback",
                refresh_token=refresh_token
            )
            self.account_manager.add_microsoft_account(new_data)
            self.log("Token Microsoft rinnovato!", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Impossibile rinnovare il token: {e}", "ERROR")
            return False

    # --- GESTIONE IMPOSTAZIONI ---

    def on_ram_changed(self, value):
        self.settings["ram_gb"] = value
        self.save_settings()

    def on_java_path_changed(self, text):
        self.settings["custom_java"] = text.strip()
        self.save_settings()

    def on_jvm_args_changed(self, text):
        self.settings["jvm_args"] = text.strip()
        self.save_settings()

    def browse_java_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Eseguibile Java", "", "Eseguibile (*.exe java javaw);;Tutti i file (*)")
        if path:
            self.java_input.setText(path)

    def open_minecraft_folder(self):
        """Apre la cartella di gioco Minecraft nel gestore file di sistema."""
        path = self.minecraft_directory
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])

    # --- LOG & UTILITY ---

    @pyqtSlot(str, str)
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "INFO": "#38bdf8",
            "ERROR": "#f87171",
            "SUCCESS": "#4ade80",
            "GAME": "#fbbf24"
        }
        color = color_map.get(level, "#e2e8f0")
        msg_html = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color}; font-weight: bold;">[{level}]</span> <span style="color: #f1f5f9;">{message}</span>'
        self.log_text.appendHtml(msg_html)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self):
        self.log_text.clear()

    def copy_log_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
        CustomMessageBox("Copia", "I log sono stati copiati negli appunti!", "info", self).exec()

    @pyqtSlot(str, str)
    def update_status(self, message, level="INFO"):
        self.action_status_label.setText(message)
        self.log(message, level)

    @pyqtSlot(int)
    def update_progress(self, progress):
        self.progress_bar.setValue(progress)
        self.progress_percentage_label.setText(f"{progress}%")

    def run_task(self, target, *args, on_finish=None, **kwargs):
        """Avvia un task asincrono con gestione thread pulita."""
        if self.worker_thread and self.worker_thread.isRunning():
            self.log("Un task è già in esecuzione.", "ERROR")
            return

        self.worker_thread = QThread()
        self.worker = Worker(target, *args, **kwargs)
        self.worker.moveToThread(self.worker_thread)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker.progress.connect(self.update_progress)
        self.worker.status_update.connect(self.update_status)
        self.worker.log_message.connect(self.log)
        self.worker.versions_loaded.connect(self.on_versions_loaded)

        if on_finish:
            self.worker.finished.connect(on_finish)

        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def closeEvent(self, event):
        """Chiusura controllata dei processi attivi."""
        if self.game_process:
            try:
                self.game_process.terminate()
                self.game_process.wait(timeout=3)
            except Exception:
                pass

        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = MinecraftLauncher()
    launcher.show()
    sys.exit(app.exec())