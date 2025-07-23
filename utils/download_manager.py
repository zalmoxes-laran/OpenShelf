"""
OpenShelf Download Manager - COMPLETE FIXED VERSION
Gestisce download, cache e estrazione file per gli asset culturali
"""

import bpy # type: ignore
import os
import tempfile
import urllib.request
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any  # <-- FIX: Aggiunto Any
import hashlib
import json
import time
import threading
class DownloadProgress:
    """Classe migliorata per tracciare il progresso del download"""

    def __init__(self, total_size: int = 0):
        self.total_size = total_size
        self.downloaded_size = 0
        self.progress_callback = None
        self.cancelled = False

        # NUOVO: Tracking velocità e tempo
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.speed_samples = []  # Lista degli ultimi campioni di velocità
        self.max_speed_samples = 10  # Mantieni solo gli ultimi 10 campioni

    def set_callback(self, callback: Callable[[int, int], None]):
        """Imposta callback per aggiornamenti progresso"""
        self.progress_callback = callback

    def update(self, downloaded: int):
        """Aggiorna il progresso CON CALCOLO VELOCITÀ"""
        current_time = time.time()

        # Calcola velocità se non è il primo update
        if self.downloaded_size > 0:
            time_diff = current_time - self.last_update_time
            bytes_diff = downloaded - self.downloaded_size

            if time_diff > 0:
                current_speed = bytes_diff / time_diff
                self.speed_samples.append(current_speed)

                # Mantieni solo gli ultimi campioni
                if len(self.speed_samples) > self.max_speed_samples:
                    self.speed_samples.pop(0)

        self.downloaded_size = downloaded
        self.last_update_time = current_time

        if self.progress_callback and not self.cancelled:
            self.progress_callback(downloaded, self.total_size)

    def get_average_speed(self) -> float:
        """Ottiene velocità media basata sui campioni recenti"""
        if not self.speed_samples:
            elapsed = time.time() - self.start_time
            if elapsed > 0 and self.downloaded_size > 0:
                return self.downloaded_size / elapsed
            return 0

        return sum(self.speed_samples) / len(self.speed_samples)

    def get_eta_seconds(self) -> float:
        """Stima tempo rimanente in secondi"""
        if self.total_size <= 0 or self.downloaded_size >= self.total_size:
            return 0

        avg_speed = self.get_average_speed()
        if avg_speed <= 0:
            return 0

        remaining_bytes = self.total_size - self.downloaded_size
        return remaining_bytes / avg_speed

    def get_speed_text(self) -> str:
        """Ottiene testo velocità formattato"""
        speed = self.get_average_speed()

        if speed > 1024 * 1024:
            return f"{speed / (1024 * 1024):.1f} MB/s"
        elif speed > 1024:
            return f"{speed / 1024:.0f} KB/s"
        else:
            return f"{speed:.0f} B/s"

    def get_eta_text(self) -> str:
        """Ottiene testo ETA formattato"""
        eta = self.get_eta_seconds()

        if eta <= 0:
            return ""
        elif eta < 60:
            return f"{eta:.0f}s"
        elif eta < 3600:
            return f"{eta / 60:.1f}m"
        else:
            return f"{eta / 3600:.1f}h"

    def cancel(self):
        """Cancella il download"""
        self.cancelled = True

    def get_percentage(self) -> int:
        """Ottiene la percentuale di completamento"""
        if self.total_size == 0:
            return 0
        return min(100, int((self.downloaded_size / self.total_size) * 100))
class CacheStatistics:
    """Statistiche dettagliate della cache"""

    def __init__(self, cache: 'DownloadCache'):
        self.cache = cache

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Ottiene statistiche dettagliate della cache"""
        try:
            stats = {
                "basic": self._get_basic_stats(),
                "files": self._get_file_stats(),
                "usage": self._get_usage_stats(),
                "age": self._get_age_stats()
            }
            return stats
        except Exception as e:
            return {"error": str(e)}

    def _get_basic_stats(self) -> Dict[str, Any]:
        """Statistiche base"""
        return {
            "total_files": len(self.cache.index),
            "total_size": sum(info.get('size', 0) for info in self.cache.index.values()),
            "cache_dir": str(self.cache.cache_dir),
            "max_size": self.cache.max_cache_size
        }

    def _get_file_stats(self) -> Dict[str, Any]:
        """Statistiche per tipo di file"""
        file_types = {}
        total_by_type = {}

        for cache_info in self.cache.index.values():
            filename = cache_info.get('original_name', '')
            ext = os.path.splitext(filename)[1].lower()

            if not ext:
                ext = 'unknown'

            file_types[ext] = file_types.get(ext, 0) + 1
            total_by_type[ext] = total_by_type.get(ext, 0) + cache_info.get('size', 0)

        return {
            "by_extension": file_types,
            "size_by_extension": total_by_type
        }

    def _get_usage_stats(self) -> Dict[str, Any]:
        """Statistiche di utilizzo"""
        now = time.time()

        recently_accessed = 0  # < 1 giorno
        old_files = 0  # > 7 giorni
        never_accessed = 0

        for cache_info in self.cache.index.values():
            last_accessed = cache_info.get('last_accessed', 0)

            if last_accessed == 0:
                never_accessed += 1
            elif now - last_accessed < 86400:  # 1 giorno
                recently_accessed += 1
            elif now - last_accessed > 604800:  # 7 giorni
                old_files += 1

        return {
            "recently_accessed": recently_accessed,
            "old_files": old_files,
            "never_accessed": never_accessed
        }

    def _get_age_stats(self) -> Dict[str, Any]:
        """Statistiche età file"""
        now = time.time()
        ages = []

        for cache_info in self.cache.index.values():
            timestamp = cache_info.get('timestamp', now)
            age_days = (now - timestamp) / 86400
            ages.append(age_days)

        if ages:
            return {
                "oldest": max(ages),
                "newest": min(ages),
                "average": sum(ages) / len(ages)
            }

        return {"oldest": 0, "newest": 0, "average": 0}
class DownloadCache:
    """Cache per i file scaricati"""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "openshelf_cache")

        self.cache_dir = Path(cache_dir)

        # FIX: Crea directory e parents se non esistono, con gestione errori
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"OpenShelf: Using cache directory: {self.cache_dir}")
        except Exception as e:
            print(f"OpenShelf: Error creating cache directory {self.cache_dir}: {e}")
            # Fallback a directory temporanea
            fallback_dir = os.path.join(tempfile.gettempdir(), "openshelf_cache_fallback")
            self.cache_dir = Path(fallback_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"OpenShelf: Using fallback cache directory: {self.cache_dir}")

        self.index_file = self.cache_dir / "cache_index.json"
        self.max_cache_size = 1024 * 1024 * 500  # 500MB max cache
        self.load_index()

    def load_index(self):
        """Carica l'indice della cache"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.index = json.load(f)
            else:
                self.index = {}
        except Exception as e:
            print(f"OpenShelf: Error loading cache index: {e}")
            self.index = {}

    def save_index(self):
        """Salva l'indice della cache"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            print(f"OpenShelf: Error saving cache index: {e}")

    def get_cache_key(self, url: str) -> str:
        """Genera chiave cache per URL"""
        return hashlib.md5(url.encode()).hexdigest()

    def is_cached(self, url: str) -> bool:
        """Verifica se URL è in cache"""
        cache_key = self.get_cache_key(url)
        if cache_key not in self.index:
            return False

        cache_info = self.index[cache_key]
        cache_path = self.cache_dir / cache_info['filename']

        # Verifica che il file esista ancora
        if not cache_path.exists():
            del self.index[cache_key]
            self.save_index()
            return False

        # Verifica età del file (opzionale)
        max_age = 7 * 24 * 3600  # 7 giorni
        if time.time() - cache_info.get('timestamp', 0) > max_age:
            self.remove_from_cache(url)
            return False

        return True

    def get_cached_path(self, url: str) -> Optional[str]:
        """Ottiene il path del file in cache"""
        if not self.is_cached(url):
            return None

        cache_key = self.get_cache_key(url)
        cache_info = self.index[cache_key]
        cache_path = self.cache_dir / cache_info['filename']

        # Aggiorna timestamp di accesso
        cache_info['last_accessed'] = time.time()
        self.save_index()

        return str(cache_path)

    def add_to_cache(self, url: str, local_path: str) -> str:
        """Aggiunge file alla cache"""
        cache_key = self.get_cache_key(url)

        # Genera nome file unico
        original_name = os.path.basename(local_path)
        if not original_name:
            original_name = "download"

        filename = f"{cache_key}_{original_name}"
        cache_path = self.cache_dir / filename

        try:
            # Copia file in cache
            shutil.copy2(local_path, cache_path)

            # Aggiorna indice
            self.index[cache_key] = {
                'url': url,
                'filename': filename,
                'timestamp': time.time(),
                'last_accessed': time.time(),
                'size': cache_path.stat().st_size,
                'original_name': original_name
            }

            self.save_index()

            # Controlla dimensione cache
            self._cleanup_if_needed()

            return str(cache_path)

        except Exception as e:
            print(f"OpenShelf: Error adding to cache: {e}")
            return local_path

    def remove_from_cache(self, url: str):
        """Rimuove file dalla cache"""
        cache_key = self.get_cache_key(url)

        if cache_key in self.index:
            cache_info = self.index[cache_key]
            cache_path = self.cache_dir / cache_info['filename']

            try:
                if cache_path.exists():
                    cache_path.unlink()
                del self.index[cache_key]
                self.save_index()
            except Exception as e:
                print(f"OpenShelf: Error removing from cache: {e}")

    def clear_cache(self):
        """Pulisce tutta la cache"""
        try:
            for cache_info in self.index.values():
                cache_path = self.cache_dir / cache_info['filename']
                if cache_path.exists():
                    cache_path.unlink()

            self.index.clear()
            self.save_index()

        except Exception as e:
            print(f"OpenShelf: Error clearing cache: {e}")

    def get_cache_size(self) -> int:
        """Ottiene dimensione totale cache"""
        total_size = 0
        for cache_info in self.index.values():
            total_size += cache_info.get('size', 0)
        return total_size

    def _cleanup_if_needed(self):
        """Pulisce la cache se supera la dimensione massima"""
        if self.get_cache_size() > self.max_cache_size:
            # Ordina per ultimo accesso
            sorted_items = sorted(
                self.index.items(),
                key=lambda x: x[1].get('last_accessed', 0)
            )

            # Rimuovi i file più vecchi
            for cache_key, cache_info in sorted_items[:len(sorted_items)//2]:
                cache_path = self.cache_dir / cache_info['filename']
                try:
                    if cache_path.exists():
                        cache_path.unlink()
                    del self.index[cache_key]
                except Exception as e:
                    print(f"OpenShelf: Error during cleanup: {e}")

            self.save_index()
class DownloadManager:
    """Gestore centralizzato per i download"""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache = DownloadCache(cache_dir)
        self.temp_dir = None
        self.active_downloads = {}
        self.download_lock = threading.Lock()

    def get_file_size(self, url: str) -> int:
        """
        Ottiene la dimensione di un file senza scaricarlo (HEAD request)

        Args:
            url: URL del file

        Returns:
            Dimensione in bytes (0 se non determinabile)
        """
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'OpenShelf/1.0 (Blender Addon)',
                    'Accept': '*/*'
                }
            )
            req.get_method = lambda: 'HEAD'  # Forza HEAD request

            with urllib.request.urlopen(req, timeout=10) as response:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    return int(content_length)

            return 0

        except Exception as e:
            print(f"OpenShelf: Error getting file size for {url}: {e}")
            return 0

    def get_file_info_quick(self, url: str) -> Dict[str, Any]:
        """
        Ottiene informazioni rapide su un file (dimensione, tipo, etc.)

        Args:
            url: URL del file

        Returns:
            Dizionario con info del file
        """
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'OpenShelf/1.0 (Blender Addon)',
                    'Accept': '*/*'
                }
            )
            req.get_method = lambda: 'HEAD'

            with urllib.request.urlopen(req, timeout=10) as response:
                return {
                    "url": url,
                    "size_bytes": int(response.headers.get('Content-Length', 0)),
                    "size_human": self.format_file_size(int(response.headers.get('Content-Length', 0))),
                    "content_type": response.headers.get('Content-Type', 'unknown'),
                    "last_modified": response.headers.get('Last-Modified', ''),
                    "server": response.headers.get('Server', ''),
                    "available": True
                }

        except Exception as e:
            return {
                "url": url,
                "size_bytes": 0,
                "size_human": "Unknown",
                "content_type": "unknown",
                "available": False,
                "error": str(e)
            }

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Formatta dimensione file in formato human-readable"""
        if size_bytes == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB"]
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1

        return f"{size:.1f} {units[unit_index]}"

    def download_file(self, url: str, use_cache: bool = True,
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
        """
        Scarica un file da URL

        Args:
            url: URL del file da scaricare
            use_cache: Se usare la cache
            progress_callback: Callback per aggiornamenti progresso (downloaded, total)

        Returns:
            Path al file scaricato o None se errore
        """

        if hasattr(bpy.app, 'online_access') and not bpy.app.online_access:
            print("OpenShelf: Online access disabled in Blender preferences")
            return None

        # Controlla cache
        if use_cache and self.cache.is_cached(url):
            cached_path = self.cache.get_cached_path(url)
            if cached_path:
                print(f"OpenShelf: Using cached file for {url}")
                if progress_callback:
                    # Simula progresso istantaneo per file cached
                    file_size = os.path.getsize(cached_path)
                    progress_callback(file_size, file_size)
                return cached_path

        # Crea directory temporanea se necessario
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix="openshelf_")

        # Determina nome file
        try:
            filename = os.path.basename(url.split('?')[0])
            if not filename or '.' not in filename:
                filename = f"download_{int(time.time())}"

            local_path = os.path.join(self.temp_dir, filename)

            # Crea progress tracker
            progress = DownloadProgress()
            if progress_callback:
                progress.set_callback(progress_callback)

            # Scarica file con progress tracking
            success = self._download_with_progress(url, local_path, progress)

            if not success:
                return None

            # Aggiungi alla cache se richiesto
            if use_cache:
                cached_path = self.cache.add_to_cache(url, local_path)
                return cached_path

            return local_path

        except Exception as e:
            print(f"OpenShelf: Error downloading {url}: {e}")
            return None

    def _download_with_progress(self, url: str, local_path: str, progress: DownloadProgress) -> bool:
        """Scarica file con tracking del progresso"""
        try:
            # Crea richiesta
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'OpenShelf/1.0 (Blender Addon)',
                    'Accept': '*/*'
                }
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                # Ottieni dimensione totale
                total_size = int(response.headers.get('Content-Length', 0))
                progress.total_size = total_size

                # Scarica in chunks
                chunk_size = 8192
                downloaded = 0

                with open(local_path, 'wb') as f:
                    while True:
                        if progress.cancelled:
                            return False

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)
                        progress.update(downloaded)

                return True

        except Exception as e:
            print(f"OpenShelf: Download error: {e}")
            return False

    def extract_archive(self, archive_path: str, extract_to: Optional[str] = None,
                       progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
        """
        Estrae un archivio ZIP

        Args:
            archive_path: Path all'archivio ZIP
            extract_to: Directory di destinazione (opzionale)
            progress_callback: Callback per progresso estrazione

        Returns:
            Path alla directory estratta o None se errore
        """
        try:
            if extract_to is None:
                if self.temp_dir is None:
                    self.temp_dir = tempfile.mkdtemp(prefix="openshelf_")
                extract_to = os.path.join(self.temp_dir, "extracted")

            os.makedirs(extract_to, exist_ok=True)

            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                file_list = zip_ref.infolist()
                total_files = len(file_list)

                for i, file_info in enumerate(file_list):
                    zip_ref.extract(file_info, extract_to)

                    if progress_callback:
                        progress_callback(i + 1, total_files)

            return extract_to

        except Exception as e:
            print(f"OpenShelf: Error extracting {archive_path}: {e}")
            return None

    def find_files_by_extension(self, directory: str, extensions: List[str]) -> List[str]:
        """Trova file con estensioni specifiche in una directory"""
        found_files = []

        # Normalizza estensioni
        normalized_extensions = []
        for ext in extensions:
            ext = ext.lower()
            if not ext.startswith('.'):
                ext = '.' + ext
            normalized_extensions.append(ext)

        # Cerca file
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in normalized_extensions:
                    found_files.append(os.path.join(root, file))

        return found_files

    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """Ottiene informazioni su un file"""
        try:
            stat = os.stat(file_path)
            return {
                "path": file_path,
                "name": os.path.basename(file_path),
                "size": stat.st_size,
                "extension": os.path.splitext(file_path)[1].lower(),
                "modified": stat.st_mtime,
                "exists": True
            }
        except Exception as e:
            return {
                "path": file_path,
                "exists": False,
                "error": str(e)
            }

    def cleanup(self):
        """Pulisce i file temporanei"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                print("OpenShelf: Temporary files cleaned up")
            except Exception as e:
                print(f"OpenShelf: Error cleaning up temp files: {e}")

    def get_cache_statistics(self) -> Dict[str, any]:
        """Ottiene statistiche sulla cache"""
        return {
            "cache_size": self.cache.get_cache_size(),
            "file_count": len(self.cache.index),
            "cache_dir": str(self.cache.cache_dir),
            "max_cache_size": self.cache.max_cache_size
        }

    def clear_cache(self):
        """Pulisce la cache"""
        self.cache.clear_cache()

    def __del__(self):
        """Cleanup automatico"""
        self.cleanup()

    def get_detailed_cache_statistics(self) -> Dict[str, Any]:
        """Ottiene statistiche cache dettagliate - NUOVO"""
        cache_stats = CacheStatistics(self.cache)
        return cache_stats.get_detailed_stats()

    def get_cache_health_report(self) -> Dict[str, Any]:
        """Genera report salute cache - NUOVO"""
        try:
            stats = self.get_detailed_cache_statistics()
            basic = stats.get('basic', {})
            usage = stats.get('usage', {})

            total_files = basic.get('total_files', 0)
            total_size = basic.get('total_size', 0)
            max_size = basic.get('max_size', self.cache.max_cache_size)

            # Calcola "salute" della cache
            health_score = 100
            issues = []
            recommendations = []

            # Check utilizzo spazio
            if max_size > 0:
                usage_percent = (total_size / max_size) * 100
                if usage_percent > 90:
                    health_score -= 20
                    issues.append("Cache nearly full")
                    recommendations.append("Consider increasing cache size or clearing old files")
                elif usage_percent > 75:
                    health_score -= 10
                    issues.append("Cache usage high")

            # Check file vecchi
            old_files = usage.get('old_files', 0)
            if old_files > total_files * 0.5:
                health_score -= 15
                issues.append("Many old unused files")
                recommendations.append("Clear cache to remove old files")

            # Check file mai acceduti
            never_accessed = usage.get('never_accessed', 0)
            if never_accessed > total_files * 0.3:
                health_score -= 10
                issues.append("Many files never accessed")
                recommendations.append("Cache may contain unnecessary files")

            if not issues:
                recommendations.append("Cache is healthy!")

            return {
                "health_score": max(0, health_score),
                "total_files": total_files,
                "total_size_mb": total_size / (1024 * 1024),
                "usage_percent": (total_size / max_size * 100) if max_size > 0 else 0,
                "issues": issues,
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "error": f"Cannot generate health report: {str(e)}",
                "health_score": 0
            }

# Istanza globale per riutilizzo
_global_download_manager = None

def get_download_manager() -> DownloadManager:
    """Ottiene l'istanza globale del download manager CON SUPPORTO DIRECTORY PERSONALIZZATA"""
    global _global_download_manager

    # Ottieni directory cache dalle preferenze
    cache_dir = None
    try:
        import bpy
        # Cerca nelle preferenze addon
        for addon_name in bpy.context.preferences.addons.keys():
            if 'openshelf' in addon_name.lower():
                prefs = bpy.context.preferences.addons[addon_name].preferences
                if hasattr(prefs, 'custom_cache_directory') and prefs.custom_cache_directory.strip():
                    cache_dir = prefs.custom_cache_directory.strip()
                    break
    except:
        pass  # Fallback se non riesce a leggere preferenze

    # Se cache_dir è cambiata o manager non esiste, ricrea
    if (_global_download_manager is None or
        (cache_dir and str(_global_download_manager.cache.cache_dir) != cache_dir)):

        print(f"OpenShelf: Creating download manager with cache dir: {cache_dir or 'default'}")
        _global_download_manager = DownloadManager(cache_dir)

    return _global_download_manager
