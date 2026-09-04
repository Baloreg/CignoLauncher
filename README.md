# 🎮 CignoLauncher

[![Python](https://img.shields.io/badge/Python-3.9+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt-6-41cd52?style=for-the-badge&logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![Minecraft](https://img.shields.io/badge/Minecraft-Vanilla%20Multi--Version-2b742b?style=for-the-badge&logo=minecraft&logoColor=white)](https://www.minecraft.net/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

**CignoLauncher** è un launcher moderno, pulito e leggero per Minecraft, progettato in Python con **PyQt6** e basato sulla libreria ufficiale [minecraft-launcher-lib](https://minecraft-launcher-lib.readthedocs.io/en/stable/).

Consente di selezionare, scaricare con un click e avviare qualunque versione ufficiale di Minecraft (Release ufficiali, Snapshot e versioni storiche), con autenticazione sia **Microsoft (OAuth 2.0 con PKCE)** che **Offline**, allocazione RAM dinamica, rilevamento automatico del runtime Java e visualizzatore di console/log in tempo reale.

---

## ✨ Caratteristiche Principali

- 🚀 **Supporto Multi-Versione Completo**: Scegli qualsiasi versione ufficiale Mojang dal selettore integrato (da Minecraft 1.0 alle versioni più recenti come 1.21+).
- ⬇️ **Download e Installazione con 1 Click**: Gestione automatica di client, asset, librerie e nativi tramite `minecraft-launcher-lib`, con barra di avanzamento e percentuale in tempo reale.
- 🎨 **Interfaccia Dark Gaming Moderna**: UI elegante, ad alto contrasto e moderna, costruita con PyQt6 (ispirata allo stile Discord e Prism Launcher).
- 👤 **Gestione Account Flessibile**:
  - **Account Microsoft (Xbox)**: Accesso sicuro tramite browser e protocollo OAuth 2.0 PKCE con rinnovo automatico del token.
  - **Account Offline**: Crea e usa profili offline immediati con nickname personalizzato.
  - **Avatar del Giocatore**: Download e visualizzazione automatica della testa/skin 3D del giocatore con caching locale.
- ⚙️ **Impostazioni di Gioco Avanzate**:
  - Slider intuitivo per la memoria RAM allocata (da 2 a 24 GB).
  - Rilevamento automatico e configurazione personalizzata dell'eseguibile Java.
  - Argomenti JVM personalizzati (es. garbage collector G1GC flags).
  - Accesso rapido con un clic alla cartella di gioco Minecraft.
- 📋 **Console e Log in Tempo Reale**: Monitoraggio live dell'output del gioco per individuare facilmente crash ed errori, con funzioni di copia e pulizia dei log.
- ⚡ **Caching Offline**: Le informazioni delle versioni vengono salvate localmente per consentire l'avvio immediato anche senza connessione internet.

---

## 🛠️ Requisiti di Sistema

- **Python**: 3.9 o superiore
- **Java**: Java 17 o 21 raccomandato (richiesto per le versioni recenti di Minecraft)
- **Sistemi Operativi supportati**: Linux, Windows 10/11, macOS

---

## 📦 Installazione

1. **Clona il repository**:
   ```bash
   git clone https://github.com/Baloreg/CignoLauncher.git
   cd CignoLauncher
   ```

2. **Crea ed attiva un ambiente virtuale (consigliato)**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Su Linux/macOS
   # .venv\Scripts\activate   # Su Windows
   ```

3. **Installa le dipendenze richieste**:
   ```bash
   .venv/bin/python -m pip install -r requirements.txt
   # In alternativa, dopo `source .venv/bin/activate`: pip install -r requirements.txt
   ```

---

## 🚀 Avvio del Launcher

Puoi avviare il launcher eseguendo:
```bash
.venv/bin/python main.py       # Linux/macOS
# .venv\\Scripts\\python.exe main.py  # Windows PowerShell
```
oppure:
```bash
.venv/bin/python cignolauncher_pyqt.py
```

---

## 🔐 Configurazione Accesso Microsoft (Opzionale)

Per abilitare il login Microsoft OAuth, imposta le variabili d'ambiente prima di avviare il launcher con i tuoi identificativi Azure:
```bash
export AZURE_CLIENT_ID="il-tuo-client-id-azure"
export AZURE_CLIENT_SECRET="il-tuo-client-secret-azure"
```
*Nota: Se non configurate, è sempre possibile giocare immediatamente in **Modalità Offline** senza alcuna configurazione aggiuntiva.*

---

## 📁 Struttura del Progetto

```
CignoLauncher/
├── cignolauncher_pyqt.py  # Finestra principale, logica multi-versione e styling PyQt6
├── main.py                # Punto di ingresso principale del programma
├── account_manager.py     # Gestione profili Microsoft e Offline
├── login_dialog_pyqt.py   # Finestra di dialogo per gestione e aggiunta account
├── utils.py               # Utilità, download avatar e generatori grafici
├── requirements.txt       # Dipendenze Python (PyQt6, minecraft-launcher-lib, ecc.)
├── .gitignore             # Esclusioni Git
├── assets/                # Icone e risorse grafiche
├── LICENSE                # Licenza MIT
└── README.md              # Documentazione del progetto
```

## 🧰 Build degli eseguibili

Il progetto include un build PyInstaller e una pipeline GitHub Actions che produce gli artefatti su runner nativi:

```bash
python3 build.py             # build per il sistema operativo corrente
python3 build.py --onefile   # singolo eseguibile quando supportato
```

Per ottenere Windows, Linux e macOS insieme, esegui la workflow `Build CignoLauncher Executables` da GitHub Actions oppure crea un tag `v*`. La compilazione multipiattaforma deve girare su ciascun sistema operativo; il risultato viene pubblicato come artefatto separato.

Le istanze vengono salvate in `~/.cignolauncher/instances` (su Windows nella cartella dati dell'applicazione), con versione, RAM, argomenti JVM, mondi e configurazioni isolati per istanza.

---

## 📜 Licenza

Questo progetto è distribuito sotto licenza **MIT**. Consulta il file [LICENSE](LICENSE) per maggiori informazioni.
