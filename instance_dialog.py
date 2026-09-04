import os
import sys
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QSpinBox, QSlider, QFrame, QMessageBox, QCheckBox,
    QListWidget, QListWidgetItem, QStackedWidget, QWidget, QSizePolicy
)
from PyQt6.QtGui import QIcon, QFont, QColor
from PyQt6.QtCore import Qt, QSize
from ui_controls import MaterialComboBox


def set_svg_icon(button, asset_name, size=18):
    icon_path = os.path.join(os.path.dirname(__file__), "assets", asset_name)
    if os.path.exists(icon_path):
        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(size, size))

class InstanceEditDialog(QDialog):
    """Dialogo per creare o modificare una singola istanza di Minecraft."""
    def __init__(self, parent, instance_manager, available_versions, instance=None):
        super().__init__(parent)
        self.instance_manager = instance_manager
        self.available_versions = available_versions
        self.instance = instance  # Se None, modalità creazione; altrimenti modifica
        self.created_instance = None

        self.setupUi()
        self.apply_stylesheet()

    def setupUi(self):
        is_edit = self.instance is not None
        title_text = "Modifica Istanza" if is_edit else "Crea Nuova Istanza"
        self.setWindowTitle(title_text)
        self.setMinimumSize(420, 380)
        self.resize(500, 460)
        self.setSizeGripEnabled(True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        header = QLabel(title_text)
        header.setObjectName("DialogHeader")
        main_layout.addWidget(header)

        # 1. Nome istanza
        name_label = QLabel("Nome dell'Istanza:")
        name_label.setObjectName("FieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Es. Survival 1.21.4, Hardcore, Modificata...")
        if is_edit:
            self.name_input.setText(self.instance.get("name", ""))
        else:
            self.name_input.setText("Nuova Istanza Vanilla")
        main_layout.addWidget(name_label)
        main_layout.addWidget(self.name_input)

        # 2. Versione Minecraft
        version_label = QLabel("Versione di Minecraft:")
        version_label.setObjectName("FieldLabel")
        self.version_combo = MaterialComboBox()
        self.version_combo.setObjectName("VersionSelector")

        main_layout.addWidget(version_label)
        main_layout.addWidget(self.version_combo)

        self.snapshot_checkbox = QCheckBox("Mostra Snapshot e versioni storiche")
        self.snapshot_checkbox.setChecked(False)
        self.snapshot_checkbox.toggled.connect(self.populate_versions)
        main_layout.addWidget(self.snapshot_checkbox)
        self.current_instance_version = self.instance.get("version", "") if is_edit else ""
        self.populate_versions()

        # 3. RAM Allocata (GB)
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

    def populate_versions(self):
        current_version = self.version_combo.currentData() or self.current_instance_version
        show_snapshots = self.snapshot_checkbox.isChecked()
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        for version in self.available_versions:
            version_id = version.get("id", "") if isinstance(version, dict) else str(version)
            version_type = version.get("type", "release") if isinstance(version, dict) else "release"
            if not show_snapshots and version_type != "release" and version_id != self.current_instance_version:
                continue
            label = f"{version_id}   •   {version_type.capitalize()}"
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "nav_versions.svg")
            self.version_combo.addItem(QIcon(icon_path), label, version_id)
        selected_index = self.version_combo.findData(current_version)
        if selected_index >= 0:
            self.version_combo.setCurrentIndex(selected_index)
        self.version_combo.blockSignals(False)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121316;
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
                background: #60a5fa;
                border: 2px solid #ffffff;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
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

    def save_instance(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Attenzione", "Inserisci un nome valido per l'istanza.")
            return

        version = self.version_combo.currentData() or "1.21.4"
        ram_gb = self.ram_spinbox.value()
        jvm_args = self.jvm_input.text().strip()

        if self.instance:
            self.instance_manager.update_instance(
                self.instance["id"],
                name=name,
                version=version,
                ram_gb=ram_gb,
                jvm_args=jvm_args
            )
            self.created_instance = self.instance
        else:
            self.created_instance = self.instance_manager.create_instance(
                name=name,
                version=version,
                ram_gb=ram_gb,
                jvm_args=jvm_args,
                set_as_current=True
            )

        self.accept()


class InstanceManagerDialog(QDialog):
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
        self.setSizeGripEnabled(True)

        main_layout = QHBoxLayout(self)
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
                background-color: #121316;
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

        for inst_id, inst in instances.items():
            name = inst.get("name", "Istanza")
            ver = inst.get("version", "Vanilla")
            is_active = (inst_id == curr_id)

            item = QListWidgetItem(f"{name}  •  {ver}")
            item.setData(Qt.ItemDataRole.UserRole, inst_id)
            if is_active:
                item.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "assets", "action_check.svg")))
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
            QMessageBox.warning(self, "Attenzione", "Non puoi eliminare l'unica istanza rimasta.")
            return

        reply = QMessageBox.question(
            self, "Elimina Istanza",
            f"Sei sicuro di voler eliminare l'istanza '{inst.get('name')}'?\nI mondi e salvataggi in questa istanza verranno rimossi.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.instance_manager.delete_instance(inst["id"], delete_files=True)
            self.refresh_list()
