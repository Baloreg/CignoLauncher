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
from PIL import Image, ImageTk
from account_manager import AccountManager
from login_dialog import LoginDialog

# ### MODIFICA 1: DPI AWARENESS E DARK TITLE BAR (INIZIO) ###
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception as e:
        print(f"Avviso: impossibile impostare DPI awareness: {e}")

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, 0)
    
    _original_popen_init = subprocess.Popen.__init__
    def _patched_popen_init(self, *args, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = 0
        kwargs['creationflags'] |= 0x08000000
        return _original_popen_init(self, *args, **kwargs)
    subprocess.Popen.__init__ = _patched_popen_init

def set_dark_title_bar(window):
    if sys.platform == "win32":
        try:
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception as e:
            print(f"Avviso: impossibile impostare la barra del titolo scura: {e}")
# ### MODIFICA 1: DPI AWARENESS E DARK TITLE BAR (FINE) ###


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CustomDialog:
    def __init__(self, parent, title, message, colors, dialog_type='info'):
        self.parent = parent
        self.result = None

        self.dialog = tk.Toplevel(parent)
        # ### MODIFICA ANTI-FLICKER E ANTI-FLASH (INIZIO) ###
        # Rendi la finestra completamente trasparente e nascondila
        self.dialog.attributes('-alpha', 0.0)
        self.dialog.withdraw()
        # ### MODIFICA ANTI-FLICKER E ANTI-FLASH (FINE) ###
        
        self.dialog.title(title)
        self.dialog.configure(bg=colors['bg'])
        self.dialog.resizable(False, False)
        
        try:
            icon_path = resource_path("assets/window_icon.ico")
            self.dialog.iconbitmap(icon_path)
        except tk.TclError:
            pass

        main_frame = ttk.Frame(self.dialog, padding=25)
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(pady=(0, 20), fill=tk.X, expand=True)
        
        icon_text, icon_color = "ℹ️", colors['text_secondary']
        if dialog_type == 'error': icon_text, icon_color = "❌", colors['error']
        elif dialog_type == 'success': icon_text, icon_color = "✅", colors['success']
        elif dialog_type == 'question': icon_text, icon_color = "❓", colors['accent']
        
        icon_label = ttk.Label(header_frame, text=icon_text, font=('Segoe UI', 24), foreground=icon_color)
        icon_label.pack(side=tk.LEFT, padx=(0, 20), anchor='n')

        message_label = ttk.Label(header_frame, text=message, wraplength=350, justify=tk.LEFT, font=('Segoe UI', 10))
        message_label.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        center_buttons_frame = ttk.Frame(button_frame)
        center_buttons_frame.pack()

        if dialog_type in ['info', 'error', 'success']:
            ok_btn = ttk.Button(center_buttons_frame, text="OK", command=self._on_ok)
            ok_btn.pack(); ok_btn.bind("<Return>", lambda e: self._on_ok()); ok_btn.focus_set()
        elif dialog_type == 'question':
            yes_btn = ttk.Button(center_buttons_frame, text="Sì", command=self._on_yes)
            yes_btn.pack(side=tk.LEFT, padx=(0, 5)); yes_btn.bind("<Return>", lambda e: self._on_yes()); yes_btn.focus_set()
            no_btn = ttk.Button(center_buttons_frame, text="No", command=self._on_no)
            no_btn.pack(side=tk.LEFT); no_btn.bind("<Return>", lambda e: self._on_no())

        # Centra la finestra e mostrala
        self.dialog.update_idletasks()
        parent_x, parent_y = self.parent.winfo_x(), self.parent.winfo_y()
        parent_w, parent_h = self.parent.winfo_width(), self.parent.winfo_height()
        dialog_w, dialog_h = self.dialog.winfo_reqwidth(), self.dialog.winfo_reqheight()
        x = parent_x + (parent_w // 2) - (dialog_w // 2)
        y = parent_y + (parent_h // 2) - (dialog_h // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        set_dark_title_bar(self.dialog)
        
        # ### MODIFICA ANTI-FLICKER E ANTI-FLASH (INIZIO) ###
        # Mostra la finestra e rendila opaca solo ora che è pronta
        self.dialog.deiconify()
        self.dialog.attributes('-alpha', 1.0)
        # ### MODIFICA ANTI-FLICKER E ANTI-FLASH (FINE) ###

    def _on_ok(self): self.dialog.destroy()
    def _on_yes(self): self.result = True; self.dialog.destroy()
    def _on_no(self): self.result = False; self.dialog.destroy()
        
    def show(self):
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.parent.wait_window(self.dialog)
        return self.result

class MinecraftLauncher:
    def __init__(self):
        self.root = tk.Tk()
        # ### MODIFICA ANTI-FLICKER E ANTI-FLASH (INIZIO) ###
        # Rendi la finestra completamente trasparente e nascondila
        self.root.attributes('-alpha', 0.0)
        self.root.withdraw()
        # ### MODIFICA ANTI-FLICKER E ANTI-FLASH (FINE) ###
        
        self.root.title("CignoLauncher")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        try:
            self.root.iconbitmap(resource_path("assets/window_icon.ico"))
        except tk.TclError:
            print("Icona della finestra (window_icon.ico) non trovata.")
        
        self.colors = {
            'bg': '#1e1e1e', 'bg_secondary': '#2d2d2d', 'bg_tertiary': '#3d3d3d',
            'accent': '#0078d4', 'accent_hover': '#106ebe', 'text': '#ffffff',
            'text_secondary': '#b0b0b0', 'success': '#4caf50', 'error': '#f44336',
            'border': '#404040'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        if sys.platform == "win32":
            appdata = os.getenv('APPDATA')
            self.launcher_directory = os.path.join(appdata, "CignoLauncher")
        else:
            home = os.path.expanduser("~")
            self.launcher_directory = os.path.join(home, ".cignolauncher")
        
        self.minecraft_directory = os.path.join(self.launcher_directory, "minecraft")
        self.modpack_folder = os.path.join(self.launcher_directory, "mods")
        self.config_folder = os.path.join(self.launcher_directory, "config")
        self.resourcepacks_folder = os.path.join(self.launcher_directory, "resourcepacks")
        self.shaderpacks_folder = os.path.join(self.launcher_directory, "shaderpacks")
        self.saves_folder = os.path.join(self.launcher_directory, "saves")
        self.additional_folders = {}
        
        for folder in [self.launcher_directory, self.minecraft_directory, self.modpack_folder, self.config_folder, self.resourcepacks_folder, self.shaderpacks_folder, self.saves_folder]:
            Path(folder).mkdir(parents=True, exist_ok=True)
        
        self.modpack_url = "https://raw.githubusercontent.com/Baloreg/Cignopack/main/manifest.json"
        self.launcher_version = "1.0.1"
        self.launcher_update_url = "https://raw.githubusercontent.com/Baloreg/Cignopack/main/launcher_version.json"
        self.launcher_download_url = "https://github.com/Baloreg/Cignopack/releases/latest/download/CignoLauncher.exe"
        self.minecraft_version = "1.20.1"
        self.forge_version = "1.20.1-47.4.6"

        # ### MODIFICA INIZIO: Inserisci qui le tue credenziali Azure ###
        # ATTENZIONE: Non salvare queste credenziali in un repository pubblico!
        self.AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "your-client-id-here")
        self.AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "your-secret-here")
        # ### MODIFICA FINE ###

        self.install_state_file = os.path.join(self.launcher_directory, "install_state.json")
        self.account_manager = AccountManager(self.launcher_directory)
        self.game_process = None
        
        self.setup_styles()
        self.setup_ui()
        
        set_dark_title_bar(self.root)
        
        self.center_window(self.root)
        self.check_updates_on_startup()
        self.check_installation_status()

    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')
        
        # ### MODIFICA ANTI-FLICKER E ANTI-FLASH (INIZIO) ###
        # Mostra la finestra e rendila opaca solo dopo averla centrata
        window.deiconify()
        window.attributes('-alpha', 1.0)
        # ### MODIFICA ANTI-FLICKER E ANTI-FLASH (FINE) ###
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=self.colors['bg'], foreground=self.colors['text'], fieldbackground=self.colors['bg_secondary'], bordercolor=self.colors['border'], darkcolor=self.colors['bg_secondary'], lightcolor=self.colors['bg_secondary'])
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['text'])
        style.configure('Title.TLabel', background=self.colors['bg'], foreground=self.colors['accent'], font=('Segoe UI', 32, 'bold'))
        style.configure('Status.TLabel', background=self.colors['bg'], foreground=self.colors['text_secondary'], font=('Segoe UI', 9))
        style.configure('TEntry', fieldbackground=self.colors['bg_secondary'], foreground=self.colors['text'], bordercolor=self.colors['border'], insertcolor=self.colors['text'])
        style.map('TEntry', fieldbackground=[('focus', self.colors['bg_tertiary'])], bordercolor=[('focus', self.colors['accent'])])
        style.configure('TSpinbox', fieldbackground=self.colors['bg_secondary'], foreground=self.colors['text'], bordercolor=self.colors['border'], arrowcolor=self.colors['text'])
        style.map('TSpinbox', fieldbackground=[('focus', self.colors['bg_tertiary'])], bordercolor=[('focus', self.colors['accent'])])
        style.configure('TButton', background=self.colors['accent'], foreground=self.colors['text'], bordercolor=self.colors['accent'], focuscolor=self.colors['accent'], font=('Segoe UI', 10, 'bold'), padding=(20, 10))
        style.map('TButton', background=[('active', self.colors['accent_hover']), ('disabled', self.colors['bg_tertiary'])], foreground=[('disabled', self.colors['text_secondary'])])
        style.configure('TProgressbar', background=self.colors['accent'], troughcolor=self.colors['bg_secondary'], bordercolor=self.colors['border'], lightcolor=self.colors['accent'], darkcolor=self.colors['accent'])
        style.configure('TLabelframe', background=self.colors['bg'], foreground=self.colors['text'], bordercolor=self.colors['border'])
        style.configure('TLabelframe.Label', background=self.colors['bg'], foreground=self.colors['text'], font=('Segoe UI', 11, 'bold'))
        
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=1, bordercolor=self.colors['border'])
        style.configure('TNotebook.Tab',
                        background=self.colors['bg'],
                        foreground=self.colors['text_secondary'],
                        padding=(15, 8),
                        font=('Segoe UI', 10, 'bold'),
                        borderwidth=0)
        style.map('TNotebook.Tab',
                  background=[('selected', self.colors['bg']), ('active', self.colors['bg_secondary'])],
                  foreground=[('selected', self.colors['accent']), ('active', self.colors['text'])],
                 )

    def load_icon(self, path, size):
        try:
            full_path = resource_path(path)
            image = Image.open(full_path).resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except FileNotFoundError:
            print(f"Icona non trovata: {path}")
            return None

    def setup_ui(self, *args, **kwargs):
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        self.icons = {
            "home": self.load_icon("assets/home_icon.png", (20, 20)),
            "account": self.load_icon("assets/account_icon.png", (20, 20)),
            "settings": self.load_icon("assets/settings_icon.png", (20, 20)),
            "log": self.load_icon("assets/log_icon.png", (20, 20))
        }

        self.home_tab = ttk.Frame(self.notebook)
        self.account_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.home_tab, text="Home", image=self.icons["home"], compound=tk.LEFT)
        self.notebook.add(self.account_tab, text="Account", image=self.icons["account"], compound=tk.LEFT)
        self.notebook.add(self.settings_tab, text="Impostazioni", image=self.icons["settings"], compound=tk.LEFT)
        self.notebook.add(self.log_tab, text="Log", image=self.icons["log"], compound=tk.LEFT)
        
        self.setup_home_tab()
        self.setup_account_tab()
        self.setup_settings_tab()
        self.setup_log_tab()
        
    def setup_home_tab(self):
        main_frame = ttk.Frame(self.home_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        top_container = ttk.Frame(main_frame)
        top_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(20, 0))

        header_frame = ttk.Frame(top_container)
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(header_frame, text="CIGNOPACK", style='Title.TLabel', anchor=tk.CENTER)
        title_label.pack(fill=tk.X, pady=(10, 5))
        
        subtitle_label = ttk.Label(header_frame, text=f"Minecraft {self.minecraft_version} • Forge {self.forge_version.split('-')[-1]}", style='Status.TLabel', anchor=tk.CENTER)
        subtitle_label.pack(fill=tk.X)
        
        logo_frame = ttk.Frame(top_container)
        logo_frame.pack(expand=True)

        bottom_container = ttk.Frame(main_frame)
        bottom_container.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 10))

        progress_frame = ttk.Frame(bottom_container)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="Pronto per il lancio", style='Status.TLabel')
        self.status_label.pack(anchor=tk.W)
        
        button_frame = ttk.Frame(bottom_container)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        buttons_container = ttk.Frame(button_frame)
        buttons_container.pack(anchor=tk.CENTER)
        
        self.install_btn = ttk.Button(buttons_container, text="Installa/Aggiorna", command=self.start_installation)
        self.install_btn.pack(side=tk.LEFT, padx=5)
        
        self.play_btn = ttk.Button(buttons_container, text="GIOCA", command=self.start_game, state=tk.DISABLED)
        self.play_btn.pack(side=tk.LEFT, padx=5)

    def setup_account_tab(self):
        main_frame = ttk.Frame(self.account_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=40)
        
        account_frame = ttk.LabelFrame(main_frame, text="Account Corrente", padding=25)
        account_frame.pack(fill=tk.X, pady=(0, 20))

        self.account_info_frame = ttk.Frame(account_frame)
        self.account_info_frame.pack(fill=tk.X)
        
        self.update_account_display()
        
        ttk.Button(main_frame, text="Gestisci Account", command=self.show_account_dialog, padding=(20, 15)).pack(pady=(20, 0))

    def setup_settings_tab(self):
        main_frame = ttk.Frame(self.settings_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=40)
        
        settings_frame = ttk.LabelFrame(main_frame, text="Impostazioni di Gioco", padding=25)
        settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        ram_frame = ttk.Frame(settings_frame)
        ram_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(ram_frame, text="RAM Allocata (GB)", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 5))
        self.ram_var = tk.StringVar(value="4")
        ram_spinbox = ttk.Spinbox(ram_frame, from_=2, to=16, textvariable=self.ram_var, font=('Segoe UI', 10), width=10)
        ram_spinbox.pack(anchor=tk.W)
        
        ttk.Label(ram_frame, text="La RAM consigliata per il modpack è tra 4 e 8 GB.", style='Status.TLabel').pack(anchor=tk.W, pady=(10, 0))

    def setup_log_tab(self):
        log_container = ttk.Frame(self.log_tab)
        log_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(log_container, text="Console", font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        log_frame = ttk.Frame(log_container)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=('Consolas', 9), bg=self.colors['bg_secondary'],
            fg=self.colors['text'], insertbackground=self.colors['text'],
            selectbackground=self.colors['accent'], selectforeground=self.colors['text'],
            relief=tk.FLAT, borderwidth=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state='disabled')
        
        self.log_text.tag_config('INFO', foreground='#4fc3f7')
        self.log_text.tag_config('ERROR', foreground='#ef5350')
        self.log_text.tag_config('SUCCESS', foreground='#66bb6a')
        self.log_text.tag_config('GAME', foreground='#ffa726')
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}\n"
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, formatted_message, level)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()

    def update_account_display(self):
        for widget in self.account_info_frame.winfo_children():
            widget.destroy()
        if self.account_manager.current_account:
            account = self.account_manager.current_account
            icon = "🌐" if account['type'] == 'microsoft' else "👤"
            type_text = "Account Microsoft" if account['type'] == 'microsoft' else "Account Offline"
            color = self.colors['success'] if account['type'] == 'microsoft' else self.colors['text_secondary']
            name_label = ttk.Label(self.account_info_frame, text=f"{icon} {account['username']}", font=('Segoe UI', 12, 'bold'))
            name_label.pack(anchor=tk.W)
            type_label = ttk.Label(self.account_info_frame, text=type_text, foreground=color, font=('Segoe UI', 9))
            type_label.pack(anchor=tk.W, pady=(2,0))
        else:
            no_account_label = ttk.Label(self.account_info_frame, text="❌ Nessun account configurato", foreground=self.colors['error'], font=('Segoe UI', 10))
            no_account_label.pack(anchor=tk.W)
            hint_label = ttk.Label(self.account_info_frame, text="Clicca 'Gestisci Account' per configurare", foreground=self.colors['text_secondary'], font=('Segoe UI', 8))
            hint_label.pack(anchor=tk.W, pady=(5, 0))

    def show_account_dialog(self):
        icon_path = resource_path("assets/window_icon.ico")
        # ### MODIFICA INIZIO: Passa le credenziali al dialogo ###
        dialog = LoginDialog(self.root, self.account_manager, self.colors, icon_path=icon_path, client_id=self.AZURE_CLIENT_ID, client_secret=self.AZURE_CLIENT_SECRET)
        # ### MODIFICA FINE ###
        dialog.show()
        self.update_account_display()
        
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
        if os.path.exists(self.install_state_file):
            try:
                with open(self.install_state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_install_state(self, state):
        with open(self.install_state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def check_installation_status(self):
        state = self.get_install_state()
        if state.get('minecraft_version') == self.minecraft_version and state.get('forge_installed') == True:
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
            
            minecraft_installed = state.get('minecraft_version') == self.minecraft_version
            if not minecraft_installed:
                self.update_status("Installazione Minecraft...")
                minecraft_launcher_lib.install.install_minecraft_version(self.minecraft_version, self.minecraft_directory, callback={"setStatus": lambda text: self.update_status(text), "setProgress": lambda current: self.callback_progress(current, 100, "Download")})
                state['minecraft_version'] = self.minecraft_version
                self.save_install_state(state)
                self.log(f"Minecraft {self.minecraft_version} installato!", "SUCCESS")
            else:
                self.log(f"Minecraft {self.minecraft_version} già installato", "SUCCESS")
            
            forge_installed = (state.get('forge_installed') == True and state.get('forge_version') == self.forge_version)
            if not forge_installed:
                self.update_status(f"Installazione Forge {self.forge_version}...")
                self.update_progress(0)
                try:
                    self.clean_corrupted_libraries()
                    self.log(f"Installazione versione ESATTA: {self.forge_version}")
                    minecraft_launcher_lib.forge.install_forge_version(self.forge_version, self.minecraft_directory, callback={"setStatus": lambda text: self.update_status(text), "setProgress": lambda current: self.callback_progress(current, 100, "Forge")}, java=self.get_java_executable())
                    self.log(f"Forge {self.forge_version} installato con successo!", "SUCCESS")
                    state['forge_installed'] = True
                    state['forge_version'] = self.forge_version
                    self.save_install_state(state)
                except Exception as forge_error:
                    error_msg = str(forge_error)
                    self.log(f"Errore installazione Forge: {error_msg}", "ERROR")
                    if "Checksum" in error_msg or "checksum" in error_msg:
                        self.update_status("Errore: File corrotto rilevato", "ERROR")
                        dialog_msg = "Sono stati rilevati file scaricati corrotti.\n\nVuoi ripulire i file corrotti e riprovare?\n(Questo cancellerà le librerie di Forge scaricate)"
                        dialog = CustomDialog(self.root, "File corrotto", dialog_msg, self.colors, dialog_type='question')
                        if dialog.show():
                            self.clean_forge_libraries()
                            state['forge_installed'] = False
                            self.save_install_state(state)
                            self.update_status("File puliti. Riprova l'installazione.")
                            self.install_btn.config(state=tk.NORMAL)
                            return
                    self.update_status("Attenzione: Installazione Forge fallita", "ERROR")
                    dialog_msg = f"L'installazione di Forge è fallita:\n{error_msg[:200]}\n\nControlla il log per dettagli completi."
                    CustomDialog(self.root, "Errore Forge", dialog_msg, self.colors, dialog_type='error').show()
                    raise
            else:
                self.log(f"Forge già installato: {state.get('forge_version', 'versione sconosciuta')}", "SUCCESS")
            
            self.update_status("Controllo aggiornamenti modpack...")
            self.update_modpack()
            self.update_status("Installazione completata!", "SUCCESS")
            self.update_progress(100)
            self.play_btn.config(state=tk.NORMAL)
            CustomDialog(self.root, "Successo", "Installazione completata con successo!", self.colors, dialog_type='success').show()
        except Exception as e:
            self.update_status(f"Errore: {str(e)}", "ERROR")
            self.log(f"Errore durante l'installazione: {str(e)}", "ERROR")
            CustomDialog(self.root, "Errore", f"Si è verificato un errore:\n{str(e)}", self.colors, dialog_type='error').show()
        finally:
            self.install_btn.config(state=tk.NORMAL)
            
    def clean_corrupted_libraries(self):
        corrupted_file = os.path.join(self.minecraft_directory, "libraries/net/minecraftforge/JarJarFileSystems/0.3.26/JarJarFileSystems-0.3.26.jar")
        if os.path.exists(corrupted_file):
            try:
                os.remove(corrupted_file)
                self.log(f"Rimosso file corrotto: {corrupted_file}")
            except Exception as e:
                self.log(f"Impossibile rimuovere file corrotto: {e}", "ERROR")
    
    def get_java_executable(self):
        java_path = minecraft_launcher_lib.utils.get_java_executable()
        if java_path:
            self.log(f"Trovato Java: {java_path}")
            return java_path
        return "java"
    
    def clean_forge_libraries(self):
        forge_libs = os.path.join(self.minecraft_directory, "libraries/net/minecraftforge")
        if os.path.exists(forge_libs):
            try:
                shutil.rmtree(forge_libs)
                self.log(f"Pulite librerie Forge da: {forge_libs}")
                CustomDialog(self.root, "Pulizia completata", "Le librerie corrotte sono state rimosse.", self.colors, dialog_type='info').show()
            except Exception as e:
                self.log(f"Errore durante la pulizia: {e}", "ERROR")
                CustomDialog(self.root, "Errore", f"Impossibile pulire le librerie:\n{e}", self.colors, dialog_type='error').show()
                
    def get_protected_files(self):
        return ['options.txt', 'optionsof.txt', 'optionsshaders.txt', 'servers.dat', 'realms_persistence.json']
    
    def is_protected_file(self, file_path, category):
        protected = self.get_protected_files()
        file_name = os.path.basename(file_path)
        if file_name in protected:
            return True
        if category == "config":
            return True
        if category == "root" and file_name in protected:
            return True
        return False
    
    def update_modpack(self):
        try:
            manifest = self.get_modpack_manifest()
            if not manifest:
                self.update_status("Nessun manifest trovato")
                return

            for folder in [self.resourcepacks_folder, self.shaderpacks_folder]:
                Path(folder).mkdir(parents=True, exist_ok=True)

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
            categories_order = ['root', 'mods', 'config', 'data', 'emotes', 'resourcepacks', 'shaderpacks']
            
            for category in categories_order:
                if category not in manifest: 
                    continue
                files = manifest[category]
                if not isinstance(files, list) or not files: 
                    continue
                
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
                    self.additional_folders[category] = target_folder
                
                Path(target_folder).mkdir(parents=True, exist_ok=True)
                
                self.log(f"Controllo {len(files)} file in {category}..." if category != "config" else f"Controllo {len(files)} file in {category} (file esistenti protetti)...")
                
                for file_info in files:
                    current_file += 1
                    self.process_file(file_info, target_folder, category, current_file, total_files)
                
                if category == "mods":
                    self.log("Pulizia mod obsolete (solo .jar)...")
                    self.clean_mods_folder(files, target_folder)

            for category, files in manifest.items():
                if category in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated'] or category in categories_order: 
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
            self.log("ℹ️ I file di configurazione esistenti sono stati preservati", "INFO")
        except Exception as e:
            self.log(f"Errore aggiornamento modpack: {e}", "ERROR")

    def clean_mods_folder(self, manifest_files, mods_folder):
        if not os.path.exists(mods_folder): return
        manifest_jar_names = {f["name"] for f in manifest_files if f["name"].endswith(".jar")}
        removed_count = 0
        for item in os.listdir(mods_folder):
            item_path = os.path.join(mods_folder, item)
            if os.path.isdir(item_path): continue
            if item.endswith(".jar") and item not in manifest_jar_names:
                try:
                    os.remove(item_path)
                    removed_count += 1
                    self.log(f"🗑️ Rimossa mod obsoleta: {item}")
                except Exception as e:
                    self.log(f"Errore rimozione {item}: {e}", "ERROR")
        if removed_count > 0:
            self.log(f"✅ Rimosse {removed_count} mod obsolete", "SUCCESS")
    
    def process_file(self, file_info, target_folder, file_type, current, total):
        file_name = file_info["name"]
        file_url = file_info["url"]
        expected_hash = file_info.get("sha256", "")
        
        file_path = os.path.join(target_folder, file_info.get("path", file_name))
        file_path = os.path.normpath(file_path)
        
        file_dir = os.path.dirname(file_path)
        if file_dir: Path(file_dir).mkdir(parents=True, exist_ok=True)
        
        if os.path.exists(file_path) and self.is_protected_file(file_path, file_type):
            self.update_progress((current / total) * 100)
            return
        
        needs_download = True
        if os.path.exists(file_path) and expected_hash:
            if self.calculate_sha256(file_path) == expected_hash: needs_download = False
            else: self.log(f"⚠ Hash diverso per {file_name}, riscarico...")
        
        if needs_download:
            self.update_status(f"Scaricamento {file_type}: {file_name}...")
            self.log(f"↓ Scaricamento {file_name}...")
            try:
                if os.path.exists(file_path): os.remove(file_path)
                self.download_file(file_url, file_path)
                if expected_hash and self.calculate_sha256(file_path) != expected_hash:
                    self.log(f"❌ Hash non corrisponde per {file_name}!", "ERROR")
                    os.remove(file_path)
                    raise Exception(f"Hash mismatch per {file_name}")
                self.log(f"✓ {file_name} scaricato con successo", "SUCCESS")
            except Exception as e:
                self.log(f"❌ Errore download {file_name}: {e}", "ERROR")
                raise
        
        self.update_progress((current / total) * 100)
        
    def get_modpack_manifest(self):
        try:
            self.log(f"Scaricamento manifest da: {self.modpack_url}")
            response = requests.get(self.modpack_url, timeout=10)
            if response.status_code == 200:
                manifest = response.json()
                self.log(f"Manifest scaricato con successo", "SUCCESS")
                categories = [k for k in manifest.keys() if k not in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated']]
                self.log(f"Categorie trovate: {', '.join(categories)}")
                return manifest
        except Exception as e:
            self.log(f"Errore scaricamento manifest: {e}", "ERROR")
        return None
        
    def download_file(self, url, destination):
        response = requests.get(url, stream=True)
        response.raise_for_status()
        is_text_file = any(str(destination).endswith(ext) for ext in ['.txt', '.properties', '.json', '.toml', '.ini', '.cfg', '.conf', '.md', '.jsonc', '.json5', '.local', '.lewidget', '.html'])
        if is_text_file:
            content = response.content.decode('utf-8', errors='ignore')
            with open(destination, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
        else:
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
                
    def calculate_sha256(self, file_path):
        try:
            is_text_file = any(str(file_path).endswith(ext) for ext in ['.txt', '.properties', '.json', '.toml', '.ini', '.cfg', '.conf', '.md', '.jsonc', '.json5', '.local', '.lewidget', '.html'])
            if is_text_file:
                with open(file_path, 'r', encoding='utf-8', errors='ignore', newline='') as f: 
                    content = f.read()
                return hashlib.sha256(content.encode('utf-8')).hexdigest()
            else:
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(8192), b""): sha256_hash.update(byte_block)
                return sha256_hash.hexdigest()
        except Exception as e:
            self.log(f"Errore calcolo hash per {file_path}: {e}", "ERROR")
            return ""
                    
    def read_game_output(self, pipe):
        try:
            for line in iter(pipe.readline, ''):
                if line: self.log(line.strip(), "GAME")
        except: pass

    def check_updates_on_startup(self):
        def check_updates_thread():
            if not self.account_manager.current_account:
                self.root.after(0, self.show_account_dialog)
            if self.check_launcher_update(): return
            if not self.check_installation_status():
                self.update_status("Installazione necessaria", "INFO")
                return
            self.update_status("Controllo aggiornamenti modpack...")
            try:
                manifest = self.get_modpack_manifest()
                if manifest:
                    needs_update = self.check_modpack_needs_update(manifest)
                    if needs_update:
                        self.log(f"Trovati aggiornamenti per {len(needs_update)} file!", "INFO")
                        dialog_msg = f"Sono disponibili aggiornamenti per il modpack:\n- {len(needs_update)} file da aggiornare\n\nVuoi scaricare gli aggiornamenti ora?"
                        dialog = CustomDialog(self.root, "Aggiornamenti disponibili", dialog_msg, self.colors, dialog_type='question')
                        if dialog.show():
                            self.start_installation()
                    else:
                        self.log("Modpack già aggiornato!", "SUCCESS")
                        self.update_status("Pronto per il lancio", "SUCCESS")
            except Exception as e:
                self.log(f"Errore controllo aggiornamenti: {e}", "ERROR")
                self.update_status("Pronto per il lancio", "SUCCESS")
        thread = threading.Thread(target=check_updates_thread, daemon=True).start()

    def check_launcher_update(self):
        try:
            self.update_status("Controllo aggiornamenti launcher...")
            response = requests.get(self.launcher_update_url, timeout=10)
            if response.status_code == 200:
                update_info = response.json()
                latest_version = update_info.get("version", "0.0.0")
                if self.compare_versions(latest_version, self.launcher_version) > 0:
                    self.log(f"Nuova versione disponibile: {latest_version}", "INFO")
                    message = f"È disponibile una nuova versione del launcher!\n\nVersione attuale: {self.launcher_version}\nNuova versione: {latest_version}\n\nNovità:\n{update_info.get('changelog', 'N/A')}\n\nVuoi scaricare e installare l'aggiornamento?"
                    dialog = CustomDialog(self.root, "Aggiornamento disponibile", message, self.colors, dialog_type='question')
                    if dialog.show():
                        self.download_and_install_update()
                        return True
                else:
                    self.log(f"Launcher aggiornato (v{self.launcher_version})", "SUCCESS")
            return False
        except Exception as e:
            self.log(f"Impossibile controllare aggiornamenti launcher: {e}", "ERROR")
            return False

    def compare_versions(self, v1, v2):
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        for i in range(max(len(parts1), len(parts2))):
            p1 = parts1[i] if i < len(parts1) else 0
            p2 = parts2[i] if i < len(parts2) else 0
            if p1 > p2: return 1
            elif p1 < p2: return -1
        return 0

    def download_and_install_update(self):
        try:
            self.update_status("Download aggiornamento launcher...")
            self.log("Scaricamento nuova versione...", "INFO")
            temp_file = os.path.join(self.launcher_directory, "CignoLauncher_new.exe")
            response = requests.get(self.launcher_download_url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0: self.update_progress((downloaded / total_size) * 100)
            self.log("Download completato!", "SUCCESS")
            batch_script = os.path.join(self.launcher_directory, "update.bat")
            current_exe = sys.executable if getattr(sys, 'frozen', False) else __file__
            with open(batch_script, 'w') as f:
                f.write(f'@echo off\necho Aggiornamento in corso...\ntimeout /t 2 /nobreak > nul\ndel /f /q "{current_exe}"\nmove /y "{temp_file}" "{current_exe}"\nstart "" "{current_exe}"\ndel /f /q "%~f0"\n')
            self.log("Riavvio del launcher...", "INFO")
            CustomDialog(self.root, "Aggiornamento completato", "Il launcher verrà riavviato per completare l'aggiornamento.", self.colors, dialog_type='info').show()
            subprocess.Popen([batch_script], creationflags=0x08000000)
            self.root.destroy()
        except Exception as e:
            self.log(f"Errore durante l'aggiornamento: {e}", "ERROR")
            CustomDialog(self.root, "Errore", f"Impossibile aggiornare il launcher:\n{e}", self.colors, dialog_type='error').show()   

    def check_modpack_needs_update(self, manifest):
        files_to_update = []
        
        for folder in [self.resourcepacks_folder, self.shaderpacks_folder]:
            Path(folder).mkdir(parents=True, exist_ok=True)
        
        for category, files in manifest.items():
            if category in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated'] or not isinstance(files, list): 
                continue
            
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
            
            for file_info in files:
                file_path = os.path.normpath(os.path.join(target_folder, file_info.get("path", file_info["name"])))
                
                if os.path.exists(file_path) and self.is_protected_file(file_path, category): 
                    continue
                
                needs_update = True
                if os.path.exists(file_path) and file_info.get("sha256"):
                    if self.calculate_sha256(file_path) == file_info["sha256"]: 
                        needs_update = False
                
                if needs_update:
                    files_to_update.append(f"{category}/{file_info['name']}")
        
        return files_to_update

    def refresh_current_account_token(self):
        """Aggiorna il token Microsoft se scaduto"""
        account = self.account_manager.current_account
        if not account or account.get("type") != "microsoft":
            return True  # Non è necessario fare nulla per account offline

        if not self.account_manager.is_token_expired():
            return True  # Token ancora valido

        self.log("Token Microsoft scaduto. Tentativo di refresh...", "INFO")
        refresh_token = account.get("refresh_token")
        if not refresh_token:
            self.log("Refresh token non trovato. È necessario un nuovo accesso.", "ERROR")
            return False

        try:
            # Usa complete_refresh con i parametri corretti
            new_data = minecraft_launcher_lib.microsoft_account.complete_refresh(
                self.AZURE_CLIENT_ID,
                self.AZURE_CLIENT_SECRET,
                "http://localhost:5000/callback",
                refresh_token
            )
            
            # Ri-usiamo la funzione add_microsoft_account che sovrascriverà i dati vecchi
            self.account_manager.add_microsoft_account(new_data)
            self.log("Token Microsoft aggiornato con successo!", "SUCCESS")
            self.update_account_display()
            return True
        except minecraft_launcher_lib.exceptions.InvalidRefreshToken:
            self.log("Refresh token non valido. È necessario un nuovo accesso.", "ERROR")
            return False
        except Exception as e:
            self.log(f"Impossibile aggiornare il token: {e}", "ERROR")
            self.log("Per favore, accedi di nuovo manualmente.", "INFO")
            return False

    def start_game(self):
        try:
            if not self.account_manager.current_account:
                CustomDialog(self.root, "Account richiesto", "Configura un account prima di giocare!", self.colors, dialog_type='info').show()
                self.show_account_dialog()
                return

            # ### MODIFICA INIZIO: Controlla e aggiorna il token prima di avviare ###
            if not self.refresh_current_account_token():
                 CustomDialog(self.root, "Accesso Scaduto", "Il tuo accesso Microsoft è scaduto e non è stato possibile rinnovarlo. Per favore, accedi di nuovo.", self.colors, dialog_type='error').show()
                 self.show_account_dialog()
                 return
            # ### MODIFICA FINE ###
            
            account_options = self.account_manager.get_launch_options()
            ram_gb = int(self.ram_var.get())
            options = {
                "username": account_options["username"], "uuid": account_options["uuid"], "token": account_options["token"],
                "jvmArguments": [f"-Xmx{ram_gb}G", f"-Xms{ram_gb}G"],
                "launcherName": "CignoLauncher", "launcherVersion": "1.0", "gameDirectory": self.launcher_directory
            }
            
            versions = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_directory)
            self.log("Versioni installate:")
            for v in versions: self.log(f"  - {v['id']}")
            
            forge_version_id = self.forge_version.replace("-", "-forge-", 1)
            
            if not any(v['id'] == forge_version_id for v in versions):
                available = [v["id"] for v in versions if "forge" in v["id"].lower()]
                error_msg = f"Forge {forge_version_id} non trovato!\n\nVersione richiesta: {forge_version_id}\n\n" + (f"Versioni Forge installate:\n" + "\n".join(available) if available else "Nessuna versione Forge trovata.") + "\n\nProva a reinstallare."
                CustomDialog(self.root, "Errore", error_msg, self.colors, dialog_type='error').show()
                self.log(error_msg, "ERROR")
                return
                
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(forge_version_id, self.minecraft_directory, options)
            
            self.update_status("Avvio del gioco...")
            self.log(f"Versione da lanciare: {forge_version_id}")
            self.log(f"Directory di gioco: {self.launcher_directory}")
            self.log("=" * 60 + "\nAvvio di Minecraft...\n" + "=" * 60, "SUCCESS")
            
            self.notebook.select(self.log_tab)
            
            self.game_process = subprocess.Popen(minecraft_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, cwd=self.launcher_directory)
            
            threading.Thread(target=self.read_game_output, args=(self.game_process.stdout,), daemon=True).start()
            
            def monitor_game():
                self.game_process.wait()
                self.log("=" * 60 + "\nMinecraft chiuso\n" + "=" * 60, "SUCCESS")
                self.update_status("Gioco chiuso", "SUCCESS")
                self.notebook.select(self.home_tab)
            threading.Thread(target=monitor_game, daemon=True).start()
            
            self.update_status("Gioco in esecuzione...", "SUCCESS")
            
        except Exception as e:
            self.log(f"Errore durante l'avvio: {str(e)}", "ERROR")
            CustomDialog(self.root, "Errore", f"Errore durante l'avvio:\n{str(e)}", self.colors, dialog_type='error').show()
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    launcher = MinecraftLauncher()
    launcher.run()