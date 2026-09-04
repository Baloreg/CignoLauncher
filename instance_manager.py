import os
import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path

class InstanceManager:
    """Gestisce le istanze isolate di Minecraft (mondi, configurazioni, RAM e versioni separate)."""
    
    def __init__(self, launcher_directory):
        self.launcher_directory = launcher_directory
        self.instances_folder = os.path.join(launcher_directory, "instances")
        self.instances_file = os.path.join(launcher_directory, "instances.json")
        
        os.makedirs(self.instances_folder, exist_ok=True)
        self.data = self.load_instances()
        self.ensure_default_instance()

    def load_instances(self):
        """Carica le istanze salvate da instances.json."""
        if os.path.exists(self.instances_file):
            try:
                with open(self.instances_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "instances" in data:
                        return data
            except Exception as e:
                print(f"[InstanceManager] Errore lettura instances.json: {e}")
        return {"instances": {}, "current_instance": None}

    def save_instances(self):
        """Salva lo stato delle istanze su instances.json."""
        try:
            with open(self.instances_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[InstanceManager] Errore salvataggio instances.json: {e}")

    def ensure_default_instance(self, default_version="1.21.4"):
        """Garantisce la presenza di almeno un'istanza predefinita."""
        if not self.data.get("instances"):
            self.create_instance(
                name="Vanilla Principale",
                version=default_version,
                ram_gb=4,
                set_as_current=True
            )
        elif not self.data.get("current_instance") or self.data["current_instance"] not in self.data["instances"]:
            first_id = next(iter(self.data["instances"]))
            self.data["current_instance"] = first_id
            self.save_instances()

    def get_instances(self):
        """Ritorna tutte le istanze registrate."""
        return self.data.get("instances", {})

    def get_current_instance(self):
        """Ritorna l'istanza attualmente attiva."""
        curr_id = self.data.get("current_instance")
        if curr_id and curr_id in self.data.get("instances", {}):
            return self.data["instances"][curr_id]
        instances = self.get_instances()
        if instances:
            first_id = next(iter(instances))
            self.data["current_instance"] = first_id
            self.save_instances()
            return instances[first_id]
        return None

    def set_current_instance(self, instance_id):
        """Imposta l'istanza attiva."""
        if instance_id in self.data.get("instances", {}):
            self.data["current_instance"] = instance_id
            self.save_instances()
            return True
        return False

    def create_instance(self, name, version, ram_gb=4, jvm_args="", set_as_current=True):
        """Crea una nuova istanza con directory dedicata."""
        clean_name = name.strip() or f"Minecraft {version}"
        instance_id = f"inst_{uuid.uuid4().hex[:8]}"
        instance_dir = os.path.join(self.instances_folder, instance_id)
        
        # Crea le cartelle isolate dell'istanza (per saves, screenshots, options)
        os.makedirs(instance_dir, exist_ok=True)
        os.makedirs(os.path.join(instance_dir, "saves"), exist_ok=True)
        os.makedirs(os.path.join(instance_dir, "screenshots"), exist_ok=True)

        instance = {
            "id": instance_id,
            "name": clean_name,
            "version": version,
            "ram_gb": int(ram_gb),
            "jvm_args": jvm_args.strip(),
            "created_at": datetime.now().isoformat(),
            "last_played": None,
            "path": instance_dir
        }

        self.data.setdefault("instances", {})[instance_id] = instance
        if set_as_current or not self.data.get("current_instance"):
            self.data["current_instance"] = instance_id
        
        self.save_instances()
        return instance

    def update_instance(self, instance_id, name=None, version=None, ram_gb=None, jvm_args=None):
        """Aggiorna le impostazioni di un'istanza esistente."""
        if instance_id not in self.data.get("instances", {}):
            return False
            
        inst = self.data["instances"][instance_id]
        if name is not None and name.strip():
            inst["name"] = name.strip()
        if version is not None and version.strip():
            inst["version"] = version.strip()
        if ram_gb is not None:
            inst["ram_gb"] = int(ram_gb)
        if jvm_args is not None:
            inst["jvm_args"] = jvm_args.strip()

        self.save_instances()
        return True

    def mark_played(self, instance_id):
        """Aggiorna il timestamp di ultimo avvio dell'istanza."""
        if instance_id in self.data.get("instances", {}):
            self.data["instances"][instance_id]["last_played"] = datetime.now().isoformat()
            self.save_instances()

    def delete_instance(self, instance_id, delete_files=True):
        """Elimina un'istanza e opzionalmente la sua cartella sul disco."""
        if instance_id not in self.data.get("instances", {}):
            return False

        inst_path = self.data["instances"][instance_id].get("path")
        del self.data["instances"][instance_id]

        if delete_files and inst_path and os.path.exists(inst_path):
            try:
                shutil.rmtree(inst_path, ignore_errors=True)
            except Exception as e:
                print(f"[InstanceManager] Errore cancellazione cartella istanza: {e}")

        # Se era l'istanza attiva, sposta su un'altra
        if self.data.get("current_instance") == instance_id:
            instances = self.data.get("instances", {})
            self.data["current_instance"] = next(iter(instances)) if instances else None

        self.save_instances()
        return True

    def get_instance_directory(self, instance_id):
        """Ritorna il percorso della cartella dell'istanza."""
        if instance_id in self.data.get("instances", {}):
            return self.data["instances"][instance_id].get("path", os.path.join(self.instances_folder, instance_id))
        return os.path.join(self.instances_folder, instance_id)
