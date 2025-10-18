import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import minecraft_launcher_lib
import webbrowser
import threading

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def set_dark_title_bar(window):
    if sys.platform != "win32": return
    try:
        import ctypes
        hwnd = window.winfo_id()
        ancestor_hwnd = ctypes.windll.user32.GetAncestor(hwnd, 2)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ancestor_hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception as e:
        print(f"Avviso: impossibile impostare la barra del titolo scura: {e}")

class CustomDialog:
    def __init__(self, parent, title, message, colors, dialog_type='info'):
        self.parent = parent
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.attributes('-alpha', 0.0)
        self.dialog.withdraw()
        
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

        self.dialog.update_idletasks()
        parent_x, parent_y = self.parent.winfo_x(), self.parent.winfo_y()
        parent_w, parent_h = self.parent.winfo_width(), self.parent.winfo_height()
        dialog_w, dialog_h = self.dialog.winfo_reqwidth(), self.dialog.winfo_reqheight()
        x = parent_x + (parent_w // 2) - (dialog_w // 2)
        y = parent_y + (parent_h // 2) - (dialog_h // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        set_dark_title_bar(self.dialog)
        
        self.dialog.deiconify()
        self.dialog.attributes('-alpha', 1.0)

    def _on_ok(self): self.dialog.destroy()
    def _on_yes(self): self.result = True; self.dialog.destroy()
    def _on_no(self): self.result = False; self.dialog.destroy()
        
    def show(self):
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.parent.wait_window(self.dialog)
        return self.result

class LoginDialog:
    def __init__(self, parent, account_manager, colors, icon_path=None, client_id=None, client_secret=None):
        self.parent = parent
        self.account_manager = account_manager
        self.colors = colors
        self.result = None
        self.client_id = client_id
        self.client_secret = client_secret
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.attributes('-alpha', 0.0)
        self.dialog.withdraw()
        
        self.dialog.title("Accedi a Minecraft")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=colors['bg'])

        if icon_path:
            try:
                self.dialog.iconbitmap(icon_path)
            except tk.TclError:
                print("Icona del dialogo non trovata o non valida.")

        self.setup_ui()
        self.center()
        self.dialog.after(50, lambda: set_dark_title_bar(self.dialog))

    def center(self):
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        parent_x, parent_y = self.parent.winfo_x(), self.parent.winfo_y()
        parent_width, parent_height = self.parent.winfo_width(), self.parent.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        self.dialog.deiconify()
        self.dialog.attributes('-alpha', 1.0)
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title = ttk.Label(main_frame, text="Accedi a Minecraft", font=('Segoe UI', 18, 'bold'), foreground=self.colors['accent'])
        title.pack(pady=(0, 20))
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        self.accounts_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.accounts_tab, text="Account salvati")
        self.setup_accounts_tab()

        self.microsoft_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.microsoft_tab, text="Accedi con Microsoft")
        self.setup_microsoft_tab()
        
        self.offline_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.offline_tab, text="Modalità Offline")
        self.setup_offline_tab()
        
        close_btn = ttk.Button(main_frame, text="Chiudi", command=self.dialog.destroy)
        close_btn.pack()

    def on_tab_changed(self, event):
        selected_tab_text = event.widget.tab(event.widget.select(), "text")
        if selected_tab_text == "Modalità Offline":
            self.dialog.after(10, lambda: self.offline_username.focus_set())
            
    def setup_accounts_tab(self):
        for widget in self.accounts_tab.winfo_children(): widget.destroy()
        accounts = self.account_manager.get_all_accounts()
        if not accounts:
            label = ttk.Label(self.accounts_tab, text="Nessun account salvato.", justify=tk.CENTER, foreground=self.colors['text_secondary'])
            label.pack(expand=True)
            return
        for account_id, account_data in accounts.items():
            account_frame = ttk.Frame(self.accounts_tab); account_frame.pack(fill=tk.X, pady=5)
            info_frame = ttk.Frame(account_frame); info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            icon = "🌐" if account_data["type"] == "microsoft" else "👤"
            name_label = ttk.Label(info_frame, text=f"{icon} {account_data['username']}", font=('Segoe UI', 11, 'bold')); name_label.pack(anchor=tk.W)
            type_label = ttk.Label(info_frame, text=f"Account {account_data['type'].capitalize()}", foreground=self.colors['text_secondary'], font=('Segoe UI', 9)); type_label.pack(anchor=tk.W)
            btn_frame = ttk.Frame(account_frame); btn_frame.pack(side=tk.RIGHT, padx=5)
            use_btn = ttk.Button(btn_frame, text="Usa", command=lambda aid=account_id: self.use_account(aid)); use_btn.pack(side=tk.LEFT, padx=2)
            remove_btn = ttk.Button(btn_frame, text="Rimuovi", command=lambda aid=account_id: self.remove_account(aid)); remove_btn.pack(side=tk.LEFT, padx=2)

    def setup_microsoft_tab(self):
        self.microsoft_tab.rowconfigure(0, weight=1)
        self.microsoft_tab.rowconfigure(1, weight=0)
        self.microsoft_tab.rowconfigure(2, weight=1)
        self.microsoft_tab.columnconfigure(0, weight=1)
        container = ttk.Frame(self.microsoft_tab)
        container.grid(row=1, column=0)
        
        desc = ttk.Label(container, text="Accedi con il tuo account Microsoft/Xbox per giocare online.", justify=tk.CENTER, foreground=self.colors['text_secondary'], wraplength=400)
        desc.pack(pady=(0, 20))

        self.ms_login_btn = ttk.Button(container, text="Accedi con Microsoft", command=self.microsoft_login)
        self.ms_login_btn.pack(pady=20)
        
        self.status_label = ttk.Label(container, text="", justify=tk.CENTER, foreground=self.colors['text_secondary'])
        self.status_label.pack()

    def microsoft_login(self):
        if not self.client_id or not self.client_secret:
            messagebox.showerror("Errore di configurazione", "Client ID o Client Secret non sono configurati nel launcher.", parent=self.dialog)
            return

        self.ms_login_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Segui le istruzioni nel browser...")
        
        threading.Thread(target=self.perform_login_thread, daemon=True).start()

    def perform_login_thread(self):
        try:
            redirect_url = "http://localhost:5000/callback"
            
            # Metodo SICURO con PKCE (raccomandato dalla documentazione)
            # La funzione restituisce una tupla: (login_url, state, code_verifier)
            login_url, state, code_verifier = minecraft_launcher_lib.microsoft_account.get_secure_login_data(
                self.client_id,
                redirect_url
            )
            
            # Apri il browser con l'URL di login
            webbrowser.open(login_url)
            
            # Aspetta che l'utente completi il login e ottieni l'URL di callback
            # La funzione get_auth_code_from_url si aspetta l'URL completo del callback
            from minecraft_launcher_lib.microsoft_account import get_auth_code_from_url
            from http.server import HTTPServer, BaseHTTPRequestHandler
            
            # Server HTTP temporaneo per catturare il callback
            auth_code = None
            callback_url = None
            
            class CallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    nonlocal auth_code, callback_url
                    callback_url = self.path
                    
                    # Verifica se l'URL contiene il codice
                    if "code=" in self.path:
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        success_html = '''
                        <html>
                        <body style="background: #1e1e1e; color: white; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
                            <div style="text-align: center;">
                                <h1>✅ Login completato!</h1>
                                <p>Puoi chiudere questa finestra e tornare al launcher.</p>
                            </div>
                        </body>
                        </html>
                        '''
                        self.wfile.write(success_html.encode())
                        
                        # Estrai il codice dall'URL
                        try:
                            auth_code = minecraft_launcher_lib.microsoft_account.parse_auth_code_url(
                                f"http://localhost:5000{self.path}",
                                state
                            )
                        except Exception as e:
                            print(f"Errore parsing URL: {e}")
                    else:
                        self.send_response(400)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    pass  # Silenzia i log del server
            
            # Avvia il server sulla porta 5000
            server = HTTPServer(('localhost', 5000), CallbackHandler)
            
            # Aspetta una singola richiesta (il callback)
            server.handle_request()
            
            if not auth_code:
                raise Exception("Nessun codice di autorizzazione ricevuto")
            
            # Completa il login con il codice ricevuto
            account_data = minecraft_launcher_lib.microsoft_account.complete_login(
                self.client_id,
                self.client_secret,
                redirect_url,
                auth_code,
                code_verifier
            )
            
            # Aggiungi l'account
            self.result = self.account_manager.add_microsoft_account(account_data)
            self.dialog.after(0, self.dialog.destroy)

        except Exception as e:
            self.dialog.after(0, lambda exc=e: self.show_error(f"Login fallito:\n{exc}"))
        finally:
            self.dialog.after(0, self.reset_ms_button)
            
    def show_error(self, message):
        messagebox.showerror("Errore di accesso", message, parent=self.dialog)

    def reset_ms_button(self):
        self.ms_login_btn.config(state=tk.NORMAL)
        self.status_label.config(text="")

    def setup_offline_tab(self):
        self.offline_tab.rowconfigure(0, weight=1)
        self.offline_tab.rowconfigure(1, weight=0)
        self.offline_tab.rowconfigure(2, weight=1)
        self.offline_tab.columnconfigure(0, weight=1)
        container = ttk.Frame(self.offline_tab)
        container.grid(row=1, column=0)
        desc = ttk.Label(container, text="Gioca inserendo un nome utente.", justify=tk.CENTER, foreground=self.colors['text_secondary'], wraplength=400)
        desc.pack(pady=(0, 20))
        input_frame = ttk.Frame(container)
        input_frame.pack(pady=10, fill=tk.X, padx=20)
        ttk.Label(input_frame, text="Username:", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 5))
        self.offline_username = ttk.Entry(input_frame, font=('Segoe UI', 11))
        self.offline_username.pack(fill=tk.X, expand=True)
        self.offline_username.insert(0, "Giocatore")
        self.offline_username.bind('<Return>', lambda e: self.offline_login())
        self.offline_username.bind("<FocusIn>", lambda e: self.offline_username.select_range(0, 'end'))
        login_btn = ttk.Button(container, text="Gioca Offline", command=self.offline_login)
        login_btn.pack(pady=20)
    
    def use_account(self, account_id):
        if self.account_manager.switch_account(account_id):
            self.result = self.account_manager.current_account
            self.dialog.destroy()
    
    def remove_account(self, account_id):
        dialog = CustomDialog(self.dialog, "Conferma", "Sei sicuro di voler rimuovere questo account?", self.colors, dialog_type='question')
        if dialog.show():
            if self.account_manager.remove_account(account_id):
                self.setup_accounts_tab()
    
    def offline_login(self):
        username = self.offline_username.get().strip()
        if not (3 <= len(username) <= 16):
            messagebox.showwarning("Attenzione", "L'username deve avere tra i 3 e i 16 caratteri.", parent=self.dialog)
            return
        try:
            self.result = self.account_manager.add_offline_account(username)
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile creare l'account:\n{e}", parent=self.dialog)
    
    def show(self):
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.after(50, self.notebook.focus_set)
        self.parent.wait_window(self.dialog)
        return self.result