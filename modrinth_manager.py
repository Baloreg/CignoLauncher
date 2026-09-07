import os
import requests
import json

MODRINTH_API_BASE = "https://api.modrinth.com/v2"
USER_AGENT = "CignoLauncher/1.0 (https://github.com/baloreg/CignoLauncher)"

class ModrinthManager:
    """Gestisce la ricerca e il download di Mod, Resource Pack e Shader da Modrinth API v2."""

    @staticmethod
    def get_headers():
        return {
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        }

    @classmethod
    def search(cls, query="", project_type="mod", minecraft_version=None, loader=None, category=None, sort_by="downloads", limit=20, offset=0):
        """
        Cerca progetti su Modrinth con supporto per categorie, ordinamento e paginazione.
        sort_by: 'downloads', 'relevance', 'newest', 'updated'
        category: es. 'optimization', 'utility', ecc.
        """
        facets = []

        # Tipo di progetto (mod, resourcepack, shader)
        if project_type:
            facets.append([f"project_type:{project_type}"])

        # Versione di Minecraft
        if minecraft_version:
            facets.append([f"versions:{minecraft_version}"])

        # Loader (solo per le mod)
        if loader and loader.lower() != "vanilla" and project_type == "mod":
            facets.append([f"loaders:{loader.lower()}"])

        # Categoria specifica (se selezionata)
        if category and category != "all":
            facets.append([f"categories:{category}"])

        params = {
            "query": query.strip(),
            "limit": limit,
            "offset": offset,
            "index": sort_by
        }

        if facets:
            params["facets"] = json.dumps(facets)

        try:
            res = requests.get(
                f"{MODRINTH_API_BASE}/search",
                params=params,
                headers=cls.get_headers(),
                timeout=10
            )
            res.raise_for_status()
            data = res.json()
            return {
                "hits": data.get("hits", []),
                "total_hits": data.get("total_hits", 0),
                "offset": data.get("offset", 0),
                "limit": data.get("limit", limit)
            }
        except Exception as e:
            print(f"[ModrinthManager] Errore durante la ricerca: {e}")
            return {"hits": [], "total_hits": 0, "offset": 0, "limit": limit, "error": str(e)}

    @classmethod
    def get_project_versions(cls, project_id, minecraft_version=None, loader=None):
        """Ottiene le versioni disponibili di un progetto su Modrinth."""
        params = {}
        if minecraft_version:
            params["game_versions"] = json.dumps([minecraft_version])
        if loader and loader.lower() != "vanilla":
            params["loaders"] = json.dumps([loader.lower()])

        try:
            res = requests.get(
                f"{MODRINTH_API_BASE}/project/{project_id}/version",
                params=params,
                headers=cls.get_headers(),
                timeout=10
            )
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[ModrinthManager] Errore recupero versioni progetto '{project_id}': {e}")
            return []

    @classmethod
    def get_primary_file_info(cls, project_id, minecraft_version=None, loader=None):
        """Trova il file primario della versione più compatibile per un dato progetto."""
        versions = cls.get_project_versions(project_id, minecraft_version, loader)
        if not versions:
            # Fallback senza filtri stretti
            versions = cls.get_project_versions(project_id)

        if not versions:
            return None

        # Prendi la versione più recente
        latest_version = versions[0]
        files = latest_version.get("files", [])
        if not files:
            return None

        # Cerca il file con 'primary': True, altrimenti il primo
        primary_file = next((f for f in files if f.get("primary")), files[0])

        return {
            "version_id": latest_version.get("id"),
            "version_number": latest_version.get("version_number"),
            "filename": primary_file.get("filename"),
            "url": primary_file.get("url"),
            "size": primary_file.get("size"),
            "hashes": primary_file.get("hashes", {})
        }

    @classmethod
    def download_file(cls, url, destination_path, progress_callback=None):
        """Scarica un file indirizzandolo verso la destinazione specificata."""
        try:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            res = requests.get(url, headers=cls.get_headers(), stream=True, timeout=30)
            res.raise_for_status()

            total_length = res.headers.get('content-length')
            downloaded = 0

            with open(destination_path, 'wb') as f:
                if total_length is None:
                    f.write(res.content)
                else:
                    total_length = int(total_length)
                    for chunk in res.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                pct = int((downloaded / total_length) * 100)
                                progress_callback(pct)
            return True
        except Exception as e:
            print(f"[ModrinthManager] Errore download file da {url}: {e}")
            return False
