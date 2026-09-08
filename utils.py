import os
import sys
import requests
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QRectF
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QBrush, QPen, QIcon, QFont

def resource_path(relative_path):
    """Ottieni il percorso assoluto delle risorse, compatibile con PyInstaller (onefile/onedir)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def download_head_pixmap(identifier, heads_folder, user_uuid=None):
    """
    Scarica la testa/avatar 2D di un giocatore Minecraft provando vari provider in sequenza.
    Supporta User-Agent e salvataggio sia per username che per UUID.
    Ritorna un QPixmap valido o None se fallisce.
    """
    if not identifier and not user_uuid:
        return None

    os.makedirs(heads_folder, exist_ok=True)

    target_id = str(user_uuid).strip() if user_uuid else str(identifier).strip()
    target_name = str(identifier).strip() if identifier else target_id

    # Lista di URL candidati per il download dell'avatar (helm con overlay)
    urls = []
    if user_uuid:
        clean_uuid = str(user_uuid).replace("-", "").strip()
        urls.append(f"https://crafthead.net/helm/{clean_uuid}/64")
        urls.append(f"https://mc-heads.net/avatar/{clean_uuid}/64")
        urls.append(f"https://minotar.net/helm/{clean_uuid}/64.png")

    if target_name:
        urls.append(f"https://crafthead.net/helm/{target_name}/64")
        urls.append(f"https://mc-heads.net/avatar/{target_name}/64")
        urls.append(f"https://minotar.net/helm/{target_name}/64.png")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/png,image/webp,image/*,*/*'
    }

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200 and len(res.content) > 100:
                pix = QPixmap()
                if pix.loadFromData(res.content) and not pix.isNull():
                    # Salva su disco per cache sia con nome utente che con UUID
                    if target_name:
                        path_name = os.path.join(heads_folder, f"{target_name}.png")
                        with open(path_name, 'wb') as f:
                            f.write(res.content)
                    if user_uuid:
                        path_uuid = os.path.join(heads_folder, f"{user_uuid}.png")
                        with open(path_uuid, 'wb') as f:
                            f.write(res.content)

                    print(f"[download_head_pixmap] Avatar per {target_name} ({user_uuid}) scaricato da {url}")
                    return pix
        except Exception as e:
            print(f"[download_head_pixmap] Tentativo fallito con {url}: {e}")

    return None


class ImageDownloader(QObject):
    """Worker in background per scaricare l'avatar 2D del giocatore."""
    finished = pyqtSignal()
    image_ready = pyqtSignal(str, QPixmap)

    def __init__(self, identifier, heads_folder, uuid=None):
        super().__init__()
        self.identifier = str(identifier).strip()
        self.uuid = str(uuid).strip() if uuid else None
        self.heads_folder = heads_folder

    def run(self):
        try:
            pixmap = download_head_pixmap(self.identifier, self.heads_folder, user_uuid=self.uuid)
            if pixmap and not pixmap.isNull():
                self.image_ready.emit(self.identifier, pixmap)
            else:
                print(f"[ImageDownloader] Impossibile recuperare avatar per {self.identifier}")
        except Exception as e:
            print(f"[ImageDownloader] Errore worker download avatar: {e}")
        finally:
            self.finished.emit()


def create_steve_avatar(size=48) -> QPixmap:
    """Genera un avatar in pixel-art di Steve a 8x8 scalato alla dimensione desiderata."""
    img = QImage(8, 8, QImage.Format.Format_RGB32)
    
    # Palette colori di base del volto di Steve
    skin_dark = QColor("#996347")
    skin_mid = QColor("#b57b55")
    skin_light = QColor("#c68a64")
    hair = QColor("#492918")
    hair_dark = QColor("#321b0e")
    eye_white = QColor("#ffffff")
    eye_pupil = QColor("#3c44aa")
    nose = QColor("#844d34")
    mouth = QColor("#5b2a1d")

    # Mappa 8x8
    pixels = [
        [hair,      hair,      hair,      hair,      hair,      hair,      hair,      hair],
        [hair,      hair,      hair,      hair,      hair,      hair,      hair,      hair],
        [hair,      skin_mid,  skin_light,skin_mid,  skin_mid,  skin_light,skin_mid,  hair],
        [skin_mid,  skin_light,skin_light,skin_mid,  skin_light,skin_light,skin_light,skin_mid],
        [skin_light,eye_white, eye_pupil, skin_mid,  skin_mid,  eye_white, eye_pupil, skin_light],
        [skin_mid,  skin_light,skin_mid,  nose,      nose,      skin_mid,  skin_light,skin_mid],
        [skin_mid,  skin_light,mouth,     mouth,     mouth,     mouth,     skin_light,skin_mid],
        [hair_dark, hair_dark, mouth,     mouth,     mouth,     mouth,     hair_dark, hair_dark],
    ]

    for y in range(8):
        for x in range(8):
            img.setPixelColor(x, y, pixels[y][x])

    pix = QPixmap.fromImage(img)
    return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)


def create_app_logo_pixmap(width=280, height=80) -> QPixmap:
    """Genera una grafica moderna per il logo CignoLauncher."""
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Disegna l'icona stilizzata di un blocco Minecraft con ali (Cigno)
    block_rect = QRectF(10, 15, 50, 50)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#3b82f6")))
    painter.drawRoundedRect(block_rect, 10, 10)

    # Accent color interno
    inner_rect = QRectF(18, 23, 34, 34)
    painter.setBrush(QBrush(QColor("#1d4ed8")))
    painter.drawRoundedRect(inner_rect, 6, 6)

    # Lettera 'C' moderna al centro del blocco
    painter.setPen(QPen(QColor("#ffffff")))
    font = QFont("Segoe UI", 20, QFont.Weight.Black)
    painter.setFont(font)
    painter.drawText(block_rect, Qt.AlignmentFlag.AlignCenter, "C")

    # Testo del Launcher
    painter.setPen(QPen(QColor("#ffffff")))
    title_font = QFont("Segoe UI", 24, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.drawText(75, 42, "CIGNO")

    accent_font = QFont("Segoe UI", 24, QFont.Weight.Light)
    painter.setFont(accent_font)
    painter.setPen(QPen(QColor("#60a5fa")))
    painter.drawText(180, 42, "LAUNCHER")

    # Sottotitolo
    sub_font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
    painter.setFont(sub_font)
    painter.setPen(QPen(QColor("#94a3b8")))
    painter.drawText(77, 60, "VANILLA MINECRAFT EDITION")

    painter.end()
    return pixmap