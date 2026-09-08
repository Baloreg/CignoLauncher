import sys
import os
import webbrowser
import threading
import requests

import minecraft_launcher_lib

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QWidget, QLineEdit, QMessageBox, QFrame,
                             QSpacerItem, QSizePolicy, QMenu, QInputDialog)
from PyQt6.QtGui import QIcon, QFont, QPixmap, QAction
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread, QTimer
from utils import create_steve_avatar, resource_path, download_head_pixmap
from dialog_utils import ask_confirmation, show_warning

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
            with open(os.devnull, 'w') as devnull:
                old_stdout = sys.stdout
                sys.stdout = devnull
                try:
                    webbrowser.open(login_url)
                finally:
                    sys.stdout = old_stdout

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
    """Finestra unificata di gestione account"""
    def __init__(self, parent, account_manager, client_id, client_secret, initial_mode=""):
        super().__init__(parent)
        self.account_manager = account_manager
        self.client_id = client_id
        self.client_secret = client_secret
        self.initial_mode = initial_mode
        self.head_labels = {}
        self.login_thread = None
        self.login_worker = None

        self.setupUi()
        self.apply_stylesheet()

    def setupUi(self):
        self.setWindowTitle("Account - CignoLauncher")
        self.setMinimumSize(480, 420)
        self.resize(540, 480)
        self.setSizeGripEnabled(True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Intestazione con titolo e pulsante "+"
        header_layout = QHBoxLayout()
        title_label = QLabel("Account")
        title_label.setObjectName("TitleLabel")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.add_account_btn = QPushButton("+ Aggiungi Account")
        self.add_account_btn.setObjectName("PrimaryActionButton")
        self.add_account_btn.clicked.connect(self.show_add_account_menu)
        header_layout.addWidget(self.add_account_btn)

        main_layout.addLayout(header_layout)

        # Contenitore scrollabile degli account salvati
        self.accounts_container = QWidget()
        self.accounts_layout = QVBoxLayout(self.accounts_container)
        self.accounts_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.accounts_layout.setContentsMargins(0, 0, 0, 0)
        self.accounts_layout.setSpacing(10)

        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidget(self.accounts_container)
        main_layout.addWidget(scroll, 1)

        self.refresh_accounts_list()

        # Pulsante Chiudi
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        close_btn = QPushButton("Chiudi")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)
        main_layout.addLayout(bottom_layout)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f8fafc;
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }
            QLabel#TitleLabel {
                font-size: 16pt;
                font-weight: bold;
                color: #f8fafc;
            }
            QPushButton#PrimaryActionButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                outline: none;
            }
            QPushButton#PrimaryActionButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#SecondaryButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 16px;
                outline: none;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #334155;
            }
            QPushButton#RemoveButton {
                background-color: #7f2930;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                outline: none;
            }
            QPushButton#RemoveButton:hover {
                background-color: #991b1b;
            }
            QFrame#AccountCard, QFrame#AccountCardActive {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QFrame#AccountCardActive {
                border: 1px solid #38bdf8;
                background-color: #152238;
            }
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: white;
            }
        """)

    def show_add_account_menu(self):
        menu = QMenu(self)
        microsoft_action = QAction("Accedi con Microsoft", self)
        microsoft_action.triggered.connect(self.microsoft_login)
        offline_action = QAction("Aggiungi Account Offline", self)
        offline_action.triggered.connect(self.prompt_offline_login)

        menu.addAction(microsoft_action)
        menu.addAction(offline_action)
        menu.exec(self.add_account_btn.mapToGlobal(self.add_account_btn.rect().bottomLeft()))

    def refresh_accounts_list(self):
        while self.accounts_layout.count():
            item = self.accounts_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.head_labels.clear()

        accounts = self.account_manager.get_all_accounts()
        curr_id = self.account_manager.accounts.get("last_used")

        if not accounts:
            no_accounts_label = QLabel("Nessun account registrato.\nClicca su '+ Aggiungi Account' per iniziare.")
            no_accounts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_accounts_label.setStyleSheet("color: #94a3b8; font-size: 11pt; padding: 40px;")
            self.accounts_layout.addWidget(no_accounts_label)
            return

        for account_id, data in accounts.items():
            is_active = (account_id == curr_id)
            frame = QFrame()
            frame.setObjectName("AccountCardActive" if is_active else "AccountCard")

            frame_layout = QHBoxLayout(frame)
            frame_layout.setContentsMargins(14, 10, 14, 10)
            frame_layout.setSpacing(14)

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
                use_btn.setObjectName("SecondaryButton")
                use_btn.clicked.connect(lambda _, aid=account_id: self.use_account(aid))
                frame_layout.addWidget(use_btn)

            remove_btn = QPushButton("Rimuovi")
            remove_btn.setObjectName("RemoveButton")
            remove_btn.clicked.connect(lambda _, aid=account_id: self.remove_account(aid))
            frame_layout.addWidget(remove_btn)

            self.accounts_layout.addWidget(frame)

            # Carica avatar
            if data['type'] == 'microsoft':
                identifier = data.get('username')
                user_uuid = data.get('uuid')
                self.load_head_image_for_dialog(identifier, head_label, user_uuid=user_uuid)
            else:
                steve_path = resource_path("assets/steve_head.png")
                steve_pix = QPixmap(steve_path)
                if steve_pix.isNull():
                    steve_pix = create_steve_avatar(36)
                head_label.setPixmap(steve_pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def load_head_image_for_dialog(self, identifier, target_label, user_uuid=None):
        if not (identifier or user_uuid) or not target_label:
            return

        heads_folder = getattr(self.parent(), 'heads_folder', os.path.expanduser("~/.cignolauncher/heads"))
        key = identifier or user_uuid
        cached_path = os.path.join(heads_folder, f"{key}.png")

        if os.path.exists(cached_path) and os.path.getsize(cached_path) > 100:
            pixmap = QPixmap(cached_path)
            if not pixmap.isNull():
                target_label.setPixmap(pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                return

        target_label.setPixmap(create_steve_avatar(36))

        def fetch_and_set():
            pix = download_head_pixmap(identifier, heads_folder, user_uuid=user_uuid)
            if pix and not pix.isNull():
                scaled = pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                QTimer.singleShot(0, lambda: target_label.setPixmap(scaled))

        threading.Thread(target=fetch_and_set, daemon=True).start()

    def use_account(self, account_id):
        self.account_manager.switch_account(account_id)
        self.refresh_accounts_list()
        if hasattr(self.parent(), 'update_account_badge'):
            self.parent().update_account_badge()
        self.accept()

    def remove_account(self, account_id):
        if ask_confirmation(self, "Rimuovi profilo", "Vuoi davvero rimuovere questo profilo?", destructive=True):
            self.account_manager.remove_account(account_id)
            self.refresh_accounts_list()

    def prompt_offline_login(self):
        username, ok = QInputDialog.getText(self, "Aggiungi Account Offline", "Inserisci il nome giocatore:")
        if ok and username:
            clean_name = username.strip()
            if not (3 <= len(clean_name) <= 16):
                show_warning(self, "Nome non valido", "Il nome utente deve avere una lunghezza compresa tra 3 e 16 caratteri.")
                return
            self.account_manager.add_offline_account(clean_name)
            self.refresh_accounts_list()
            self.accept()

    def microsoft_login(self):
        if not self.client_id or not self.client_secret or "your-" in self.client_id:
            QMessageBox.critical(self, "Configurazione Azure Mancante",
                                 "I parametri AZURE_CLIENT_ID e AZURE_CLIENT_SECRET non sono impostati.")
            return

        self.add_account_btn.setEnabled(False)

        self.login_thread = QThread(self)
        self.login_worker = MicrosoftLoginWorker(self.client_id, self.client_secret)
        self.login_worker.moveToThread(self.login_thread)

        def cleanup_login():
            self.login_thread = None
            self.login_worker = None

        self.login_worker.success.connect(self.on_login_success)
        self.login_worker.error.connect(self.on_login_error)
        self.login_worker.finished.connect(self.login_thread.quit)
        self.login_worker.finished.connect(self.login_worker.deleteLater)
        self.login_thread.finished.connect(self.login_thread.deleteLater)
        self.login_thread.finished.connect(cleanup_login)
        self.login_thread.started.connect(self.login_worker.run)

        self.login_thread.start()

    def on_login_success(self, account_data):
        self.account_manager.add_microsoft_account(account_data)
        self.refresh_accounts_list()
        if hasattr(self.parent(), 'update_account_badge'):
            self.parent().update_account_badge()
        self.accept()

    def on_login_error(self, error_message):
        QMessageBox.critical(self, "Errore di Accesso", f"Impossibile completare il login Microsoft:\n{error_message}")
        self.add_account_btn.setEnabled(True)


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
