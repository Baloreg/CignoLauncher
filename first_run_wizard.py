import os
import threading
from PyQt6.QtCore import Qt, QTimer, QSize, QThread
from PyQt6.QtGui import QPixmap, QIcon, QMovie, QAction
from PyQt6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWizard,
    QWizardPage,
    QDialog,
    QPushButton,
    QSlider,
    QCheckBox,
    QScrollArea,
    QFrame,
    QMenu,
    QInputDialog,
    QMessageBox,
)
from ui_controls import MaterialComboBox
from utils import resource_path, download_head_pixmap, create_steve_avatar
from custom_window import CustomWindowMixin
from dialog_utils import ask_confirmation, show_warning, custom_text_input
from instance_dialog import LoaderFetchWorker
from login_dialog_pyqt import MicrosoftLoginWorker


class FirstRunWizard(QDialog, CustomWindowMixin):
    def __init__(self, parent, default_version, instance, logo_path="",
                 arrow_path="assets/chevron_down.svg", available_versions=None):
        super().__init__(parent)
        self.default_version = default_version
        self.instance = instance
        self.available_versions = available_versions or []
        self.logo_path = logo_path
        self.arrow_path = arrow_path.replace("\\", "/")
        self.up_arrow_path = self.arrow_path.replace("chevron_down", "chevron_up")

        self.instance_manager = getattr(parent, 'instance_manager', None)
        self.account_manager = getattr(parent, 'account_manager', None)
        self.heads_folder = getattr(parent, 'heads_folder', os.path.join(getattr(parent, 'launcher_directory', os.path.expanduser("~/.cignolauncher")), "heads"))

        self.current_icon_path = instance.get("icon", "") if instance else ""
        self.current_movie = None
        self.head_labels = {}
        self.login_thread = None
        self.login_worker = None
        self.fetch_worker = None

        self.setWindowTitle("Configura CignoLauncher")
        self.setMinimumSize(640, 560)
        self.resize(700, 620)

        self.init_custom_frame(title="Configura CignoLauncher", icon=self.windowIcon(), show_maximize=False)

        self.wizard = QWizard(self)
        self.wizard.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.wizard.setOption(QWizard.WizardOption.NoCancelButtonOnLastPage, True)
        self.wizard.setButtonText(QWizard.WizardButton.NextButton, "Continua")
        self.wizard.setButtonText(QWizard.WizardButton.BackButton, "Indietro")
        self.wizard.setButtonText(QWizard.WizardButton.FinishButton, "Inizia")
        self.wizard.setButtonText(QWizard.WizardButton.CancelButton, "Salta")

        self.wizard.addPage(self.create_welcome_page())
        self.wizard.addPage(self.create_instance_page())
        self.wizard.addPage(self.create_account_page())
        self.wizard.addPage(self.create_ready_page())
        self.wizard.setStyleSheet(self.stylesheet(self.arrow_path, self.up_arrow_path))

        self.content_layout.addWidget(self.wizard)
        self.wizard.accepted.connect(self.accept)
        self.wizard.rejected.connect(self.reject)
        self.adjustSize()

    def create_welcome_page(self):
        page = QWizardPage()
        page.setTitle("Benvenuto in CignoLauncher")
        page.setSubTitle("Configura il launcher e la tua prima istanza in pochi secondi.")
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        logo = QLabel()
        pixmap = QPixmap(self.logo_path)
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaledToWidth(280, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        text = QLabel(
            "Gestisci più istanze Minecraft isolate, ognuna con la propria versione, "
            "mod loader, memoria dedicata e cartella salvataggi. "
            "Configura subito la tua prima istanza e collega il tuo account."
        )
        text.setWordWrap(True)
        text.setObjectName("WizardBody")
        layout.addWidget(text)
        layout.addStretch()
        return page

    def create_instance_page(self):
        page = QWizardPage()
        page.setTitle("Prepara la tua istanza")
        page.setSubTitle("Queste impostazioni verranno usate per creare la tua prima istanza di gioco.")
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # Icon row
        icon_row = QHBoxLayout()
        icon_label = QLabel("Icona dell'Istanza:")
        icon_label.setObjectName("FieldLabel")
        self.edit_icon_btn = QPushButton()
        self.edit_icon_btn.setObjectName("IconEditButton")
        self.edit_icon_btn.setFixedSize(64, 64)
        self.edit_icon_btn.setToolTip("Clicca per scegliere un'icona (blocco o GIF animata)")
        self.edit_icon_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1d26;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QPushButton:hover {
                border-color: #3b82f6;
            }
        """)
        self.edit_icon_btn.clicked.connect(self.choose_icon)
        self.update_edit_icon_display()
        icon_row.addWidget(icon_label)
        icon_row.addStretch()
        icon_row.addWidget(self.edit_icon_btn)
        layout.addLayout(icon_row)

        # Name
        name_label = QLabel("Nome dell'Istanza:")
        name_label.setObjectName("FieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Es. Survival Principale, Modpack...")
        if self.instance and self.instance.get("name"):
            self.name_input.setText(self.instance.get("name"))
        else:
            self.name_input.setText("Vanilla Principale")
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)

        # Version
        version_label = QLabel("Versione di Minecraft:")
        version_label.setObjectName("FieldLabel")
        self.version_combo = MaterialComboBox()
        self.version_combo.setObjectName("VersionSelector")
        layout.addWidget(version_label)
        layout.addWidget(self.version_combo)

        self.snapshot_checkbox = QCheckBox("Mostra Snapshot e versioni storiche")
        self.snapshot_checkbox.setChecked(False)
        self.snapshot_checkbox.toggled.connect(self.populate_versions)
        layout.addWidget(self.snapshot_checkbox)

        # Loader
        loader_label = QLabel("Client Moddato / Loader:")
        loader_label.setObjectName("FieldLabel")
        self.loader_combo = MaterialComboBox()
        self.loader_combo.setObjectName("LoaderSelector")
        for l_label, l_val in [("Vanilla", "vanilla"), ("Fabric", "fabric"), ("Forge", "forge"), ("NeoForge", "neoforge"), ("Quilt", "quilt")]:
            self.loader_combo.addItem(l_label, l_val)
        layout.addWidget(loader_label)
        layout.addWidget(self.loader_combo)

        # Loader Version Container
        self.loader_version_container = QWidget()
        lv_layout = QVBoxLayout(self.loader_version_container)
        lv_layout.setContentsMargins(0, 0, 0, 0)
        lv_layout.setSpacing(6)
        self.loader_version_label = QLabel("Versione Loader:")
        self.loader_version_label.setObjectName("FieldLabel")
        self.loader_version_combo = MaterialComboBox()
        lv_layout.addWidget(self.loader_version_label)
        lv_layout.addWidget(self.loader_version_combo)
        layout.addWidget(self.loader_version_container)

        self.loader_combo.currentIndexChanged.connect(self.on_loader_changed)
        self.version_combo.currentIndexChanged.connect(self.update_loader_versions)

        self.current_instance_version = self.instance.get("version", self.default_version) if self.instance else self.default_version
        self.populate_versions()
        if self.instance:
            idx = self.loader_combo.findData(self.instance.get("loader_type", "vanilla"))
            if idx >= 0:
                self.loader_combo.setCurrentIndex(idx)
        self.on_loader_changed()

        # RAM
        ram_label = QLabel("RAM Allocata per questa istanza:")
        ram_label.setObjectName("FieldLabel")
        layout.addWidget(ram_label)
        ram_row = QHBoxLayout()
        self.ram_slider = QSlider(Qt.Orientation.Horizontal)
        self.ram_slider.setRange(2, 24)
        self.ram_spinbox = QSpinBox()
        self.ram_spinbox.setRange(2, 24)
        self.ram_spinbox.setSuffix(" GB")
        self.ram_spinbox.setFixedWidth(85)
        initial_ram = int(self.instance.get("ram_gb", 4)) if self.instance else 4
        self.ram_slider.setValue(initial_ram)
        self.ram_spinbox.setValue(initial_ram)
        self.ram_slider.valueChanged.connect(self.ram_spinbox.setValue)
        self.ram_spinbox.valueChanged.connect(self.ram_slider.setValue)
        ram_row.addWidget(self.ram_slider, 1)
        ram_row.addWidget(self.ram_spinbox)
        layout.addLayout(ram_row)

        # JVM Args
        jvm_label = QLabel("Argomenti JVM Personalizzati (Opzionale):")
        jvm_label.setObjectName("FieldLabel")
        self.jvm_input = QLineEdit()
        self.jvm_input.setPlaceholderText("Es. -XX:+UseG1GC")
        if self.instance:
            self.jvm_input.setText(self.instance.get("jvm_args", ""))
        layout.addWidget(jvm_label)
        layout.addWidget(self.jvm_input)

        layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        return page

    def create_account_page(self):
        page = QWizardPage()
        page.setTitle("Configura il tuo account")
        page.setSubTitle("Collega un account Microsoft Xbox o aggiungi un profilo offline.")
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        acc_label = QLabel("Account registrati:")
        header_layout.addWidget(acc_label)
        header_layout.addStretch()

        self.add_account_btn = QPushButton("+ Aggiungi Account")
        self.add_account_btn.setObjectName("PrimaryActionButton")
        self.add_account_btn.clicked.connect(self.show_add_account_menu)
        header_layout.addWidget(self.add_account_btn)
        layout.addLayout(header_layout)

        self.accounts_container = QWidget()
        self.accounts_layout = QVBoxLayout(self.accounts_container)
        self.accounts_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.accounts_layout.setContentsMargins(0, 0, 0, 0)
        self.accounts_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidget(self.accounts_container)
        layout.addWidget(scroll, 1)

        self.refresh_accounts_list()
        layout.addStretch()
        return page

    def choose_icon(self):
        from block_icons_dialog import BlockIconSelectorDialog
        dialog = BlockIconSelectorDialog(self)
        dialog.icon_selected.connect(self.on_icon_chosen)
        dialog.exec()

    def on_icon_chosen(self, path):
        if path:
            self.current_icon_path = path
            self.update_edit_icon_display()

    def update_edit_icon_display(self):
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie = None

        if self.current_icon_path and "block_icons" in self.current_icon_path:
            base_name = os.path.basename(self.current_icon_path)
            block_id = os.path.splitext(base_name)[0]
            bundled_gif = resource_path(f"assets/block_icons/{block_id}.gif")
            bundled_png = resource_path(f"assets/block_icons/{block_id}.png")
            if os.path.exists(bundled_gif):
                self.current_icon_path = bundled_gif
            elif os.path.exists(bundled_png):
                self.current_icon_path = bundled_png

        if self.current_icon_path and os.path.exists(self.current_icon_path):
            if self.current_icon_path.lower().endswith(".gif"):
                movie = QMovie(self.current_icon_path, parent=self)
                movie.frameChanged.connect(lambda: self.update_dialog_movie_frame(movie))
                movie.start()
                self.current_movie = movie
                return
            else:
                pix = QPixmap(self.current_icon_path)
                if not pix.isNull():
                    scaled = pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.edit_icon_btn.setIcon(QIcon(scaled))
                    self.edit_icon_btn.setIconSize(QSize(48, 48))
                    return

        icon_path = resource_path("assets/nav_instances.svg")
        if os.path.exists(icon_path):
            self.edit_icon_btn.setIcon(QIcon(icon_path))
            self.edit_icon_btn.setIconSize(QSize(32, 32))

    def update_dialog_movie_frame(self, movie):
        if self.edit_icon_btn and movie:
            try:
                current_pix = movie.currentPixmap()
                if not current_pix.isNull():
                    scaled = current_pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.edit_icon_btn.setIcon(QIcon(scaled))
                    self.edit_icon_btn.setIconSize(QSize(48, 48))
            except RuntimeError:
                pass

    def on_loader_changed(self):
        loader_type = self.loader_combo.currentData()
        is_modded = loader_type != "vanilla"
        self.loader_version_container.setVisible(is_modded)
        self.populate_versions()
        self.update_loader_versions()

    def set_available_versions(self, versions, preferred_version=None):
        self.available_versions = versions or []
        current_data = self.version_combo.currentData()
        self.populate_versions()
        if current_data:
            idx = self.version_combo.findData(current_data)
            if idx >= 0:
                self.version_combo.setCurrentIndex(idx)
        elif preferred_version:
            idx = self.version_combo.findData(preferred_version)
            if idx >= 0:
                self.version_combo.setCurrentIndex(idx)

    def populate_versions(self):
        current_version = self.version_combo.currentData() or self.current_instance_version
        show_snapshots = self.snapshot_checkbox.isChecked()
        loader_type = self.loader_combo.currentData() or "vanilla"
        loader_prefix = f"{loader_type.capitalize()} " if loader_type != "vanilla" else ""

        self.version_combo.blockSignals(True)
        self.version_combo.clear()

        icon_path = resource_path("assets/nav_versions.svg")

        if loader_type != "vanilla":
            try:
                import minecraft_launcher_lib as mll
                loader = mll.mod_loader.get_mod_loader(loader_type)
                mc_versions = loader.get_minecraft_versions(stable_only=not show_snapshots)
                for ver_str in mc_versions:
                    label = f"{loader_prefix}{ver_str}   •   Release"
                    self.version_combo.addItem(QIcon(icon_path), label, ver_str)
            except Exception as e:
                for version in self.available_versions:
                    version_id = version.get("id", "") if isinstance(version, dict) else str(version)
                    version_type = version.get("type", "release") if isinstance(version, dict) else "release"
                    if not show_snapshots and version_type != "release" and version_id != self.current_instance_version:
                        continue
                    label = f"{loader_prefix}{version_id}   •   {version_type.capitalize()}"
                    self.version_combo.addItem(QIcon(icon_path), label, version_id)
        else:
            for version in self.available_versions:
                version_id = version.get("id", "") if isinstance(version, dict) else str(version)
                version_type = version.get("type", "release") if isinstance(version, dict) else "release"
                if not show_snapshots and version_type != "release" and version_id != self.current_instance_version:
                    continue
                label = f"{version_id}   •   {version_type.capitalize()}"
                self.version_combo.addItem(QIcon(icon_path), label, version_id)

        selected_index = self.version_combo.findData(current_version)
        if selected_index >= 0:
            self.version_combo.setCurrentIndex(selected_index)
        elif self.version_combo.count() > 0:
            self.version_combo.setCurrentIndex(0)

        self.version_combo.blockSignals(False)

    def update_loader_versions(self):
        mc_version = self.version_combo.currentData()
        loader_type = self.loader_combo.currentData()

        if not loader_type or loader_type == "vanilla" or not mc_version:
            if hasattr(self, 'loader_version_container'):
                self.loader_version_container.setVisible(False)
            return

        self.loader_version_container.setVisible(True)
        self.loader_version_combo.clear()
        self.loader_version_combo.addItem("Caricamento versioni...", None)
        self.loader_version_combo.setEnabled(False)

        self.fetch_worker = LoaderFetchWorker(loader_type, mc_version)
        self.fetch_worker.finished.connect(self.populate_loader_combo)

        thread = threading.Thread(target=self.fetch_worker.run, daemon=True)
        thread.start()

    def populate_loader_combo(self, versions):
        self.loader_version_combo.clear()
        self.loader_version_combo.setEnabled(True)

        if not versions:
            self.loader_version_combo.addItem("Nessuna versione loader trovata", "")
            return

        for v in versions:
            v_id = v.get("id") if isinstance(v, dict) else str(v)
            v_name = v.get("name") if isinstance(v, dict) else str(v)
            display_name = f"{self.loader_combo.currentText()} {v_name}"
            self.loader_version_combo.addItem(display_name, v_id)

        self.loader_version_combo.setCurrentIndex(0)

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

        if not self.account_manager:
            return

        accounts = self.account_manager.get_all_accounts()
        curr_id = self.account_manager.accounts.get("last_used")

        if not accounts:
            no_accounts_label = QLabel("Nessun account registrato.\nClicca su '+ Aggiungi Account' per configurarlo.")
            no_accounts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_accounts_label.setStyleSheet("color: #94a3b8; font-size: 10pt; padding: 20px;")
            self.accounts_layout.addWidget(no_accounts_label)
            return

        for account_id, data in accounts.items():
            is_active = (account_id == curr_id)
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: #16181f;
                    border: 1px solid #282c39;
                    border-radius: 8px;
                }
            """)
            if is_active:
                frame.setStyleSheet("""
                    QFrame {
                        background-color: #152238;
                        border: 1px solid #282c39;
                        border-radius: 8px;
                    }
                """)

            frame_layout = QHBoxLayout(frame)
            frame_layout.setContentsMargins(12, 8, 12, 8)
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
            name_label.setStyleSheet("background: transparent; border: none; color: #f8fafc;")

            acc_type = "Microsoft Xbox" if data['type'] == 'microsoft' else "Offline"
            type_color = "#38bdf8" if data['type'] == 'microsoft' else "#94a3b8"
            type_label = QLabel(f"<span style='color: {type_color}; font-size: 9pt;'>{acc_type}</span>")
            type_label.setStyleSheet("background: transparent; border: none;")

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

            if data['type'] == 'microsoft':
                self.load_head_image_for_dialog(data.get('username'), head_label, user_uuid=data.get('uuid'))
            else:
                steve_path = resource_path("assets/steve_head.png")
                steve_pix = QPixmap(steve_path)
                if steve_pix.isNull():
                    steve_pix = create_steve_avatar(36)
                head_label.setPixmap(steve_pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def load_head_image_for_dialog(self, identifier, target_label, user_uuid=None):
        if not (identifier or user_uuid) or not target_label:
            return
        heads_folder = getattr(self, 'heads_folder', None) or getattr(self.parent(), 'heads_folder', os.path.expanduser("~/.cignolauncher/heads"))
        key = identifier or user_uuid
        cached_path = os.path.join(heads_folder, f"{key}.png")
        if os.path.exists(cached_path) and os.path.getsize(cached_path) > 100:
            pixmap = QPixmap(cached_path)
            if not pixmap.isNull():
                target_label.setPixmap(pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                return
        steve_path = resource_path("assets/steve_head.png")
        steve_pix = QPixmap(steve_path)
        if steve_pix.isNull():
            steve_pix = create_steve_avatar(36)
        target_label.setPixmap(steve_pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        def fetch_and_set():
            pix = download_head_pixmap(identifier, heads_folder, user_uuid=user_uuid)
            if pix and not pix.isNull():
                scaled = pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                QTimer.singleShot(0, lambda: target_label.setPixmap(scaled))

        threading.Thread(target=fetch_and_set, daemon=True).start()

    def use_account(self, account_id):
        if self.account_manager:
            self.account_manager.switch_account(account_id)
            self.refresh_accounts_list()
            if hasattr(self.parent(), 'update_account_badge'):
                self.parent().update_account_badge()

    def remove_account(self, account_id):
        if self.account_manager:
            self.account_manager.remove_account(account_id)
            self.refresh_accounts_list()
            if hasattr(self.parent(), 'update_account_badge'):
                self.parent().update_account_badge()

    def prompt_offline_login(self):
        username, ok = custom_text_input(self, "Aggiungi Account Offline", "Inserisci il nome giocatore:")
        if ok and username:
            clean_name = username.strip()
            if not (3 <= len(clean_name) <= 16):
                show_warning(self, "Nome non valido", "Il nome utente deve avere una lunghezza compresa tra 3 e 16 caratteri.")
                return
            if self.account_manager:
                self.account_manager.add_offline_account(clean_name)
                self.refresh_accounts_list()
                if hasattr(self.parent(), 'update_account_badge'):
                    self.parent().update_account_badge()

    def microsoft_login(self):
        client_id = getattr(self.parent(), 'AZURE_CLIENT_ID', "00000000402b5328")
        client_secret = getattr(self.parent(), 'AZURE_CLIENT_SECRET', "")
        if not client_id or "your-" in client_id:
            QMessageBox.critical(self, "Configurazione Azure Mancante", "I parametri AZURE_CLIENT_ID non sono impostati.")
            return

        self.add_account_btn.setEnabled(False)

        self.login_thread = QThread(self)
        self.login_worker = MicrosoftLoginWorker(client_id, client_secret)
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
        if self.account_manager:
            self.account_manager.add_microsoft_account(account_data)
        username = account_data.get('name')
        uuid_str = account_data.get('id')
        if username or uuid_str:
            download_head_pixmap(username, self.heads_folder, user_uuid=uuid_str)

        self.refresh_accounts_list()
        self.add_account_btn.setEnabled(True)
        if hasattr(self.parent(), 'update_account_badge'):
            self.parent().update_account_badge()

    def on_login_error(self, err_msg):
        QMessageBox.critical(self, "Errore di Accesso", f"Impossibile completare il login Microsoft:\n{err_msg}")
        self.add_account_btn.setEnabled(True)

    def create_ready_page(self):
        page = QWizardPage()
        page.setTitle("Tutto pronto")
        page.setSubTitle("L'istanza e l'account sono pronti.")
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        summary = QLabel(
            "CignoLauncher ha configurato la tua prima istanza e l'account.\n"
            "Clicca su 'Inizia' per aprire la schermata principale e iniziare a giocare."
        )
        summary.setWordWrap(True)
        summary.setObjectName("WizardBody")
        layout.addWidget(summary)
        layout.addStretch()
        return page

    def accept(self):
        name = self.name_input.text().strip() or "Vanilla Principale"
        version = self.version_combo.currentData() or self.version_combo.currentText().split("•")[0].strip() or (self.version_combo.itemData(0) if self.version_combo.count() > 0 else "")
        loader_type = self.loader_combo.currentData() or "vanilla"
        loader_version = self.loader_version_combo.currentData() if loader_type != "vanilla" else ""
        ram_gb = self.ram_spinbox.value()
        jvm_args = self.jvm_input.text().strip()

        if self.instance_manager:
            if self.instance and isinstance(self.instance, dict) and self.instance.get("id"):
                self.instance_manager.update_instance(
                    self.instance["id"],
                    name=name,
                    version=version,
                    loader_type=loader_type,
                    loader_version=loader_version,
                    ram_gb=ram_gb,
                    jvm_args=jvm_args,
                    icon=self.current_icon_path
                )
            else:
                new_inst = self.instance_manager.create_instance(
                    name=name,
                    version=version,
                    loader_type=loader_type,
                    loader_version=loader_version,
                    ram_gb=ram_gb,
                    jvm_args=jvm_args,
                    set_as_current=True
                )
                if new_inst and self.current_icon_path:
                    self.instance_manager.update_instance(new_inst["id"], icon=self.current_icon_path)

        self.instance_name = name
        self.instance_version = version
        self.instance_ram = ram_gb
        self.profile_mode = "offline" if (self.account_manager and self.account_manager.current_account and self.account_manager.current_account.get("type") == "offline") else "online"

        super().accept()

    @staticmethod
    def stylesheet(arrow_path, up_arrow_path="assets/chevron_up.svg"):
        return f"""
            QWizard {{
                background-color: #0f1115;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            QWizardPage {{
                background-color: #0f1115;
            }}
            QLabel {{
                background-color: transparent;
                color: #f1f5f9;
            }}
            QWizardPage > QLabel {{
                font-size: 10pt;
                color: #94a3b8;
            }}
            QLabel#DialogHeader {{
                font-size: 15pt;
                font-weight: 800;
                color: #38bdf8;
                margin-bottom: 5px;
            }}
            QLabel#FieldLabel {{
                font-size: 9pt;
                font-weight: 600;
                color: #cbd5e1;
            }}
            QLabel#WizardBody {{
                color: #cbd5e1;
                font-size: 11pt;
                line-height: 1.4;
            }}
            QLineEdit, QComboBox {{
                background-color: #1a1d26;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 26px 4px 10px;
                font-size: 9pt;
            }}
            QComboBox::drop-down {{
                width: 22px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: url({arrow_path});
                width: 10px;
                height: 6px;
            }}
            QComboBox QAbstractItemView {{
                min-width: 240px;
                outline: none;
                background-color: #1a1d26;
                color: #ffffff;
                selection-background-color: #2563eb;
                border: 1px solid #334155;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid #3b82f6;
            }}
            QCheckBox {{
                color: #aebbd0;
                spacing: 8px;
                font-size: 9pt;
                border: none;
                background: transparent;
            }}
            QCheckBox:hover {{
                border: none;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid #52627a;
                border-radius: 5px;
                background-color: #1a1d26;
            }}
            QCheckBox::indicator:hover {{
                border-color: #60a5fa;
            }}
            QCheckBox::indicator:checked {{
                image: url(assets/action_check.svg);
                background-color: #3578e5;
                border-color: #60a5fa;
            }}
            QSpinBox {{
                background-color: #1a1d26;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                font-size: 10pt;
                font-weight: 700;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: #1a1d26;
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: #3b82f6;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: #38bdf8;
                border: none;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: #60a5fa;
            }}
            QPushButton#PrimaryButton, QPushButton#PrimaryActionButton {{
                background-color: #10b981;
                color: white;
                font-weight: 700;
                padding: 6px 14px;
                border: none;
                border-radius: 6px;
                font-size: 9pt;
                min-height: 28px;
            }}
            QPushButton#PrimaryButton:hover, QPushButton#PrimaryActionButton:hover {{
                background-color: #059669;
            }}
            QPushButton#SecondaryButton {{
                background-color: #1f232d;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 9pt;
                min-height: 28px;
            }}
            QPushButton#SecondaryButton:hover {{
                background-color: #2a303e;
                color: white;
            }}
            QPushButton#RemoveButton {{
                background-color: #7f2930;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 9pt;
                min-height: 28px;
            }}
            QPushButton#IconEditButton {{
                background-color: #1a1d26;
                border: 1px solid #334155;
                border-radius: 6px;
                min-width: 64px;
                min-height: 64px;
                max-width: 64px;
                max-height: 64px;
                padding: 0px;
            }}
            QPushButton#IconEditButton:hover {{
                border-color: #3b82f6;
            }}
            QWizard QPushButton {{
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 9pt;
                font-weight: 600;
                min-height: 28px;
                min-width: 70px;
                padding: 5px 12px;
            }}
            QWizard QPushButton:hover {{
                background-color: #1d4ed8;
            }}
            QWizard QPushButton:disabled {{
                background-color: #1e222d;
                color: #64748b;
            }}
        """.replace("__DOWN_ARROW__", arrow_path).replace("__UP_ARROW__", up_arrow_path)
