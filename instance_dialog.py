import os
import sys
import subprocess
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QSpinBox, QSlider, QFrame, QMessageBox, QCheckBox,
    QListWidget, QListWidgetItem, QStackedWidget, QWidget, QSizePolicy
)
from PyQt6.QtGui import QIcon, QFont, QColor
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from ui_controls import MaterialComboBox
from dialog_utils import ask_confirmation, show_warning
from utils import resource_path, parse_version_key
from custom_window import CustomWindowMixin


def set_svg_icon(button, asset_name, size=18):
    icon_path = resource_path(f"assets/{asset_name}")
    if os.path.exists(icon_path):
        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(size, size))

class LoaderFetchWorker(QObject):
    finished = pyqtSignal(list)

    def __init__(self, loader_type, mc_version):
        super().__init__()
        self.loader_type = loader_type
        self.mc_version = mc_version

    def run(self):
        try:
            import minecraft_launcher_lib as mll
            loader = mll.mod_loader.get_mod_loader(self.loader_type)
            versions = loader.get_loader_versions(self.mc_version, stable_only=True)
            self.finished.emit(versions if isinstance(versions, list) else [])
        except Exception as e:
            print(f"[LoaderFetchWorker] Errore recupero versioni: {e}")
            self.finished.emit([])


class InstanceEditDialog(QDialog, CustomWindowMixin):
    """Dialogo per creare o modificare una singola istanza di Minecraft."""
    def __init__(self, parent, instance_manager, available_versions, instance=None):
        super().__init__(parent)
        self.instance_manager = instance_manager
        self.available_versions = available_versions
        self.instance = instance  # Se None, modalità creazione; altrimenti modifica
        self.created_instance = None
        self.current_icon_path = self.instance.get("icon", "") if instance is not None else ""
        self.current_movie = None

        self.setupUi()
        self.apply_stylesheet()

    def setupUi(self):
        is_edit = self.instance is not None
        title_text = "Modifica Istanza" if is_edit else "Crea Nuova Istanza"
        self.setWindowTitle(title_text)
        self.setMinimumSize(460, 630)
        self.resize(520, 660)

        self.init_custom_frame(title=title_text, icon=self.windowIcon(), show_maximize=False)

        main_layout = self.content_layout
        main_layout.setContentsMargins(20, 14, 20, 14)
        main_layout.setSpacing(10)

        # Icona dell'Istanza
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
        main_layout.addLayout(icon_row)

        # 1. Nome istanza
        name_label = QLabel("Nome dell'Istanza:")
        name_label.setObjectName("FieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Es. La mia Survival, Modpack Fabric...")
        if is_edit:
            self.name_input.setText(self.instance.get("name", ""))
        else:
            self.name_input.setText("")
        main_layout.addWidget(name_label)
        main_layout.addWidget(self.name_input)

        # 2. Versione Minecraft
        self.version_label = QLabel("Versione di Minecraft:")
        self.version_label.setObjectName("FieldLabel")
        self.version_combo = MaterialComboBox()
        self.version_combo.setObjectName("VersionSelector")
        main_layout.addWidget(self.version_label)
        main_layout.addWidget(self.version_combo)

        self.snapshot_checkbox = QCheckBox("Mostra Snapshot e versioni storiche")
        self.snapshot_checkbox.setChecked(False)
        self.snapshot_checkbox.toggled.connect(self.populate_versions)
        main_layout.addWidget(self.snapshot_checkbox)

        # 3. Client Moddato / Loader
        loader_label = QLabel("Client Moddato / Loader:")
        loader_label.setObjectName("FieldLabel")
        self.loader_combo = MaterialComboBox()
        self.loader_combo.setObjectName("LoaderSelector")
        
        loaders = [
            ("Vanilla", "vanilla"),
            ("Fabric", "fabric"),
            ("Forge", "forge"),
            ("NeoForge", "neoforge"),
            ("Quilt", "quilt")
        ]
        for label, val in loaders:
            self.loader_combo.addItem(label, val)
        
        main_layout.addWidget(loader_label)
        main_layout.addWidget(self.loader_combo)

        # 3b. Versione specifica del Loader (Contenitore per evitare salti di layout)
        self.loader_version_container = QWidget()
        lv_layout = QVBoxLayout(self.loader_version_container)
        lv_layout.setContentsMargins(0, 0, 0, 0)
        lv_layout.setSpacing(8)
        
        self.loader_version_label = QLabel("Versione Loader:")
        self.loader_version_label.setObjectName("FieldLabel")
        self.loader_version_combo = MaterialComboBox()
        
        lv_layout.addWidget(self.loader_version_label)
        lv_layout.addWidget(self.loader_version_combo)
        main_layout.addWidget(self.loader_version_container)
        
        # Connessioni
        self.loader_combo.currentIndexChanged.connect(self.on_loader_changed)
        self.version_combo.currentIndexChanged.connect(self.update_loader_versions)
        
        # Popolamento iniziale
        self.current_instance_version = self.instance.get("version", "") if is_edit else ""
        self.populate_versions()
        
        if is_edit:
            idx = self.loader_combo.findData(self.instance.get("loader_type", "vanilla"))
            self.loader_combo.setCurrentIndex(idx)
        
        self.on_loader_changed() # Imposta visibilità corretta

        # 4. RAM Allocata (GB)
        ram_label = QLabel("RAM Allocata per questa istanza:")
        ram_label.setObjectName("FieldLabel")
        main_layout.addWidget(ram_label)

        ram_row = QHBoxLayout()
        self.ram_slider = QSlider(Qt.Orientation.Horizontal)
        self.ram_slider.setRange(2, 24)

        self.ram_spinbox = QSpinBox()
        self.ram_spinbox.setRange(2, 24)
        self.ram_spinbox.setSuffix(" GB")
        self.ram_spinbox.setFixedWidth(85)

        initial_ram = self.instance.get("ram_gb", 4) if is_edit else 4
        self.ram_slider.setValue(initial_ram)
        self.ram_spinbox.setValue(initial_ram)

        self.ram_slider.valueChanged.connect(self.ram_spinbox.setValue)
        self.ram_spinbox.valueChanged.connect(self.ram_slider.setValue)

        ram_row.addWidget(self.ram_slider, 1)
        ram_row.addWidget(self.ram_spinbox)
        main_layout.addLayout(ram_row)

        # 4. Argomenti JVM opzionali
        jvm_label = QLabel("Argomenti JVM Personalizzati (Opzionale):")
        jvm_label.setObjectName("FieldLabel")
        self.jvm_input = QLineEdit()
        self.jvm_input.setPlaceholderText("Es. -XX:+UseG1GC")
        if is_edit:
            self.jvm_input.setText(self.instance.get("jvm_args", ""))
        main_layout.addWidget(jvm_label)
        main_layout.addWidget(self.jvm_input)

        main_layout.addStretch()

        # Pulsanti Azione
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Annulla")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Salva Istanza" if is_edit else "Crea Istanza")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.save_instance)
        btn_row.addWidget(save_btn)

        main_layout.addLayout(btn_row)

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
                from PyQt6.QtGui import QMovie, QIcon
                from PyQt6.QtCore import QSize
                movie = QMovie(self.current_icon_path, parent=self)
                movie.frameChanged.connect(lambda: self.update_dialog_movie_frame(movie))
                movie.start()
                self.current_movie = movie
                return
            else:
                from PyQt6.QtGui import QIcon, QPixmap
                from PyQt6.QtCore import QSize, Qt
                pix = QPixmap(self.current_icon_path)
                if not pix.isNull():
                    scaled = pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.edit_icon_btn.setIcon(QIcon(scaled))
                    self.edit_icon_btn.setIconSize(QSize(48, 48))
                    return

        # Fallback SVG o placeholder
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize
        icon_path = resource_path("assets/nav_instances.svg")
        if os.path.exists(icon_path):
            self.edit_icon_btn.setIcon(QIcon(icon_path))
            self.edit_icon_btn.setIconSize(QSize(32, 32))

    def update_dialog_movie_frame(self, movie):
        if self.edit_icon_btn and movie:
            try:
                from PyQt6.QtGui import QIcon
                from PyQt6.QtCore import QSize, Qt
                current_pix = movie.currentPixmap()
                if not current_pix.isNull():
                    scaled = current_pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.edit_icon_btn.setIcon(QIcon(scaled))
                    self.edit_icon_btn.setIconSize(QSize(48, 48))
            except RuntimeError:
                pass

    def on_loader_changed(self):
        """Gestisce il cambio di loader, filtrando le versioni di Minecraft se necessario."""
        loader_type = self.loader_combo.currentData()
        is_modded = loader_type != "vanilla"
        
        self.loader_version_container.setVisible(is_modded)
        
        # Se cambiamo loader, rinfreschiamo le versioni di MC disponibili
        self.populate_versions()
        self.update_loader_versions()

    def populate_versions(self):
        current_version = self.version_combo.currentData() or self.current_instance_version
        show_snapshots = self.snapshot_checkbox.isChecked()
        loader_type = self.loader_combo.currentData() or "vanilla"
        loader_prefix = f"{loader_type.capitalize()} " if loader_type != "vanilla" else ""
        
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        
        icon_path = resource_path("assets/nav_versions.svg")

        # Se abbiamo un loader moddato, possiamo interrogare direttamente le versioni supportate
        if loader_type != "vanilla":
            try:
                import minecraft_launcher_lib as mll
                loader = mll.mod_loader.get_mod_loader(loader_type)
                mc_versions = loader.get_minecraft_versions(stable_only=not show_snapshots)
                try:
                    mc_versions = sorted(mc_versions, key=parse_version_key, reverse=True)
                except Exception:
                    mc_versions = sorted(mc_versions, reverse=True)

                for ver_str in mc_versions:
                    label = f"{loader_prefix}{ver_str}   •   Release"
                    self.version_combo.addItem(QIcon(icon_path), label, ver_str)
            except Exception as e:
                print(f"[populate_versions] Errore recupero versioni moddate: {e}")
                # Fallback su available_versions
                try:
                    sorted_versions = sorted(self.available_versions, key=parse_version_key, reverse=True)
                except Exception:
                    sorted_versions = self.available_versions

                for version in sorted_versions:
                    version_id = version.get("id", "") if isinstance(version, dict) else str(version)
                    version_type = version.get("type", "release") if isinstance(version, dict) else "release"
                    if not show_snapshots and version_type != "release" and version_id != self.current_instance_version:
                        continue
                    label = f"{loader_prefix}{version_id}   •   {version_type.capitalize()}"
                    self.version_combo.addItem(QIcon(icon_path), label, version_id)
        else:
            # Modalità Vanilla standard
            try:
                sorted_versions = sorted(self.available_versions, key=parse_version_key, reverse=True)
            except Exception:
                sorted_versions = self.available_versions

            for version in sorted_versions:
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

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                background-color: transparent;
                color: #f1f5f9;
            }
            QLabel#DialogHeader {
                font-size: 15pt;
                font-weight: 800;
                color: #38bdf8;
                margin-bottom: 5px;
            }
            QLabel#FieldLabel {
                font-size: 9pt;
                font-weight: 600;
                color: #cbd5e1;
            }
            QLineEdit, QComboBox {
                background-color: #1a1d26;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 26px 4px 10px;
                font-size: 9pt;
            }
            QComboBox::drop-down {
                width: 22px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: url(assets/chevron_down.svg);
                width: 10px;
                height: 6px;
            }
            QComboBox QAbstractItemView {
                min-width: 240px;
                outline: none;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3b82f6;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1d26;
                color: #ffffff;
                selection-background-color: #2563eb;
                border: 1px solid #334155;
            }
            QCheckBox {
                color: #aebbd0;
                spacing: 8px;
                font-size: 9pt;
                border: none;
                background: transparent;
            }
            QCheckBox:hover {
                border: none;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #52627a;
                border-radius: 5px;
                background-color: #1a1d26;
            }
            QCheckBox::indicator:hover {
                border-color: #60a5fa;
            }
            QCheckBox::indicator:checked {
                image: url(assets/action_check.svg);
                background-color: #3578e5;
                border-color: #60a5fa;
            }
            QSpinBox {
                background-color: #1a1d26;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                font-size: 10pt;
                font-weight: 700;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1a1d26;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #38bdf8;
                border: none;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #60a5fa;
            }
            QPushButton#PrimaryButton {
                background-color: #10b981;
                color: white;
                font-weight: 700;
                padding: 9px 20px;
                border: none;
                border-radius: 6px;
                font-size: 10pt;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #059669;
            }
            QPushButton#SecondaryButton {
                background-color: #1f232d;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 9px 16px;
                font-size: 10pt;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #2a303e;
                color: white;
            }
        """)

    def on_loader_changed(self):
        """Gestisce il cambio di loader, filtrando le versioni di Minecraft se necessario."""
        loader_type = self.loader_combo.currentData()
        is_modded = loader_type != "vanilla"
        
        self.loader_version_container.setVisible(is_modded)
        
        # Aggiorna le versioni MC compatibili con il loader
        self.populate_versions()
        self.update_loader_versions()
        
        # Adatta automaticamente le dimensioni della finestra per evitare tagli
        self.adjustSize()

    def update_loader_versions(self):
        """Carica le versioni del loader compatibili con la versione di Minecraft selezionata."""
        mc_version = self.version_combo.currentData()
        loader_type = self.loader_combo.currentData()
        
        if not loader_type or loader_type == "vanilla" or not mc_version:
            if hasattr(self, 'loader_version_container'):
                self.loader_version_container.setVisible(False)
                self.adjustSize()
            return

        self.loader_version_container.setVisible(True)
        self.loader_version_combo.clear()
        self.loader_version_combo.addItem("Caricamento versioni...", None)
        self.loader_version_combo.setEnabled(False)
        self.adjustSize()

        # Usiamo un worker thread con pyqtSignal per sicurezza totale in PyQt6
        self.fetch_worker = LoaderFetchWorker(loader_type, mc_version)
        self.fetch_worker.finished.connect(self.populate_loader_combo)
        
        thread = threading.Thread(target=self.fetch_worker.run, daemon=True)
        thread.start()

    def populate_loader_combo(self, versions):
        self.loader_version_combo.clear()
        self.loader_version_combo.setEnabled(True)
        
        if not versions:
            self.loader_version_combo.addItem("Nessuna versione loader trovata", "")
            self.adjustSize()
            return

        # Ordina le versioni dal più recente al più vecchio (inverso) con parsing semantico
        try:
            versions = sorted(versions, key=parse_version_key, reverse=True)
        except Exception:
            try:
                versions = sorted(versions, key=lambda v: v.get("id") if isinstance(v, dict) else str(v), reverse=True)
            except Exception:
                pass

        for v in versions:
            v_id = v.get("id") if isinstance(v, dict) else str(v)
            v_name = v.get("name") if isinstance(v, dict) else str(v)
            # Mostriamo chiaramente la versione del loader
            display_name = f"{self.loader_combo.currentText()} {v_name}"
            self.loader_version_combo.addItem(display_name, v_id)
        
        # Preseleziona la versione salvata o la prima (più recente)
        if self.instance:
            saved_v = self.instance.get("loader_version")
            idx = self.loader_version_combo.findData(saved_v)
            if idx >= 0:
                self.loader_version_combo.setCurrentIndex(idx)
            else:
                self.loader_version_combo.setCurrentIndex(0)
        else:
            self.loader_version_combo.setCurrentIndex(0)

        self.adjustSize()

    def save_instance(self):
        name = self.name_input.text().strip()
        if not name:
            show_warning(self, "Nome istanza", "Inserisci un nome valido per l'istanza.")
            return

        version = self.version_combo.currentData() or "1.21.4"
        loader_type = self.loader_combo.currentData() or "vanilla"
        loader_version = self.loader_version_combo.currentData() if loader_type != "vanilla" else ""
        ram_gb = self.ram_spinbox.value()
        jvm_args = self.jvm_input.text().strip()

        if self.instance:
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
            self.created_instance = self.instance
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
                new_inst["icon"] = self.current_icon_path
            self.created_instance = new_inst

        self.accept()


class InstanceManagerDialog(QDialog, CustomWindowMixin):
    """Dialogo per visualizzare, selezionare, creare, modificare ed eliminare tutte le istanze."""
    def __init__(self, parent, instance_manager, available_versions):
        super().__init__(parent)
        self.instance_manager = instance_manager
        self.available_versions = available_versions

        self.setupUi()
        self.apply_stylesheet()
        self.refresh_list()

    def setupUi(self):
        self.setWindowTitle("Gestione Istanze Minecraft - CignoLauncher")
        self.setMinimumSize(560, 420)
        self.resize(760, 540)

        self.init_custom_frame(title="Gestione Istanze Minecraft - CignoLauncher", icon=self.windowIcon(), show_maximize=True)

        main_layout = QHBoxLayout()
        self.content_layout.addLayout(main_layout)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(18)

        # Colonna Sinistra: Lista Istanze
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        title = QLabel("Le tue Istanze")
        title.setObjectName("ListHeader")
        left_col.addWidget(title)

        self.instances_list = QListWidget()
        self.instances_list.setObjectName("InstancesList")
        self.instances_list.itemSelectionChanged.connect(self.on_selection_changed)
        left_col.addWidget(self.instances_list, 1)

        new_btn = QPushButton("Crea Nuova Istanza")
        set_svg_icon(new_btn, "action_add.svg")
        new_btn.setObjectName("NewInstanceButton")
        new_btn.setFixedHeight(40)
        new_btn.clicked.connect(self.create_instance)
        left_col.addWidget(new_btn)

        main_layout.addLayout(left_col, 1)

        # Colonna Destra: Dettagli Istanza & Azioni
        self.right_col = QVBoxLayout()
        self.right_col.setSpacing(14)

        self.detail_card = QFrame()
        self.detail_card.setObjectName("DetailCard")
        detail_layout = QVBoxLayout(self.detail_card)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)

        self.detail_name = QLabel("Seleziona un'istanza")
        self.detail_name.setObjectName("DetailName")
        self.detail_version = QLabel("Versione: -")
        self.detail_ram = QLabel("RAM: -")
        self.detail_path = QLabel("Cartella: -")
        self.detail_path.setWordWrap(True)
        self.detail_path.setStyleSheet("color: #64748b; font-size: 8pt;")

        detail_layout.addWidget(self.detail_name)
        detail_layout.addWidget(self.detail_version)
        detail_layout.addWidget(self.detail_ram)
        detail_layout.addWidget(self.detail_path)
        detail_layout.addStretch()

        self.right_col.addWidget(self.detail_card, 1)

        # Pulsanti Azione per l'istanza selezionata
        btn_actions_layout = QVBoxLayout()
        btn_actions_layout.setSpacing(8)

        self.select_active_btn = QPushButton("Imposta come Attiva")
        set_svg_icon(self.select_active_btn, "action_check.svg")
        self.select_active_btn.setObjectName("PrimaryActionButton")
        self.select_active_btn.clicked.connect(self.set_active_instance)

        self.edit_btn = QPushButton("Modifica Istanza")
        set_svg_icon(self.edit_btn, "action_edit.svg")
        self.edit_btn.setObjectName("ActionBtn")
        self.edit_btn.clicked.connect(self.edit_instance)

        self.open_folder_btn = QPushButton("Apri Cartella Salvataggi")
        set_svg_icon(self.open_folder_btn, "action_folder.svg")
        self.open_folder_btn.setObjectName("ActionBtn")
        self.open_folder_btn.clicked.connect(self.open_instance_folder)

        self.delete_btn = QPushButton("Elimina Istanza")
        set_svg_icon(self.delete_btn, "action_delete.svg")
        self.delete_btn.setObjectName("DeleteBtn")
        self.delete_btn.clicked.connect(self.delete_instance)

        btn_actions_layout.addWidget(self.select_active_btn)
        btn_actions_layout.addWidget(self.edit_btn)
        btn_actions_layout.addWidget(self.open_folder_btn)
        btn_actions_layout.addWidget(self.delete_btn)

        self.right_col.addLayout(btn_actions_layout)
        main_layout.addLayout(self.right_col, 1)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                background-color: transparent;
                color: #f1f5f9;
            }
            QLabel#ListHeader {
                font-size: 14pt;
                font-weight: 800;
                color: #ffffff;
            }
            QListWidget#InstancesList {
                background-color: #16181f;
                border: 1px solid #232631;
                border-radius: 8px;
                padding: 6px;
                color: #ffffff;
                font-size: 10pt;
            }
            QListWidget#InstancesList::item {
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 4px;
                min-height: 24px;
            }
            QListWidget#InstancesList::item:hover {
                background-color: #1f232d;
            }
            QListWidget#InstancesList::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QFrame#DetailCard {
                background-color: #16181f;
                border: 1px solid #232631;
                border-radius: 8px;
            }
            QLabel#DetailName {
                font-size: 13pt;
                font-weight: 800;
                color: #38bdf8;
            }
            QPushButton#NewInstanceButton {
                background-color: #3b82f6;
                color: white;
                font-weight: 700;
                border: none;
                border-radius: 6px;
                font-size: 10pt;
            }
            QPushButton#NewInstanceButton:hover {
                background-color: #2563eb;
            }
            QPushButton#PrimaryActionButton {
                background-color: #10b981;
                color: white;
                font-weight: 700;
                padding: 8px;
                border: none;
                border-radius: 6px;
            }
            QPushButton#PrimaryActionButton:hover {
                background-color: #059669;
            }
            QPushButton#ActionBtn {
                background-color: #1f232d;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
                font-weight: 600;
            }
            QPushButton#ActionBtn:hover {
                background-color: #2a303e;
                color: white;
            }
            QPushButton#DeleteBtn {
                background-color: #7f1d1d;
                color: #fca5a5;
                border: 1px solid #991b1b;
                border-radius: 6px;
                padding: 8px;
                font-weight: 600;
            }
            QPushButton#DeleteBtn:hover {
                background-color: #991b1b;
                color: white;
            }
        """)

    def refresh_list(self):
        self.instances_list.clear()
        instances = self.instance_manager.get_instances()
        current = self.instance_manager.get_current_instance()
        curr_id = current.get("id") if current else None

        ordered_instances = sorted(
            instances.items(),
            key=lambda entry: entry[1].get("created_at", ""),
            reverse=True,
        )
        for inst_id, inst in ordered_instances:
            name = inst.get("name", "Istanza")
            ver = inst.get("version", "Vanilla")
            is_active = (inst_id == curr_id)

            item = QListWidgetItem(f"{name}  •  {ver}")
            item.setData(Qt.ItemDataRole.UserRole, inst_id)
            if is_active:
                item.setIcon(QIcon(resource_path("assets/action_check.svg")))
            self.instances_list.addItem(item)

            if is_active:
                self.instances_list.setCurrentItem(item)

        if not instances:
            self.on_selection_changed()

    def get_selected_instance(self):
        curr_item = self.instances_list.currentItem()
        if not curr_item:
            return None
        inst_id = curr_item.data(Qt.ItemDataRole.UserRole)
        instances = self.instance_manager.get_instances()
        return instances.get(inst_id)

    def on_selection_changed(self):
        inst = self.get_selected_instance()
        has_sel = inst is not None
        self.select_active_btn.setEnabled(has_sel)
        self.edit_btn.setEnabled(has_sel)
        self.open_folder_btn.setEnabled(has_sel)
        self.delete_btn.setEnabled(has_sel)

        if inst:
            self.detail_name.setText(inst.get("name", "Istanza"))
            self.detail_version.setText(f"Versione Minecraft: <b>{inst.get('version', '')}</b>")
            self.detail_ram.setText(f"Memoria RAM: <b>{inst.get('ram_gb', 4)} GB</b>")
            self.detail_path.setText(f"Percorso: {inst.get('path', '')}")
        else:
            self.detail_name.setText("Nessuna istanza selezionata")
            self.detail_version.setText("Versione: -")
            self.detail_ram.setText("RAM: -")
            self.detail_path.setText("Cartella: -")

    def create_instance(self):
        dlg = InstanceEditDialog(self, self.instance_manager, self.available_versions)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_list()

    def edit_instance(self):
        inst = self.get_selected_instance()
        if not inst:
            return
        dlg = InstanceEditDialog(self, self.instance_manager, self.available_versions, instance=inst)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_list()

    def set_active_instance(self):
        inst = self.get_selected_instance()
        if not inst:
            return
        self.instance_manager.set_current_instance(inst["id"])
        self.refresh_list()
        self.accept()

    def open_instance_folder(self):
        inst = self.get_selected_instance()
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

    def delete_instance(self):
        inst = self.get_selected_instance()
        if not inst:
            return
        if len(self.instance_manager.get_instances()) <= 1:
            show_warning(self, "Impossibile eliminare", "Non puoi eliminare l'unica istanza rimasta.")
            return

        confirmed = ask_confirmation(
            self,
            "Elimina istanza",
            f"Sei sicuro di voler eliminare l'istanza '{inst.get('name')}'?\nI mondi e salvataggi in questa istanza verranno rimossi.",
            destructive=True,
        )
        if confirmed:
            self.instance_manager.delete_instance(inst["id"], delete_files=True)
            self.refresh_list()
