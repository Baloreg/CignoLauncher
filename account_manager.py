import json
import os
import uuid
from pathlib import Path
import minecraft_launcher_lib
from datetime import datetime, timedelta

class AccountManager:
    """Gestisce gli account Minecraft (Microsoft e Offline)"""
    
    def __init__(self, launcher_directory):
        self.launcher_directory = launcher_directory
        self.accounts_file = os.path.join(launcher_directory, "accounts.json")
        self.accounts = self.load_accounts()
        self.current_account = None
        
        # Carica l'ultimo account usato
        if self.accounts:
            last_used = self.accounts.get("last_used")
            if last_used and last_used in self.accounts.get("profiles", {}):
                self.current_account = self.accounts["profiles"][last_used]
    
    def load_accounts(self):
        """Carica gli account salvati"""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"profiles": {}, "last_used": None}
    
    def save_accounts(self):
        """Salva gli account su file"""
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=2)
    
    def add_offline_account(self, username):
        """Aggiunge un account offline"""
        account_id = f"offline_{username}"
        
        account = {
            "type": "offline",
            "username": username,
            "uuid": str(uuid.uuid4()),
            "added_at": datetime.now().isoformat()
        }
        
        self.accounts["profiles"][account_id] = account
        self.accounts["last_used"] = account_id
        self.current_account = account
        self.save_accounts()
        
        return account
    
    def add_microsoft_account(self, auth_data):
        """Aggiunge un account Microsoft"""
        account_id = f"microsoft_{auth_data['name']}"
        
        account = {
            "type": "microsoft",
            "username": auth_data["name"],
            "uuid": auth_data["id"],
            "access_token": auth_data["access_token"],
            "refresh_token": auth_data.get("refresh_token"),
            "expires_at": (datetime.now() + timedelta(seconds=auth_data.get("expires_in", 3600))).isoformat(),
            "added_at": datetime.now().isoformat()
        }
        
        self.accounts["profiles"][account_id] = account
        self.accounts["last_used"] = account_id
        self.current_account = account
        self.save_accounts()
        
        return account
    
    def remove_account(self, account_id):
        """Rimuove un account"""
        if account_id in self.accounts["profiles"]:
            del self.accounts["profiles"][account_id]
            
            # Se era l'account corrente, resetta
            if self.accounts["last_used"] == account_id:
                self.accounts["last_used"] = None
                self.current_account = None
            
            self.save_accounts()
            return True
        return False
    
    def switch_account(self, account_id):
        """Cambia account attivo"""
        if account_id in self.accounts["profiles"]:
            self.current_account = self.accounts["profiles"][account_id]
            self.accounts["last_used"] = account_id
            self.save_accounts()
            return True
        return False
    
    def get_launch_options(self):
        """Ottiene le opzioni di lancio per l'account corrente"""
        if not self.current_account:
            # Account offline di default
            return {
                "username": "Giocatore",
                "uuid": str(uuid.uuid4()),
                "token": ""
            }
        
        if self.current_account["type"] == "offline":
            return {
                "username": self.current_account["username"],
                "uuid": self.current_account["uuid"],
                "token": ""
            }
        else:
            # Account Microsoft
            return {
                "username": self.current_account["username"],
                "uuid": self.current_account["uuid"],
                "token": self.current_account["access_token"]
            }
    
    def is_token_expired(self):
        """Controlla se il token Microsoft è scaduto"""
        if not self.current_account or self.current_account["type"] == "offline":
            return False
        
        expires_at = datetime.fromisoformat(self.current_account.get("expires_at", "1970-01-01T00:00:00"))
        # Aggiungiamo un margine di 5 minuti per sicurezza
        return datetime.now() >= (expires_at - timedelta(minutes=5))
    
    def refresh_microsoft_token(self):
        """Rinnova il token Microsoft (DEPRECATO - Logica spostata nel launcher principale)"""
        if not self.current_account or self.current_account["type"] != "microsoft":
            return False
        
        print("La logica di refresh è stata spostata nel launcher principale (cignolauncher.py).")
        return False
    
    def get_all_accounts(self):
        """Ritorna tutti gli account salvati"""
        return self.accounts["profiles"]
    
    def has_accounts(self):
        """Controlla se ci sono account salvati"""
        return len(self.accounts["profiles"]) > 0