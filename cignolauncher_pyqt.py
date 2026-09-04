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
    QButtonGroup, QListWidget, QListWidgetItem, QScrollArea
)
from PyQt6.QtGui import QIcon, QFont, QTextCursor, QPixmap, QColor
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt, pyqtSlot, QEvent, QSize, QTimer

from account_manager import AccountManager
from instance_manager import InstanceManager
from instance_dialog import InstanceEditDialog, InstanceManagerDialog
from first_run_wizard import FirstRunWizard
from ui_controls import MaterialComboBox
from login_dialog_pyqt import LoginDialog, CustomMessageBox
from utils import ImageDownloader, create_steve_avatar, create_app_logo_pixmap

DEFAULT_POPULAR_VERSIONS = [
    {"id": "1.21.4", "type": "release"},
    {"id": "1.21.3", "type": "release"},
    {"id": "1.21.1", "type": "release"},
    {"id": "1.20.6", "type": "release"},
    {"id": "1.20.4", "type": "release"},
    {"id": "1.20.2", "type": "release"},
    {"id": "1.20.1", "type": "release"},
    {"id": "1.19.4", "type": "release"},
    {"id": "1.18.2", "type": "release"},
    {"id": "1.17.1", "type": "release"},
    {"id": "1.16.5", "type": "release"},
    {"id": "1.12.2", "type": "release"},
    {"id": "1.8.9", "type": "release"},
    {"id": "1.7.10", "type": "release"}
]

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
    """Launcher Minecraft moderno multi-versione e multi-istanza."""

    def __init__(self):
        super().__init__()
        self.launcher_name = "CignoLauncher"
        self.launcher_version = "2.1.0"

        self.setup_paths()
        self.load_settings()
        self.first_run = not bool(self.settings.get("last_version"))
        self.onboarding_pending = (
            not bool(self.settings.get("onboarding_completed"))
            and not bool(self.settings.get("last_version"))
        )
        self.account_manager = AccountManager(self.launcher_directory)
        self.instance_manager = InstanceManager(self.launcher_directory)

        self.game_process = None
        self.worker_thread = None
        self.worker = None
        self.first_run_wizard = None

        # Inizializzazione versioni con default
        self.all_versions = self.load_cached_versions()
        self.installed_version_ids = set()

        # Al primo avvio la versione selezionata è SEMPRE l'ultima release ufficiale
        default_latest = self.get_latest_official_release()
        self.selected_version = self.settings.get("last_version") or default_latest

        # Assicura che l'istanza di default usi l'ultima versione disponibile
        self.instance_manager.ensure_default_instance(default_version=default_latest)

        self.AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "your-client-id")
        self.AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "your-secret-value")

        self.setupUi()
        self.apply_modern_stylesheet()

        # Popola subito la UI sincronicamente
        self.update_installed_versions_cache()
        self.refresh_instances_selector()
        self.populate_version_dropdown()
        self.update_account_badge()

        # Carica elenco completo versioni in background
        self.refresh_version_list(initial=True)

        # Se non c'è nessun account collegato, apri login dialog all'avvio
        QTimer.singleShot(250, self.start_startup_flow)

    def start_startup_flow(self):
        if self.onboarding_pending:
            active_instance = self.instance_manager.get_current_instance()
            wizard = FirstRunWizard(
                self,
                self.get_latest_official_release(),
                active_instance or {},
                resource_path("assets/logo.png"),
                resource_path("assets/chevron_down.svg"),
                available_versions=self.all_versions,
            )
            self.first_run_wizard = wizard
            if wizard.exec() == FirstRunWizard.DialogCode.Accepted and active_instance:
                self.instance_manager.update_instance(
                    active_instance["id"],
                    name=wizard.instance_name,
                    version=wizard.instance_version,
                    ram_gb=wizard.instance_ram,
                )
                self.settings["onboarding_completed"] = True
                self.settings["last_version"] = wizard.instance_version
                self.settings["profile_mode"] = wizard.profile_mode
                self.save_settings()
                self.refresh_instances_selector()
                self.first_run = False
                if wizard.profile_mode == "offline" and wizard.offline_username_value:
                    self.account_manager.add_offline_account(wizard.offline_username_value)
                    self.update_account_badge()
            self.onboarding_pending = False
            self.first_run_wizard = None
            self.show()
        self.check_account_on_startup()

    def get_latest_official_release(self):
        """Identifica l'ultima versione Release ufficiale Mojang disponibile."""
        for v in self.all_versions:
            if isinstance(v, dict) and v.get("type") == "release":
                return v.get("id")
            elif isinstance(v, str) and not ("-" in v or "w" in v or "pre" in v or "rc" in v):
                return v
        return "1.21.4"

    def load_cached_versions(self):
        if os.path.exists(self.versions_cache_file):
            try:
                with open(self.versions_cache_file, "r", encoding="utf-8") as handle:
                    cached = json.load(handle)
                if isinstance(cached, list) and cached:
                    return cached
            except Exception:
                pass
        return list(DEFAULT_POPULAR_VERSIONS)

    def setup_paths(self):
        """Inizializza i percorsi di gioco e configurazione."""
        custom_data_dir = os.getenv("CIGNO_DATA_DIR")
        if custom_data_dir:
            self.launcher_directory = os.path.abspath(custom_data_dir)
        elif sys.platform == "win32":
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
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                print(f"Avviso: impossibile creare cartella {folder}: {e}")

    def load_settings(self):
        """Carica le impostazioni da settings.json con valori di default."""
        self.settings = {
            "ram_gb": 4,
            "show_snapshots": False,
            "last_version": "",
            "custom_java": "",
            "jvm_args": "",
            "onboarding_completed": False,
            "profile_mode": ""
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
        self.setWindowTitle(f"{self.launcher_name} v{self.launcher_version} - Vanilla & Instances")
        self.setMinimumSize(820, 600)
        self.resize(1040, 700)

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
        sidebar_widget.setFixedWidth(204)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(12, 18, 12, 14)
        sidebar_layout.setSpacing(8)

        # Brand
        brand_container = QWidget()
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(4, 4, 4, 14)
        brand_layout.setSpacing(10)

        logo_icon_label = QLabel()
        logo_icon_label.setPixmap(create_steve_avatar(36))

        brand_text_layout = QVBoxLayout()
        brand_text_layout.setSpacing(1)
        app_title = QLabel("CignoLauncher")
        app_title.setObjectName("SidebarTitle")
        app_sub = QLabel("Multi-Istanza")
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
            ("Gioca", 0, "assets/nav_play.svg"),
            ("Istanze", 1, "assets/nav_instances.svg"),
            ("Account", 2, "assets/nav_account.svg"),
            ("Impostazioni", 3, "assets/nav_settings.svg"),
            ("Console & Log", 4, "assets/nav_console.svg")
        ]

        self.nav_buttons = []
        for text, page_idx, icon_file in nav_items:
            btn = QPushButton(text)
            icon_path = resource_path(icon_file)
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(18, 18))
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
        self.sidebar_account_frame.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.sidebar_type_label = QLabel("Clicca per accedere")
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

        # Inizializza le 5 tab
        self.home_tab = QWidget()
        self.instances_tab = QWidget()
        self.account_tab = QWidget()
        self.settings_tab = QWidget()
        self.log_tab = QWidget()

        self.setup_home_tab()
        self.setup_instances_tab()
        self.setup_account_tab()
        self.setup_settings_tab()
        self.setup_log_tab()

        for page in (self.home_tab, self.instances_tab, self.account_tab, self.settings_tab, self.log_tab):
            page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setWidget(page)
            self.pages.addWidget(scroll_area)

        self.nav_buttons[0].setChecked(True)

    def setup_home_tab(self):
        """Schermata principale di lancio con supporto Istanze e Versioni."""
        layout = QVBoxLayout(self.home_tab)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Hero Card
        hero_card = QFrame()
        hero_card.setObjectName("HeroCard")
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(25, 20, 25, 20)

        hero_text_box = QVBoxLayout()
        hero_text_box.setSpacing(4)
        hero_title = QLabel("Pronto a esplorare?")
        hero_title.setObjectName("HeroTitle")
        hero_desc = QLabel("Avvia la tua istanza personalizzata o installa nuove versioni di Minecraft.")
        hero_desc.setObjectName("HeroDesc")
        hero_desc.setWordWrap(True)
        hero_text_box.addWidget(hero_title)
        hero_text_box.addWidget(hero_desc)

        hero_layout.addLayout(hero_text_box)
        hero_layout.addStretch()

        hero_badge = QLabel()
        hero_badge.setObjectName("HeroBadge")
        hero_badge.setFixedSize(68, 68)
        hero_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        launcher_icon = QPixmap(resource_path("assets/window_icon.ico"))
        if not launcher_icon.isNull():
            hero_badge.setPixmap(launcher_icon.scaled(
                48,
                48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        hero_layout.addWidget(hero_badge)

        layout.addWidget(hero_card)

        # Card Istanza Attiva
        instance_card = QFrame()
        instance_card.setObjectName("ModernCard")
        inst_layout = QVBoxLayout(instance_card)
        inst_layout.setContentsMargins(24, 18, 24, 18)
        inst_layout.setSpacing(12)

        inst_top_row = QHBoxLayout()
        inst_card_header = QLabel("📦  Istanza Attiva")
        inst_card_header.setObjectName("SectionHeader")
        inst_top_row.addWidget(inst_card_header)
        inst_top_row.addStretch()

        manage_inst_btn = QPushButton("⚙️ Gestisci Istanze")
        manage_inst_btn.setObjectName("SecondaryButton")
        manage_inst_btn.clicked.connect(self.open_instances_dialog)
        inst_top_row.addWidget(manage_inst_btn)

        new_inst_btn = QPushButton("➕ Nuova Istanza")
        new_inst_btn.setObjectName("SecondaryButton")
        new_inst_btn.clicked.connect(self.create_new_instance_dialog)
        inst_top_row.addWidget(new_inst_btn)

        inst_layout.addLayout(inst_top_row)

        inst_select_row = QHBoxLayout()
        self.instance_combo = MaterialComboBox(fit_popup_to_field=True, popup_row_height=56)
        self.instance_combo.setObjectName("InstanceComboBox")
        self.instance_combo.setMinimumHeight(32)
        self.instance_combo.setMaxVisibleItems(8)
        self.instance_combo.currentIndexChanged.connect(self.on_instance_selected)
        inst_select_row.addWidget(self.instance_combo, 1)

        open_dir_btn = QPushButton("📁 Cartella Salvataggi")
        open_dir_btn.setObjectName("SecondaryButton")
        open_dir_btn.setFixedHeight(34)
        open_dir_btn.clicked.connect(self.open_active_instance_folder)
        inst_select_row.addWidget(open_dir_btn)

        inst_layout.addLayout(inst_select_row)

        # Info badge istanza
        inst_info_row = QHBoxLayout()
        self.instance_info_badge = QLabel("Istanza: -")
        self.instance_info_badge.setObjectName("StatusPill")
        inst_info_row.addWidget(self.instance_info_badge)
        inst_info_row.addStretch()
        inst_layout.addLayout(inst_info_row)

        layout.addWidget(instance_card)

        # Card Selezione Versione Minecraft
        version_card = QFrame()
        version_card.setObjectName("ModernCard")
        v_layout = QVBoxLayout(version_card)
        v_layout.setContentsMargins(24, 18, 24, 18)
        v_layout.setSpacing(12)

        card_header = QLabel("Versione di Minecraft")
        card_header.setObjectName("SectionHeader")
        v_layout.addWidget(card_header)

        select_row = QHBoxLayout()
        select_row.setSpacing(12)

        self.version_combo = MaterialComboBox()
        self.version_combo.setObjectName("VersionComboBox")
        self.version_combo.setMinimumHeight(32)
        self.version_combo.setMaxVisibleItems(8)
        self.version_combo.setMinimumContentsLength(24)
        self.version_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.version_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.version_combo.currentIndexChanged.connect(self.on_version_selected)
        select_row.addWidget(self.version_combo, 1)

        self.refresh_ver_btn = QPushButton("🔄 Aggiorna Lista")
        self.refresh_ver_btn.setObjectName("SecondaryButton")
        self.refresh_ver_btn.setFixedHeight(34)
        self.refresh_ver_btn.clicked.connect(lambda: self.refresh_version_list(force_network=True))
        select_row.addWidget(self.refresh_ver_btn)

        v_layout.addLayout(select_row)

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
        bottom_layout.setContentsMargins(24, 16, 24, 18)
        bottom_layout.setSpacing(10)

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
        self.main_action_btn.setFixedSize(220, 50)
        self.main_action_btn.clicked.connect(self.handle_main_action)
        btn_row.addWidget(self.main_action_btn)

        btn_row.addStretch()
        bottom_layout.addLayout(btn_row)

        layout.addWidget(bottom_card)

    def setup_instances_tab(self):
        """Schermata dedicata di gestione completa delle istanze."""
        layout = QVBoxLayout(self.instances_tab)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        top_row = QHBoxLayout()
        header = QLabel("Gestione Istanze")
        header.setObjectName("PageHeader")
        top_row.addWidget(header)
        top_row.addStretch()

        new_inst_btn = QPushButton("➕  Crea Nuova Istanza")
        new_inst_btn.setObjectName("PrimaryActionButton")
        new_inst_btn.clicked.connect(self.create_new_instance_dialog)
        top_row.addWidget(new_inst_btn)
        layout.addLayout(top_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(18)

        # Lista Istanze
        self.instances_page_list = QListWidget()
        self.instances_page_list.setObjectName("InstancesListWidget")
        self.instances_page_list.itemSelectionChanged.connect(self.on_instance_page_selection_changed)
        content_row.addWidget(self.instances_page_list, 1)

        # Dettagli Istanza Selezionata
        details_panel = QFrame()
        details_panel.setObjectName("ModernCard")
        panel_layout = QVBoxLayout(details_panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(12)

        self.inst_page_title = QLabel("Seleziona un'istanza")
        self.inst_page_title.setObjectName("LargeAccountName")
        self.inst_page_ver = QLabel("Versione: -")
        self.inst_page_ram = QLabel("RAM Dedicata: -")
        self.inst_page_path = QLabel("Percorso Salvataggi: -")
        self.inst_page_path.setWordWrap(True)
        self.inst_page_path.setStyleSheet("color: #64748b; font-size: 8pt;")

        panel_layout.addWidget(self.inst_page_title)
        panel_layout.addWidget(self.inst_page_ver)
        panel_layout.addWidget(self.inst_page_ram)
        panel_layout.addWidget(self.inst_page_path)
        panel_layout.addStretch()

        self.btn_page_activate = QPushButton("✓  Imposta come Attiva")
        self.btn_page_activate.setObjectName("PrimaryActionButton")
        self.btn_page_activate.clicked.connect(self.activate_selected_instance_from_page)

        self.btn_page_edit = QPushButton("✏️  Modifica Istanza")
        self.btn_page_edit.setObjectName("SecondaryButton")
        self.btn_page_edit.clicked.connect(self.edit_selected_instance_from_page)

        self.btn_page_folder = QPushButton("📁  Apri Cartella Salvataggi")
        self.btn_page_folder.setObjectName("SecondaryButton")
        self.btn_page_folder.clicked.connect(self.open_selected_instance_folder_from_page)

        self.btn_page_delete = QPushButton("🗑️  Elimina Istanza")
        self.btn_page_delete.setObjectName("DeleteButton")
        self.btn_page_delete.clicked.connect(self.delete_selected_instance_from_page)

        panel_layout.addWidget(self.btn_page_activate)
        panel_layout.addWidget(self.btn_page_edit)
        panel_layout.addWidget(self.btn_page_folder)
        panel_layout.addWidget(self.btn_page_delete)

        content_row.addWidget(details_panel, 1)
        layout.addLayout(content_row)

    def setup_account_tab(self):
        """Schermata account."""
        layout = QVBoxLayout(self.account_tab)
        layout.setContentsMargins(28, 24, 28, 24)
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
        """Schermata impostazioni globali."""
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        header = QLabel("Impostazioni Globali")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        settings_card = QFrame()
        settings_card.setObjectName("ModernCard")
        card_layout = QVBoxLayout(settings_card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(16)

        # 1. RAM Default
        ram_label = QLabel("Allocazione Memoria RAM Globale (GB):")
        ram_label.setObjectName("SettingTitle")
        card_layout.addWidget(ram_label)

        ram_control_row = QHBoxLayout()
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

        card_layout.addWidget(self.create_separator())

        # 2. Java Eseguibile
        java_label = QLabel("Eseguibile Java (lascia vuoto per auto-rilevamento):")
        java_label.setObjectName("SettingTitle")
        card_layout.addWidget(java_label)

        java_row = QHBoxLayout()
        self.java_input = QLineEdit(self.settings.get("custom_java", ""))
        self.java_input.setPlaceholderText("Auto-rilevato automaticamente")
        self.java_input.textChanged.connect(self.on_java_path_changed)

        browse_java_btn = QPushButton("Sfoglia...")
        browse_java_btn.setObjectName("SecondaryButton")
        browse_java_btn.clicked.connect(self.browse_java_path)

        java_row.addWidget(self.java_input, 1)
        java_row.addWidget(browse_java_btn)
        card_layout.addLayout(java_row)

        card_layout.addWidget(self.create_separator())

        # 3. Argomenti JVM
        jvm_label = QLabel("Argomenti JVM Globali:")
        jvm_label.setObjectName("SettingTitle")
        card_layout.addWidget(jvm_label)

        self.jvm_input = QLineEdit(self.settings.get("jvm_args", ""))
        self.jvm_input.setPlaceholderText("Es. -XX:+UseG1GC")
        self.jvm_input.textChanged.connect(self.on_jvm_args_changed)
        card_layout.addWidget(self.jvm_input)

        card_layout.addWidget(self.create_separator())

        # 4. Cartella Minecraft
        dir_label = QLabel("Cartella Dati Minecraft:")
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
        """Schermata console per log."""
        layout = QVBoxLayout(self.log_tab)
        layout.setContentsMargins(28, 24, 28, 24)
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
        line.setStyleSheet("background-color: #232631; max-height: 1px;")
        return line

    def apply_modern_stylesheet(self):
        """Applica il design system dark gaming moderno con bugfix grafici."""
        down_arrow = resource_path("assets/chevron_down.svg").replace("\\", "/")
        up_arrow = resource_path("assets/chevron_up.svg").replace("\\", "/")
        stylesheet = """
            QWidget {
                background-color: #0f1115;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            QMainWindow {
                background-color: #0f1115;
            }
            /* FIX CRITICO: I QLabel devono avere sfondo trasparente per evitare riquadri neri */
            QLabel {
                background-color: transparent;
                color: #f1f5f9;
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
                border-radius: 14px;
                padding: 0;
            }
            QFrame#ModernCard {
                background-color: #16181f;
                border: 1px solid #232631;
                border-radius: 12px;
            }
            QLabel#SectionHeader {
                font-size: 11pt;
                font-weight: 700;
                color: #f8fafc;
            }
            QLabel#PageHeader {
                font-size: 16pt;
                font-weight: 800;
                color: #ffffff;
                margin-bottom: 5px;
            }
            QComboBox {
                background-color: #1f232d;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 3px 26px 3px 10px;
                font-size: 9pt;
                font-weight: 600;
            }
            QComboBox::drop-down {
                width: 22px;
                border: none;
                background-color: transparent;
            }
            QComboBox::down-arrow {
                image: url(__DOWN_ARROW__);
                width: 10px;
                height: 6px;
            }
            QComboBox:focus {
                border: 1px solid #3b82f6;
            }
            QComboBox QAbstractItemView {
                background-color: #1f232d;
                color: #ffffff;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                border: 1px solid #334155;
                padding: 4px;
                outline: none;
                min-width: 260px;
                show-decoration-selected: 1;
            }
            QComboBox QAbstractItemView::item {
                min-height: 30px;
                padding: 5px 8px;
            }
            QSpinBox {
                padding: 5px 30px 5px 10px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                border: none;
                background-color: transparent;
            }
            QSpinBox::up-button {
                subcontrol-position: top right;
            }
            QSpinBox::down-button {
                subcontrol-position: bottom right;
            }
            QSpinBox::up-arrow {
                image: url(__UP_ARROW__);
                width: 10px;
                height: 6px;
            }
            QSpinBox::down-arrow {
                image: url(__DOWN_ARROW__);
                width: 10px;
                height: 6px;
            }
            QScrollArea {
                background-color: #0f1115;
                border: none;
            }
            QScrollBar:vertical {
                background: #0f1115;
                width: 10px;
                margin: 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 36px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #475569;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QLabel#StatusPill {
                font-size: 9pt;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 6px;
                background-color: #1f232d;
            }
            QCheckBox {
                background-color: transparent;
                color: #94a3b8;
                font-size: 9pt;
                spacing: 8px;
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
                font-size: 9pt;
                font-weight: 600;
                border: 1px solid #334155;
                border-radius: 7px;
                padding: 6px 12px;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #2a303e;
                color: #ffffff;
                border-color: #475569;
            }
            QPushButton#PrimaryActionButton {
                background-color: #3b82f6;
                color: white;
                font-size: 9pt;
                font-weight: 700;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
            }
            QPushButton#PrimaryActionButton:hover {
                background-color: #2563eb;
            }
            QPushButton#DeleteButton {
                background-color: #7f1d1d;
                color: #fca5a5;
                font-size: 9pt;
                font-weight: 600;
                border: 1px solid #991b1b;
                border-radius: 7px;
                padding: 7px 14px;
            }
            QPushButton#DeleteButton:hover {
                background-color: #991b1b;
                color: white;
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
            QListWidget#InstancesListWidget {
                background-color: #16181f;
                border: 1px solid #232631;
                border-radius: 10px;
                padding: 6px;
                color: #ffffff;
            }
            QListWidget#InstancesListWidget::item {
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget#InstancesListWidget::item:hover {
                background-color: #1f232d;
            }
            QListWidget#InstancesListWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
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
        """
        self.setStyleSheet(
            stylesheet.replace("__DOWN_ARROW__", down_arrow).replace("__UP_ARROW__", up_arrow)
        )

    # --- GESTIONE ISTANZE ---

    def refresh_instances_selector(self):
        """Aggiorna il selettore istanze nella Home e la lista nella tab Istanze."""
        self.instance_combo.blockSignals(True)
        self.instance_combo.clear()

        instances = self.instance_manager.get_instances()
        current = self.instance_manager.get_current_instance()
        curr_id = current.get("id") if current else None

        sel_idx = 0
        idx = 0
        for inst_id, inst in instances.items():
            name = inst.get("name", "Istanza")
            ver = inst.get("version", "Vanilla")
            ram = inst.get("ram_gb", 4)
            self.instance_combo.addItem(f"{name}  [{ver} - {ram}GB]", inst_id)
            if inst_id == curr_id:
                sel_idx = idx
            idx += 1

        if self.instance_combo.count() > 0:
            self.instance_combo.setCurrentIndex(sel_idx)

        self.instance_combo.blockSignals(False)
        self.update_active_instance_ui()
        self.refresh_instances_page_list()

    def on_instance_selected(self, index):
        inst_id = self.instance_combo.currentData()
        if inst_id:
            self.instance_manager.set_current_instance(inst_id)
            self.update_active_instance_ui()

    def update_active_instance_ui(self):
        """Allinea la versione e le info UI con l'istanza attualmente attiva."""
        inst = self.instance_manager.get_current_instance()
        if not inst:
            return

        inst_ver = inst.get("version", "")
        self.instance_info_badge.setText(f"Istanza: {inst.get('name')}  •  Versione: {inst_ver}  •  RAM: {inst.get('ram_gb', 4)} GB")

        # Seleziona la versione dell'istanza nel selettore versioni se diversa
        if inst_ver and inst_ver != self.selected_version:
            self.selected_version = inst_ver
            self.populate_version_dropdown()
        else:
            self.update_version_status_ui()

    def open_instances_dialog(self):
        dlg = InstanceManagerDialog(self, self.instance_manager, self.all_versions)
        dlg.exec()
        self.refresh_instances_selector()

    def create_new_instance_dialog(self):
        dlg = InstanceEditDialog(self, self.instance_manager, self.all_versions)
        if dlg.exec() == InstanceEditDialog.DialogCode.Accepted:
            self.refresh_instances_selector()

    def open_active_instance_folder(self):
        inst = self.instance_manager.get_current_instance()
        if not inst:
            return
        path = inst.get("path")
        if path and os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])

    def refresh_instances_page_list(self):
        """Aggiorna la lista nella tab Istanze."""
        self.instances_page_list.clear()
        instances = self.instance_manager.get_instances()
        current = self.instance_manager.get_current_instance()
        curr_id = current.get("id") if current else None

        for inst_id, inst in instances.items():
            name = inst.get("name", "Istanza")
            ver = inst.get("version", "Vanilla")
            is_active = (inst_id == curr_id)
            tag = "  [ATTIVA]" if is_active else ""
            item = QListWidgetItem(f"📦  {name}  •  {ver}{tag}")
            item.setData(Qt.ItemDataRole.UserRole, inst_id)
            self.instances_page_list.addItem(item)
            if is_active:
                self.instances_page_list.setCurrentItem(item)

        self.on_instance_page_selection_changed()

    def on_instance_page_selection_changed(self):
        curr_item = self.instances_page_list.currentItem()
        if not curr_item:
            self.inst_page_title.setText("Nessuna istanza selezionata")
            self.inst_page_ver.setText("Versione: -")
            self.inst_page_ram.setText("RAM: -")
            self.inst_page_path.setText("Percorso: -")
            self.btn_page_activate.setEnabled(False)
            self.btn_page_edit.setEnabled(False)
            self.btn_page_folder.setEnabled(False)
            self.btn_page_delete.setEnabled(False)
            return

        inst_id = curr_item.data(Qt.ItemDataRole.UserRole)
        inst = self.instance_manager.get_instances().get(inst_id)
        if not inst:
            return

        self.inst_page_title.setText(inst.get("name", "Istanza"))
        self.inst_page_ver.setText(f"Versione Minecraft: <b>{inst.get('version', '')}</b>")
        self.inst_page_ram.setText(f"Memoria RAM: <b>{inst.get('ram_gb', 4)} GB</b>")
        self.inst_page_path.setText(f"Percorso: {inst.get('path', '')}")

        self.btn_page_activate.setEnabled(True)
        self.btn_page_edit.setEnabled(True)
        self.btn_page_folder.setEnabled(True)
        self.btn_page_delete.setEnabled(True)

    def activate_selected_instance_from_page(self):
        curr_item = self.instances_page_list.currentItem()
        if curr_item:
            inst_id = curr_item.data(Qt.ItemDataRole.UserRole)
            self.instance_manager.set_current_instance(inst_id)
            self.refresh_instances_selector()

    def edit_selected_instance_from_page(self):
        curr_item = self.instances_page_list.currentItem()
        if curr_item:
            inst_id = curr_item.data(Qt.ItemDataRole.UserRole)
            inst = self.instance_manager.get_instances().get(inst_id)
            if inst:
                dlg = InstanceEditDialog(self, self.instance_manager, self.all_versions, instance=inst)
                if dlg.exec() == InstanceEditDialog.DialogCode.Accepted:
                    self.refresh_instances_selector()

    def open_selected_instance_folder_from_page(self):
        curr_item = self.instances_page_list.currentItem()
        if curr_item:
            inst_id = curr_item.data(Qt.ItemDataRole.UserRole)
            path = self.instance_manager.get_instance_directory(inst_id)
            if path and os.path.exists(path):
                if sys.platform == 'win32':
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', path])
                else:
                    subprocess.Popen(['xdg-open', path])

    def delete_selected_instance_from_page(self):
        curr_item = self.instances_page_list.currentItem()
        if not curr_item:
            return
        inst_id = curr_item.data(Qt.ItemDataRole.UserRole)
        inst = self.instance_manager.get_instances().get(inst_id)
        if not inst:
            return

        if len(self.instance_manager.get_instances()) <= 1:
            QMessageBox.warning(self, "Attenzione", "Non puoi eliminare l'unica istanza rimasta.")
            return

        reply = QMessageBox.question(
            self, "Elimina Istanza",
            f"Sei sicuro di voler eliminare l'istanza '{inst.get('name')}'?\nI mondi e salvataggi in questa istanza verranno rimossi.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.instance_manager.delete_instance(inst_id, delete_files=True)
            self.refresh_instances_selector()

    # --- VERSIONI MINECRAFT ---

    def refresh_version_list(self, force_network=False, initial=False):
        """Recupera la lista delle versioni (da cache o rete) e le versioni installate."""
        self.action_status_label.setText("Caricamento elenco versioni...")
        self.refresh_ver_btn.setEnabled(False)

        def task():
            cached_data = None
            if not force_network and os.path.exists(self.versions_cache_file):
                try:
                    with open(self.versions_cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list) and len(data) > 0:
                            cached_data = data
                except Exception:
                    pass

            versions = []
            if cached_data:
                versions = cached_data
                self.worker.log_message.emit(f"Caricate {len(versions)} versioni dalla cache locale.", "INFO")
            else:
                try:
                    self.worker.log_message.emit("Connessione a Mojang per recuperare l'elenco versioni...", "INFO")
                    raw_data = minecraft_launcher_lib.utils.get_version_list()
                    if isinstance(raw_data, list):
                        versions = raw_data
                    elif isinstance(raw_data, dict) and "versions" in raw_data:
                        versions = raw_data["versions"]
                    elif isinstance(raw_data, dict):
                        versions = list(raw_data.values())

                    if versions:
                        self.worker.log_message.emit(f"Scaricato elenco con {len(versions)} versioni da Mojang.", "SUCCESS")
                        try:
                            with open(self.versions_cache_file, "w", encoding="utf-8") as f:
                                json.dump(versions, f)
                        except Exception:
                            pass
                except Exception as e:
                    self.worker.log_message.emit(f"Impossibile contattare Mojang: {e}", "ERROR")

            if not versions:
                if cached_data:
                    versions = cached_data
                else:
                    self.worker.log_message.emit("Utilizzo elenco versioni di fallback.", "INFO")
                    versions = DEFAULT_POPULAR_VERSIONS

            latest_release = ""
            for v in versions:
                if isinstance(v, dict) and v.get("type") == "release":
                    latest_release = v.get("id")
                    break

            self.worker.versions_loaded.emit(versions, latest_release)

        self.run_task(task, on_finish=lambda: self.refresh_ver_btn.setEnabled(True))

    @pyqtSlot(list, str)
    def on_versions_loaded(self, versions, latest_release):
        self.all_versions = versions
        if self.first_run_wizard is not None:
            self.first_run_wizard.set_available_versions(versions, preferred_version=latest_release)
        if self.first_run and latest_release:
            self.selected_version = latest_release
            active_instance = self.instance_manager.get_current_instance()
            if active_instance and self.first_run_wizard is None:
                self.instance_manager.update_instance(active_instance["id"], version=latest_release)
            if self.first_run_wizard is None:
                self.settings["last_version"] = latest_release
                self.save_settings()
                self.first_run = False
        self.update_installed_versions_cache()
        self.populate_version_dropdown()
        self.action_status_label.setText("Pronto per il lancio")

    def update_installed_versions_cache(self):
        """Rileva quali versioni sono attualmente installate nella cartella locale."""
        try:
            installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_directory)
            self.installed_version_ids = {v["id"] for v in installed if isinstance(v, dict) and "id" in v}
        except Exception:
            self.installed_version_ids = set()

    def populate_version_dropdown(self):
        """Riempie il ComboBox con le versioni. Al primo avvio seleziona SEMPRE l'ultima release ufficiale."""
        self.version_combo.blockSignals(True)
        self.version_combo.clear()

        show_all = self.snapshot_checkbox.isChecked()

        # Identifica l'ultima versione ufficiale release
        latest_official = self.get_latest_official_release()
        target_version = self.selected_version or latest_official

        idx_to_select = 0
        added_count = 0

        for v in self.all_versions:
            if isinstance(v, dict):
                v_id = v.get("id", "")
                v_type = v.get("type", "release")
            else:
                v_id = str(v)
                v_type = "release"

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

            # Aggiorna anche l'istanza attiva se l'utente cambia versione nella Home
            inst = self.instance_manager.get_current_instance()
            if inst and inst.get("version") != v_id:
                self.instance_manager.update_instance(inst["id"], version=v_id)
                self.update_active_instance_ui()

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
        active_inst = self.instance_manager.get_current_instance()
        inst_label = f" ({active_inst.get('name')})" if active_inst else ""

        if is_installed:
            self.version_status_pill.setText(f"✓ {self.selected_version} è installata e pronta")
            self.version_status_pill.setStyleSheet("background-color: #064e3b; color: #34d399; border: 1px solid #059669;")
            self.main_action_btn.setText(f"▶  GIOCA{inst_label}")
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

    # --- INSTALLAZIONE E LANCIO GIOCO ---

    def handle_main_action(self):
        if not self.selected_version:
            return

        is_installed = self.selected_version in self.installed_version_ids
        if is_installed:
            self.launch_game()
        else:
            self.install_selected_version()

    def install_selected_version(self):
        """Scarica e installa la versione Minecraft selezionata."""
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
        """Avvia Minecraft con la cartella isolata e le impostazioni dell'istanza attiva."""
        if self.is_task_running():
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

        active_inst = self.instance_manager.get_current_instance()
        if not active_inst:
            CustomMessageBox("Errore", "Nessuna istanza configurata.", "error", self).exec()
            return

        instance_dir = self.instance_manager.get_instance_directory(active_inst["id"])
        account_opts = self.account_manager.get_launch_options()

        # RAM specifica dell'istanza o impostazione globale
        ram_gb = active_inst.get("ram_gb") or self.settings.get("ram_gb", 4)

        jvm_args = [f"-Xmx{ram_gb}G", f"-Xms{ram_gb}G"]

        # Unione argomenti JVM globali e dell'istanza
        global_jvm = self.settings.get("jvm_args", "").strip()
        inst_jvm = active_inst.get("jvm_args", "").strip()

        if global_jvm:
            jvm_args.extend(global_jvm.split())
        if inst_jvm:
            jvm_args.extend(inst_jvm.split())

        options = {
            "username": account_opts["username"],
            "uuid": account_opts["uuid"],
            "token": account_opts["token"],
            "jvmArguments": jvm_args,
            "launcherName": self.launcher_name,
            "launcherVersion": self.launcher_version,
            "gameDirectory": instance_dir  # ISOLAMENTO ISTANZA: salvataggi, mondi e opzioni separati!
        }

        custom_java = self.settings.get("custom_java", "").strip()
        if custom_java and os.path.exists(custom_java):
            options["executablePath"] = custom_java

        version_id = active_inst.get("version") or self.selected_version
        self.log(f"Lancio istanza '{active_inst.get('name')}' con Minecraft {version_id} (RAM: {ram_gb}GB)...", "INFO")
        self.log(f"Cartella di gioco isolata: {instance_dir}", "INFO")

        try:
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                version_id,
                self.minecraft_directory,
                options
            )

            self.log("Comando di avvio generato con successo. Esecuzione del processo...", "SUCCESS")
            self.action_status_label.setText(f"{active_inst.get('name')} in esecuzione")
            self.main_action_btn.setEnabled(False)
            self.main_action_btn.setText("■ IN ESECUZIONE")

            self.instance_manager.mark_played(active_inst["id"])

            # Passa alla tab Console
            self.nav_buttons[4].setChecked(True)
            self.pages.setCurrentIndex(4)

            subprocess_args = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
                'text': True,
                'encoding': 'utf-8',
                'errors': 'ignore',
                'cwd': instance_dir
            }
            if sys.platform == "win32":
                subprocess_args['creationflags'] = subprocess.CREATE_NO_WINDOW

            self.game_process = subprocess.Popen(minecraft_command, **subprocess_args)

            threading.Thread(target=self.monitor_game_process, daemon=True).start()
            threading.Thread(target=self.read_game_output, args=(self.game_process.stdout,), daemon=True).start()

        except Exception as e:
            self.log(f"Errore irreversibile durante l'avvio: {e}", "ERROR")
            CustomMessageBox("Errore di Avvio", f"Impossibile avviare l'istanza '{active_inst.get('name')}':\n{e}", "error", self).exec()
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
        self.nav_buttons[0].setChecked(True)
        self.pages.setCurrentIndex(0)

    # --- ACCOUNT & STARTUP LOGIN CHECK ---

    def check_account_on_startup(self):
        """Apre la finestra di login all'avvio se non è configurato alcun account."""
        if not self.account_manager.current_account:
            self.show_account_dialog()

    def show_account_dialog(self):
        dialog = LoginDialog(
            self,
            self.account_manager,
            client_id=self.AZURE_CLIENT_ID,
            client_secret=self.AZURE_CLIENT_SECRET,
            initial_mode=self.settings.get("profile_mode", ""),
        )
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

    # --- IMPOSTAZIONI ---

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
        path = self.minecraft_directory
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])

    # --- LOG & THREAD MANAGEMENT ---

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

    def is_task_running(self):
        """Verifica in sicurezza se un task in background è in esecuzione."""
        if self.worker_thread is not None:
            try:
                return self.worker_thread.isRunning()
            except RuntimeError:
                self.worker_thread = None
                self.worker = None
        return False

    def run_task(self, target, *args, on_finish=None, **kwargs):
        """Avvia un task asincrono con gestione thread e memoria pulita."""
        if self.is_task_running():
            self.log("Un'operazione è già in corso.", "ERROR")
            return

        thread = QThread(self)
        worker = Worker(target, *args, **kwargs)
        worker.moveToThread(thread)

        self.worker_thread = thread
        self.worker = worker

        def cleanup():
            if self.worker_thread is thread:
                self.worker_thread = None
                self.worker = None

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(cleanup)

        worker.progress.connect(self.update_progress)
        worker.status_update.connect(self.update_status)
        worker.log_message.connect(self.log)
        worker.versions_loaded.connect(self.on_versions_loaded)

        if on_finish:
            worker.finished.connect(on_finish)

        thread.started.connect(worker.run)
        thread.start()

    def closeEvent(self, event):
        """Chiusura controllata dei processi attivi."""
        if self.game_process:
            try:
                self.game_process.terminate()
                self.game_process.wait(timeout=3)
            except Exception:
                pass

        if self.is_task_running():
            try:
                self.worker_thread.quit()
                self.worker_thread.wait(2000)
            except Exception:
                pass

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = MinecraftLauncher()
    launcher.show()
    sys.exit(app.exec())