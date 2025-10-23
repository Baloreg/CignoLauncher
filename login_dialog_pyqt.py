# login_dialog_pyqt.py (con fix per lo stile dei pulsanti e estetica migliorata)

import sys
import os
import webbrowser
import threading

import minecraft_launcher_lib

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTabWidget, QWidget, QLineEdit, QMessageBox, QFrame, 
                             QSpacerItem, QSizePolicy)
from PyQt6.QtGui import QIcon, QFont, QPixmap
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread
from utils import ImageDownloader

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Worker per il login Microsoft in background
class MicrosoftLoginWorker(QObject):
    finished = pyqtSignal()
    success = pyqtSignal(dict)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, client_id, client_secret):
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        
    def run(self):
        try:
            redirect_url = "http://localhost:5000/callback"
            
            login_url, state, code_verifier = minecraft_launcher_lib.microsoft_account.get_secure_login_data(self.client_id, redirect_url)
            self.status_update.emit("Apertura browser per l'autenticazione...")
            webbrowser.open(login_url)

            from http.server import HTTPServer, BaseHTTPRequestHandler
            auth_code = None
            
            class CallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    nonlocal auth_code
                    # Scrivi una risposta HTML professionale
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    
                    try:
                        # Carica il file HTML esterno
                        html_path = resource_path('callback.html')
                        with open(html_path, 'rb') as f:
                            self.wfile.write(f.read())
                    except FileNotFoundError:
                        # Fallback nel caso in cui il file non sia trovato
                        fallback_html = b"<h1>Login completato!</h1><p>Puoi chiudere questa finestra.</p>"
                        self.wfile.write(fallback_html)

                    if "code=" in self.path:
                        try:
                            auth_code = minecraft_launcher_lib.microsoft_account.parse_auth_code_url(
                                f"http://localhost:5000{self.path}", state
                            )
                        except Exception as e:
                            print(f"Errore parsing URL: {e}")
                def log_message(self, format, *args): pass
            
            server = HTTPServer(('localhost', 5000), CallbackHandler)
            server.handle_request()

            if not auth_code:
                raise Exception("Nessun codice di autorizzazione ricevuto.")

            self.status_update.emit("Autenticazione completata, ottenimento token...")
            account_data = minecraft_launcher_lib.microsoft_account.complete_login(
                self.client_id, self.client_secret, redirect_url, auth_code, code_verifier
            )
            self.success.emit(account_data)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class LoginDialog(QDialog):
    def __init__(self, parent, account_manager, client_id, client_secret):
        super().__init__(parent)
        self.account_manager = account_manager
        self.client_id = client_id
        self.client_secret = client_secret
        
        self.setupUi()
        self.apply_stylesheet()
        
    def setupUi(self):
        self.setWindowTitle("Accedi a Minecraft")
        self.setFixedSize(500, 450)
        self.setWindowIcon(QIcon(resource_path("assets/window_icon.ico")))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)
        
        title = QLabel("Accedi a Minecraft")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.notebook = QTabWidget()
        
        self.head_labels = {}
        
        self.accounts_tab = QWidget()
        self.microsoft_tab = QWidget()
        self.offline_tab = QWidget()
        
        self.notebook.addTab(self.accounts_tab, "Account salvati")
        self.notebook.addTab(self.microsoft_tab, "Accedi con Microsoft")
        self.notebook.addTab(self.offline_tab, "Modalità Offline")
        
        self.refresh_accounts_tab()
        self.setup_microsoft_tab()
        self.setup_offline_tab()
        
        close_btn = QPushButton("Chiudi")
        close_btn.setObjectName("CloseButton")
        close_btn.clicked.connect(self.reject)
        
        main_layout.addWidget(title)
        main_layout.addWidget(self.notebook)
        main_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def apply_stylesheet(self):
        parent_style = self.parent().styleSheet()
        self.setStyleSheet(parent_style + """
            #LoginDialog { 
                background-color: #2d2d2d; 
            }
            QLabel#TitleLabel { 
                font-size: 18pt; 
                color: #0078d4; 
                margin-bottom: 10px;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #3d3d3d;
                color: #b0b0b0;
                padding: 8px 15px;
                font-weight: bold;
                border: none;
                border-radius: 15px;
                margin: 2px;
            }
            QTabBar::tab:hover {
                background-color: #4f4f4f;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                color: white;
            }
            QPushButton#RemoveButton, QPushButton#CloseButton {
                background-color: transparent;
                color: #b0b0b0;
                border: 1px solid #404040;
                font-weight: normal;
            }
            QPushButton#RemoveButton:hover, QPushButton#CloseButton:hover {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #5a5a5a;
            }
        """)

    def refresh_accounts_tab(self):
        layout = self.accounts_tab.layout()
        if not layout:
            layout = QVBoxLayout(self.accounts_tab)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            layout.setContentsMargins(15, 15, 15, 15)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        self.head_labels.clear() # Pulisci il dizionario

        accounts = self.account_manager.get_all_accounts()
        if not accounts:
            # ... (codice per nessun account, rimane uguale)
            no_accounts_label = QLabel("Nessun account salvato.")
            no_accounts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
            layout.addWidget(no_accounts_label)
            layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
            return

        for account_id, data in accounts.items():
            frame = QFrame()
            frame_layout = QHBoxLayout(frame)
            frame_layout.setContentsMargins(0, 5, 0, 5)
            
            # Label per la testa
            head_label = QLabel()
            head_label.setFixedSize(32, 32)
            head_label.setStyleSheet("border-radius: 4px;")
            self.head_labels[data['uuid']] = head_label # Salva il riferimento

            info_label = QLabel(f"<b>{data['username']}</b><br><small style='color: #b0b0b0;'>Account {data['type'].capitalize()}</small>")
            
            use_btn = QPushButton("Usa")
            remove_btn = QPushButton("Rimuovi")
            remove_btn.setObjectName("RemoveButton")
            
            use_btn.clicked.connect(lambda _, aid=account_id: self.use_account(aid))
            remove_btn.clicked.connect(lambda _, aid=account_id: self.remove_account(aid))
            
            frame_layout.addWidget(head_label) # Aggiungi la testa
            frame_layout.addWidget(info_label)
            frame_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
            frame_layout.addWidget(use_btn)
            frame_layout.addWidget(remove_btn)
            layout.addWidget(frame)
            
            # Carica l'immagine
            if data['type'] == 'microsoft':
                self.load_head_image_for_dialog(data['uuid'])
            else:
                pixmap = QPixmap(resource_path("assets/steve_head.png"))
                head_label.setPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    
    def load_head_image_for_dialog(self, uuid):
        # Usa la cartella heads definita nel launcher principale (parent)
        heads_folder = self.parent().heads_folder
        cached_path = os.path.join(heads_folder, f"{uuid}.png")
        
        target_label = self.head_labels.get(uuid)
        if not target_label: return

        if os.path.exists(cached_path):
            pixmap = QPixmap(cached_path)
            target_label.setPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            return
        
        # Imposta placeholder
        pixmap = QPixmap(resource_path("assets/steve_head.png"))
        target_label.setPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        self.downloader_thread = QThread()
        self.image_worker = ImageDownloader(uuid, heads_folder)
        self.image_worker.moveToThread(self.downloader_thread)
        
        self.image_worker.image_ready.connect(self.on_image_loaded_for_dialog)
        self.downloader_thread.started.connect(self.image_worker.run)
        self.image_worker.finished.connect(self.downloader_thread.quit)
        self.image_worker.finished.connect(self.image_worker.deleteLater)
        self.downloader_thread.finished.connect(self.downloader_thread.deleteLater)
        
        self.downloader_thread.start()

    def on_image_loaded_for_dialog(self, uuid, pixmap):
        target_label = self.head_labels.get(uuid)
        if target_label and not pixmap.isNull():
             target_label.setPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def setup_microsoft_tab(self):
        layout = QVBoxLayout(self.microsoft_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        desc = QLabel("Accedi con il tuo account Microsoft/Xbox per giocare online.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ms_login_btn = QPushButton("Accedi con Microsoft")
        self.ms_login_btn.clicked.connect(self.microsoft_login)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        layout.addWidget(self.ms_login_btn)
        layout.addWidget(self.status_label)

    def setup_offline_tab(self):
        layout = QVBoxLayout(self.offline_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        desc = QLabel("Gioca inserendo un nome utente (da 3 a 16 caratteri).")
        self.offline_username = QLineEdit("Giocatore")
        self.offline_username.setPlaceholderText("Username")
        self.offline_username.returnPressed.connect(self.offline_login)
        self.offline_username.setFixedWidth(200)
        login_btn = QPushButton("Gioca Offline")
        login_btn.clicked.connect(self.offline_login)
        layout.addWidget(desc)
        layout.addWidget(self.offline_username)
        layout.addWidget(login_btn)
        
    def use_account(self, account_id):
        self.account_manager.switch_account(account_id)
        self.accept()

    def remove_account(self, account_id):
        reply = QMessageBox.question(self, "Conferma", "Sei sicuro di voler rimuovere questo account?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.account_manager.remove_account(account_id)
            self.refresh_accounts_tab()

    def offline_login(self):
        username = self.offline_username.text().strip()
        if not (3 <= len(username) <= 16):
            QMessageBox.warning(self, "Attenzione", "L'username deve avere tra 3 e 16 caratteri.")
            return
        self.account_manager.add_offline_account(username)
        self.accept()

    def microsoft_login(self):
        if not self.client_id or not self.client_secret or "your-" in self.client_id:
            QMessageBox.critical(self, "Errore di configurazione", "Client ID o Client Secret non sono configurati correttamente nel launcher.")
            return

        self.ms_login_btn.setEnabled(False)
        self.status_label.setText("In attesa del login nel browser...")
        
        self.login_thread = QThread()
        self.login_worker = MicrosoftLoginWorker(self.client_id, self.client_secret)
        self.login_worker.moveToThread(self.login_thread)
        
        self.login_worker.success.connect(self.on_login_success)
        self.login_worker.error.connect(self.on_login_error)
        self.login_worker.finished.connect(self.login_thread.quit)
        self.login_worker.finished.connect(self.login_worker.deleteLater)
        self.login_thread.finished.connect(self.login_thread.deleteLater)
        self.login_thread.started.connect(self.login_worker.run)
        
        self.login_thread.start()

    def on_login_success(self, account_data):
        self.account_manager.add_microsoft_account(account_data)
        self.accept()

    def on_login_error(self, error_message):
        QMessageBox.critical(self, "Errore di accesso", f"Login fallito:\n{error_message}")
        self.ms_login_btn.setEnabled(True)
        self.status_label.setText("")

# Un wrapper per QMessageBox per uno stile più semplice
class CustomMessageBox(QMessageBox):
    def __init__(self, title, message, msg_type='info', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setText(message)
        
        icon_map = {
            'info': QMessageBox.Icon.Information,
            'error': QMessageBox.Icon.Critical,
            'success': QMessageBox.Icon.Information,
            'question': QMessageBox.Icon.Question
        }
        self.setIcon(icon_map.get(msg_type, QMessageBox.Icon.NoIcon))
        
        if msg_type == 'question':
            self.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        else:
            self.setStandardButtons(QMessageBox.StandardButton.Ok)

        # --- MODIFICA CHIAVE ---
        # Rimuoviamo la riga che sovrascrive lo stile.
        # Ora il dialogo erediterà lo stile completo del parent, inclusi i pulsanti.
        # if parent:
        #     self.setStyleSheet("background-color: #2d2d2d; color: white;")