import os
import uuid
import urllib.request
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QMovie
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QScrollArea, QWidget, QFileDialog, QLineEdit
)
from dialog_utils import show_warning
from utils import resource_path


MINECRAFT_BLOCKS = [
    {
        "name": "Terra (Dirt)",
        "id": "dirt",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/2/2f/Dirt.png/revision/latest?cb=20220112085643"
    },
    {
        "name": "Blocco d'Erba",
        "id": "grass_block",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/c/c7/Grass_Block.png/revision/latest?cb=20230226144250"
    },
    {
        "name": "Ghiaia",
        "id": "gravel",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9d/Gravel_JE5_BE4.png/revision/latest?cb=20200315183831"
    },
    {
        "name": "Blocco di Magma",
        "id": "magma_block",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/d/d1/Magma_Block_JE2_BE2.gif/revision/latest?cb=20200915183320"
    },
    {
        "name": "Pietra",
        "id": "stone",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/d/d4/Stone.png/revision/latest?cb=20220112085705"
    },
    {
        "name": "Pietra dell'End",
        "id": "end_stone",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/4/43/End_Stone_JE3_BE2.png/revision/latest?cb=20200315175115"
    },
    {
        "name": "Zucca Intagliata",
        "id": "carved_pumpkin",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/8/8e/Carved_Pumpkin_%28S%29_JE4.png/revision/latest?cb=20210112033634"
    },
    {
        "name": "Tronco di Quercia",
        "id": "oak_log",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/e/e9/Oak_Log_%28UD%29_JE5_BE3.png/revision/latest?cb=20200317191604"
    },
    {
        "name": "Balla di Fieno",
        "id": "hay_bale",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/c/c7/Hay_Bale_%28UD%29_JE2_BE2.png/revision/latest?cb=20200315184142"
    },
    {
        "name": "Nido d'Ape",
        "id": "bee_nest",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/4/44/Bee_Nest_%28S%29_JE1.png/revision/latest?cb=20210115133016"
    },
    {
        "name": "Banco da Lavoro",
        "id": "crafting_table",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/b/b7/Crafting_Table_JE4_BE3.png/revision/latest?cb=20191229083528"
    },
    {
        "name": "Tagliapietre",
        "id": "stonecutter",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/93/Stonecutter_JE2_BE1.gif/revision/latest?cb=20190527132036"
    },
    {
        "name": "Blocco di Diamante",
        "id": "block_of_diamond",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/c/c8/Block_of_Diamond_JE5_BE3.png/revision/latest?cb=20200226013851"
    },
    {
        "name": "Leggio con Libro",
        "id": "lectern",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/1/17/Lectern_with_Book_%28S%29.png/revision/latest?cb=20211224073803"
    },
    {
        "name": "Tavolo per Incantesimi",
        "id": "enchanting_table",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/3/31/Enchanting_Table.gif/revision/latest?cb=20220222115558"
    },
    {
        "name": "TNT",
        "id": "tnt",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/a/a2/TNT_JE3_BE2.png/revision/latest?cb=20210110120939"
    },
    {
        "name": "Portale dell'End",
        "id": "end_portal_frame",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/c/c7/End_Portal_Frame_%28S%29_JE6_BE3.png/revision/latest?cb=20220317090601"
    },
    {
        "name": "Bedrock",
        "id": "bedrock",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/6/68/Bedrock_JE2_BE2.png/revision/latest?cb=20200224220504"
    },
    {
        "name": "Sculk",
        "id": "sculk",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/6/67/Sculk_JE1_BE1.gif/revision/latest?cb=20210829064613"
    },
    {
        "name": "Forno Acceso",
        "id": "lit_furnace",
        "url": "https://static.wikia.nocookie.net/minecraft_gamepedia/images/c/c5/Lit_Furnace_%28S%29.gif/revision/latest?cb=20200831134706"
    }
]

class BlockIconSelectorDialog(QDialog):
    """Finestra di dialogo per selezionare l'icona dell'istanza dai blocchi locali."""
    icon_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scegli Icona Istanza")
        self.setMinimumSize(560, 500)
        self.resize(600, 560)
        self.selected_path = None
        self.active_movies = []

        self.setupUi()
        self.apply_stylesheet()

    def setupUi(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        header = QLabel("Seleziona Icona Blocco")
        header.setObjectName("DialogHeader")
        main_layout.addWidget(header)

        desc = QLabel("Scegli un'icona per personalizzare questa istanza:")
        desc.setStyleSheet("color: #94a3b8; font-size: 9.5pt;")
        main_layout.addWidget(desc)

        # Input per link diretto immagine/GIF (URL) e pulsante Sfoglia accanto
        link_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Incolla link diretto immagine o GIF (es. https://.../img.gif)")
        self.url_input.setObjectName("UrlInput")
        
        load_url_btn = QPushButton("Usa Link")
        load_url_btn.setObjectName("SecondaryButton")
        load_url_btn.clicked.connect(self.load_from_url)

        custom_btn = QPushButton("Sfoglia...")
        custom_btn.setObjectName("SecondaryButton")
        custom_btn.clicked.connect(self.browse_custom_image)
        
        link_layout.addWidget(self.url_input, 1)
        link_layout.addWidget(load_url_btn)
        link_layout.addWidget(custom_btn)
        main_layout.addLayout(link_layout)

        # Griglia dei blocchi
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(12)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        blocks_cache_dir = os.path.expanduser("~/.cignolauncher/block_icons")
        os.makedirs(blocks_cache_dir, exist_ok=True)

        columns = 4
        for idx, block in enumerate(MINECRAFT_BLOCKS):
            row = idx // columns
            col = idx % columns

            btn = QPushButton()
            btn.setFixedSize(96, 96)
            btn.setToolTip(block["name"])
            btn.setObjectName("BlockIconButton")

            block_id = block["id"]
            url = block.get("url")

            # Priorità alle risorse 3D bundled ufficiali nell'applicazione
            bundled_gif = resource_path(f"assets/block_icons/{block_id}.gif")
            bundled_png = resource_path(f"assets/block_icons/{block_id}.png")

            if os.path.exists(bundled_gif) and os.path.getsize(bundled_gif) > 0:
                local_path = bundled_gif
            elif os.path.exists(bundled_png) and os.path.getsize(bundled_png) > 0:
                local_path = bundled_png
            else:
                ext = ".gif" if (url and ".gif" in url.lower()) else ".png"
                if url and ".webp" in url.lower():
                    ext = ".webp"
                elif url and (".jpg" in url.lower() or ".jpeg" in url.lower()):
                    ext = ".jpg"

                icon_filename = f"{block_id}{ext}"
                local_path = os.path.join(blocks_cache_dir, icon_filename)

                if url and (not os.path.exists(local_path) or os.path.getsize(local_path) == 0):
                    try:
                        import ssl
                        context = ssl.create_default_context()
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
                        }
                        req = urllib.request.Request(url, headers=headers)
                        with urllib.request.urlopen(req, context=context, timeout=10) as response, open(local_path, 'wb') as out_file:
                            out_file.write(response.read())
                    except Exception as e:
                        print(f"[BlockIconSelectorDialog] Errore download sincrono icona {local_path} ({url}): {e}")

            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                self.set_button_icon(btn, local_path)

            btn.clicked.connect(lambda _, path=local_path: self.on_block_chosen(path))
            grid_layout.addWidget(btn, row, col)

        scroll.setWidget(grid_widget)
        main_layout.addWidget(scroll, 1)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        close_btn = QPushButton("Annulla")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.reject)
        bottom_row.addWidget(close_btn)

        main_layout.addLayout(bottom_row)
        self.adjustSize()

    def set_button_icon(self, btn, path):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            if path.lower().endswith(".gif"):
                movie = QMovie(path, parent=self)
                movie.frameChanged.connect(lambda: self.update_grid_movie_frame(btn, movie))
                movie.start()
                self.active_movies.append(movie)
            else:
                pix = QPixmap(path)
                if not pix.isNull():
                    scaled = pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    btn.setIcon(QIcon(scaled))
                    btn.setIconSize(QSize(64, 64))

    def update_grid_movie_frame(self, btn, movie):
        if btn and movie:
            try:
                current_pix = movie.currentPixmap()
                if not current_pix.isNull():
                    scaled = current_pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    btn.setIcon(QIcon(scaled))
                    btn.setIconSize(QSize(64, 64))
            except RuntimeError:
                pass

    def on_block_chosen(self, path):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            self.selected_path = path
            self.icon_selected.emit(path)
            self.accept()

    def browse_custom_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona Immagine Personalizzata", "", "Immagini (*.png *.jpg *.jpeg *.ico *.gif *.webp)"
        )
        if file_path:
            self.selected_path = file_path
            self.icon_selected.emit(file_path)
            self.accept()

    def load_from_url(self):
        url = self.url_input.text().strip()
        if not url:
            show_warning(self, "Link vuoto", "Inserisci un link URL valido per l'immagine o GIF.")
            return

        try:
            icons_dir = os.path.expanduser("~/.cignolauncher/instance_icons")
            os.makedirs(icons_dir, exist_ok=True)
            
            ext = ".gif" if ".gif" in url.lower() else ".png"
            lower_url = url.lower()
            if ".webp" in lower_url:
                ext = ".webp"
            elif ".jpg" in lower_url or ".jpeg" in lower_url:
                ext = ".jpg"
            elif "." in url.split("/")[-1] and len(url.split("/")[-1].split("?")[0]) <= 8:
                possible_ext = os.path.splitext(url.split("/")[-1].split("?")[0])[1].lower()
                if possible_ext in [".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp"]:
                    ext = possible_ext

            filename = f"icon_{uuid.uuid4().hex[:8]}{ext}"
            local_path = os.path.join(icons_dir, filename)

            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
            }

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=context, timeout=15) as response, open(local_path, 'wb') as out_file:
                out_file.write(response.read())

            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                self.selected_path = local_path
                self.icon_selected.emit(local_path)
                self.accept()
            else:
                show_warning(self, "Errore", "Impossibile scaricare l'immagine dal link specificato.")
        except Exception as e:
            show_warning(self, "Errore di Connessione", f"Impossibile scaricare l'immagine:\n{e}")

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #f8fafc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #f8fafc;
                font-size: 10pt;
            }
            QLabel#DialogHeader {
                font-size: 16pt;
                font-weight: bold;
                color: #ffffff;
            }
            QLineEdit#UrlInput {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                color: #f8fafc;
                font-size: 9.5pt;
            }
            QLineEdit#UrlInput:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton#SecondaryButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f8fafc;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton#BlockIconButton {
                background-color: #1a1d26;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QPushButton#BlockIconButton:hover {
                border-color: #3b82f6;
                background-color: #222633;
            }
        """)
