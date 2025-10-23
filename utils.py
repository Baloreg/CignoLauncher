# utils.py

import os
import requests
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap

# Classe Worker per scaricare immagini in background
class ImageDownloader(QObject):
    finished = pyqtSignal()
    image_ready = pyqtSignal(str, QPixmap)

    def __init__(self, uuid, heads_folder):
        super().__init__()
        self.uuid = uuid
        self.heads_folder = heads_folder

    def run(self):
        try:
            image_path = os.path.join(self.heads_folder, f"{self.uuid}.png")
            # Scarica solo se l'immagine non è in cache
            if not os.path.exists(image_path):
                url = f"https://crafatar.com/avatars/{self.uuid}?size=48&overlay"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                with open(image_path, 'wb') as f:
                    f.write(response.content)
            
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.image_ready.emit(self.uuid, pixmap)
        except Exception as e:
            print(f"Errore download immagine per {self.uuid}: {e}")
        finally:
            self.finished.emit()