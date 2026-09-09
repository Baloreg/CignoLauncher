import os
import shutil
import threading
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QListWidget, QListWidgetItem, QWidget, QFrame,
    QProgressBar, QMessageBox, QScrollArea, QSplitter, QComboBox
)

from modrinth_manager import ModrinthManager
from dialog_utils import ask_confirmation, show_warning
from utils import resource_path
from custom_window import CustomWindowMixin

def set_svg_icon(widget, icon_name, size=18):
    """Utility per impostare un'icona SVG da assets a un widget."""
    icon_path = resource_path(f"assets/{icon_name}")
    if os.path.exists(icon_path):
        widget.setIcon(QIcon(icon_path))
        from PyQt6.QtCore import QSize
        widget.setIconSize(QSize(size, size))

def show_info(parent, title, message):
    QMessageBox.information(parent, title, message)

def show_error(parent, title, message):
    QMessageBox.critical(parent, title, message)

class DownloadWorker(QObject):
    finished = pyqtSignal(bool, str, str)  # success, message, file_path
    progress = pyqtSignal(int)

    def __init__(self, project_id, project_title, target_folder, mc_version, loader):
        super().__init__()
        self.project_id = project_id
        self.project_title = project_title
        self.target_folder = target_folder
        self.mc_version = mc_version
        self.loader = loader

    def run(self):
        info = ModrinthManager.get_primary_file_info(self.project_id, self.mc_version, self.loader)
        if not info or not info.get("url"):
            self.finished.emit(False, f"Nessun file compatibile trovato su Modrinth per '{self.project_title}'.", "")
            return

        filename = info.get("filename", f"{self.project_id}.jar")
        dest_path = os.path.join(self.target_folder, filename)

        def prog_cb(pct):
            self.progress.emit(pct)

        success = ModrinthManager.download_file(info["url"], dest_path, progress_callback=prog_cb)
        if success:
            self.finished.emit(True, f"'{self.project_title}' installato con successo ({filename})!", dest_path)
        else:
            self.finished.emit(False, f"Errore durante il download di '{self.project_title}'.", "")


class SearchWorker(QObject):
    finished = pyqtSignal(list, int, int)  # hits, total_hits, offset
    error = pyqtSignal(str)

    def __init__(self, query, project_type, mc_version, loader, category, sort_by, offset):
        super().__init__()
        self.query = query
        self.project_type = project_type
        self.mc_version = mc_version
        self.loader = loader
        self.category = category
        self.sort_by = sort_by
        self.offset = offset

    def run(self):
        res = ModrinthManager.search(
            query=self.query,
            project_type=self.project_type,
            minecraft_version=self.mc_version,
            loader=self.loader,
            category=self.category,
            sort_by=self.sort_by,
            offset=self.offset
        )
        if "error" in res:
            self.error.emit(res["error"])
        else:
            self.finished.emit(res.get("hits", []), res.get("total_hits", 0), res.get("offset", 0))


class ModrinthItemCard(QFrame):
    """Card grafica per visualizzare un risultato di ricerca Modrinth con download integrato."""
    installed_success = pyqtSignal(str)  # filename

    def __init__(self, hit_data, target_folder, mc_version, loader, installed_filenames=None, parent=None):
        super().__init__(parent)
        self.hit_data = hit_data
        self.target_folder = target_folder
        self.mc_version = mc_version
        self.loader = loader
        self.installed_filenames = [f.lower() for f in (installed_filenames or [])]
        self.setObjectName("ModrinthCard")
        self.setupUi()

    def setupUi(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)

        # Icona del progetto
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setStyleSheet("background-color: #334155; border-radius: 8px;")

        icon_url = self.hit_data.get("icon_url")
        if icon_url:
            threading.Thread(target=self.load_icon, args=(icon_url,), daemon=True).start()

        layout.addWidget(self.icon_label)

        # Info del progetto
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title = self.hit_data.get("title", "Senza Titolo")
        author = self.hit_data.get("author", "Sconosciuto")
        downloads = self.hit_data.get("downloads", 0)
        description = self.hit_data.get("description", "")
        slug = self.hit_data.get("slug", "").lower()
        project_id = self.hit_data.get("project_id", "").lower()

        title_label = QLabel(f"<b>{title}</b> <span style='color: #94a3b8;'>di {author}</span>")
        title_label.setStyleSheet("font-size: 11pt; color: #f8fafc;")

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #94a3b8; font-size: 8.5pt;")

        meta_label = QLabel(f"Download: {downloads:,}")
        meta_label.setStyleSheet("color: #38bdf8; font-size: 8pt; font-weight: bold;")

        info_layout.addWidget(title_label)
        info_layout.addWidget(desc_label)
        info_layout.addWidget(meta_label)

        layout.addLayout(info_layout, 1)

        # Controllo se è già installato
        is_installed = any(
            slug in fname or project_id in fname or title.lower().replace(" ", "") in fname.replace("-", "").replace("_", "")
            for fname in self.installed_filenames
        )

        # Container destro per Azione (Pulsante o ProgressBar)
        self.action_container = QWidget()
        self.action_container.setStyleSheet("background: transparent;")
        self.action_layout = QVBoxLayout(self.action_container)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(4)
        self.action_container.setFixedWidth(130)

        # Pulsante Installa / Installato
        self.install_btn = QPushButton("Installato" if is_installed else "Installa")
        if is_installed:
            self.install_btn.setEnabled(False)
            self.install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #064e3b;
                    color: #34d399;
                    border: 1px solid #059669;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
            """)
        else:
            self.install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1d4ed8;
                }
            """)
            self.install_btn.clicked.connect(self.start_download)

        self.action_layout.addWidget(self.install_btn)

        # Barra di progresso (nascosta inizialmente)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                background-color: #0f172a;
                text-align: center;
                color: white;
                font-size: 7.5pt;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 5px;
            }
        """)
        self.action_layout.addWidget(self.progress_bar)

        layout.addWidget(self.action_container)

    def start_download(self):
        project_id = self.hit_data.get("project_id")
        title = self.hit_data.get("title", project_id)

        self.install_btn.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        worker = DownloadWorker(
            project_id=project_id,
            project_title=title,
            target_folder=self.target_folder,
            mc_version=self.mc_version,
            loader=self.loader
        )

        def on_progress(pct):
            self.progress_bar.setValue(pct)

        def on_finished(success, message, file_path):
            if success:
                filename = os.path.basename(file_path)
                self.progress_bar.setVisible(False)
                self.install_btn.setVisible(True)
                self.install_btn.setEnabled(False)
                self.install_btn.setText("Installato")
                self.install_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #064e3b;
                        color: #34d399;
                        border: 1px solid #059669;
                        border-radius: 8px;
                        padding: 8px 16px;
                        font-weight: bold;
                    }
                """)
                show_info(self, "Installazione Completata", message)
                self.installed_success.emit(filename)
            else:
                self.progress_bar.setVisible(False)
                self.install_btn.setVisible(True)
                show_error(self, "Errore Installazione", message)

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)

        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

    def set_installed_state(self, filename):
        """Imposta lo stato del pulsante su 'Installato' in tempo reale."""
        self.install_btn.setEnabled(False)
        self.install_btn.setText("Installato")
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #064e3b;
                color: #34d399;
                border: 1px solid #059669;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }
        """)
        try:
            self.install_btn.clicked.disconnect()
        except Exception:
            pass

    def set_uninstalled_state(self):
        """Ripristina lo stato del pulsante su 'Installa' in tempo reale."""
        self.install_btn.setEnabled(True)
        self.install_btn.setText("Installa")
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        try:
            self.install_btn.clicked.disconnect()
        except Exception:
            pass
        self.install_btn.clicked.connect(self.start_download)

    def load_icon(self, url):
        try:
            import requests
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(res.content)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    from PyQt6.QtCore import QMetaObject, Q_ARG
                    QMetaObject.invokeMethod(self.icon_label, "setPixmap", Qt.ConnectionType.QueuedConnection, Q_ARG(QPixmap, scaled))
        except Exception:
            pass


class ModrinthCategoryTab(QWidget):
    """Tab per gestire una specifica categoria: Mod, Resource Pack, o Shader."""

    def __init__(self, instance, category_type, parent=None):
        super().__init__(parent)
        self.instance = instance
        self.category_type = category_type  # 'mod', 'resourcepack', 'shader'
        self.instance_path = instance.get("path", "")
        self.mc_version = instance.get("version", "1.20.4")
        self.loader = instance.get("loader_type", "vanilla")

        # Cartella di destinazione
        folder_names = {
            "mod": "mods",
            "resourcepack": "resourcepacks",
            "shader": "shaderpacks"
        }
        self.target_folder = os.path.join(self.instance_path, folder_names.get(category_type, "mods"))
        os.makedirs(self.target_folder, exist_ok=True)

        self.setupUi()

    def setupUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Sub-tab: Cerca / Installati
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setObjectName("SubTabWidget")

        # Tab 1: Cerca su Modrinth
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(8, 8, 8, 8)
        search_layout.setSpacing(10)

        # Controlli ricerca (Barra superiore)
        search_bar_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(f"Cerca {self.category_type} su Modrinth...")
        self.search_input.returnPressed.connect(lambda: self.perform_search(reset=True))

        # Filtro Categoria
        self.category_combo = QComboBox()
        self.category_combo.addItem("Tutte le categorie", "all")
        if self.category_type == "mod":
            cats = [
                ("Ottimizzazione", "optimization"),
                ("Utility / UI", "utility"),
                ("Mondo / Biomi", "worldgen"),
                ("Gameplay", "gameplay"),
                ("Librerie / API", "library"),
                ("Avventura", "adventure"),
                ("Magia", "magic"),
                ("Tecnologia", "technology")
            ]
        elif self.category_type == "resourcepack":
            cats = [
                ("Texture", "texture"),
                ("Interfaccia", "interface"),
                ("Realistico", "realistic"),
                ("Medievale", "medieval"),
                ("PVP", "pvp")
            ]
        else:
            cats = [
                ("PBR", "pbr"),
                ("Stylized", "stylized"),
                ("Performance", "performance")
            ]
        for name, val in cats:
            self.category_combo.addItem(name, val)
        self.category_combo.currentIndexChanged.connect(lambda: self.perform_search(reset=True))

        # Ordinamento
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Più scaricati", "downloads")
        self.sort_combo.addItem("Più rilevanti", "relevance")
        self.sort_combo.addItem("Più recenti", "newest")
        self.sort_combo.addItem("Aggiornati di recente", "updated")
        self.sort_combo.currentIndexChanged.connect(lambda: self.perform_search(reset=True))

        self.search_btn = QPushButton("Cerca")
        self.search_btn.setObjectName("PrimaryActionButton")
        self.search_btn.clicked.connect(lambda: self.perform_search(reset=True))

        search_bar_layout.addWidget(self.search_input, 2)
        search_bar_layout.addWidget(self.category_combo, 1)
        search_bar_layout.addWidget(self.sort_combo, 1)
        search_bar_layout.addWidget(self.search_btn)
        search_layout.addLayout(search_bar_layout)

        # Area scroll dei risultati
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(8)
        
        # Pulsante Carica Altri (inserito alla fine della lista)
        self.load_more_btn = QPushButton("Carica Altri Risultati")
        self.load_more_btn.setObjectName("SecondaryButton")
        self.load_more_btn.clicked.connect(self.load_more)
        self.load_more_btn.setVisible(False)
        self.load_more_btn.setMinimumHeight(40)

        self.results_layout.addStretch()

        self.results_scroll.setWidget(self.results_container)
        search_layout.addWidget(self.results_scroll, 1)

        self.sub_tabs.addTab(search_widget, "Cerca su Modrinth")

        # Tab 2: Installati
        installed_widget = QWidget()
        installed_layout = QVBoxLayout(installed_widget)
        installed_layout.setContentsMargins(8, 8, 8, 8)
        installed_layout.setSpacing(10)

        inst_top = QHBoxLayout()
        inst_title = QLabel("Elementi installati in questa istanza:")
        inst_title.setStyleSheet("color: #cbd5e1; font-weight: bold;")
        inst_top.addWidget(inst_title)
        inst_top.addStretch()

        refresh_btn = QPushButton("Aggiorna")
        set_svg_icon(refresh_btn, "action_refresh.svg")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.clicked.connect(self.refresh_installed)

        open_folder_btn = QPushButton("Apri Cartella")
        set_svg_icon(open_folder_btn, "action_folder.svg")
        open_folder_btn.setObjectName("SecondaryButton")
        open_folder_btn.clicked.connect(self.open_folder)

        inst_top.addWidget(refresh_btn)
        inst_top.addWidget(open_folder_btn)
        installed_layout.addLayout(inst_top)

        self.installed_list = QListWidget()
        self.installed_list.setObjectName("InstalledFilesList")
        installed_layout.addWidget(self.installed_list, 1)

        self.sub_tabs.addTab(installed_widget, "File Installati")

        layout.addWidget(self.sub_tabs)

        # Esegui una ricerca iniziale popolando i più popolari
        self.perform_search()
        self.refresh_installed()

    def perform_search(self, reset=True):
        if reset:
            self.current_offset = 0
            # Rimuovi tutti i widget eccetto il pulsante load_more e lo stretch finale
            while self.results_layout.count() > 2:
                item = self.results_layout.takeAt(0)
                if item.widget() and item.widget() != self.load_more_btn:
                    item.widget().deleteLater()

        query = self.search_input.text().strip()
        category = self.category_combo.currentData()
        sort_by = self.sort_combo.currentData()

        self.search_btn.setEnabled(False)
        self.search_btn.setText("Ricerca...")

        worker = SearchWorker(
            query=query,
            project_type=self.category_type,
            mc_version=self.mc_version,
            loader=self.loader if self.category_type == "mod" else None,
            category=category,
            sort_by=sort_by,
            offset=self.current_offset
        )
        
        def on_search_done(hits, total_hits, offset):
            self.search_btn.setEnabled(True)
            self.search_btn.setText("Cerca")
            
            # Rimuovi eventuale etichetta "Nessun risultato" precedente
            for i in range(self.results_layout.count()):
                item = self.results_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QLabel) and item.widget() != self.load_more_btn:
                    item.widget().deleteLater()
                    break

            if not hits and offset == 0:
                no_res = QLabel("Nessun risultato trovato per questa configurazione.")
                no_res.setStyleSheet("color: #94a3b8; font-style: italic; padding: 20px;")
                no_res.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.results_layout.insertWidget(0, no_res)
                self.load_more_btn.setVisible(False)
                return

            # Ottieni i file già installati nella cartella
            installed_files = []
            if os.path.exists(self.target_folder):
                installed_files = os.listdir(self.target_folder)

            for hit in hits:
                card = ModrinthItemCard(
                    hit_data=hit,
                    target_folder=self.target_folder,
                    mc_version=self.mc_version,
                    loader=self.loader,
                    installed_filenames=installed_files
                )
                card.installed_success.connect(lambda f: self.refresh_installed())
                # Inserisci prima del pulsante load_more (penultimo elemento prima dello stretch)
                insert_idx = self.results_layout.count() - 2 if self.load_more_btn.isVisible() else self.results_layout.count() - 1
                self.results_layout.insertWidget(max(0, insert_idx), card)

            # Gestione visibilità pulsante Carica Altri (posizionato subito prima dello stretch finale)
            if offset + len(hits) < total_hits:
                self.load_more_btn.setVisible(True)
                self.load_more_btn.setText(f"Carica Altri Risultati ({offset + len(hits)} di {total_hits})")
                # Sposta il pulsante load_more prima dello stretch finale
                self.results_layout.removeWidget(self.load_more_btn)
                self.results_layout.insertWidget(self.results_layout.count() - 1, self.load_more_btn)
            else:
                self.load_more_btn.setVisible(False)

        def on_search_error(err_msg):
            self.search_btn.setEnabled(True)
            self.search_btn.setText("Cerca")
            err_label = QLabel(f"Errore ricerca: {err_msg}")
            err_label.setStyleSheet("color: #ef4444; padding: 20px;")
            self.results_layout.insertWidget(0, err_label)

        worker.finished.connect(on_search_done)
        worker.error.connect(on_search_error)

        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

    def load_more(self):
        self.current_offset += 20
        self.perform_search(reset=False)

    def refresh_installed(self):
        self.installed_list.clear()
        if not os.path.exists(self.target_folder):
            return

        try:
            files = sorted(os.listdir(self.target_folder))
            for f in files:
                file_path = os.path.join(self.target_folder, f)
                if os.path.isfile(file_path) and not f.startswith("."):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    
                    # Widget riga personalizzata con cestino integrato
                    row_widget = QWidget()
                    row_widget.setFixedHeight(40)
                    row_layout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(10, 2, 8, 2)
                    
                    name_label = QLabel(f"{f}  ({size_mb:.2f} MB)")
                    name_label.setStyleSheet("color: #f8fafc; font-size: 9.5pt; background: transparent;")
                    
                    del_btn = QPushButton()
                    set_svg_icon(del_btn, "action_delete.svg", size=14)
                    del_btn.setFixedSize(32, 32)
                    del_btn.setObjectName("DeleteButton")
                    del_btn.setToolTip("Elimina file")
                    del_btn.clicked.connect(lambda checked, fp=file_path, fn=f: self.delete_file(fp, fn))
                    
                    row_layout.addWidget(name_label, 1)
                    row_layout.addWidget(del_btn)
                    
                    item = QListWidgetItem(self.installed_list)
                    item.setSizeHint(row_widget.sizeHint())
                    self.installed_list.addItem(item)
                    self.installed_list.setItemWidget(item, row_widget)

            if self.installed_list.count() == 0:
                item = QListWidgetItem("Nessun elemento installato in questa cartella.")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.installed_list.addItem(item)
        except Exception as e:
            print(f"[ModrinthCategoryTab] Errore lettura file installati: {e}")

    def delete_file(self, file_path, filename):
        if ask_confirmation(self, "Conferma Eliminazione", f"Sei sicuro di voler eliminare '{filename}'?", destructive=True):
            try:
                os.remove(file_path)
                self.refresh_installed()
                
                # Aggiorna in tempo reale le card di ricerca (riabilitando il pulsante Installa)
                for i in range(self.results_layout.count()):
                    item = self.results_layout.itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), ModrinthItemCard):
                        card = item.widget()
                        # Se il nome file eliminato contiene parole chiave del progetto, ripristina lo stato
                        slug = card.hit_data.get("slug", "").lower()
                        proj_id = card.hit_data.get("project_id", "").lower()
                        if slug in filename.lower() or proj_id in filename.lower():
                            card.set_uninstalled_state()

                show_info(self, "Eliminato", f"File '{filename}' eliminato con successo.")
            except Exception as e:
                show_error(self, "Errore", f"Impossibile eliminare il file: {e}")

    def open_folder(self):
        try:
            import subprocess
            import sys
            if sys.platform == "win32":
                os.startfile(self.target_folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.target_folder])
            else:
                subprocess.Popen(["xdg-open", self.target_folder])
        except Exception as e:
            show_error(self, "Errore Cartella", f"Impossibile aprire la cartella: {e}")


class ModManagerDialog(QDialog, CustomWindowMixin):
    """Finestra di gestione completa di Mod, Resource Pack e Shader per un'istanza."""

    def __init__(self, parent, instance):
        super().__init__(parent)
        self.instance = instance
        self.setWindowTitle(f"Gestione Addon - {instance.get('name', 'Istanza')}")
        self.setMinimumSize(780, 580)
        self.resize(850, 620)

        self.setupUi()
        self.apply_stylesheet()

    def setupUi(self):
        self.init_custom_frame(
            title=f"Gestione Addon - {self.instance.get('name', 'Istanza')}",
            icon=self.windowIcon(),
            show_maximize=True
        )

        main_layout = self.content_layout
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header
        header_layout = QHBoxLayout()
        
        inst_name = self.instance.get('name', 'Istanza')
        mc_ver = self.instance.get('version', '1.20.4')
        loader = self.instance.get('loader_type', 'vanilla').capitalize()

        header_layout.addStretch()

        badge_label = QLabel(f"MC {mc_ver} • Loader: {loader}")
        badge_label.setStyleSheet("""
            background-color: #1e293b;
            color: #38bdf8;
            padding: 6px 12px;
            border-radius: 12px;
            font-weight: bold;
            border: 1px solid #334155;
        """)
        header_layout.addWidget(badge_label)

        main_layout.addLayout(header_layout)

        # Tab principali in base al tipo di loader
        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName("MainContentTabWidget")

        loader_type = self.instance.get("loader_type", "vanilla")

        if loader_type != "vanilla":
            # Per client moddati: Mod, Resource Pack, Shader
            self.mods_tab = ModrinthCategoryTab(self.instance, "mod", self)
            self.main_tabs.addTab(self.mods_tab, "Mod")

            self.rp_tab = ModrinthCategoryTab(self.instance, "resourcepack", self)
            self.main_tabs.addTab(self.rp_tab, "Resource Pack")

            self.shaders_tab = ModrinthCategoryTab(self.instance, "shader", self)
            self.main_tabs.addTab(self.shaders_tab, "Shader")
        else:
            # Per istanze Vanilla: solo Resource Pack
            self.rp_tab = ModrinthCategoryTab(self.instance, "resourcepack", self)
            self.main_tabs.addTab(self.rp_tab, "Resource Pack")

        main_layout.addWidget(self.main_tabs, 1)

        # Pulsante Chiusura
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = QPushButton("Chiudi")
        close_btn.setObjectName("PrimaryActionButton")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        main_layout.addLayout(bottom_layout)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #f8fafc;
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }
            QLabel#DialogHeader {
                font-size: 16pt;
                font-weight: bold;
                color: #f8fafc;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background-color: #0f172a;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #0f172a;
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
            QLineEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
                color: #f8fafc;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
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
                padding: 8px 14px;
                outline: none;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #334155;
            }
            QPushButton#DeleteButton {
                background-color: #7f2930;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }
            QPushButton#DeleteButton:hover {
                background-color: #991b1b;
            }
            QFrame#ModrinthCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QFrame#ModrinthCard:hover {
                border: 1px solid #475569;
            }
            QListWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f8fafc;
                padding: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #334155;
                color: #38bdf8;
            }
        """)
