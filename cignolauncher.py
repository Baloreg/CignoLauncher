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
        self.root.title("CignoLaucher")
        self.root.geometry("700x550")
        
        # Percorsi
        self.minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()
        self.modpack_folder = os.path.join(self.minecraft_directory, "mods")
        
        # URL dove ospiti il tuo modpack (modifica questo!)
        self.modpack_url = "https://raw.githubusercontent.com/Baloreg/Cignopack/main/manifest.json"
        
        # Versioni
        self.minecraft_version = "1.20.1"
        self.forge_version = "1.20.1-47.4.6"
        forge_installed = self.forge_version.replace("-","-forge-")
        
        # Processo del gioco
        self.game_process = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Frame principale
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Titolo
        title_label = ttk.Label(main_frame, text="Cignopack", 
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Username
        ttk.Label(main_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(main_frame, width=30)
        self.username_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        self.username_entry.insert(0, "Giocatore")
        
        # RAM
        ttk.Label(main_frame, text="RAM (GB):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.ram_var = tk.StringVar(value="4")
        ram_spinbox = ttk.Spinbox(main_frame, from_=2, to=16, textvariable=self.ram_var, width=28)
        ram_spinbox.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.grid(row=3, column=0, columnspan=2, pady=15)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Pronto", 
                                     font=('Arial', 10))
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Area log con scrollbar
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70, 
                                                   state='disabled', wrap=tk.WORD,
                                                   font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Pulsanti
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        self.install_btn = ttk.Button(button_frame, text="Installa/Aggiorna", 
                                     command=self.start_installation)
        self.install_btn.grid(row=0, column=0, padx=5)
        
        self.play_btn = ttk.Button(button_frame, text="Gioca", 
                                  command=self.start_game, state=tk.DISABLED)
        self.play_btn.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="Pulisci Log", 
                  command=self.clear_log).grid(row=0, column=2, padx=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
    def log(self, message, level="INFO"):
        """Aggiunge un messaggio al log interno"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()
        
    def clear_log(self):
        """Pulisce l'area log"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        
    def update_status(self, message):
        self.status_label.config(text=message)
        self.log(message)
        
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
        
    def start_installation(self):
        thread = threading.Thread(target=self.install_game)
        thread.daemon = True
        thread.start()
        
    def install_game(self):
        try:
            self.install_btn.config(state=tk.DISABLED)
            
            # 1. Installa Minecraft vanilla
            self.update_status("Installazione Minecraft...")
            minecraft_launcher_lib.install.install_minecraft_version(
                self.minecraft_version,
                self.minecraft_directory,
                callback={
                    "setStatus": lambda text: self.update_status(text),
                    "setProgress": lambda current: self.callback_progress(current, 100, "Download")
                }
            )
            
            # 2. Installa Forge
            self.update_status("Ricerca versione Forge...")
            self.update_progress(0)
            
            try:
                self.clean_corrupted_libraries()
                
                self.update_status("Scaricamento lista versioni Forge...")
                forge_versions = minecraft_launcher_lib.forge.list_forge_versions()
                
                compatible_versions = [v for v in forge_versions if self.minecraft_version in v]
                
                if not compatible_versions:
                    raise Exception(f"Nessuna versione Forge trovata per Minecraft {self.minecraft_version}")
                
                version_to_install = self.forge_version
                
                if version_to_install not in compatible_versions:
                    raise Exception(f"Nessuna versione Forge trovata con quel nome")
                
                self.log(f"Versioni Forge 1.20.1 trovate: {len(compatible_versions)}")
                self.log(f"Installazione versione: {version_to_install}")
                
                self.update_status(f"Installazione Forge {version_to_install}...")
                
                # Installa Forge con callback personalizzato per i processor
                minecraft_launcher_lib.forge.install_forge_version(
                    version_to_install,
                    self.minecraft_directory,
                    callback={
                        "setStatus": lambda text: self.update_status(text),
                        "setProgress": lambda current: self.callback_progress(current, 100, "Forge")
                    },
                    java=self.get_java_executable()
                )
                
                self.log(f"Forge installato con successo: {version_to_install}")
                
            except Exception as forge_error:
                error_msg = str(forge_error)
                self.log(f"Errore installazione Forge: {error_msg}", "ERROR")
                
                if "Checksum" in error_msg or "checksum" in error_msg:
                    self.update_status("Errore: File corrotto rilevato")
                    if messagebox.askyesno(
                        "File corrotto", 
                        "Sono stati rilevati file scaricati corrotti.\n\n"
                        "Vuoi ripulire i file corrotti e riprovare?\n"
                        "(Questo cancellerà le librerie di Forge scaricate)"
                    ):
                        self.clean_forge_libraries()
                        self.update_status("File puliti. Riprova l'installazione.")
                        self.install_btn.config(state=tk.NORMAL)
                        return
                
                self.update_status("Attenzione: Installazione Forge fallita")
                messagebox.showerror(
                    "Errore Forge", 
                    f"L'installazione di Forge è fallita:\n{error_msg[:200]}\n\n"
                    "Controlla la console per dettagli completi."
                )
                raise
                
            # 3. Scarica/Aggiorna modpack
            self.update_status("Controllo aggiornamenti modpack...")
            self.update_modpack()
            
            self.update_status("Installazione completata!")
            self.update_progress(100)
            self.play_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Successo", "Installazione completata con successo!")
            
        except Exception as e:
            self.update_status(f"Errore: {str(e)}")
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
                import shutil
                shutil.rmtree(forge_libs)
                self.log(f"Pulite librerie Forge da: {forge_libs}")
                messagebox.showinfo("Pulizia completata", "Le librerie corrotte sono state rimosse.")
            except Exception as e:
                self.log(f"Errore durante la pulizia: {e}", "ERROR")
                messagebox.showerror("Errore", f"Impossibile pulire le librerie:\n{e}")
                
    def update_modpack(self):
        """Scarica e aggiorna le mod del modpack"""
        try:
            Path(self.modpack_folder).mkdir(parents=True, exist_ok=True)
            manifest = self.get_modpack_manifest()
            
            if not manifest:
                self.update_status("Nessun manifest trovato, usando mod locali")
                return
                
            for i, mod in enumerate(manifest.get("mods", [])):
                mod_name = mod["name"]
                mod_url = mod["url"]
                expected_hash = mod.get("sha256", "")
                
                mod_path = os.path.join(self.modpack_folder, mod_name)
                
                needs_download = True
                if os.path.exists(mod_path) and expected_hash:
                    current_hash = self.calculate_sha256(mod_path)
                    if current_hash == expected_hash:
                        needs_download = False
                        
                if needs_download:
                    self.update_status(f"Scaricamento {mod_name}...")
                    self.download_file(mod_url, mod_path)
                    
                progress = ((i + 1) / len(manifest["mods"])) * 100
                self.update_progress(progress)
                
            self.clean_old_mods(manifest)
            
        except Exception as e:
            self.log(f"Errore aggiornamento modpack: {e}", "ERROR")
            
    def get_modpack_manifest(self):
        """Scarica il manifest del modpack dal server"""
        try:
            response = requests.get(self.modpack_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
            
        return {
            "mods": []
        }
        
    def download_file(self, url, destination):
        """Scarica un file da URL"""
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
    def calculate_sha256(self, file_path):
        """Calcola l'hash SHA256 di un file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    def clean_old_mods(self, manifest):
        """Rimuove mod non presenti nel manifest"""
        if not os.path.exists(self.modpack_folder):
            return
            
        manifest_mods = {mod["name"] for mod in manifest.get("mods", [])}
        
        for file in os.listdir(self.modpack_folder):
            if file.endswith(".jar") and file not in manifest_mods:
                file_path = os.path.join(self.modpack_folder, file)
                try:
                    os.remove(file_path)
                    self.log(f"Rimossa mod obsoleta: {file}")
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
                "gameDirectory": self.minecraft_directory  # IMPORTANTE: imposta la directory di gioco
            }
             
            # Trova la versione Forge installata
            versions = minecraft_launcher_lib.utils.get_installed_versions(
                self.minecraft_directory
            )
            
            self.log("Versioni installate:")
            for v in versions:
                self.log(f"  - {v['id']}")
            
            forge_version = None
            for version in versions:
                version_id = version["id"].lower()
                if ("forge" in version_id or "neoforge" in version_id):
                    # if self.minecraft_version in version["id"]:
                    if version_id == self.forge_version.replace("-","-forge-"):
                        forge_version = version["id"]
                        self.log(f"Trovata versione Forge: {forge_version}")
                        break
            
            if not forge_version:
                for version in versions:
                    version_id = version["id"].lower()
                    if "1.20" in version_id and ("forge" in version_id or "neoforge" in version_id):
                        forge_version = version["id"]
                        self.log(f"Trovata versione Forge/NeoForge alternativa: {forge_version}")
                        break
                        
            if not forge_version:
                available = [v["id"] for v in versions if "forge" in v["id"].lower() or "neoforge" in v["id"].lower()]
                error_msg = "Forge non installato!\n\n"
                if available:
                    error_msg += "Versioni Forge/NeoForge trovate:\n" + "\n".join(available)
                else:
                    error_msg += "Nessuna versione Forge/NeoForge trovata.\nProva a reinstallare cliccando 'Installa/Aggiorna'."
                messagebox.showerror("Errore", error_msg)
                return
                
            # Prepara il comando di lancio
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                forge_version,
                self.minecraft_directory,
                options
            )
            
            self.update_status("Avvio del gioco...")
            self.log(f"Comando di lancio: {' '.join(minecraft_command)}")
            self.log("=" * 50)
            self.log("Avvio di Minecraft...")
            self.log("=" * 50)
            
            # Avvia Minecraft con cattura dell'output
            self.game_process = subprocess.Popen(
                minecraft_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.minecraft_directory  # IMPORTANTE: esegui dalla directory .minecraft
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
                self.log("=" * 50)
                self.log("Minecraft chiuso")
                self.log("=" * 50)
                self.update_status("Gioco chiuso")
                
            monitor_thread = threading.Thread(target=monitor_game)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            self.update_status("Gioco in esecuzione...")
            
        except Exception as e:
            self.log(f"Errore durante l'avvio: {str(e)}", "ERROR")
            messagebox.showerror("Errore", f"Errore durante l'avvio:\n{str(e)}")
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    launcher = MinecraftLauncher()
    launcher.run()