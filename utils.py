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
    Scarica o genera la testa/avatar 2D con overlay del casco di un giocatore Minecraft
    direttamente dai server ufficiali Mojang (Sessionserver) o tramite provider alternativi.
    Ritorna un QPixmap valido o None se fallisce.
    """
    if not identifier and not user_uuid:
        return None

    os.makedirs(heads_folder, exist_ok=True)

    target_id = str(user_uuid).strip() if user_uuid else str(identifier).strip()
    target_name = str(identifier).strip() if identifier else target_id
    clean_uuid = str(user_uuid).replace("-", "").strip() if user_uuid else ""

    # 1. Tentativo ufficiale Mojang Sessionserver se abbiamo un UUID Java valido (32 hex chars)
    if len(clean_uuid) == 32 and all(c in "0123456789abcdefABCDEF" for c in clean_uuid):
        try:
            profile_url = f"https://sessionserver.mojang.com/session/minecraft/profile/{clean_uuid}"
            res = requests.get(profile_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for prop in data.get("properties", []):
                    if prop.get("name") == "textures":
                        val = prop.get("value", "")
                        import base64
                        import json
                        decoded = base64.b64decode(val).decode("utf-8")
                        tex_data = json.loads(decoded)
                        skin_url = tex_data.get("textures", {}).get("SKIN", {}).get("url")
                        if skin_url:
                            skin_res = requests.get(skin_url, timeout=5)
                            if skin_res.status_code == 200:
                                skin_img = QImage.fromData(skin_res.content)
                                if not skin_img.isNull():
                                    # Estrai testa (8x8 a 8,8) e overlay elmo/cappello (8x8 a 40,8)
                                    head_img = skin_img.copy(8, 8, 8, 8)
                                    overlay_img = skin_img.copy(40, 8, 8, 8)

                                    final_img = QImage(8, 8, QImage.Format.Format_ARGB32)
                                    final_img.fill(Qt.GlobalColor.transparent)
                                    painter = QPainter(final_img)
                                    painter.drawImage(0, 0, head_img)
                                    painter.drawImage(0, 0, overlay_img)
                                    painter.end()

                                    pix = QPixmap.fromImage(final_img).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
                                    if not pix.isNull():
                                        if target_name:
                                            pix.save(os.path.join(heads_folder, f"{target_name}.png"), "PNG")
                                        pix.save(os.path.join(heads_folder, f"{clean_uuid}.png"), "PNG")
                                        print(f"[download_head_pixmap] Avatar generato da skin ufficiale Mojang per {target_name} ({clean_uuid})")
                                        return pix
        except Exception as e:
            print(f"[download_head_pixmap] Tentativo Mojang sessionserver fallito: {e}")

    # 2. Fallback su provider alternativi (Minotar, MC-Heads, Crafatar)
    urls = []
    if len(clean_uuid) == 32 and all(c in "0123456789abcdefABCDEF" for c in clean_uuid):
        urls.append(f"https://minotar.net/helm/{clean_uuid}/64.png")
        urls.append(f"https://mc-heads.net/avatar/{clean_uuid}/64")
        urls.append(f"https://crafatar.com/avatars/{clean_uuid}?size=64&helm")

    if target_name:
        urls.append(f"https://minotar.net/helm/{target_name}/64.png")
        urls.append(f"https://mc-heads.net/avatar/{target_name}/64")
        urls.append(f"https://crafatar.com/avatars/{target_name}?size=64&helm")

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
                    if target_name:
                        with open(os.path.join(heads_folder, f"{target_name}.png"), 'wb') as f:
                            f.write(res.content)
                    if clean_uuid:
                        with open(os.path.join(heads_folder, f"{clean_uuid}.png"), 'wb') as f:
                            f.write(res.content)

                    print(f"[download_head_pixmap] Avatar per {target_name} ({clean_uuid}) scaricato da {url}")
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


def parse_version_key(v):
    """Chiave di ordinamento semantico robusta per versioni Minecraft e Loader (es. 1.21.1 dopo 1.4.2)."""
    if isinstance(v, dict):
        v = v.get("id", "") or v.get("name", "")
    s = str(v).strip()
    for prefix in ["Forge ", "Fabric ", "Quilt ", "NeoForge "]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    
    parts = []
    import re
    tokens = re.split(r'[\.\-\_]', s)
    for token in tokens:
        if token.isdigit():
            parts.append((0, int(token)))
        else:
            m = re.match(r'^(\d+)(.*)$', token)
            if m:
                parts.append((0, int(m.group(1))))
                if m.group(2):
                    parts.append((1, m.group(2)))
            else:
                parts.append((1, token))
    return parts
