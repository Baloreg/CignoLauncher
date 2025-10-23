import sys
import os
import json
import hashlib
import requests
import subprocess
import threading
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

import minecraft_launcher_lib

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QProgressBar, QStackedWidget, QPlainTextEdit,
                             QSpinBox, QFrame, QGroupBox, QMessageBox, QSpacerItem, QSizePolicy,
                             QListWidget, QListWidgetItem, QButtonGroup, QTextBrowser)
from PyQt6.QtGui import QIcon, QFont, QTextCursor, QPixmap, QMovie
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt, pyqtSlot, QEvent, QSize

# Importa le classi convertite
from account_manager import AccountManager
from login_dialog_pyqt import LoginDialog, CustomMessageBox
from utils import ImageDownloader

# Monkey-patch per nascondere le finestre della console su Windows
# durante l'installazione di Forge.
if sys.platform == 'win32':
    import subprocess
    # Conserva una copia dell'originale, per sicurezza
    _original_Popen = subprocess.Popen
    
    # Definisci una nuova funzione Popen che aggiunge la flag CREATE_NO_WINDOW
    def _new_Popen(*args, **kwargs):
        # Aggiungi la flag se non è già presente
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        # Chiama la funzione Popen originale con gli argomenti modificati
        return _original_Popen(*args, **kwargs)

    # Sostituisci la Popen di sistema con la nostra versione modificata
    subprocess.Popen = _new_Popen

# Funzione per gestire i percorsi degli asset
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Classe Worker per task in background
class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str, str)
    log_message = pyqtSignal(str, str)
    show_dialog = pyqtSignal(str, str, str)
    update_check_complete = pyqtSignal(list)
    news_ready = pyqtSignal(str)
    news_animation_ready = pyqtSignal(str)
    
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.log_message.emit(f"Errore critico nel thread: {e}", "ERROR")
            self.status_update.emit(f"Errore: {e}", "ERROR")
        finally:
            self.finished.emit()

# Classe evento per il logging
class LogEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self, message):
        super().__init__(self.EVENT_TYPE)
        self.message = message

# Evento per la chiusura del gioco
class GameClosedEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self):
        super().__init__(self.EVENT_TYPE)

class MinecraftLauncher(QMainWindow):
    
    def __init__(self):
        super().__init__()
        
        self.launcher_version = "1.0.1"
        self.minecraft_version = "1.20.1"
        self.forge_version = "1.20.1-47.4.6"
        self.setup_paths()
        self.account_manager = AccountManager(self.launcher_directory)
        self.game_process = None
        self.AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "your-client-id")
        self.AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "your-secret-value")
        self.install_state_file = os.path.join(self.launcher_directory, "install_state.json")
        self.setupUi()
        self.apply_stylesheet()
        self.worker_thread = None
        self.worker = None
        self.check_installation_status()
        self.check_updates_on_startup()

    def setup_paths(self):
        if sys.platform == "win32":
            appdata = os.getenv('APPDATA')
            self.launcher_directory = os.path.join(appdata, "CignoLauncher")
        else:
            home = os.path.expanduser("~")
            self.launcher_directory = os.path.join(home, ".cignolauncher")
        
        self.minecraft_directory = os.path.join(self.launcher_directory, "minecraft")
        self.modpack_folder = os.path.join(self.launcher_directory, "mods")
        self.config_folder = os.path.join(self.launcher_directory, "config")
        self.resourcepacks_folder = os.path.join(self.launcher_directory, "resourcepacks")
        self.shaderpacks_folder = os.path.join(self.launcher_directory, "shaderpacks")
        self.saves_folder = os.path.join(self.launcher_directory, "saves")
        self.heads_folder = os.path.join(self.launcher_directory, "heads")
        self.news_assets_folder = os.path.join(self.launcher_directory, "news_assets")

        for folder in [self.launcher_directory, self.minecraft_directory, self.modpack_folder, self.config_folder, self.resourcepacks_folder, self.shaderpacks_folder, self.saves_folder, self.heads_folder, self.news_assets_folder]:
            Path(folder).mkdir(parents=True, exist_ok=True)
            
        self.modpack_url = "https://raw.githubusercontent.com/Baloreg/Cignopack/main/manifest.json"
        self.launcher_update_url = "https://raw.githubusercontent.com/Baloreg/Cignopack/main/launcher_version.json"
        self.launcher_download_url = "https://github.com/Baloreg/Cignopack/releases/latest/download/CignoLauncher.exe"
        self.news_url = "https://raw.githubusercontent.com/Baloreg/Cignopack/main/news.json"

    def setupUi(self):
        self.setWindowTitle("CignoLauncher")
        self.setFixedSize(800, 600)
        self.setWindowIcon(QIcon(resource_path("assets/window_icon.ico")))
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar_widget = QWidget()
        sidebar_widget.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(5, 10, 5, 5)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        sidebar_widget.setFixedWidth(65)

        self.pages = QStackedWidget()

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        btn_home = QPushButton(QIcon(resource_path("assets/home_icon.png")), "")
        btn_account = QPushButton(QIcon(resource_path("assets/account_icon.png")), "")
        btn_settings = QPushButton(QIcon(resource_path("assets/settings_icon.png")), "")
        btn_log = QPushButton(QIcon(resource_path("assets/log_icon.png")), "")
        
        buttons = [btn_home, btn_account, btn_settings, btn_log]

        for i, btn in enumerate(buttons):
            btn.setCheckable(True)
            btn.setIconSize(QSize(32, 32))
            sidebar_layout.addWidget(btn)
            self.button_group.addButton(btn, i)

        self.button_group.idClicked.connect(self.pages.setCurrentIndex)
        
        main_layout.addWidget(sidebar_widget)
        main_layout.addWidget(self.pages, 1)

        self.home_tab, self.account_tab, self.settings_tab, self.log_tab = QWidget(), QWidget(), QWidget(), QWidget()

        self.setup_home_tab()
        self.setup_account_tab()
        self.setup_settings_tab()
        self.setup_log_tab()
        
        self.pages.addWidget(self.home_tab)
        self.pages.addWidget(self.account_tab)
        self.pages.addWidget(self.settings_tab)
        self.pages.addWidget(self.log_tab)
        
        btn_home.setChecked(True)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget { background-color: #2d2d2d; color: #ffffff; font-family: 'Segoe UI'; }
            QMainWindow { border: 1px solid #404040; }
            QWidget#sidebar { background-color: #1e1e1e; }
            QWidget#sidebar QPushButton { height: 50px; border: none; border-radius: 8px; background-color: transparent; }
            QWidget#sidebar QPushButton:hover { background-color: #3d3d3d; }
            QWidget#sidebar QPushButton:checked { background-color: #0078d4; }
            QStackedWidget { border-left: 1px solid #404040; }
            QLabel#TitleLabel { font-size: 32pt; font-weight: bold; color: #0078d4; }
            QLabel#StatusLabel, QLabel#SubtitleLabel { color: #b0b0b0; font-size: 9pt; }
            QPushButton {
                background-color: #0078d4; color: white; font-weight: bold;
                padding: 12px 25px; border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:disabled { background-color: #3d3d3d; color: #b0b0b0; }
            QProgressBar { border: 1px solid #404040; border-radius: 4px; text-align: center; height: 10px; }
            QProgressBar::chunk { background-color: #0078d4; border-radius: 4px; }
            QPlainTextEdit, QGroupBox { border: 1px solid #404040; border-radius: 4px; }
            QGroupBox { font-size: 11pt; font-weight: bold; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 10px; }

            /* --- Stile per il riquadro News --- */
            QTextBrowser {
                background-color: #1e1e1e;
                border: none;
                padding: 5px;
            }               

            /* --- STILE MIGLIORATO PER QSPINBOX --- */
            QSpinBox {
                background-color: #1e1e1e;
                border: 1px solid #404040;
                border-radius: 4px;
                color: white;
                padding: 5px;
                font-size: 10pt;
            }
            QSpinBox:focus {
                border: 1px solid #0078d4;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border;
                width: 18px;
                background-color: #3d3d3d;
                border: none;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4f4f4f;
            }
            QSpinBox::up-button {
                subcontrol-position: top right;
                margin-top: 1px;
                margin-right: 1px;
                border-top-right-radius: 3px;
            }
            QSpinBox::down-button {
                subcontrol-position: bottom right;
                margin-bottom: 1px;
                margin-right: 1px;
                border-bottom-right-radius: 3px;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 10px;
                height: 10px;
            }
            /* --- FINE STILE QSPINBOX --- */
        """)

    def setup_home_tab(self):
        layout = QVBoxLayout(self.home_tab)
        layout.setContentsMargins(30, 20, 30, 20)
        # Crea un QLabel per contenere il logo
        logo_label = QLabel()
        # Carica l'immagine del logo dal percorso delle risorse
        pixmap = QPixmap(resource_path("assets/logo.png")) 

        # Imposta il pixmap sulla label, scalando l'immagine a una larghezza di 400px
        # Puoi cambiare 400 con la dimensione che preferisci per il tuo logo
        logo_label.setPixmap(pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation))

        # Allinea il logo al centro
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel(f"Minecraft {self.minecraft_version} • Forge {self.forge_version.split('-')[-1]}")
        subtitle_label.setObjectName("SubtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- INIZIO MODIFICA LAYOUT ---

        # 1. Contenitore per la parte superiore (logo e sottotitolo)
        # Raggruppiamo il logo e il sottotitolo in un unico widget.
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0) # Nessun margine interno
        top_layout.addWidget(logo_label)
        top_layout.addWidget(subtitle_label)

        # 2. Aggiungiamo il contenitore superiore al layout principale.
        # Ora il logo è ancorato in alto.
        layout.addWidget(top_container)

        # 3. Creiamo lo spazio flessibile per le future news.
        # addStretch() crea uno spazio vuoto che si espande per riempire l'area disponibile,
        # spingendo tutto ciò che viene dopo verso il basso.
        # --- Inizio Sezione News ---
        news_group_box = QGroupBox("News & Aggiornamenti")
        news_layout = QVBoxLayout(news_group_box)
        news_layout.setSpacing(10) # Aggiunge un po' di spazio tra gli elementi

        # 1. Label per la GIF animata (inizialmente nascosta)
        self.news_gif_label = QLabel()
        self.news_gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.news_gif_label.hide() # Nascondiamo la label finché non abbiamo la GIF
        news_layout.addWidget(self.news_gif_label)

        # 2. Riquadro per le notizie testuali
        self.news_browser = QTextBrowser()
        self.news_browser.setReadOnly(True)
        self.news_browser.setOpenExternalLinks(True)
        self.news_browser.setHtml("<p style='color: #b0b0b0;'>Caricamento notizie...</p>")
        news_layout.addWidget(self.news_browser)

        layout.addWidget(news_group_box)
        # --- Fine Sezione News ---

        # --- FINE MODIFICA LAYOUT ---

        # La parte inferiore con i pulsanti rimane invariata
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0,0,0,0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.status_label = QLabel("Pronto per il lancio")
        self.status_label.setObjectName("StatusLabel")
        self.install_btn = QPushButton("Installa/Aggiorna")
        self.install_btn.clicked.connect(self.start_installation)
        self.play_btn = QPushButton("GIOCA")
        self.play_btn.clicked.connect(self.start_game)
        self.play_btn.setEnabled(False)
        button_layout = QHBoxLayout()
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        button_layout.addWidget(self.install_btn)
        button_layout.addWidget(self.play_btn)
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addLayout(button_layout)
        layout.addWidget(bottom_container)
    
    def setup_account_tab(self):
        layout = QVBoxLayout(self.account_tab)
        layout.setContentsMargins(30, 40, 30, 40)
        self.account_frame = QFrame()
        self.account_frame_layout = QVBoxLayout(self.account_frame)
        self.account_frame_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        group_box = QGroupBox("Account Corrente")
        group_layout = QVBoxLayout(group_box)
        group_layout.addWidget(self.account_frame)
        manage_btn = QPushButton("Gestisci Account")
        manage_btn.clicked.connect(self.show_account_dialog)
        layout.addWidget(group_box)
        layout.addWidget(manage_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.update_account_display()

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(30, 40, 30, 40)
        group_box = QGroupBox("Impostazioni di Gioco")
        group_layout = QVBoxLayout(group_box)
        
        ram_widget = QWidget()
        ram_layout = QVBoxLayout(ram_widget)
        ram_layout.setContentsMargins(0, 0, 0, 0)
        ram_layout.setSpacing(5)

        ram_label = QLabel("RAM Allocata (GB)")
        self.ram_spinbox = QSpinBox()
        self.ram_spinbox.setRange(2, 16)
        self.ram_spinbox.setValue(4)
        self.ram_spinbox.setFixedWidth(120)
        
        ram_layout.addWidget(ram_label)
        ram_layout.addWidget(self.ram_spinbox)
        
        ram_info = QLabel("La RAM consigliata per il modpack è tra 4 e 8 GB.")
        ram_info.setObjectName("StatusLabel")
        
        group_layout.addWidget(ram_widget, alignment=Qt.AlignmentFlag.AlignLeft)
        group_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))
        group_layout.addWidget(ram_info)
        
        layout.addWidget(group_box)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def setup_log_tab(self):
        layout = QVBoxLayout(self.log_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        log_label = QLabel("Console")
        log_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(log_label)
        layout.addWidget(self.log_text)

    def _perform_startup_tasks(self):
        """
        Esegue tutte le operazioni di avvio (controllo aggiornamenti e news)
        in un unico thread in background.
        """
        # ... (La parte del controllo aggiornamenti rimane uguale) ...
        try:
            manifest = self.get_modpack_manifest()
            if not manifest:
                self.worker.log_message.emit("Impossibile controllare aggiornamenti.", "ERROR")
            else:
                files_to_update = self.check_modpack_needs_update(manifest)
                self.worker.update_check_complete.emit(files_to_update)
        except Exception as e:
            self.worker.log_message.emit(f"Errore controllo aggiornamenti: {e}", "ERROR")

        # --- LOGICA NEWS AGGIORNATA ---
        try:
            response = requests.get(self.news_url, timeout=10)
            response.raise_for_status()
            news_data = response.json()

            # Processa la GIF animata (se presente nel primo articolo)
            if news_data and 'image_url' in news_data[0]:
                item = news_data[0]
                image_url = news_data[0]['image_url']
                expected_hash = item.get('sha256') # Ottieni l'hash dal JSON
                file_extension = os.path.splitext(image_url)[1]
                hashed_name = hashlib.md5(image_url.encode()).hexdigest()
                local_path = os.path.join(self.news_assets_folder, f"{hashed_name}{file_extension}")

                needs_download = True

                if os.path.exists(local_path) and expected_hash and self.calculate_sha256(local_path) == expected_hash:
                    needs_download = False
                
                if needs_download:
                    try:
                        # Se il file esiste ma ha l'hash sbagliato, lo sovrascriviamo
                        self.worker.log_message.emit(f"Download nuova versione di: {os.path.basename(image_url)}", "INFO")
                        img_response = requests.get(image_url, timeout=15)
                        img_response.raise_for_status()
                        with open(local_path, 'wb') as f: f.write(img_response.content)
                    except Exception as img_e:
                        self.worker.log_message.emit(f"Errore scaricando immagine news: {img_e}", "ERROR")

                self.worker.news_animation_ready.emit(local_path)

            html = """<style>
                h3 { color: #0078d4; margin-bottom: 5px; }
                p { color: #ffffff; margin-top: 0; padding-bottom: 10px; }
                hr { border: 1px solid #404040; margin: 10px 0;}
            </style>"""
            
            start_index = 1 if (news_data and 'image_url' in news_data[0]) else 0
        
            for i, item in enumerate(news_data[start_index:]):
                html += f"<h3>{item['title']}</h3>"
                html += f"<p>{item['content']}</p>"
                if i < len(news_data[start_index:]) - 1:
                    html += "<hr>"

            self.worker.news_ready.emit(html)
        except Exception as e:
            self.worker.log_message.emit(f"Errore nel caricamento delle news: {e}", "ERROR")
            self.worker.news_ready.emit("")
    
    @pyqtSlot(str)
    def set_news_animation(self, gif_path):
        """Imposta e avvia la QMovie sulla label dedicata."""
        if not os.path.exists(gif_path): return
        
        # Crea l'oggetto QMovie
        self.news_movie = QMovie(gif_path)
        self.news_gif_label.setMovie(self.news_movie)
        
        # --- INIZIO CORREZIONE PER ZeroDivisionError ---
        # Otteniamo la larghezza originale del frame
        original_width = self.news_movie.frameRect().width()

        # Eseguiamo il ridimensionamento SOLO SE la larghezza è valida (maggiore di 0)
        # per evitare la divisione per zero.
        if original_width > 0:
            original_height = self.news_movie.frameRect().height()
            # Calcoliamo la nuova altezza mantenendo le proporzioni
            new_height = int(350 * original_height / original_width)
            self.news_movie.setScaledSize(QSize(350, new_height))
        # Se la larghezza è 0 (perché il file non è ancora caricato), non facciamo nulla.
        # La QMovie userà la sua dimensione predefinita una volta caricata.
        # --- FINE CORREZIONE ---

        # Avvia l'animazione
        self.news_movie.start()
        self.news_gif_label.show()
    
    @pyqtSlot(str)
    def update_news_display(self, html_content):
        """Aggiorna il riquadro delle news con il contenuto HTML."""
        if html_content:
            self.news_browser.setHtml(html_content)
        else:
            self.news_browser.setHtml("<p style='color: #ef5350;'>Impossibile caricare le notizie.</p>")

    @pyqtSlot(str, str)
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {"INFO": "#4fc3f7", "ERROR": "#ef5350", "SUCCESS": "#66bb6a", "GAME": "#ffa726"}
        color = color_map.get(level, "#ffffff")
        formatted_message = f'<span style="color: {color};">[{timestamp}] [{level}] {message}</span>'
        self.log_text.appendHtml(formatted_message)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
    
    def update_account_display(self):
        # Pulisci il frame precedente
        while self.account_frame_layout.count():
            item = self.account_frame_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if self.account_manager.current_account:
            account = self.account_manager.current_account
            
            # Layout principale per l'account
            account_widget = QWidget()
            h_layout = QHBoxLayout(account_widget)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(15)

            # Label per la testa
            head_label = QLabel()
            head_label.setFixedSize(48, 48)
            head_label.setStyleSheet("border-radius: 5px;") # Arrotonda gli angoli

            # Layout per il testo (username, tipo)
            v_layout = QVBoxLayout()
            v_layout.setSpacing(0)
            v_layout.setContentsMargins(0, 0, 0, 0)
            
            name_label = QLabel(f"{account['username']}")
            name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            
            type_label = QLabel("Account Microsoft" if account['type'] == 'microsoft' else "Account Offline")
            color = "#4caf50" if account['type'] == 'microsoft' else "#b0b0b0"
            type_label.setStyleSheet(f"color: {color}; font-size: 9pt;")
            
            v_layout.addWidget(name_label)
            v_layout.addWidget(type_label)
            
            h_layout.addWidget(head_label)
            h_layout.addLayout(v_layout)
            h_layout.addStretch()

            self.account_frame_layout.addWidget(account_widget)

            # Carica l'immagine
            if account['type'] == 'microsoft':
                self.load_head_image(account['uuid'], head_label)
            else: # Offline
                pixmap = QPixmap(resource_path("assets/steve_head.png"))
                head_label.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            no_account_label = QLabel("❌ Nessun account configurato")
            no_account_label.setStyleSheet("color: #f44336; font-size: 10pt;")
            hint_label = QLabel("Clicca 'Gestisci Account' per configurare")
            hint_label.setObjectName("StatusLabel")
            self.account_frame_layout.addWidget(no_account_label)
            self.account_frame_layout.addWidget(hint_label)

    def load_head_image(self, uuid, target_label):
        cached_path = os.path.join(self.heads_folder, f"{uuid}.png")
        if os.path.exists(cached_path):
            pixmap = QPixmap(cached_path)
            target_label.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            return

        # Imposta un'immagine di placeholder mentre scarica
        placeholder = QPixmap(resource_path("assets/steve_head.png"))
        target_label.setPixmap(placeholder.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        # Scarica in background
        self.downloader_thread = QThread()
        self.image_worker = ImageDownloader(uuid, self.heads_folder)
        self.image_worker.moveToThread(self.downloader_thread)
        
        # Connetti i segnali
        self.image_worker.image_ready.connect(lambda u, p: self.on_image_loaded(u, p, target_label))
        self.downloader_thread.started.connect(self.image_worker.run)
        self.image_worker.finished.connect(self.downloader_thread.quit)
        self.image_worker.finished.connect(self.image_worker.deleteLater)
        self.downloader_thread.finished.connect(self.downloader_thread.deleteLater)
        
        self.downloader_thread.start()

    def on_image_loaded(self, uuid, pixmap, target_label):
        # Assicurati di aggiornare il label corretto
        if target_label and not pixmap.isNull():
             target_label.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def show_account_dialog(self):
        dialog = LoginDialog(self, self.account_manager, client_id=self.AZURE_CLIENT_ID, client_secret=self.AZURE_CLIENT_SECRET)
        dialog.exec()
        self.update_account_display()
        
    @pyqtSlot(str, str)
    def update_status(self, message, level="INFO"):
        self.status_label.setText(message)
        self.log(message, level)
        
    @pyqtSlot(int)
    def update_progress(self, progress):
        self.progress_bar.setValue(progress)
    
    def run_task(self, target, *args, **kwargs):
        if self.worker_thread and self.worker_thread.isRunning():
            self.log("Un'operazione è già in corso.", "ERROR")
            return
        self.worker_thread = QThread()
        self.worker = Worker(target, *args, **kwargs)
        self.worker.moveToThread(self.worker_thread)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.on_task_finished)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.progress.connect(self.update_progress)
        self.worker.status_update.connect(self.update_status)
        self.worker.log_message.connect(self.log)
        self.worker.show_dialog.connect(self.show_message_box)
        self.worker.update_check_complete.connect(self.on_update_check_finished)
        self.worker.news_ready.connect(self.update_news_display)
        self.worker.news_animation_ready.connect(self.set_news_animation)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()
        self.install_btn.setEnabled(False)
        self.play_btn.setEnabled(False)

    def on_task_finished(self):
        self.log("Operazione in background terminata.", "INFO")
        self.install_btn.setEnabled(True)
        self.check_installation_status()
        self.worker_thread = None
        self.worker = None

    @pyqtSlot(list)
    def on_update_check_finished(self, files_to_update):
        if files_to_update:
            self.log(f"Trovati {len(files_to_update)} file da aggiornare.", "INFO")
            msg = f"Sono disponibili {len(files_to_update)} aggiornamenti per il modpack.\n\nVuoi scaricarli ora?"
            reply = CustomMessageBox("Aggiornamenti disponibili", msg, 'question', self).exec()
            if reply == QMessageBox.StandardButton.Yes:
                self.start_installation()
        else:
            self.log("Il modpack è già aggiornato.", "SUCCESS")

    @pyqtSlot(str, str, str)
    def show_message_box(self, title, message, msg_type='info'):
        CustomMessageBox(title, message, msg_type, self).exec()

    def get_install_state(self):
        if os.path.exists(self.install_state_file):
            try:
                with open(self.install_state_file, 'r') as f: return json.load(f)
            except: pass
        return {}
    
    def save_install_state(self, state):
        with open(self.install_state_file, 'w') as f: json.dump(state, f, indent=2)
    
    def check_installation_status(self):
        state = self.get_install_state()
        if state.get('minecraft_version') == self.minecraft_version and state.get('forge_installed'):
            self.play_btn.setEnabled(True)
            self.update_status("Pronto per il lancio", "SUCCESS")
            return True
        else:
            self.play_btn.setEnabled(False)
            self.update_status("Installazione necessaria", "INFO")
            return False
        
    def start_installation(self):
        self.run_task(self.install_game)
        
    def install_game(self):
        try:
            state = self.get_install_state()
            if state.get('minecraft_version') != self.minecraft_version:
                self.worker.status_update.emit("Installazione Minecraft...", "INFO")
                minecraft_launcher_lib.install.install_minecraft_version(
                    self.minecraft_version, self.minecraft_directory, 
                    callback={"setStatus": lambda t: self.worker.status_update.emit(t,"INFO"), "setProgress": lambda v: self.worker.progress.emit(v)}
                )
                state['minecraft_version'] = self.minecraft_version
                self.save_install_state(state)
                self.worker.log_message.emit(f"Minecraft {self.minecraft_version} installato!", "SUCCESS")
            if not (state.get('forge_installed') and state.get('forge_version') == self.forge_version):
                self.worker.status_update.emit(f"Installazione Forge {self.forge_version}...", "INFO")
                self.worker.progress.emit(0)
                try:
                    minecraft_launcher_lib.forge.install_forge_version(
                        self.forge_version, self.minecraft_directory,
                        callback={"setStatus": lambda t: self.worker.status_update.emit(t, "INFO")}
                    )
                    state['forge_installed'] = True
                    state['forge_version'] = self.forge_version
                    self.save_install_state(state)
                    self.worker.log_message.emit(f"Forge {self.forge_version} installato!", "SUCCESS")
                except Exception as e:
                    self.worker.log_message.emit(f"Errore installazione Forge: {e}", "ERROR")
                    self.worker.show_dialog.emit("Errore Forge", f"L'installazione è fallita:\n{e}", 'error')
                    return
            self.worker.status_update.emit("Aggiornamento modpack...", "INFO")
            self.update_modpack()
            self.worker.status_update.emit("Installazione completata!", "SUCCESS")
            self.worker.progress.emit(100)
            self.worker.show_dialog.emit("Successo", "Installazione/Aggiornamento completato!", 'success')
        except Exception as e:
            self.worker.status_update.emit(f"Errore: {e}", "ERROR")
            self.worker.log_message.emit(f"Errore durante l'installazione: {e}", "ERROR")
            self.worker.show_dialog.emit("Errore", f"Si è verificato un errore:\n{e}", 'error')

    def update_modpack(self):
        try:
            manifest = self.get_modpack_manifest()
            if not manifest: raise Exception("Impossibile scaricare il manifest del modpack.")
            all_files = []
            for category, files in manifest.items():
                if isinstance(files, list):
                    for file_info in files:
                        target_folder = self.get_target_folder(category)
                        file_info['target_folder'], file_info['category'] = target_folder, category
                        all_files.append(file_info)
            if not all_files:
                self.worker.log_message.emit("Nessun file da elaborare nel manifest.", "INFO")
                return
            total_files = len(all_files)
            for i, file_info in enumerate(all_files):
                self.process_file(file_info, file_info['target_folder'], file_info['category'], i + 1, total_files)
            if 'mods' in manifest:
                self.clean_mods_folder(manifest['mods'], self.modpack_folder)
            self.worker.log_message.emit("Tutti i file del modpack sono aggiornati!", "SUCCESS")
        except Exception as e:
            self.worker.log_message.emit(f"Errore aggiornamento modpack: {e}", "ERROR")
            raise

    def get_target_folder(self, category):
        folder_map = { "root": self.launcher_directory, "mods": self.modpack_folder, "config": self.config_folder, "resourcepacks": self.resourcepacks_folder, "shaderpacks": self.shaderpacks_folder }
        return folder_map.get(category, os.path.join(self.launcher_directory, category))

    def process_file(self, file_info, target_folder, file_type, current, total):
        file_name, file_url, expected_hash = file_info["name"], file_info["url"], file_info.get("sha256", "")
        file_path = os.path.normpath(os.path.join(target_folder, file_info.get("path", file_name)))
        Path(os.path.dirname(file_path)).mkdir(parents=True, exist_ok=True)
        if os.path.exists(file_path) and (file_type == 'config' or file_name in ['options.txt', 'servers.dat']):
            self.worker.progress.emit(int((current / total) * 100))
            return
        needs_download = True
        if os.path.exists(file_path) and expected_hash and self.calculate_sha256(file_path) == expected_hash:
            needs_download = False
        if needs_download:
            self.worker.status_update.emit(f"Download ({current}/{total}): {file_name}", "INFO")
            try:
                self.download_file(file_url, file_path)
                if expected_hash and self.calculate_sha256(file_path) != expected_hash:
                    raise Exception(f"Hash mismatch per {file_name}")
            except Exception as e:
                if os.path.exists(file_path): os.remove(file_path)
                raise
        self.worker.progress.emit(int((current / total) * 100))

    def clean_mods_folder(self, manifest_files, mods_folder):
        if not os.path.exists(mods_folder): return
        manifest_jar_names = {f["name"] for f in manifest_files if f["name"].endswith(".jar")}
        for item in os.listdir(mods_folder):
            if item.endswith(".jar") and item not in manifest_jar_names:
                try:
                    os.remove(os.path.join(mods_folder, item))
                    self.worker.log_message.emit(f"Rimossa mod obsoleta: {item}", "INFO")
                except Exception as e:
                    self.worker.log_message.emit(f"Errore rimozione {item}: {e}", "ERROR")

    def get_modpack_manifest(self):
        try:
            self.log("Scaricamento manifest...", "INFO")
            response = requests.get(self.modpack_url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.log(f"Errore di rete scaricando il manifest: {e}", "ERROR")
            return None
    
    def download_file(self, url, destination):
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)

    def calculate_sha256(self, file_path):
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""): sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except IOError: return ""

    def start_game(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.show_message_box("Attendi", "Un'altra operazione è in corso.", "info")
            return
        if not self.account_manager.current_account:
            self.show_message_box("Account richiesto", "Configura un account prima di giocare!", 'info')
            self.show_account_dialog()
            return
        if not self.refresh_current_account_token():
            self.show_message_box("Accesso Scaduto", "Il tuo accesso Microsoft è scaduto. Accedi di nuovo.", 'error')
            self.show_account_dialog()
            return
        
        account_options = self.account_manager.get_launch_options()
        ram_gb = self.ram_spinbox.value()
        options = { "username": account_options["username"], "uuid": account_options["uuid"], "token": account_options["token"], "jvmArguments": [f"-Xmx{ram_gb}G", f"-Xms{ram_gb}G"], "launcherName": "CignoLauncher", "launcherVersion": self.launcher_version, "gameDirectory": self.launcher_directory }
        forge_version_id = self.forge_version.replace("-", "-forge-", 1)
        
        try:
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(forge_version_id, self.minecraft_directory, options)
            self.update_status("Avvio del gioco...", "SUCCESS")
            
            self.button_group.button(3).setChecked(True)
            self.pages.setCurrentIndex(3)

            subprocess_args = {
                'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT, 'text': True,
                'encoding': 'utf-8', 'errors': 'ignore',
                'cwd': self.launcher_directory
            }
            if sys.platform == "win32":
                subprocess_args['creationflags'] = subprocess.CREATE_NO_WINDOW

            self.game_process = subprocess.Popen(minecraft_command, **subprocess_args)
            
            self.install_btn.setEnabled(False)
            self.play_btn.setEnabled(False)

            threading.Thread(target=self.monitor_game_process, daemon=True).start()
            threading.Thread(target=self.read_game_output, args=(self.game_process.stdout,), daemon=True).start()

        except Exception as e:
            self.log(f"Errore durante l'avvio: {e}", "ERROR")
            self.show_message_box("Errore Avvio", f"Impossibile avviare il gioco:\n{e}", 'error')
            self.check_installation_status()

    def read_game_output(self, pipe):
        for line in iter(pipe.readline, ''):
            if line: QApplication.postEvent(self, LogEvent(line.strip()))
    
    def event(self, event):
        if event.type() == LogEvent.EVENT_TYPE:
            self.log(event.message, "GAME")
            return True
        if event.type() == GameClosedEvent.EVENT_TYPE:
            self.on_game_closed()
            return True
        return super().event(event)
    
    def on_game_closed(self):
        self.log("Il processo di gioco è terminato.", "SUCCESS")
        self.game_process = None
        self.button_group.button(0).setChecked(True)
        self.pages.setCurrentIndex(0)
        self.check_installation_status()

    def monitor_game_process(self):
        if self.game_process:
            self.game_process.wait()
            QApplication.postEvent(self, GameClosedEvent())
    
    def check_updates_on_startup(self):
        """
        Controlla lo stato iniziale del launcher e avvia le operazioni
        in background (aggiornamenti e news).
        """
        if not self.account_manager.current_account:
            self.show_account_dialog()
        
        # Avvia il task combinato che gestirà sia gli aggiornamenti che le news.
        self.log("Avvio operazioni iniziali (aggiornamenti e news)...", "INFO")
        self.run_task(self._perform_startup_tasks)

    def check_modpack_needs_update(self, manifest):
        files_to_update = []
        for category, files in manifest.items():
            if not isinstance(files, list): continue
            target_folder = self.get_target_folder(category)
            for file_info in files:
                file_path = os.path.normpath(os.path.join(target_folder, file_info.get("path", file_info["name"])))
                if os.path.exists(file_path) and (category == 'config' or os.path.basename(file_path) in ['options.txt', 'servers.dat']):
                    continue
                needs_update = True
                if os.path.exists(file_path) and file_info.get("sha256") and self.calculate_sha256(file_path) == file_info["sha256"]: 
                    needs_update = False
                if needs_update:
                    files_to_update.append(file_info)
        return files_to_update

    def refresh_current_account_token(self):
        account = self.account_manager.current_account
        if not account or account.get("type") != "microsoft": return True
        if not self.account_manager.is_token_expired(): return True

        self.log("Token Microsoft scaduto. Tentativo di refresh...", "INFO")
        refresh_token = account.get("refresh_token")
        if not refresh_token:
            self.log("Refresh token non trovato. E necessario un nuovo accesso.", "ERROR")
            return False
            
        try:
            # --- QUESTA E' LA CHIAMATA CORRETTA CON TUTTI I PARAMETRI ---
            new_data = minecraft_launcher_lib.microsoft_account.complete_refresh(
                client_id=self.AZURE_CLIENT_ID,
                client_secret=self.AZURE_CLIENT_SECRET,
                redirect_uri="http://localhost:5000/callback",
                refresh_token=refresh_token
            )
            # -----------------------------------------------------------------

            self.account_manager.add_microsoft_account(new_data)
            self.log("Token Microsoft aggiornato con successo!", "SUCCESS")
            self.update_account_display()
            return True
        except Exception as e:
            self.log(f"Impossibile aggiornare il token: {e}", "ERROR")
            return False
    
    def closeEvent(self, event):
        """
        Gestisce l'evento di chiusura della finestra per terminare
        i processi in modo pulito.
        """
        # Controlla se il processo del gioco è in esecuzione e terminalo
        if self.game_process:
            self.log("Tentativo di chiudere il processo di gioco...", "INFO")
            try:
                self.game_process.terminate()
                self.game_process.wait(timeout=5) # Aspetta al massimo 5 secondi
                self.log("Processo di gioco terminato.", "SUCCESS")
            except Exception as e:
                self.log(f"Errore durante la chiusura del gioco: {e}", "ERROR")

        # Controlla se un thread del worker è in esecuzione e attendi che finisca
        if self.worker_thread and self.worker_thread.isRunning():
            self.log("Attendo la fine del task in background prima di chiudere...", "INFO")
            self.worker_thread.quit()
            self.worker_thread.wait() # Attende bloccando che il thread finisca

        # Accetta l'evento e permette alla finestra di chiudersi
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = MinecraftLauncher()
    launcher.show()
    sys.exit(app.exec())