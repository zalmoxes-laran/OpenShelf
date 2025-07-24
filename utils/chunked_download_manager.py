"""
OpenShelf Chunked Download Manager
Download manager per operazioni non-bloccanti con progress callback
"""

import os
import requests
import hashlib
import time
from pathlib import Path
from typing import Optional, Callable, Iterator, Tuple
import tempfile
import shutil

class ChunkedDownloadSession:
    """Sessione di download chunked per file singolo"""
    
    def __init__(self, url: str, destination_path: str, chunk_size: int = 64 * 1024):
        self.url = url
        self.destination_path = destination_path
        self.chunk_size = chunk_size
        self.response = None
        self.chunk_iterator = None
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.temp_path = None
        self.temp_file = None
        self.is_complete = False
        self.error_message = None
        self.start_time = time.time()
        
    def initialize(self) -> bool:
        """Inizializza la sessione di download"""
        try:
            # Crea directory di destinazione se non esiste
            os.makedirs(os.path.dirname(self.destination_path), exist_ok=True)
            
            # HEAD request per ottenere dimensione file
            head_response = requests.head(self.url, timeout=10, allow_redirects=True)
            if head_response.status_code == 200:
                self.total_bytes = int(head_response.headers.get('content-length', 0))
            
            # Inizia download stream
            self.response = requests.get(self.url, stream=True, timeout=30)
            self.response.raise_for_status()
            
            # Se HEAD non ha funzionato, prova content-length dalla response
            if self.total_bytes == 0:
                self.total_bytes = int(self.response.headers.get('content-length', 0))
            
            # Crea file temporaneo
            temp_dir = os.path.dirname(self.destination_path)
            self.temp_path = os.path.join(temp_dir, f".{os.path.basename(self.destination_path)}.tmp")
            self.temp_file = open(self.temp_path, 'wb')
            
            # Crea iterator per chunk
            self.chunk_iterator = self.response.iter_content(chunk_size=self.chunk_size)
            
            print(f"ChunkedDownload: Initialized download for {self.url}")
            print(f"  - Total size: {self.total_bytes} bytes ({self.total_bytes / (1024*1024):.1f} MB)")
            print(f"  - Chunk size: {self.chunk_size} bytes")
            
            return True
            
        except Exception as e:
            self.error_message = f"Failed to initialize download: {str(e)}"
            print(f"ChunkedDownload: {self.error_message}")
            self._cleanup()
            return False
    
    def download_next_chunk(self) -> Tuple[bool, float]:
        """
        Scarica il prossimo chunk
        Returns: (has_more_data, progress_percentage)
        """
        if self.is_complete or self.error_message:
            return False, 100.0 if self.is_complete else 0.0
            
        try:
            # Ottieni prossimo chunk
            chunk = next(self.chunk_iterator)
            
            if chunk:
                # Scrivi chunk su file
                self.temp_file.write(chunk)
                self.downloaded_bytes += len(chunk)
                
                # Calcola progress
                if self.total_bytes > 0:
                    progress = (self.downloaded_bytes / self.total_bytes) * 100
                else:
                    # Se non conosciamo la dimensione, usa una stima basata sul tempo
                    elapsed = time.time() - self.start_time
                    estimated_total = max(self.downloaded_bytes * 2, self.downloaded_bytes + (1024 * 1024))  # Stima conservativa
                    progress = min(95, (self.downloaded_bytes / estimated_total) * 100)
                
                return True, progress
            else:
                # Fine del file
                return self._finalize_download()
                
        except StopIteration:
            # Fine dell'iterator
            return self._finalize_download()
            
        except Exception as e:
            self.error_message = f"Download chunk error: {str(e)}"
            print(f"ChunkedDownload: {self.error_message}")
            self._cleanup()
            return False, 0.0
    
    def _finalize_download(self) -> Tuple[bool, float]:
        """Finalizza il download spostando il file temporaneo"""
        try:
            if self.temp_file:
                self.temp_file.close()
                self.temp_file = None
            
            # Sposta file temporaneo alla destinazione finale
            if os.path.exists(self.temp_path):
                shutil.move(self.temp_path, self.destination_path)
                self.is_complete = True
                
                elapsed = time.time() - self.start_time
                speed = self.downloaded_bytes / elapsed if elapsed > 0 else 0
                print(f"ChunkedDownload: Download completed successfully")
                print(f"  - Downloaded: {self.downloaded_bytes} bytes")
                print(f"  - Time: {elapsed:.1f}s")
                print(f"  - Speed: {speed / 1024:.1f} KB/s")
                
                return False, 100.0  # No more data, 100% complete
            else:
                self.error_message = "Temporary file disappeared"
                return False, 0.0
                
        except Exception as e:
            self.error_message = f"Failed to finalize download: {str(e)}"
            print(f"ChunkedDownload: {self.error_message}")
            self._cleanup()
            return False, 0.0
    
    def _cleanup(self):
        """Pulizia risorse"""
        try:
            if self.temp_file:
                self.temp_file.close()
                self.temp_file = None
            
            if self.temp_path and os.path.exists(self.temp_path):
                os.remove(self.temp_path)
                self.temp_path = None
                
            if self.response:
                self.response.close()
                self.response = None
                
        except Exception as e:
            print(f"ChunkedDownload: Cleanup error: {e}")
    
    def cancel(self):
        """Cancella il download"""
        self.error_message = "Download cancelled by user"
        self._cleanup()
    
    def get_status(self) -> dict:
        """Restituisce stato corrente del download"""
        return {
            'url': self.url,
            'downloaded_bytes': self.downloaded_bytes,
            'total_bytes': self.total_bytes,
            'is_complete': self.is_complete,
            'error_message': self.error_message,
            'progress_percentage': (self.downloaded_bytes / max(1, self.total_bytes)) * 100,
            'elapsed_time': time.time() - self.start_time
        }


class ChunkedDownloadManager:
    """Manager principale per download chunked non-bloccanti"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions = {}  # url -> ChunkedDownloadSession
        
    def start_chunked_download(self, url: str, progress_callback: Optional[Callable] = None, 
                             use_cache: bool = True) -> Optional[str]:
        """
        Inizia un download chunked
        Returns: session_id se successo, None se errore
        """
        try:
            # Genera nome file dalla URL
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"asset_{url_hash}.zip"  # Assumiamo ZIP per adesso
            destination_path = str(self.cache_dir / filename)
            
            # Controlla cache se richiesto
            if use_cache and os.path.exists(destination_path):
                print(f"ChunkedDownload: File già in cache: {destination_path}")
                return destination_path
            
            # Crea nuova sessione
            session = ChunkedDownloadSession(url, destination_path)
            
            if session.initialize():
                session_id = f"download_{int(time.time() * 1000)}"  # Timestamp in ms
                self.active_sessions[session_id] = {
                    'session': session,
                    'progress_callback': progress_callback,
                    'destination_path': destination_path
                }
                
                print(f"ChunkedDownload: Started session {session_id}")
                return session_id
            else:
                return None
                
        except Exception as e:
            print(f"ChunkedDownload: Failed to start download: {e}")
            return None
    
    def process_active_downloads(self) -> dict:
        """
        Processa tutti i download attivi per un ciclo
        Returns: dict con stato di tutti i download
        """
        results = {}
        completed_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            session = session_data['session']
            callback = session_data['progress_callback']
            
            # Processa prossimo chunk
            has_more, progress = session.download_next_chunk()
            
            # Chiama callback se presente
            if callback:
                try:
                    callback(session.downloaded_bytes, session.total_bytes)
                except Exception as e:
                    print(f"ChunkedDownload: Callback error: {e}")
            
            # Aggiorna risultati
            status = session.get_status()
            results[session_id] = {
                'progress': progress,
                'has_more': has_more,
                'status': status,
                'destination_path': session_data['destination_path']
            }
            
            # Segna completati per rimozione
            if not has_more or session.error_message:
                completed_sessions.append(session_id)
        
        # Rimuovi sessioni completate
        for session_id in completed_sessions:
            session_data = self.active_sessions.pop(session_id)
            session_data['session']._cleanup()
            
            if session_data['session'].is_complete:
                print(f"ChunkedDownload: Session {session_id} completed successfully")
            else:
                print(f"ChunkedDownload: Session {session_id} failed: {session_data['session'].error_message}")
        
        return results
    
    def cancel_download(self, session_id: str):
        """Cancella un download specifico"""
        if session_id in self.active_sessions:
            session_data = self.active_sessions.pop(session_id)
            session_data['session'].cancel()
            print(f"ChunkedDownload: Cancelled session {session_id}")
    
    def cancel_all_downloads(self):
        """Cancella tutti i download attivi"""
        for session_id in list(self.active_sessions.keys()):
            self.cancel_download(session_id)
    
    def get_active_download_count(self) -> int:
        """Restituisce numero di download attivi"""
        return len(self.active_sessions)
    
    def cleanup(self):
        """Pulizia completa"""
        self.cancel_all_downloads()


# Singleton per accesso globale
_chunked_download_manager = None

def get_chunked_download_manager(cache_dir: str = None) -> ChunkedDownloadManager:
    """Ottiene istanza singleton del manager"""
    global _chunked_download_manager
    
    if _chunked_download_manager is None:
        if cache_dir is None:
            import tempfile
            cache_dir = os.path.join(tempfile.gettempdir(), "openshelf_cache")
        
        _chunked_download_manager = ChunkedDownloadManager(cache_dir)
    
    return _chunked_download_manager