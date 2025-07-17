"""
OpenShelf Download Manager
Gestisce download, cache e estrazione file per gli asset culturali
"""

import os
import tempfile
import urllib.request
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Callable
import hashlib
import json
import time
import threading

class DownloadProgress:
    """Classe per tracciare il progresso del download"""
    
    def __init__(self, total_size: int = 0):
        self.total_size = total_size
        self.downloaded_size = 0
        self.progress_callback = None
        self.cancelled = False
        
    def set_callback(self, callback: Callable[[int, int], None]):
        """Imposta callback per aggiornamenti progresso"""
        self.progress_callback = callback
        
    def update(self, downloaded: int):
        """Aggiorna il progresso"""
        self.downloaded_size = downloaded
        if self.progress_callback and not self.cancelled:
            self.progress_callback(downloaded, self.total_size)
    
    def cancel(self):
        """Cancella il download"""
        self.cancelled = True
    
    def get_percentage(self) -> int:
        """Ottiene la percentuale di completamento"""
        if self.total_size == 0:
            return 0
        return min(100, int((self.downloaded_size / self.total_size) * 100))

class DownloadCache:
    """Cache per i file scaricati"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "openshelf_cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
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

# Istanza globale per riutilizzo
_global_download_manager = None

def get_download_manager() -> DownloadManager:
    """Ottiene l'istanza globale del download manager"""
    global _global_download_manager
    if _global_download_manager is None:
        _global_download_manager = DownloadManager()
    return _global_download_manager
