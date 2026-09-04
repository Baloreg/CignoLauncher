import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timedelta

class AccountManager:
    """Gestisce gli account Minecraft (Microsoft e Offline)."""
    
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
            elif self.accounts.get("profiles"):
                # Se non c'è last_used ma ci sono profili, seleziona il primo
                first_id = next(iter(self.accounts["profiles"]))
                self.current_account = self.accounts["profiles"][first_id]
                self.accounts["last_used"] = first_id
    
    def load_accounts(self):
        """Carica gli account salvati da accounts.json"""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "profiles" in data:
                        return data
            except Exception as e:
                print(f"[AccountManager] Errore caricamento accounts.json: {e}")
        return {"profiles": {}, "last_used": None}
    
    def save_accounts(self):
        """Salva gli account su file con indentazione leggibile"""
        try:
            os.makedirs(os.path.dirname(self.accounts_file), exist_ok=True)
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, indent=2)
        except Exception as e:
            print(f"[AccountManager] Errore salvataggio accounts.json: {e}")
    
    def add_offline_account(self, username):
        """Aggiunge o aggiorna un account offline"""
        clean_name = username.strip()
        if not clean_name:
            raise ValueError("Il nome utente non può essere vuoto.")
            
        account_id = f"offline_{clean_name}"
        
        # Se esisteva già un UUID per questo username, conserviamolo
        existing = self.accounts["profiles"].get(account_id)
        player_uuid = existing["uuid"] if existing and "uuid" in existing else str(uuid.uuid4())
        
        account = {
            "type": "offline",
            "username": clean_name,
            "uuid": player_uuid,
            "added_at": datetime.now().isoformat()
        }
        
        self.accounts["profiles"][account_id] = account
        self.accounts["last_used"] = account_id
        self.current_account = account
        self.save_accounts()
        return account
    
    def add_microsoft_account(self, auth_data):
        """Aggiunge o aggiorna un account Microsoft autenticato"""
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
        """Rimuove un account salvato"""
        if account_id in self.accounts["profiles"]:
            del self.accounts["profiles"][account_id]
            
            if self.accounts["last_used"] == account_id:
                if self.accounts["profiles"]:
                    next_id = next(iter(self.accounts["profiles"]))
                    self.accounts["last_used"] = next_id
                    self.current_account = self.accounts["profiles"][next_id]
                else:
                    self.accounts["last_used"] = None
                    self.current_account = None
            
            self.save_accounts()
            return True
        return False
    
    def switch_account(self, account_id):
        """Cambia l'account attivo corrente"""
        if account_id in self.accounts["profiles"]:
            self.current_account = self.accounts["profiles"][account_id]
            self.accounts["last_used"] = account_id
            self.save_accounts()
            return True
        return False
    
    def get_launch_options(self):
        """Ritorna le opzioni di lancio per l'account corrente"""
        if not self.current_account:
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
            return {
                "username": self.current_account["username"],
                "uuid": self.current_account["uuid"],
                "token": self.current_account.get("access_token", "")
            }
    
    def is_token_expired(self):
        """Verifica se il token Microsoft è scaduto o in scadenza (margine 5 min)"""
        if not self.current_account or self.current_account.get("type") != "microsoft":
            return False
        
        try:
            expires_at = datetime.fromisoformat(self.current_account.get("expires_at", "1970-01-01T00:00:00"))
            return datetime.now() >= (expires_at - timedelta(minutes=5))
        except Exception:
            return True
    
    def get_all_accounts(self):
        """Ritorna tutti i profili salvati"""
        return self.accounts.get("profiles", {})
    
    def has_accounts(self):
        """Controlla se esiste almeno un profilo configurato"""
        return len(self.accounts.get("profiles", {})) > 0