import os
import json
import hashlib
from pathlib import Path
import argparse

class ManifestGenerator:
    def __init__(self, mods_folder, base_url):
        """
        mods_folder: Cartella contenente le mod (.jar)
        base_url: https://raw.githubusercontent.com/Baloreg/Cignopack/main/mods)
        """
        self.mods_folder = Path(mods_folder)
        self.base_url = base_url.rstrip('/')
        
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
    
    def generate_manifest(self):
        """Genera il manifest.json con tutte le mod nella cartella"""
        if not self.mods_folder.exists():
            print(f"Errore: La cartella {self.mods_folder} non esiste!")
            return None
        
        mods = []
        jar_files = sorted(self.mods_folder.glob("*.jar"))
        
        if not jar_files:
            print(f"Attenzione: Nessun file .jar trovato in {self.mods_folder}")
            return None
        
        print(f"Elaborazione di {len(jar_files)} mod...\n")
        
        for jar_file in jar_files:
            print(f"Processando: {jar_file.name}")
            
            # Calcola hash SHA256
            sha256 = self.calculate_sha256(jar_file)
            
            # Ottieni dimensione file
            size = self.get_file_size(jar_file)
            
            # Crea l'URL completo
            url = f"{self.base_url}/{jar_file.name}"
            
            mod_info = {
                "name": jar_file.name,
                "url": url,
                "sha256": sha256,
                "size": size
            }
            
            mods.append(mod_info)
            print(f"  ✓ Hash: {sha256[:16]}...")
            print(f"  ✓ Size: {size:,} bytes")
            print()
        
        manifest = {
            "version": "1.0.0",
            "minecraft_version": "1.21.1",
            "forge_version": "neoforge-1.21.1-21.1.72",
            "modpack_name": "Il Mio Modpack",
            "last_updated": "",
            "mods": mods
        }
        
        return manifest
    
    def save_manifest(self, manifest, output_path="manifest.json"):
        """Salva il manifest in un file JSON"""
        if manifest is None:
            return False
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Manifest generato con successo: {output_path}")
        print(f"   Totale mod: {len(manifest['mods'])}")
        
        total_size = sum(mod['size'] for mod in manifest['mods'])
        print(f"   Dimensione totale: {total_size / (1024*1024):.2f} MB")
        
        return True
    
    def verify_manifest(self, manifest_path="manifest.json"):
        """Verifica che tutte le mod nel manifest esistano fisicamente"""
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        print("\n🔍 Verifica manifest...")
        all_valid = True
        
        for mod in manifest['mods']:
            mod_path = self.mods_folder / mod['name']
            
            if not mod_path.exists():
                print(f"  ❌ MANCANTE: {mod['name']}")
                all_valid = False
            else:
                current_hash = self.calculate_sha256(mod_path)
                if current_hash != mod['sha256']:
                    print(f"  ⚠️  HASH DIVERSO: {mod['name']}")
                    all_valid = False
                else:
                    print(f"  ✓ {mod['name']}")
        
        if all_valid:
            print("\n✅ Tutti i file sono validi!")
        else:
            print("\n⚠️  Alcuni file hanno problemi!")
        
        return all_valid


def main():
    parser = argparse.ArgumentParser(
        description='Genera manifest.json per modpack Minecraft'
    )
    parser.add_argument(
        'mods_folder',
        help='Cartella contenente i file .jar delle mod'
    )
    parser.add_argument(
        'base_url',
        help='URL base di GitHub (es: https://raw.githubusercontent.com/user/repo/main/mods)'
    )
    parser.add_argument(
        '--output',
        default='manifest.json',
        help='Nome del file manifest da generare (default: manifest.json)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verifica il manifest esistente'
    )
    
    args = parser.parse_args()
    
    generator = ManifestGenerator(args.mods_folder, args.base_url)
    
    if args.verify:
        if not os.path.exists(args.output):
            print(f"Errore: {args.output} non esiste!")
            return
        generator.verify_manifest(args.output)
    else:
        manifest = generator.generate_manifest()
        if manifest:
            generator.save_manifest(manifest, args.output)


if __name__ == "__main__":
    # Esempio di uso diretto senza argomenti
    print("=== Generatore Manifest Modpack ===\n")
    
    # Configura qui i tuoi parametri
    MODS_FOLDER = "./mods"  # Cartella con le tue mod
    BASE_URL = "https://raw.githubusercontent.com/Baloreg/Cignopack/main/mods"
    
    # Se vuoi usare lo script da linea di comando, commenta le righe sotto
    # e usa: python manifest_generator.py ./mods https://raw.githubusercontent.com/...
    
    if len(os.sys.argv) > 1:
        # Usa argomenti da linea di comando
        main()
    else:
        # Uso diretto
        generator = ManifestGenerator(MODS_FOLDER, BASE_URL)
        manifest = generator.generate_manifest()
        
        if manifest:
            generator.save_manifest(manifest)
            
            # Opzionale: verifica il manifest appena creato
            print("\n" + "="*50)
            generator.verify_manifest()