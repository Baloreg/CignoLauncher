import os
import json
import hashlib
from pathlib import Path
import argparse
from datetime import datetime

class ManifestGenerator:
    def __init__(self, base_folder, base_url):
        """
        base_folder: Cartella principale contenente le sottocartelle del modpack
        base_url: URL base (es: https://raw.githubusercontent.com/Baloreg/Cignopack/main)
        """
        self.base_folder = Path(base_folder)
        self.base_url = base_url.rstrip('/')
        
        # File e cartelle da ignorare
        self.ignore_patterns = {
            '.git', '.gitignore', '.DS_Store', 'Thumbs.db',
            '__pycache__', '*.pyc', '*.pyo', '*.tmp', '*.bak',
            'manifest.json', '.gitkeep', 'desktop.ini'
        }
        
    def should_ignore(self, path):
        """Verifica se un file/cartella deve essere ignorato"""
        name = path.name
        
        # Ignora file nascosti (che iniziano con .)
        if name.startswith('.'):
            return True
        
        # Ignora file temporanei
        if name.endswith(('~', '.tmp', '.bak', '.swp')):
            return True
        
        # Ignora pattern specifici
        if name in self.ignore_patterns:
            return True
        
        return False
        
    def calculate_sha256(self, file_path):
        """Calcola l'hash SHA256 di un file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_file_size(self, file_path):
        """Ottiene la dimensione del file in bytes"""
        return os.path.getsize(file_path)
    
    def process_folder(self, folder_path, folder_name):
        """Processa ricorsivamente una cartella e ritorna la lista dei file"""
        if not folder_path.exists():
            print(f"⚠️  Cartella {folder_name}/ non trovata, skip...")
            return []
        
        files = []
        total_files = 0
        
        print(f"\n📁 Processando cartella: {folder_name}/")
        print("-" * 60)
        
        # Processa ricorsivamente tutti i file
        for root, dirs, filenames in os.walk(folder_path):
            # Rimuovi cartelle da ignorare
            dirs[:] = [d for d in dirs if not self.should_ignore(Path(root) / d)]
            
            for filename in sorted(filenames):
                file_path = Path(root) / filename
                
                # Ignora file da ignorare
                if self.should_ignore(file_path):
                    continue
                
                total_files += 1
                
                # Calcola il path relativo dalla cartella della categoria
                relative_path = file_path.relative_to(folder_path)
                path_str = str(relative_path).replace('\\', '/')  # Windows -> Unix path
                
                print(f"  [{total_files}] {path_str}")
                
                try:
                    # Calcola hash SHA256
                    sha256 = self.calculate_sha256(file_path)
                    
                    # Ottieni dimensione file
                    size = self.get_file_size(file_path)
                    
                    # Crea l'URL completo
                    url = f"{self.base_url}/{folder_name}/{path_str}"
                    
                    file_info = {
                        "name": filename,
                        "path": path_str,
                        "url": url,
                        "sha256": sha256,
                        "size": size
                    }
                    
                    files.append(file_info)
                    
                    print(f"      ✓ Hash: {sha256[:16]}...")
                    print(f"      ✓ Size: {size:,} bytes")
                    
                except Exception as e:
                    print(f"      ❌ Errore: {e}")
        
        if total_files == 0:
            print(f"  ℹ️  Nessun file trovato")
        else:
            print(f"\n  ✅ Totale: {len(files)} file processati")
        
        return files
    
    def get_all_folders(self):
        """Trova tutte le sottocartelle nella cartella base"""
        if not self.base_folder.exists():
            print(f"❌ Errore: La cartella {self.base_folder} non esiste!")
            return []
        
        folders = []
        for item in sorted(self.base_folder.iterdir()):
            if item.is_dir() and not self.should_ignore(item):
                folders.append(item.name)
        
        return folders
    
    def generate_manifest(self, minecraft_version="1.20.1", forge_version="1.20.1-47.3.0", modpack_name="Cignopack"):
        """Genera il manifest.json completo processando tutte le cartelle"""
        print("\n" + "=" * 60)
        print("🚀 GENERAZIONE MANIFEST AUTOMATICA")
        print("=" * 60)
        
        # Trova tutte le cartelle
        folders = self.get_all_folders()
        
        if not folders:
            print("❌ Nessuna cartella trovata!")
            return None
        
        print(f"\n📂 Cartelle trovate: {', '.join(folders)}")
        
        # Crea la struttura base del manifest
        manifest = {
            "version": "1.0.0",
            "minecraft_version": minecraft_version,
            "forge_version": forge_version,
            "modpack_name": modpack_name,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Processa ogni cartella trovata
        total_files = 0
        for folder_name in folders:
            folder_path = self.base_folder / folder_name
            files = self.process_folder(folder_path, folder_name)
            manifest[folder_name] = files
            total_files += len(files)
        
        print("\n" + "=" * 60)
        print(f"✅ Processamento completato: {total_files} file totali")
        print("=" * 60)
        
        return manifest
    
    def save_manifest(self, manifest, output_path="manifest.json"):
        """Salva il manifest in un file JSON"""
        if manifest is None:
            return False
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 60)
        print("💾 MANIFEST SALVATO")
        print("=" * 60)
        print(f"📄 File: {output_path}")
        print(f"📦 Modpack: {manifest['modpack_name']}")
        print(f"🎮 Minecraft: {manifest['minecraft_version']}")
        print(f"⚙️  Forge: {manifest['forge_version']}")
        print(f"📅 Aggiornato: {manifest['last_updated']}")
        print()
        
        # Mostra statistiche per categoria
        print("📊 Contenuto per categoria:")
        total_size = 0
        total_files = 0
        
        for key, value in manifest.items():
            # Salta i metadati
            if key in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated']:
                continue
            
            if isinstance(value, list):
                file_count = len(value)
                category_size = sum(item['size'] for item in value)
                total_size += category_size
                total_files += file_count
                
                print(f"  • {key}: {file_count} file ({category_size / (1024*1024):.2f} MB)")
        
        print(f"\n💾 Totale: {total_files} file - {total_size / (1024*1024):.2f} MB")
        print("=" * 60)
        
        return True
    
    def verify_manifest(self, manifest_path="manifest.json"):
        """Verifica che tutti i file nel manifest esistano fisicamente"""
        if not os.path.exists(manifest_path):
            print(f"❌ Errore: {manifest_path} non esiste!")
            return False
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        print("\n" + "=" * 60)
        print("🔍 VERIFICA INTEGRITÀ MANIFEST")
        print("=" * 60)
        
        all_valid = True
        total_files = 0
        valid_files = 0
        errors = []
        
        for key, value in manifest.items():
            # Salta i metadati
            if key in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated']:
                continue
            
            if not isinstance(value, list):
                continue
            
            if not value:  # Lista vuota
                continue
            
            print(f"\n📁 Verifica categoria: {key}")
            print("-" * 60)
            
            folder_path = self.base_folder / key
            
            for item in value:
                total_files += 1
                file_path = folder_path / item['path']
                
                if not file_path.exists():
                    print(f"  ❌ MANCANTE: {item['path']}")
                    errors.append(f"Mancante: {key}/{item['path']}")
                    all_valid = False
                else:
                    try:
                        current_hash = self.calculate_sha256(file_path)
                        if current_hash != item['sha256']:
                            print(f"  ⚠️  HASH DIVERSO: {item['path']}")
                            print(f"      Atteso:  {item['sha256'][:16]}...")
                            print(f"      Trovato: {current_hash[:16]}...")
                            errors.append(f"Hash diverso: {key}/{item['path']}")
                            all_valid = False
                        else:
                            print(f"  ✓ {item['path']}")
                            valid_files += 1
                    except Exception as e:
                        print(f"  ❌ ERRORE: {item['path']} - {e}")
                        errors.append(f"Errore lettura: {key}/{item['path']}")
                        all_valid = False
        
        print("\n" + "=" * 60)
        print("📊 RISULTATO VERIFICA")
        print("=" * 60)
        print(f"✓ File validi: {valid_files}/{total_files}")
        
        if all_valid:
            print("✅ Tutti i file sono validi!")
        else:
            print(f"❌ Trovati {len(errors)} problemi:")
            for error in errors[:10]:  # Mostra max 10 errori
                print(f"  • {error}")
            if len(errors) > 10:
                print(f"  ... e altri {len(errors) - 10} errori")
        
        print("=" * 60)
        
        return all_valid
    
    def compare_manifests(self, old_manifest_path, new_manifest_path="manifest.json"):
        """Confronta due manifest e mostra le differenze"""
        if not os.path.exists(old_manifest_path):
            print(f"❌ Errore: {old_manifest_path} non esiste!")
            return
        
        if not os.path.exists(new_manifest_path):
            print(f"❌ Errore: {new_manifest_path} non esiste!")
            return
        
        with open(old_manifest_path, 'r', encoding='utf-8') as f:
            old_manifest = json.load(f)
        
        with open(new_manifest_path, 'r', encoding='utf-8') as f:
            new_manifest = json.load(f)
        
        print("\n" + "=" * 60)
        print("🔄 CONFRONTO MANIFEST")
        print("=" * 60)
        
        for category in set(list(old_manifest.keys()) + list(new_manifest.keys())):
            if category in ['version', 'minecraft_version', 'forge_version', 'modpack_name', 'last_updated']:
                continue
            
            old_files = {f['path']: f for f in old_manifest.get(category, [])}
            new_files = {f['path']: f for f in new_manifest.get(category, [])}
            
            added = set(new_files.keys()) - set(old_files.keys())
            removed = set(old_files.keys()) - set(new_files.keys())
            modified = []
            
            for path in set(old_files.keys()) & set(new_files.keys()):
                if old_files[path]['sha256'] != new_files[path]['sha256']:
                    modified.append(path)
            
            if added or removed or modified:
                print(f"\n📁 {category}:")
                if added:
                    print(f"  ➕ Aggiunti: {len(added)}")
                    for f in list(added)[:5]:
                        print(f"     • {f}")
                    if len(added) > 5:
                        print(f"     ... e altri {len(added) - 5}")
                
                if removed:
                    print(f"  ➖ Rimossi: {len(removed)}")
                    for f in list(removed)[:5]:
                        print(f"     • {f}")
                    if len(removed) > 5:
                        print(f"     ... e altri {len(removed) - 5}")
                
                if modified:
                    print(f"  🔄 Modificati: {len(modified)}")
                    for f in modified[:5]:
                        print(f"     • {f}")
                    if len(modified) > 5:
                        print(f"     ... e altri {len(modified) - 5}")
        
        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Genera manifest.json automatico per modpack Minecraft',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:

  # Genera manifest da cartella (processa TUTTE le sottocartelle)
  python manifest_generator.py ./modpack https://raw.githubusercontent.com/user/repo/main

  # Specifica nome modpack e versioni
  python manifest_generator.py ./modpack https://... --name "MioModpack" --minecraft 1.20.1 --forge 1.20.1-47.3.0

  # Verifica manifest esistente
  python manifest_generator.py ./modpack https://... --verify

  # Confronta due manifest
  python manifest_generator.py ./modpack https://... --compare old_manifest.json

Lo script processerà AUTOMATICAMENTE tutte le sottocartelle trovate!
        """
    )
    
    parser.add_argument(
        'base_folder',
        help='Cartella principale contenente le sottocartelle del modpack'
    )
    parser.add_argument(
        'base_url',
        help='URL base di GitHub (es: https://raw.githubusercontent.com/user/repo/main)'
    )
    parser.add_argument(
        '--output',
        default='manifest.json',
        help='Nome del file manifest da generare (default: manifest.json)'
    )
    parser.add_argument(
        '--name',
        default='Cignopack',
        help='Nome del modpack (default: Cignopack)'
    )
    parser.add_argument(
        '--minecraft',
        default='1.20.1',
        help='Versione di Minecraft (default: 1.20.1)'
    )
    parser.add_argument(
        '--forge',
        default='1.20.1-47.3.0',
        help='Versione di Forge (default: 1.20.1-47.3.0)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verifica il manifest esistente'
    )
    parser.add_argument(
        '--compare',
        metavar='OLD_MANIFEST',
        help='Confronta con un manifest precedente'
    )
    
    args = parser.parse_args()
    
    generator = ManifestGenerator(args.base_folder, args.base_url)
    
    if args.verify:
        generator.verify_manifest(args.output)
    elif args.compare:
        generator.compare_manifests(args.compare, args.output)
    else:
        manifest = generator.generate_manifest(args.minecraft, args.forge, args.name)
        if manifest:
            generator.save_manifest(manifest, args.output)
            
            # Verifica automatica
            print("\n")
            generator.verify_manifest(args.output)


if __name__ == "__main__":
    if len(os.sys.argv) > 1:
        main()
    else:
        print("=" * 60)
        print("🚀 Generatore Manifest Automatico")
        print("=" * 60)
        print()
        
        # ⚙️ CONFIGURA QUI
        BASE_FOLDER = "./modpack"
        BASE_URL = "https://raw.githubusercontent.com/Baloreg/Cignopack/main"
        MODPACK_NAME = "Cignopack"
        MINECRAFT_VERSION = "1.20.1"
        FORGE_VERSION = "1.20.1-47.3.0"
        
        print(f"📁 Cartella: {BASE_FOLDER}")
        print(f"🌐 URL: {BASE_URL}")
        print(f"📦 Nome: {MODPACK_NAME}")
        print(f"🎮 Minecraft: {MINECRAFT_VERSION}")
        print(f"⚙️  Forge: {FORGE_VERSION}")
        
        generator = ManifestGenerator(BASE_FOLDER, BASE_URL)
        manifest = generator.generate_manifest(MINECRAFT_VERSION, FORGE_VERSION, MODPACK_NAME)
        
        if manifest:
            generator.save_manifest(manifest)
            print("\n")
            generator.verify_manifest()