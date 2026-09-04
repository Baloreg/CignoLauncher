import os
import requests
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QRectF
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QBrush, QPen, QIcon, QFont

class ImageDownloader(QObject):
    """Worker in background per scaricare l'avatar del giocatore (testa) da Crafatar."""
    finished = pyqtSignal()
    image_ready = pyqtSignal(str, QPixmap)

    def __init__(self, uuid_str, heads_folder):
        super().__init__()
        self.uuid = str(uuid_str)
        self.heads_folder = heads_folder

    def run(self):
        try:
            os.makedirs(self.heads_folder, exist_ok=True)
            image_path = os.path.join(self.heads_folder, f"{self.uuid}.png")
            
            if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
                url = f"https://crafatar.com/avatars/{self.uuid}?size=64&overlay"
                response = requests.get(url, timeout=8)
                response.raise_for_status()
                with open(image_path, 'wb') as f:
                    f.write(response.content)
            
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.image_ready.emit(self.uuid, pixmap)
        except Exception as e:
            # Fallback silenzioso
            pass
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