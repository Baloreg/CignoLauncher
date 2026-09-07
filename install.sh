#!/usr/bin/env bash
set -e

APP_NAME="CignoLauncher"
BINARY_NAME="CignoLauncher"

echo "=== Installazione di $APP_NAME per Linux (Debian, Ubuntu, Linux Mint, ecc.) ==="

# Determina la directory di installazione (sistema se root, utente altrimenti)
if [ "$EUID" -eq 0 ]; then
    INSTALL_DIR="/usr/local/bin"
    DESKTOP_DIR="/usr/share/applications"
    ICON_DIR="/usr/share/pixmaps"
else
    INSTALL_DIR="$HOME/.local/bin"
    DESKTOP_DIR="$HOME/.local/share/applications"
    ICON_DIR="$HOME/.local/share/pixmaps"
    mkdir -p "$INSTALL_DIR" "$DESKTOP_DIR" "$ICON_DIR"
fi

# Trova la cartella dello script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copia l'eseguibile
if [ -f "$SCRIPT_DIR/$BINARY_NAME" ]; then
    echo "Copia dell'eseguibile in $INSTALL_DIR..."
    cp "$SCRIPT_DIR/$BINARY_NAME" "$INSTALL_DIR/cignolauncher"
    chmod +x "$INSTALL_DIR/cignolauncher"
else
    echo "Errore: Impossibile trovare l'eseguibile $BINARY_NAME nella cartella dello script."
    exit 1
fi

# Gestione icona: converte window_icon.ico in PNG per massima compatibilità su Linux Mint/Cinnamon
ICON_PATH="$ICON_DIR/cignolauncher.png"
echo "Installazione dell'icona (window_icon.ico)..."

if [ -f "$SCRIPT_DIR/assets/window_icon.ico" ]; then
    python3 -c "
import sys
try:
    from PIL import Image
    img = Image.open('$SCRIPT_DIR/assets/window_icon.ico')
    img.save('$ICON_PATH', 'PNG')
    print('Icona convertita con successo da ICO a PNG.')
except Exception as e:
    print('Conversione ICO fallita, copio come .ico:', e)
    import shutil
    shutil.copy('$SCRIPT_DIR/assets/window_icon.ico', '$ICON_DIR/cignolauncher.ico')
    global ICON_PATH
    ICON_PATH = '$ICON_DIR/cignolauncher.ico'
" || cp "$SCRIPT_DIR/assets/window_icon.ico" "$ICON_DIR/cignolauncher.ico"
elif [ -f "$SCRIPT_DIR/assets/logo.png" ]; then
    cp "$SCRIPT_DIR/assets/logo.png" "$ICON_PATH"
fi

if [ ! -f "$ICON_PATH" ] && [ -f "$ICON_DIR/cignolauncher.ico" ]; then
    ICON_PATH="$ICON_DIR/cignolauncher.ico"
fi

# Crea il file .desktop con percorso assoluto dell'icona
echo "Creazione del collegamento nel menu Applicazioni..."
cat << EOF > "$DESKTOP_DIR/cignolauncher.desktop"
[Desktop Entry]
Type=Application
Name=CignoLauncher
Comment=Minecraft Vanilla & Instances Launcher
Exec=$INSTALL_DIR/cignolauncher
Icon=$ICON_PATH
Terminal=false
Categories=Game;JavaGame;
StartupWMClass=CignoLauncher
EOF

if [ "$EUID" -eq 0 ]; then
    update-desktop-database -q || true
    gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
else
    update-desktop-database "$HOME/.local/share/applications" -q || true
fi

echo "=== Installazione completata con successo! ==="
echo "Puoi avviare CignoLauncher dal menu delle applicazioni o digitando 'cignolauncher' nel terminale."
