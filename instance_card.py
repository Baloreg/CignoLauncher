import os
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QMovie
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame, QMenu
)
from PyQt6.QtGui import QAction
from block_icons_dialog import BlockIconSelectorDialog
from utils import resource_path

def set_svg_icon(widget, icon_name, size=36):
    """Utility per impostare un'icona SVG da assets a un widget."""
    icon_path = resource_path(f"assets/{icon_name}")
    if os.path.exists(icon_path):
        widget.setIcon(QIcon(icon_path))
        widget.setIconSize(QSize(size, size))

class InstanceCard(QFrame):
    """Card quadrata con supporto per icone fisse e GIF animate in alto."""
    launched = pyqtSignal(str)          # instance_id
    activated = pyqtSignal(str)         # instance_id
    edited = pyqtSignal(str)            # instance_id
    mods_requested = pyqtSignal(str)    # instance_id
    folder_requested = pyqtSignal(str)  # instance_id
    deleted = pyqtSignal(str)           # instance_id
    icon_changed = pyqtSignal(str, str) # instance_id, new_icon_path

    def __init__(self, instance_data, instance_manager=None, is_active=False, parent=None):
        super().__init__(parent)
        self.instance = instance_data
        self.instance_manager = instance_manager
        self.instance_id = instance_data.get("id")
        self.is_active = is_active
        self.current_movie = None
        self.setObjectName("InstanceCardActive" if is_active else "InstanceCard")
        
        self.setFixedSize(210, 255)
        self.setupUi()

    def setupUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Icona Quadrata Centrale in alto
        self.icon_btn = QPushButton()
        self.icon_btn.setFixedSize(80, 80)
        self.icon_btn.setToolTip("Clicca per scegliere un'icona a blocco 3D o personalizzata (anche GIF animate!)")
        self.icon_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a2234;
                border: 2px solid #2e3b52;
                border-radius: 16px;
            }
            QPushButton:hover {
                border-color: #38bdf8;
                background-color: #1e293b;
            }
        """)
        self.load_custom_icon()
        self.icon_btn.clicked.connect(self.change_icon)
        layout.addWidget(self.icon_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # 2. Nome dell'istanza
        name = self.instance.get("name", "Istanza")
        self.title_label = QLabel(name)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 10.5pt; font-weight: bold; color: #f8fafc;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # 3. Dettagli (Versione • Loader)
        version = self.instance.get("version", "1.21.4")
        loader_type = self.instance.get("loader_type", "vanilla").capitalize()

        badge_text = f"{version} • {loader_type}"
        if self.is_active:
            badge_text += " <span style='color: #10b981; font-weight: bold;'>● Attiva</span>"

        self.details_label = QLabel(badge_text)
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details_label.setStyleSheet("color: #94a3b8; font-size: 8pt;")
        layout.addWidget(self.details_label)

        layout.addStretch()

        # 4. Pulsanti Azione in fondo
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)

        # Pulsante Avvia / Gioca
        self.play_btn = QPushButton("Avvia")
        self.play_btn.setObjectName("PrimaryActionButton")
        self.play_btn.setStyleSheet("""
            QPushButton#PrimaryActionButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton#PrimaryActionButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.play_btn.clicked.connect(lambda: self.launched.emit(self.instance_id))
        bottom_row.addWidget(self.play_btn, 1)

        # Pulsante Gestione Mod / Resource Pack dedicato
        loader_type_str = self.instance.get("loader_type", "vanilla").lower()
        btn_text = "Pack" if loader_type_str == "vanilla" else "Mod"
        tooltip_text = "Gestisci Resource Pack" if loader_type_str == "vanilla" else "Gestisci Addon (Mod/Shader/Pack)"

        self.mods_btn = QPushButton(btn_text)
        self.mods_btn.setObjectName("SecondaryButton")
        self.mods_btn.setFixedSize(50, 30)
        self.mods_btn.setToolTip(tooltip_text)
        self.mods_btn.setStyleSheet("""
            QPushButton#SecondaryButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 7px;
                font-weight: bold;
                font-size: 8.5pt;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #334155;
            }
        """)
        self.mods_btn.clicked.connect(lambda: self.mods_requested.emit(self.instance_id))
        bottom_row.addWidget(self.mods_btn)

        # Pulsante Menu Altre Azioni ("...")
        self.more_btn = QPushButton("•••")
        self.more_btn.setObjectName("SecondaryButton")
        self.more_btn.setFixedSize(34, 30)
        self.more_btn.setToolTip("Altre opzioni (Addon, Modifica, Cartella, Elimina)")
        self.more_btn.setStyleSheet("""
            QPushButton#SecondaryButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 7px;
                font-weight: bold;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #334155;
            }
        """)
        self.more_btn.clicked.connect(self.show_context_menu)
        bottom_row.addWidget(self.more_btn)

        layout.addLayout(bottom_row)

    def show_context_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: white;
            }
        """)

        loader_type = self.instance.get("loader_type", "vanilla").lower()
        action_text = "Gestisci Resource Pack" if loader_type == "vanilla" else "Gestisci Addon (Mod/Shader/Pack)"
        addon_action = QAction(action_text, self)
        addon_action.triggered.connect(lambda: self.mods_requested.emit(self.instance_id))
        menu.addAction(addon_action)

        if not self.is_active:
            activate_action = QAction("Imposta come Attiva", self)
            activate_action.triggered.connect(lambda: self.activated.emit(self.instance_id))
            menu.addAction(activate_action)

        edit_action = QAction("Modifica Istanza", self)
        edit_action.triggered.connect(lambda: self.edited.emit(self.instance_id))
        menu.addAction(edit_action)

        folder_action = QAction("Apri Cartella", self)
        folder_action.triggered.connect(lambda: self.folder_requested.emit(self.instance_id))
        menu.addAction(folder_action)

        menu.addSeparator()

        delete_action = QAction("Elimina Istanza", self)
        delete_action.triggered.connect(lambda: self.deleted.emit(self.instance_id))
        menu.addAction(delete_action)

        menu.exec(self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft()))

    def load_custom_icon(self):
        # Ferma eventuale movie precedente
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie = None

        icon_path = self.instance.get("icon", "")
        if icon_path and os.path.exists(icon_path):
            if icon_path.lower().endswith(".gif"):
                # Supporto GIF animate con QMovie
                self.current_movie = QMovie(icon_path, parent=self)
                self.current_movie.setScaledSize(QSize(64, 64))
                self.current_movie.frameChanged.connect(self.update_movie_frame)
                self.current_movie.start()
                return
            else:
                pix = QPixmap(icon_path)
                if not pix.isNull():
                    self.icon_btn.setIcon(QIcon(pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)))
                    self.icon_btn.setIconSize(QSize(64, 64))
                    return

        # Icona SVG di default come placeholder
        set_svg_icon(self.icon_btn, "nav_instances.svg", size=36)

    def update_movie_frame(self):
        if hasattr(self, 'icon_btn') and self.icon_btn and self.current_movie:
            try:
                self.icon_btn.setIcon(QIcon(self.current_movie.currentPixmap()))
                self.icon_btn.setIconSize(QSize(64, 64))
            except RuntimeError:
                pass

    def change_icon(self):
        dialog = BlockIconSelectorDialog(self)
        dialog.icon_selected.connect(lambda path: self.on_icon_chosen(path))
        dialog.exec()

    def on_icon_chosen(self, path):
        if path:
            self.instance["icon"] = path
            if self.instance_manager:
                self.instance_manager.update_instance(self.instance_id, icon=path)
            
            self.load_custom_icon()
            self.icon_changed.emit(self.instance_id, path)
            self.update()
            self.repaint()
