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
from utils import ImageDownloader, create_steve_avatar

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MicrosoftLoginWorker(QObject):
    """Worker in background per gestire il flusso OAuth Microsoft con PKCE."""
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
            
            login_url, state, code_verifier = minecraft_launcher_lib.microsoft_account.get_secure_login_data(
                self.client_id, redirect_url
            )
            self.status_update.emit("Apertura del browser in corso...")
            webbrowser.open(login_url)

            from http.server import HTTPServer, BaseHTTPRequestHandler
            auth_code = None
            
            class CallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    nonlocal auth_code
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    
                    html_content = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <title>CignoLauncher - Login completato</title>
                        <style>
                            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121316; color: #fff; text-align: center; padding-top: 80px; }
                            .card { background: #1a1c22; max-width: 480px; margin: auto; padding: 40px; border-radius: 12px; border: 1px solid #2a2e39; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
                            h1 { color: #10b981; margin-bottom: 10px; }
                            p { color: #94a3b8; font-size: 16px; }
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <h1>✓ Accesso Riuscito!</h1>
                            <p>Autenticazione con Microsoft completata con successo.</p>
                            <p>Puoi chiudere questa scheda e tornare a <b>CignoLauncher</b>.</p>
                        </div>
                    </body>
                    </html>
                    """
                    self.wfile.write(html_content.encode('utf-8'))

                    if "code=" in self.path:
                        try:
                            auth_code = minecraft_launcher_lib.microsoft_account.parse_auth_code_url(
                                f"http://localhost:5000{self.path}", state
                            )
                        except Exception as e:
                            print(f"Errore parsing URL di callback: {e}")
                def log_message(self, format, *args): pass
            
            server = HTTPServer(('localhost', 5000), CallbackHandler)
            server.handle_request()

            if not auth_code:
                raise Exception("Nessun codice di autorizzazione ricevuto dal browser.")

            self.status_update.emit("Ottenimento token di gioco Mojang...")
            account_data = minecraft_launcher_lib.microsoft_account.complete_login(
                self.client_id, self.client_secret, redirect_url, auth_code, code_verifier
            )
            self.success.emit(account_data)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class LoginDialog(QDialog):
    """Finestra di gestione e aggiunta account (Microsoft & Offline)"""
    def __init__(self, parent, account_manager, client_id, client_secret):
        super().__init__(parent)
        self.account_manager = account_manager
        self.client_id = client_id
        self.client_secret = client_secret
        self.head_labels = {}
        
        self.setupUi()
        self.apply_stylesheet()
        
    def setupUi(self):
        self.setWindowTitle("Gestione Account - CignoLauncher")
        self.setMinimumSize(540, 480)
        self.resize(540, 480)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)
        
        title_box = QHBoxLayout()
        title_label = QLabel("Gestione Account")
        title_label.setObjectName("TitleLabel")
        title_box.addWidget(title_label)
        main_layout.addLayout(title_box)
        
        self.notebook = QTabWidget()
        
        self.accounts_tab = QWidget()
        self.microsoft_tab = QWidget()
        self.offline_tab = QWidget()
        
        self.notebook.addTab(self.accounts_tab, "Account salvati")
        self.notebook.addTab(self.offline_tab, "Modalità Offline")
        self.notebook.addTab(self.microsoft_tab, "Accedi con Microsoft")
        
        self.refresh_accounts_tab()
        self.setup_offline_tab()
        self.setup_microsoft_tab()
        
        close_btn = QPushButton("Chiudi")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.accept)
        
        main_layout.addWidget(self.notebook)
        main_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121316;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #f1f5f9;
            }
            QLabel#TitleLabel {
                font-size: 16pt;
                font-weight: bold;
                color: #38bdf8;
            }
            QTabWidget::pane {
                border: 1px solid #272a34;
                border-radius: 8px;
                background-color: #1a1c23;
                padding: 10px;
            }
            QTabBar::tab {
                background-color: #16181f;
                color: #94a3b8;
                padding: 8px 18px;
                font-weight: 600;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                border: 1px solid #272a34;
                border-bottom: none;
            }
            QTabBar::tab:hover {
                background-color: #222530;
                color: #e2e8f0;
            }
            QTabBar::tab:selected {
                background-color: #1a1c23;
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
            QLineEdit {
                background-color: #121316;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: 600;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #272a34;
                color: #64748b;
            }
            QPushButton#SecondaryButton {
                background-color: #222530;
                color: #cbd5e1;
                border: 1px solid #334155;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
            QPushButton#RemoveButton {
                background-color: #7f1d1d;
                color: #fca5a5;
                border: 1px solid #991b1b;
            }
            QPushButton#RemoveButton:hover {
                background-color: #991b1b;
                color: white;
            }
            QFrame#AccountCard {
                background-color: #16181f;
                border: 1px solid #272a34;
                border-radius: 8px;
                padding: 6px;
            }
            QFrame#AccountCardActive {
                background-color: #1a2333;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 6px;
            }
        """)

    def refresh_accounts_tab(self):
        layout = self.accounts_tab.layout()
        if not layout:
            layout = QVBoxLayout(self.accounts_tab)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        self.head_labels.clear()

        accounts = self.account_manager.get_all_accounts()
        current_acc = self.account_manager.current_account
        curr_id = self.account_manager.accounts.get("last_used")

        if not accounts:
            no_accounts_label = QLabel("Nessun account registrato.\nAggiungi un account Offline o accedi con Microsoft.")
            no_accounts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_accounts_label.setStyleSheet("color: #94a3b8; font-size: 11pt; padding: 40px;")
            layout.addWidget(no_accounts_label)
            return

        for account_id, data in accounts.items():
            is_active = (account_id == curr_id)
            frame = QFrame()
            frame.setObjectName("AccountCardActive" if is_active else "AccountCard")
            
            frame_layout = QHBoxLayout(frame)
            frame_layout.setContentsMargins(10, 8, 10, 8)
            frame_layout.setSpacing(12)
            
            head_label = QLabel()
            head_label.setFixedSize(36, 36)
            head_label.setStyleSheet("border-radius: 4px; background: #222530;")
            self.head_labels[data['uuid']] = head_label

            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            
            name_text = f"<b>{data['username']}</b>"
            if is_active:
                name_text += " <span style='color: #10b981; font-size: 9pt;'>● Attivo</span>"
            name_label = QLabel(name_text)
            
            acc_type = "Microsoft Xbox" if data['type'] == 'microsoft' else "Offline"
            type_color = "#38bdf8" if data['type'] == 'microsoft' else "#94a3b8"
            type_label = QLabel(f"<span style='color: {type_color}; font-size: 9pt;'>{acc_type}</span>")
            
            text_layout.addWidget(name_label)
            text_layout.addWidget(type_label)
            
            frame_layout.addWidget(head_label)
            frame_layout.addLayout(text_layout)
            frame_layout.addStretch()

            if not is_active:
                use_btn = QPushButton("Usa")
                use_btn.clicked.connect(lambda _, aid=account_id: self.use_account(aid))
                frame_layout.addWidget(use_btn)
            
            remove_btn = QPushButton("Rimuovi")
            remove_btn.setObjectName("RemoveButton")
            remove_btn.clicked.connect(lambda _, aid=account_id: self.remove_account(aid))
            frame_layout.addWidget(remove_btn)

            layout.addWidget(frame)
            
            # Carica avatar
            if data['type'] == 'microsoft':
                self.load_head_image_for_dialog(data['uuid'])
            else:
                head_label.setPixmap(create_steve_avatar(36))

    def load_head_image_for_dialog(self, uuid_str):
        heads_folder = getattr(self.parent(), 'heads_folder', os.path.expanduser("~/.cignolauncher/heads"))
        cached_path = os.path.join(heads_folder, f"{uuid_str}.png")
        target_label = self.head_labels.get(uuid_str)
        if not target_label:
            return

        if os.path.exists(cached_path) and os.path.getsize(cached_path) > 0:
            pixmap = QPixmap(cached_path)
            target_label.setPixmap(pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            return
        
        target_label.setPixmap(create_steve_avatar(36))
        
        # Download in background
        self.downloader_thread = QThread()
        self.image_worker = ImageDownloader(uuid_str, heads_folder)
        self.image_worker.moveToThread(self.downloader_thread)
        self.image_worker.image_ready.connect(lambda u, p: self.on_image_loaded_for_dialog(u, p))
        self.downloader_thread.started.connect(self.image_worker.run)
        self.image_worker.finished.connect(self.downloader_thread.quit)
        self.image_worker.finished.connect(self.image_worker.deleteLater)
        self.downloader_thread.finished.connect(self.downloader_thread.deleteLater)
        self.downloader_thread.start()

    def on_image_loaded_for_dialog(self, uuid_str, pixmap):
        target_label = self.head_labels.get(uuid_str)
        if target_label and not pixmap.isNull():
            target_label.setPixmap(pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def setup_offline_tab(self):
        layout = QVBoxLayout(self.offline_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        
        desc = QLabel("La modalità offline consente di giocare senza autenticazione Microsoft.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #94a3b8;")
        
        form_layout = QHBoxLayout()
        form_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.offline_username = QLineEdit()
        self.offline_username.setPlaceholderText("Nome giocatore (es. Steve)")
        self.offline_username.setFixedWidth(220)
        self.offline_username.returnPressed.connect(self.offline_login)
        
        login_btn = QPushButton("Aggiungi e Seleziona")
        login_btn.clicked.connect(self.offline_login)
        
        form_layout.addWidget(self.offline_username)
        form_layout.addWidget(login_btn)
        
        layout.addWidget(desc)
        layout.addLayout(form_layout)

    def setup_microsoft_tab(self):
        layout = QVBoxLayout(self.microsoft_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)
        
        desc = QLabel("Accedi con il tuo account Microsoft / Xbox per giocare online sui server multiplayer autenticati.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #94a3b8;")
        
        self.ms_login_btn = QPushButton("Apri Browser e Accedi con Microsoft")
        self.ms_login_btn.clicked.connect(self.microsoft_login)
        self.ms_login_btn.setMinimumHeight(38)
        
        self.ms_status_label = QLabel("")
        self.ms_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ms_status_label.setStyleSheet("color: #38bdf8; font-weight: 500;")
        
        layout.addWidget(desc)
        layout.addWidget(self.ms_login_btn)
        layout.addWidget(self.ms_status_label)

    def use_account(self, account_id):
        self.account_manager.switch_account(account_id)
        self.refresh_accounts_tab()
        self.accept()

    def remove_account(self, account_id):
        reply = QMessageBox.question(self, "Conferma eliminazione", "Vuoi davvero rimuovere questo profilo?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.account_manager.remove_account(account_id)
            self.refresh_accounts_tab()

    def offline_login(self):
        username = self.offline_username.text().strip()
        if not (3 <= len(username) <= 16):
            QMessageBox.warning(self, "Nome non valido", "Il nome utente deve avere una lunghezza compresa tra 3 e 16 caratteri.")
            return
        self.account_manager.add_offline_account(username)
        self.refresh_accounts_tab()
        self.accept()

    def microsoft_login(self):
        if not self.client_id or not self.client_secret or "your-" in self.client_id:
            QMessageBox.critical(self, "Configurazione Azure Mancante",
                                 "I parametri AZURE_CLIENT_ID e AZURE_CLIENT_SECRET non sono impostati.\n"
                                 "Puoi impostarli tramite variabili d'ambiente oppure utilizzare la modalità Offline.")
            return

        self.ms_login_btn.setEnabled(False)
        self.ms_status_label.setText("In attesa dell'autorizzazione nel browser...")
        
        self.login_thread = QThread()
        self.login_worker = MicrosoftLoginWorker(self.client_id, self.client_secret)
        self.login_worker.moveToThread(self.login_thread)
        
        self.login_worker.status_update.connect(lambda msg: self.ms_status_label.setText(msg))
        self.login_worker.success.connect(self.on_login_success)
        self.login_worker.error.connect(self.on_login_error)
        self.login_worker.finished.connect(self.login_thread.quit)
        self.login_worker.finished.connect(self.login_worker.deleteLater)
        self.login_thread.finished.connect(self.login_thread.deleteLater)
        self.login_thread.started.connect(self.login_worker.run)
        
        self.login_thread.start()

    def on_login_success(self, account_data):
        self.account_manager.add_microsoft_account(account_data)
        self.refresh_accounts_tab()
        self.accept()

    def on_login_error(self, error_message):
        QMessageBox.critical(self, "Errore di Accesso", f"Impossibile completare il login Microsoft:\n{error_message}")
        self.ms_login_btn.setEnabled(True)
        self.ms_status_label.setText("")


class CustomMessageBox(QMessageBox):
    """Wrapper QMessageBox con stile dark moderno coerente"""
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

        self.setStyleSheet("""
            QMessageBox {
                background-color: #16181f;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #f1f5f9;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: 600;
                padding: 6px 14px;
                border: none;
                border-radius: 5px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)