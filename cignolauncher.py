import minecraft_launcher_lib
import subprocess
import sys
import os
import json
import hashlib
import requests
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from datetime import datetime
import shutil

# Patch per nascondere le finestre CMD su Windows
if sys.platform == "win32":
    import ctypes
    
    # Nascondi la finestra della console del launcher stesso
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    
    SW_HIDE = 0
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, SW_HIDE)
    
    # Monkey-patch subprocess.Popen per nascondere finestre CMD
    _original_popen_init = subprocess.Popen.__init__
    
    def _patched_popen_init(self, *args, **kwargs):
        # Aggiungi creationflags per nascondere la finestra
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = 0
        kwargs['creationflags'] |= 0x08000000  # CREATE_NO_WINDOW
        return _original_popen_init(self, *args, **kwargs)
    
    subprocess.Popen.__init__ = _patched_popen_init

class MinecraftLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CignoLauncher")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # Colori tema scuro
        self.colors = {
            'bg': '#1e1e1e',
            'bg_secondary': '#2d2d2d',
            'bg_tertiary': '#3d3d3d',
            'accent': '#0078d4',
            'accent_hover': '#106ebe',
            'text': '#ffffff',
            'text_secondary': '#b0b0b0',
            'success': '#4caf50',
            'error': '#f44336',
            'border': '#404040'
        }
        
        # Configura lo stile del root
        self.root.configure(bg=self.colors['bg'])
        
        # Percorsi personalizzati - cartella dedicata in Roaming
        if sys.platform == "win32":
            appdata = os.getenv('APPDATA')
            self.launcher_directory = os.path.join(appdata, "CignoLauncher")
        else:
            # Linux/Mac
            home = os.path.expanduser("~")
            self.launcher_directory = os.path.join(home, ".cignolauncher")
        
        # Crea la struttura delle cartelle
        self.minecraft_directory = os.path.join(self.launcher_directory, "minecraft")
        self.modpack_folder = os.path.join(self.launcher_directory, "mods")
        self.config_folder = os.path.join(self.launcher_directory, "config")
        self.resourcepacks_folder = os.path.join(self.launcher_directory, "resourcepacks")
        self.shaderpacks_folder = os.path.join(self.launcher_directory, "shaderpacks")
        self.saves_folder = os.path.join(self.launcher_directory, "saves")
        
        # Cartelle aggiuntive per il modpack
        self.additional_folders = {}
        
        # Crea tutte le cartelle base
        for folder in [self.launcher_directory, self.minecraft_directory, 
                      self.modpack_folder, self.config_folder, 
                      self.resourcepacks_folder, self.shaderpacks_folder, self.saves_folder]:
            Path(folder).mkdir(parents=True, exist_ok=True)
        
        # URL dove ospiti il tuo modpack (modifica questo!)
        self.modpack_url = "https://raw.githubusercontent.com/Baloreg/Cignopack/main/manifest.json"
        
        # Versioni - MODIFICA QUESTE PER CAMBIARE LA VERSIONE
        self.minecraft_version = "1.20.1"
        self.forge_version = "1.20.1-47.4.6"  # Versione ESATTA di Forge da installare
        
        # File di stato installazione
        self.install_state_file = os.path.join(self.launcher_directory, "install_state.json")
        
        # Processo del gioco
        self.game_process = None
        
        self.setup_styles()
        self.setup_ui()
        
        # Controlla se l'installazione è già completa
        self.check_installation_status()
        
    def setup_styles(self):
        """Configura gli stili personalizzati per il tema scuro"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurazione generale
        style.configure('.',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       fieldbackground=self.colors['bg_secondary'],
                       bordercolor=self.colors['border'],
                       darkcolor=self.colors['bg_secondary'],
                       lightcolor=self.colors['bg_secondary'])
        
        # Frame
        style.configure('TFrame',
                       background=self.colors['bg'])
        
        # Label
        style.configure('TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text'])
        
        style.configure('Title.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['accent'],
                       font=('Segoe UI', 24, 'bold'))
        
        style.configure('Status.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text_secondary'],
                       font=('Segoe UI', 9))
        
        # Entry
        style.configure('TEntry',
                       fieldbackground=self.colors['bg_secondary'],
                       foreground=self.colors['text'],
                       bordercolor=self.colors['border'],
                       insertcolor=self.colors['text'])
        
        style.map('TEntry',
                 fieldbackground=[('focus', self.colors['bg_tertiary'])],
                 bordercolor=[('focus', self.colors['accent'])])
        
        # Spinbox
        style.configure('TSpinbox',
                       fieldbackground=self.colors['bg_secondary'],
                       foreground=self.colors['text'],
                       bordercolor=self.colors['border'],
                       arrowcolor=self.colors['text'])
        
        style.map('TSpinbox',
                 fieldbackground=[('focus', self.colors['bg_tertiary'])],
                 bordercolor=[('focus', self.colors['accent'])])
        
        # Button
        style.configure('TButton',
                       background=self.colors['accent'],
                       foreground=self.colors['text'],
                       bordercolor=self.colors['accent'],
                       focuscolor=self.colors['accent'],
                       font=('Segoe UI', 10, 'bold'),
                       padding=(20, 10))
        
        style.map('TButton',
                 background=[('active', self.colors['accent_hover']),
                           ('disabled', self.colors['bg_tertiary'])],
                 foreground=[('disabled', self.colors['text_secondary'])])
        
        # Progressbar
        style.configure('TProgressbar',
                       background=self.colors['accent'],
                       troughcolor=self.colors['bg_secondary'],
                       bordercolor=self.colors['border'],
                       lightcolor=self.colors['accent'],
                       darkcolor=self.colors['accent'])
        
        # Notebook (tabs)
        style.configure('TNotebook',
                       background=self.colors['bg'],
                       bordercolor=self.colors['border'])
        
        style.configure('TNotebook.Tab',
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_secondary'],
                       padding=(20, 10),
                       font=('Segoe UI', 10))
        
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['bg'])],
                 foreground=[('selected', self.colors['accent'])],
                 expand=[('selected', [1, 1, 1, 0])])
        
        # LabelFrame
        style.configure('TLabelframe',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       bordercolor=self.colors['border'])
        
        style.configure('TLabelframe.Label',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10, 'bold'))
        
    def setup_ui(self):
        # Container principale
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Notebook per i tab
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Tab principale (Home)
        self.home_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.home_tab, text="  Home  ")
        
        # Tab log
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="  Log  ")
        
        self.setup_home_tab()
        self.setup_log_tab()
        
    def setup_home_tab(self):
        # Frame principale con padding
        main_frame = ttk.Frame(self.home_tab, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header con logo/titolo
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        title_label = ttk.Label(header_frame, text="CIGNOPACK", style='Title.TLabel')
        title_label.pack()
        
        subtitle_label = ttk.Label(header_frame, 
                                   text=f"Minecraft {self.minecraft_version} • Forge {self.forge_version.split('-')[-1]}",
                                   style='Status.TLabel')
        subtitle_label.pack(pady=(5, 0))
        
        # Sezione impostazioni
        settings_frame = ttk.LabelFrame(main_frame, text="Impostazioni", padding="20")
        settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Username
        username_frame = ttk.Frame(settings_frame)
        username_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(username_frame, text="Username", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 5))
        self.username_entry = ttk.Entry(username_frame, font=('Segoe UI', 10))
        self.username_entry.pack(fill=tk.X)
        self.username_entry.insert(0, "Giocatore")
        
        # RAM
        ram_frame = ttk.Frame(settings_frame)
        ram_frame.pack(fill=tk.X)
        
        ttk.Label(ram_frame, text="RAM Allocata (GB)", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 5))
        self.ram_var = tk.StringVar(value="4")
        ram_spinbox = ttk.Spinbox(ram_frame, from_=2, to=16, textvariable=self.ram_var, 
                                  font=('Segoe UI', 10), width=10)
        ram_spinbox.pack(anchor=tk.W)
        
        # Progress e status
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="Pronto per il lancio", 
                                     style='Status.TLabel')
        self.status_label.pack(anchor=tk.W)
        
        # Pulsanti azione
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Usa pack invece di grid per centrare meglio
        buttons_container = ttk.Frame(button_frame)
        buttons_container.pack(anchor=tk.CENTER)
        
        self.install_btn = ttk.Button(buttons_container, text="Installa/Aggiorna", 
                                     command=self.start_installation)
        self.install_btn.pack(side=tk.LEFT, padx=5)
        
        self.play_btn = ttk.Button(buttons_container, text="GIOCA", 
                                  command=self.start_game, state=tk.DISABLED)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
    def setup_log_tab(self):
        log_container = ttk.Frame(self.log_tab)
        log_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Titolo
        ttk.Label(log_container, text="Console", font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Area log
        log_frame = ttk.Frame(log_container)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg=self.colors['bg_secondary'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            selectbackground=self.colors['accent'],
            selectforeground=self.colors['text'],
            relief=tk.FLAT,
            borderwidth=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state='disabled')
        
        # Tag per colorare i log
        self.log_text.tag_config('INFO', foreground='#4fc3f7')
        self.log_text.tag_config('ERROR', foreground='#ef5350')
        self.log_text.tag_config('SUCCESS', foreground='#66bb6a')
        self.log_text.tag_config('GAME', foreground='#ffa726')
        
    def log(self, message, level="INFO"):
        """Aggiunge un messaggio al log interno"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, formatted_message, level)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()
        
    def update_status(self, message, level="INFO"):
        self.status_label.config(text=message)
        self.log(message, level)
        
    def update_progress(self, progress):
        self.progress_var.set(progress)
        self.root.update()
        
    def callback_progress(self, current, total, text=""):
        if total > 0:
            progress = (current / total) * 100
            self.update_progress(progress)
        status = f"{text}: {current}/{total}"
        self.status_label.config(text=status)
        self.root.update()
        
    def get_install_state(self):
        """Legge lo stato dell'installazione"""
        if os.path.exists(self.install_state_file):
            try:
                with open(self.install_state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_install_state(self, state):
        """Salva lo stato dell'installazione"""
        with open(self.install_state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def check_installation_status(self):
        """Controlla se Minecraft e Forge sono già installati"""
        state = self.get_install_state()
        
        # Controlla se la versione è installata
        if state.get('minecraft_version') == self.minecraft_version and \
           state.get('forge_installed') == True:
            self.log("Installazione base già presente", "SUCCESS")
            self.play_btn.config(state=tk.NORMAL)
            self.update_status("Pronto per il lancio", "SUCCESS")
            return True
        return False
        
    def start_installation(self):
        thread = threading.Thread(target=self.install_game)
        thread.daemon = True
        thread.start()
        
    def install_game(self):
        try:
            self.install_btn.config(state=tk.DISABLED)
            state = self.get_install_state()
            
            # 1. Controlla se Minecraft vanilla è già installato
            minecraft_installed = state.get('minecraft_version') == self.minecraft_version
            
            if not minecraft_installed:
                self.update_status("Installazione Minecraft...")
                minecraft_launcher_lib.install.install_minecraft_version(
                    self.minecraft_version,
                    self.minecraft_directory,
                    callback={
                        "setStatus": lambda text: self.update_status(text),
                        "setProgress": lambda current: self.callback_progress(current, 100, "Download")
                    }
                )
                state['minecraft_version'] = self.minecraft_version
                self.save_install_state(state)
                self.log(f"Minecraft {self.minecraft_version} installato!", "SUCCESS")
            else:
                self.log(f"Minecraft {self.minecraft_version} già installato", "SUCCESS")
            
            # 2. Controlla se Forge è già installato (versione ESATTA)
            forge_installed = (state.get('forge_installed') == True and 
                             state.get('forge_version') == self.forge_version)
            
            if not forge_installed:
                self.update_status(f"Installazione Forge {self.forge_version}...")
                self.update_progress(0)
                
                try:
                    self.clean_corrupted_libraries()
                    
                    self.log(f"Installazione versione ESATTA: {self.forge_version}")
                    
                    # Installa la versione ESATTA di Forge specificata
                    minecraft_launcher_lib.forge.install_forge_version(
                        self.forge_version,
                        self.minecraft_directory,
                        callback={
                            "setStatus": lambda text: self.update_status(text),
                            "setProgress": lambda current: self.callback_progress(current, 100, "Forge")
                        },
                        java=self.get_java_executable()
                    )
                    
                    self.log(f"Forge {self.forge_version} installato con successo!", "SUCCESS")
                    state['forge_installed'] = True
                    state['forge_version'] = self.forge_version
                    self.save_install_state(state)
                    
                except Exception as forge_error:
                    error_msg = str(forge_error)
                    self.log(f"Errore installazione Forge: {error_msg}", "ERROR")
                    
                    if "Checksum" in error_msg or "checksum" in error_msg:
                        self.update_status("Errore: File corrotto rilevato", "ERROR")
                        if messagebox.askyesno(
                            "File corrotto", 
                            "Sono stati rilevati file scaricati corrotti.\n\n"
                            "Vuoi ripulire i file corrotti e riprovare?\n"
                            "(Questo cancellerà le librerie di Forge scaricate)"
                        ):
                            self.clean_forge_libraries()
                            state['forge_installed'] = False
                            self.save_install_state(state)
                            self.update_status("File puliti. Riprova l'installazione.")
                            self.install_btn.config(state=tk.NORMAL)
                            return
                    
                    self.update_status("Attenzione: Installazione Forge fallita", "ERROR")
                    messagebox.showerror(
                        "Errore Forge", 
                        f"L'installazione di Forge è fallita:\n{error_msg[:200]}\n\n"
                        "Controlla il log per dettagli completi."
                    )
                    raise
            else:
                self.log(f"Forge già installato: {state.get('forge_version', 'versione sconosciuta')}", "SUCCESS")
            
            # 3. Scarica/Aggiorna modpack e file
            self.update_status("Controllo aggiornamenti modpack...")
            self.update_modpack()
            
            self.update_status("Installazione completata!", "SUCCESS")
            self.update_progress(100)
            self.play_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Successo", "Installazione completata con successo!")
            
        except Exception as e:
            self.update_status(f"Errore: {str(e)}", "ERROR")
            self.log(f"Errore durante l'installazione: {str(e)}", "ERROR")
            messagebox.showerror("Errore", f"Si è verificato un errore:\n{str(e)}")
        finally:
            self.install_btn.config(state=tk.NORMAL)
            
    def clean_corrupted_libraries(self):
        """Rimuove librerie con checksum errato"""
        corrupted_file = os.path.join(
            self.minecraft_directory, 
            "libraries/net/minecraftforge/JarJarFileSystems/0.3.26/JarJarFileSystems-0.3.26.jar"
        )
        if os.path.exists(corrupted_file):
            try:
                os.remove(corrupted_file)
                self.log(f"Rimosso file corrotto: {corrupted_file}")
            except Exception as e:
                self.log(f"Impossibile rimuovere file corrotto: {e}", "ERROR")
    
    def get_java_executable(self):
        """Trova il percorso dell'eseguibile Java"""
        # Cerca prima il Java di Minecraft
        java_path = minecraft_launcher_lib.utils.get_java_executable()
        if java_path:
            self.log(f"Trovato Java: {java_path}")
            return java_path
        
        # Fallback su java di sistema
        return "java"
    
    def clean_forge_libraries(self):
        """Pulisce tutte le librerie Forge per forzare un re-download"""
        forge_libs = os.path.join(self.minecraft_directory, "libraries/net/minecraftforge")
        if os.path.exists(forge_libs):
            try:
                shutil.rmtree(forge_libs)
                self.log(f"Pulite librerie Forge da: {forge_libs}")
                messagebox.showinfo("Pulizia completata", "Le librerie corrotte sono state rimosse.")
            except Exception as e:
                self.log(f"Errore durante la pulizia: {e}", "ERROR")
                messagebox.showerror("Errore", f"Impossibile pulire le librerie:\n{e}")
                
    def update_modpack(self):
        """Scarica e aggiorna tutti i file del modpack"""
        try:
            # Scarica il manifest del modpack
            manifest = self.get_modpack_manifest()
            
            if not manifest:
                self.update_status("Nessun manifest trovato")
                return
            
            # Conta tutti i file da tutte le categorie
            total_files = 0
            for key, value in manifest.items():
                if key in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated']:
                    continue
                if isinstance(value, list):
                    total_files += len(value)
            
            if total_files == 0:
                self.log("Nessun file da scaricare nel manifest")
                return
            
            current_file = 0
            
            # ORDINE IMPORTANTE: processa "root" per prima!
            categories_order = ['root', 'config', 'mods', 'data', 'emotes', 'fancymenu_data', 
                              'resourcepacks', 'shaderpacks']
            
            # Processa categorie nell'ordine specificato prima
            for category in categories_order:
                if category not in manifest:
                    continue
                    
                files = manifest[category]
                if not isinstance(files, list) or not files:
                    continue
                
                # Determina la cartella di destinazione
                if category == "root":
                    target_folder = self.launcher_directory
                elif category == "mods":
                    target_folder = self.modpack_folder
                elif category == "config":
                    target_folder = self.config_folder
                elif category == "resourcepacks":
                    target_folder = self.resourcepacks_folder
                elif category == "shaderpacks":
                    target_folder = self.shaderpacks_folder
                else:
                    target_folder = os.path.join(self.launcher_directory, category)
                    Path(target_folder).mkdir(parents=True, exist_ok=True)
                    self.additional_folders[category] = target_folder
                
                self.log(f"Controllo {len(files)} file in {category}...")
                
                for file_info in files:
                    current_file += 1
                    self.process_file(file_info, target_folder, category, current_file, total_files)
                
                # Pulisci file obsoleti solo per cartelle specifiche
                if category in ["mods", "resourcepacks", "shaderpacks"]:
                    extension = ".jar" if category == "mods" else ".zip"
                    self.clean_old_files(files, target_folder, extension)
            
            # Processa eventuali categorie rimanenti non nell'ordine
            for category, files in manifest.items():
                if category in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated']:
                    continue
                if category in categories_order:
                    continue
                if not isinstance(files, list) or not files:
                    continue
                
                target_folder = os.path.join(self.launcher_directory, category)
                Path(target_folder).mkdir(parents=True, exist_ok=True)
                self.additional_folders[category] = target_folder
                
                self.log(f"Controllo {len(files)} file in {category}...")
                
                for file_info in files:
                    current_file += 1
                    self.process_file(file_info, target_folder, category, current_file, total_files)
            
            self.log("Tutti i file del modpack sono aggiornati!", "SUCCESS")
            
        except Exception as e:
            self.log(f"Errore aggiornamento modpack: {e}", "ERROR")
    
    def process_file(self, file_info, target_folder, file_type, current, total):
        """Processa un singolo file (scarica se necessario)"""
        file_name = file_info["name"]
        file_url = file_info["url"]
        expected_hash = file_info.get("sha256", "")
        
        # Gestisci path relativi (per config, data, e altre cartelle con sottocartelle)
        if "path" in file_info and file_info["path"]:
            # Path completo relativo dalla cartella di categoria
            file_path = os.path.join(target_folder, file_info["path"])
        else:
            # File diretto nella cartella
            file_path = os.path.join(target_folder, file_name)
        
        # Normalizza il path per evitare problemi con separatori
        file_path = os.path.normpath(file_path)
        
        # Crea le directory necessarie
        file_dir = os.path.dirname(file_path)
        if file_dir:
            Path(file_dir).mkdir(parents=True, exist_ok=True)
        
        # Controlla se il file esiste e se l'hash corrisponde
        needs_download = True
        if os.path.exists(file_path):
            if expected_hash:
                # Verifica hash solo se fornito
                current_hash = self.calculate_sha256(file_path)
                if current_hash == expected_hash:
                    needs_download = False
                    # Log compatto: solo se è root o se verboso
                    if file_type == "root":
                        self.log(f"✓ {file_name} già aggiornato (root)", "SUCCESS")
                else:
                    self.log(f"⚠ Hash diverso per {file_name}, riscarico...")
            else:
                # Nessun hash disponibile, considera il file valido
                needs_download = False
                self.log(f"✓ {file_name} già presente (no hash check)")
        
        if needs_download:
            self.update_status(f"Scaricamento {file_type}: {file_name}...")
            self.log(f"↓ Scaricamento {file_name}...")
            
            # Log extra per file root
            if file_type == "root":
                self.log(f"   Path: {file_path}")
                self.log(f"   URL: {file_url}")
            
            try:
                # Elimina file esistente se corrotto
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                self.download_file(file_url, file_path)
                
                # Verifica hash dopo download
                if expected_hash:
                    downloaded_hash = self.calculate_sha256(file_path)
                    if downloaded_hash != expected_hash:
                        self.log(f"❌ Hash non corrisponde per {file_name}!", "ERROR")
                        self.log(f"   Atteso: {expected_hash[:16]}...")
                        self.log(f"   Ottenuto: {downloaded_hash[:16]}...")
                        os.remove(file_path)
                        raise Exception(f"Hash mismatch per {file_name}")
                
                self.log(f"✓ {file_name} scaricato con successo", "SUCCESS")
            except Exception as e:
                self.log(f"❌ Errore download {file_name}: {e}", "ERROR")
                raise
        
        progress = (current / total) * 100
        self.update_progress(progress)
        
    def get_modpack_manifest(self):
        """Scarica il manifest del modpack dal server"""
        try:
            self.log(f"Scaricamento manifest da: {self.modpack_url}")
            response = requests.get(self.modpack_url, timeout=10)
            if response.status_code == 200:
                manifest = response.json()
                self.log(f"Manifest scaricato con successo", "SUCCESS")
                
                # Log delle categorie trovate
                categories = [k for k in manifest.keys() if k not in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated']]
                self.log(f"Categorie trovate: {', '.join(categories)}")
                
                return manifest
        except Exception as e:
            self.log(f"Errore scaricamento manifest: {e}", "ERROR")
            
        return None
        
    def download_file(self, url, destination):
        """Scarica un file da URL"""
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Determina se è un file di testo dal nome
        is_text_file = destination.endswith(('.txt', '.properties', '.json', '.toml', 
                                            '.ini', '.cfg', '.conf', '.md', '.jsonc',
                                            '.json5', '.local', '.lewidget'))

        if is_text_file:
            # Per file di testo, scarica come testo e normalizza i line endings
            content = response.text
            # Scrivi con encoding UTF-8 e line endings nativi del sistema
            with open(destination, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # Per file binari, scarica normalmente
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                
    def calculate_sha256(self, file_path):
        """Calcola l'hash SHA256 di un file"""
        try:
            # Determina se è un file di testo
            is_text_file = str(file_path).endswith(('.txt', '.properties', '.json', '.toml',
                                                    '.ini', '.cfg', '.conf', '.md', '.jsonc',
                                                    '.json5', '.local', '.lewidget'))
            
            if is_text_file:
                # Per file di testo, leggi come testo per normalizzare i line endings
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                # Calcola l'hash del contenuto testuale
                return hashlib.sha256(content.encode('utf-8')).hexdigest()
            else:
                # Per file binari, calcola normalmente
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(8192), b""):
                        sha256_hash.update(byte_block)
                return sha256_hash.hexdigest()
        except Exception as e:
            self.log(f"Errore calcolo hash per {file_path}: {e}", "ERROR")
            return ""
        
    def clean_old_files(self, manifest_files, folder, extension):
        """Rimuove file non presenti nel manifest"""
        if not os.path.exists(folder):
            return
            
        manifest_names = {f["name"] for f in manifest_files}
        
        for file in os.listdir(folder):
            if file.endswith(extension) and file not in manifest_names:
                file_path = os.path.join(folder, file)
                try:
                    os.remove(file_path)
                    self.log(f"Rimosso file obsoleto: {file}")
                except Exception as e:
                    self.log(f"Errore rimozione {file}: {e}", "ERROR")
                    
    def read_game_output(self, pipe):
        """Legge l'output del processo del gioco e lo mostra nel log"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    self.log(line.strip(), "GAME")
        except:
            pass
            
    def start_game(self):
        try:
            username = self.username_entry.get() or "Giocatore"
            ram_gb = int(self.ram_var.get())
            
            # Opzioni di lancio
            options = {
                "username": username,
                "uuid": "",
                "token": "",
                "jvmArguments": [f"-Xmx{ram_gb}G", f"-Xms{ram_gb}G"],
                "launcherName": "CignoLauncher",
                "launcherVersion": "1.0",
                "gameDirectory": self.launcher_directory  # Directory principale del launcher
            }
            
            # Trova la versione Forge ESATTA installata
            versions = minecraft_launcher_lib.utils.get_installed_versions(
                self.minecraft_directory
            )
            
            self.log("Versioni installate:")
            for v in versions:
                self.log(f"  - {v['id']}")
            
            # Costruisci il nome della versione come viene salvata da Forge
            # Formato: 1.20.1-forge-47.3.0 invece di 1.20.1-47.3.0
            forge_version_id = self.forge_version.replace("-", "-forge-", 1)
            
            # Cerca la versione ESATTA
            version_found = False
            for version in versions:
                if version["id"] == forge_version_id:
                    version_found = True
                    self.log(f"✓ Trovata versione Forge ESATTA: {forge_version_id}", "SUCCESS")
                    break
                        
            if not version_found:
                # Mostra le versioni disponibili per debug
                available = [v["id"] for v in versions if "forge" in v["id"].lower()]
                error_msg = f"Forge {forge_version_id} non trovato!\n\n"
                error_msg += f"Versione richiesta: {forge_version_id}\n"
                error_msg += f"(da self.forge_version = '{self.forge_version}')\n\n"
                if available:
                    error_msg += "Versioni Forge installate:\n" + "\n".join(available)
                else:
                    error_msg += "Nessuna versione Forge trovata."
                error_msg += "\n\nProva a reinstallare cliccando 'Installa/Aggiorna'."
                messagebox.showerror("Errore", error_msg)
                self.log(error_msg, "ERROR")
                return
                
            # Prepara il comando di lancio con la versione ESATTA
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                forge_version_id,
                self.minecraft_directory,
                options
            )
            
            self.update_status("Avvio del gioco...")
            self.log(f"Versione da lanciare: {forge_version_id}")
            self.log(f"Directory di gioco: {self.launcher_directory}")
            self.log("=" * 60)
            self.log("Avvio di Minecraft...", "SUCCESS")
            self.log("=" * 60)
            
            # Passa automaticamente al tab Log
            self.notebook.select(self.log_tab)
            
            # Avvia Minecraft con cattura dell'output
            self.game_process = subprocess.Popen(
                minecraft_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.launcher_directory  # Esegui dalla directory del launcher
            )
            
            # Thread per leggere l'output
            output_thread = threading.Thread(
                target=self.read_game_output, 
                args=(self.game_process.stdout,)
            )
            output_thread.daemon = True
            output_thread.start()
            
            # Thread per monitorare la chiusura del gioco
            def monitor_game():
                self.game_process.wait()
                self.log("=" * 60)
                self.log("Minecraft chiuso", "SUCCESS")
                self.log("=" * 60)
                self.update_status("Gioco chiuso", "SUCCESS")
                # Torna al tab Home
                self.notebook.select(self.home_tab)
                
            monitor_thread = threading.Thread(target=monitor_game)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            self.update_status("Gioco in esecuzione...", "SUCCESS")
            
        except Exception as e:
            self.log(f"Errore durante l'avvio: {str(e)}", "ERROR")
            messagebox.showerror("Errore", f"Errore durante l'avvio:\n{str(e)}")
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    launcher = MinecraftLauncher()
    launcher.run()