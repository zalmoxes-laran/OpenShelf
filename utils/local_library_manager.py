# utils/local_library_manager.py
"""
OpenShelf Local Library Manager
Gestisce la libreria locale di modelli 3D con metadati
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile
import zipfile
import uuid
import time

class LocalLibraryManager:
    """Gestisce la libreria locale di modelli 3D"""

    def __init__(self, library_path: Optional[str] = None):
        """
        Inizializza il gestore della libreria locale

        Args:
            library_path: Path alla directory della libreria locale
        """
        if library_path:
            self.library_path = Path(library_path)
        else:
            # Default: Documents/OpenShelf_Library
            self.library_path = Path.home() / "Documents" / "OpenShelf_Library"

        # Crea directory se non existe
        self.library_path.mkdir(parents=True, exist_ok=True)

        # Subdirectories
        self.models_dir = self.library_path / "models"
        self.temp_dir = self.library_path / "temp"

        self.models_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)

    def get_asset_directory(self, asset_id: str) -> Path:
        """Ottiene la directory per un asset specifico"""
        # Sanitizza l'asset_id per il filesystem
        safe_id = "".join(c for c in asset_id if c.isalnum() or c in "._-")
        return self.models_dir / f"asset_{safe_id}"

    def is_asset_downloaded(self, asset_id: str) -> bool:
        """Controlla se un asset è già presente nella libreria locale"""
        asset_dir = self.get_asset_directory(asset_id)
        metadata_file = asset_dir / "metadata.json"

        # Deve esistere sia la directory che il file metadata
        if not asset_dir.exists() or not metadata_file.exists():
            return False

        # Verifica che ci sia almeno un file 3D
        supported_extensions = ['.obj', '.gltf', '.glb']
        for ext in supported_extensions:
            if list(asset_dir.glob(f"*{ext}")):
                return True

        return False

    def get_asset_metadata(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Legge i metadati di un asset dalla libreria locale"""
        asset_dir = self.get_asset_directory(asset_id)
        metadata_file = asset_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"OpenShelf: Error reading metadata for {asset_id}: {e}")
            return None

    def save_asset_metadata(self, asset_id: str, metadata: Dict[str, Any]) -> bool:
        """Salva i metadati di un asset nella libreria locale"""
        asset_dir = self.get_asset_directory(asset_id)
        asset_dir.mkdir(parents=True, exist_ok=True)

        metadata_file = asset_dir / "metadata.json"

        try:
            # Aggiungi timestamp
            import time
            metadata['downloaded_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            metadata['library_version'] = "1.0"

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"OpenShelf: Error saving metadata for {asset_id}: {e}")
            return False

    def download_asset_to_library(self, asset_data, model_urls: List[str],
                                 progress_callback: Optional[callable] = None) -> Optional[str]:
        """
        Scarica un asset nella libreria locale

        Args:
            asset_data: Dati dell'asset
            model_urls: Lista di URL dei modelli
            progress_callback: Callback per il progresso

        Returns:
            Path al file del modello scaricato o None se errore
        """
        asset_id = asset_data.asset_id
        asset_dir = self.get_asset_directory(asset_id)

        # Se già scaricato, restituisci il path esistente
        if self.is_asset_downloaded(asset_id):
            print(f"OpenShelf: Asset {asset_id} already in library")
            return self._get_primary_model_file(asset_id)

        print(f"OpenShelf: Downloading asset {asset_id} to library...")

        # Crea directory temporanea per questo download
        temp_download_dir = self.temp_dir / f"download_{uuid.uuid4().hex[:8]}"
        temp_download_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Prova a scaricare da ogni URL
            downloaded_archive = None
            for i, url in enumerate(model_urls):
                if progress_callback:
                    progress_callback(f"Trying download {i+1}/{len(model_urls)}")

                downloaded_archive = self._download_file(url, temp_download_dir, progress_callback)
                if downloaded_archive:
                    break

            if not downloaded_archive:
                raise Exception("Failed to download from any URL")

            # Estrai l'archivio nella directory temporanea
            if progress_callback:
                progress_callback("Extracting archive...")

            extract_dir = temp_download_dir / "extracted"
            self._extract_archive(downloaded_archive, extract_dir)

            # Trova file 3D
            model_files = self._find_3d_files(extract_dir)
            if not model_files:
                raise Exception("No 3D files found in archive")

            # Crea directory asset finale
            asset_dir.mkdir(parents=True, exist_ok=True)

            # Copia tutti i file nella directory asset
            if progress_callback:
                progress_callback("Organizing files...")

            self._copy_asset_files(extract_dir, asset_dir)

            # Salva metadati
            metadata = {
                'asset_id': asset_data.asset_id,
                'name': asset_data.name,
                'description': asset_data.description,
                'repository': asset_data.repository,
                'object_type': asset_data.object_type,
                'inventory_number': asset_data.inventory_number,
                'materials': asset_data.materials.split(', ') if asset_data.materials else [],
                'chronology': asset_data.chronology.split(', ') if asset_data.chronology else [],
                'license_info': asset_data.license_info,
                'quality_score': asset_data.quality_score,
                'source_urls': model_urls,
                'files': [f.name for f in asset_dir.iterdir() if f.is_file()]
            }

            self.save_asset_metadata(asset_id, metadata)

            # Trova e restituisci il file modello principale
            primary_model = self._get_primary_model_file(asset_id)

            if progress_callback:
                progress_callback("Download complete!")

            print(f"OpenShelf: Asset {asset_id} downloaded to {asset_dir}")
            return primary_model

        except Exception as e:
            print(f"OpenShelf: Error downloading asset {asset_id}: {e}")
            return None
        finally:
            # Pulizia directory temporanea
            if temp_download_dir.exists():
                shutil.rmtree(temp_download_dir, ignore_errors=True)

    def _get_primary_model_file(self, asset_id: str) -> Optional[str]:
        """Trova il file modello principale per un asset"""
        asset_dir = self.get_asset_directory(asset_id)

        # Priorità: .obj, .gltf, .glb
        priority_extensions = ['.obj', '.gltf', '.glb']

        for ext in priority_extensions:
            files = list(asset_dir.glob(f"*{ext}"))
            if files:
                return str(files[0])  # Restituisce il primo trovato

        return None

    def _download_file(self, url: str, download_dir: Path,
                      progress_callback: Optional[callable] = None) -> Optional[Path]:
        """Scarica un file da URL"""
        try:
            import urllib.request

            filename = url.split('/')[-1]
            if not filename or '.' not in filename:
                filename = f"download_{uuid.uuid4().hex[:8]}.zip"

            local_path = download_dir / filename

            def report_progress(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    progress_callback(f"Downloading... {percent}%")

            urllib.request.urlretrieve(url, local_path, report_progress)
            return local_path

        except Exception as e:
            print(f"OpenShelf: Download error for {url}: {e}")
            return None

    def _extract_archive(self, archive_path: Path, extract_dir: Path):
        """Estrai un archivio ZIP"""
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    def _find_3d_files(self, directory: Path) -> List[Path]:
        """Trova tutti i file 3D in una directory"""
        supported_extensions = ['.obj', '.gltf', '.glb']
        found_files = []

        for ext in supported_extensions:
            found_files.extend(directory.rglob(f"*{ext}"))

        return found_files

    def _copy_asset_files(self, source_dir: Path, dest_dir: Path):
        """Copia tutti i file dell'asset nella directory finale"""
        for item in source_dir.rglob("*"):
            if item.is_file():
                # Mantieni struttura relativa
                relative_path = item.relative_to(source_dir)
                dest_file = dest_dir / relative_path

                # Crea directory padre se necessario
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(item, dest_file)

    def get_library_stats(self) -> Dict[str, Any]:
        """Ottiene statistiche della libreria locale"""
        try:
            asset_count = len([d for d in self.models_dir.iterdir() if d.is_dir()])

            total_size = 0
            for root, dirs, files in os.walk(self.models_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass

            return {
                "library_path": str(self.library_path),
                "asset_count": asset_count,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "exists": self.library_path.exists()
            }
        except Exception as e:
            return {
                "error": str(e),
                "library_path": str(self.library_path),
                "exists": False
            }

    def open_library_folder(self):
        """Apre la cartella della libreria nel file manager del sistema"""
        import subprocess
        import sys

        try:
            if sys.platform == "win32":
                os.startfile(self.library_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", self.library_path])
            else:  # Linux
                subprocess.run(["xdg-open", self.library_path])
        except Exception as e:
            print(f"OpenShelf: Cannot open library folder: {e}")

    def remove_asset(self, asset_id: str) -> bool:
        """Rimuove un asset dalla libreria locale"""
        asset_dir = self.get_asset_directory(asset_id)

        try:
            if asset_dir.exists():
                shutil.rmtree(asset_dir)
                print(f"OpenShelf: Removed asset {asset_id} from library")
                return True
            return False
        except Exception as e:
            print(f"OpenShelf: Error removing asset {asset_id}: {e}")
            return False

# Istanza globale
_global_library_manager = None

def get_library_manager() -> LocalLibraryManager:
    """Ottiene l'istanza globale del library manager"""
    global _global_library_manager

    # Ottieni path dalla preferenze se disponibile
    library_path = None
    try:
        import bpy
        for addon_name in bpy.context.preferences.addons.keys():
            if 'openshelf' in addon_name.lower():
                prefs = bpy.context.preferences.addons[addon_name].preferences
                if hasattr(prefs, 'local_library_path') and prefs.local_library_path.strip():
                    library_path = prefs.local_library_path.strip()
                    break
    except:
        pass

    # Crea o aggiorna manager se necessario
    if (_global_library_manager is None or
        (library_path and str(_global_library_manager.library_path) != library_path)):

        print(f"OpenShelf: Creating library manager with path: {library_path or 'default'}")
        _global_library_manager = LocalLibraryManager(library_path)

    return _global_library_manager
