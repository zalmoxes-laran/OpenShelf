"""
OpenShelf File Utils
Utilities per gestione file, validazione e operazioni filesystem
"""

import os
import shutil
import tempfile
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import mimetypes
import urllib.parse

class FileUtils:
    """Utility per operazioni su file"""
    
    @staticmethod
    def get_file_hash(filepath: str, hash_type: str = 'md5') -> str:
        """
        Calcola hash di un file
        
        Args:
            filepath: Path al file
            hash_type: Tipo di hash ('md5', 'sha1', 'sha256')
            
        Returns:
            Hash del file come stringa esadecimale
        """
        try:
            hash_obj = hashlib.new(hash_type)
            
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            print(f"OpenShelf: Error calculating hash for {filepath}: {e}")
            return ""
    
    @staticmethod
    def get_file_info(filepath: str) -> Dict[str, Any]:
        """
        Ottiene informazioni dettagliate su un file
        
        Args:
            filepath: Path al file
            
        Returns:
            Dizionario con informazioni sul file
        """
        try:
            if not os.path.exists(filepath):
                return {"exists": False, "error": "File does not exist"}
            
            stat = os.stat(filepath)
            path_obj = Path(filepath)
            
            # Informazioni base
            info = {
                "exists": True,
                "path": str(path_obj.absolute()),
                "name": path_obj.name,
                "stem": path_obj.stem,
                "suffix": path_obj.suffix,
                "size": stat.st_size,
                "size_human": FileUtils.format_file_size(stat.st_size),
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "is_file": path_obj.is_file(),
                "is_dir": path_obj.is_dir(),
                "is_symlink": path_obj.is_symlink(),
                "permissions": oct(stat.st_mode)[-3:]
            }
            
            # MIME type
            mime_type, encoding = mimetypes.guess_type(filepath)
            info["mime_type"] = mime_type
            info["encoding"] = encoding
            
            # Categoria file
            info["category"] = FileUtils.get_file_category(path_obj.suffix)
            
            # Hash del file (solo per file piccoli)
            if stat.st_size < 10 * 1024 * 1024:  # 10MB
                info["md5"] = FileUtils.get_file_hash(filepath, 'md5')
            
            return info
            
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Formatta dimensione file in formato human-readable
        
        Args:
            size_bytes: Dimensione in bytes
            
        Returns:
            Stringa formattata (es. "1.5 MB")
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"
    
    @staticmethod
    def get_file_category(extension: str) -> str:
        """
        Determina categoria di un file dall'estensione
        
        Args:
            extension: Estensione file (con o senza punto)
            
        Returns:
            Categoria del file
        """
        if not extension:
            return "unknown"
        
        ext = extension.lower()
        if ext.startswith('.'):
            ext = ext[1:]
        
        categories = {
            "3d_model": ["obj", "gltf", "glb", "fbx", "dae", "3ds", "blend", "max", "ma", "mb"],
            "texture": ["jpg", "jpeg", "png", "tga", "bmp", "tiff", "exr", "hdr"],
            "archive": ["zip", "rar", "7z", "tar", "gz", "bz2"],
            "document": ["pdf", "doc", "docx", "txt", "rtf", "odt"],
            "audio": ["mp3", "wav", "ogg", "flac", "aac"],
            "video": ["mp4", "avi", "mkv", "mov", "wmv", "flv"],
            "data": ["json", "xml", "csv", "yaml", "yml"],
            "code": ["py", "js", "html", "css", "cpp", "c", "java"]
        }
        
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        
        return "other"
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        Crea un nome file sicuro rimuovendo caratteri problematici
        
        Args:
            filename: Nome file originale
            
        Returns:
            Nome file sicuro
        """
        # Caratteri da rimuovere o sostituire
        unsafe_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
        
        safe_name = filename
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')
        
        # Rimuovi spazi multipli e all'inizio/fine
        safe_name = ' '.join(safe_name.split())
        
        # Limita lunghezza
        if len(safe_name) > 200:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:200-len(ext)] + ext
        
        return safe_name
    
    @staticmethod
    def create_temp_directory(prefix: str = "openshelf_") -> str:
        """
        Crea una directory temporanea
        
        Args:
            prefix: Prefisso per il nome directory
            
        Returns:
            Path alla directory temporanea
        """
        return tempfile.mkdtemp(prefix=prefix)
    
    @staticmethod
    def ensure_directory(directory: str) -> bool:
        """
        Assicura che una directory esista
        
        Args:
            directory: Path alla directory
            
        Returns:
            True se la directory esiste o è stata creata
        """
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"OpenShelf: Error creating directory {directory}: {e}")
            return False
    
    @staticmethod
    def copy_file(source: str, destination: str, overwrite: bool = False) -> bool:
        """
        Copia un file
        
        Args:
            source: File sorgente
            destination: File destinazione
            overwrite: Se sovrascrivere file esistente
            
        Returns:
            True se copia riuscita
        """
        try:
            if not os.path.exists(source):
                print(f"OpenShelf: Source file {source} does not exist")
                return False
            
            if os.path.exists(destination) and not overwrite:
                print(f"OpenShelf: Destination {destination} already exists")
                return False
            
            # Assicura che la directory destinazione esista
            dest_dir = os.path.dirname(destination)
            if dest_dir and not FileUtils.ensure_directory(dest_dir):
                return False
            
            shutil.copy2(source, destination)
            return True
            
        except Exception as e:
            print(f"OpenShelf: Error copying file: {e}")
            return False
    
    @staticmethod
    def move_file(source: str, destination: str, overwrite: bool = False) -> bool:
        """
        Sposta un file
        
        Args:
            source: File sorgente
            destination: File destinazione
            overwrite: Se sovrascrivere file esistente
            
        Returns:
            True se spostamento riuscito
        """
        try:
            if not os.path.exists(source):
                print(f"OpenShelf: Source file {source} does not exist")
                return False
            
            if os.path.exists(destination) and not overwrite:
                print(f"OpenShelf: Destination {destination} already exists")
                return False
            
            # Assicura che la directory destinazione esista
            dest_dir = os.path.dirname(destination)
            if dest_dir and not FileUtils.ensure_directory(dest_dir):
                return False
            
            shutil.move(source, destination)
            return True
            
        except Exception as e:
            print(f"OpenShelf: Error moving file: {e}")
            return False
    
    @staticmethod
    def delete_file(filepath: str, force: bool = False) -> bool:
        """
        Elimina un file
        
        Args:
            filepath: Path al file
            force: Forza eliminazione anche se read-only
            
        Returns:
            True se eliminazione riuscita
        """
        try:
            if not os.path.exists(filepath):
                return True  # File già non esistente
            
            if force:
                # Rimuovi attributo read-only se presente
                os.chmod(filepath, 0o666)
            
            os.remove(filepath)
            return True
            
        except Exception as e:
            print(f"OpenShelf: Error deleting file {filepath}: {e}")
            return False
    
    @staticmethod
    def delete_directory(directory: str, force: bool = False) -> bool:
        """
        Elimina una directory e tutto il contenuto
        
        Args:
            directory: Path alla directory
            force: Forza eliminazione
            
        Returns:
            True se eliminazione riuscita
        """
        try:
            if not os.path.exists(directory):
                return True  # Directory già non esistente
            
            if force:
                # Rimuovi attributi read-only da tutti i file
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        filepath = os.path.join(root, file)
                        os.chmod(filepath, 0o666)
            
            shutil.rmtree(directory)
            return True
            
        except Exception as e:
            print(f"OpenShelf: Error deleting directory {directory}: {e}")
            return False
    
    @staticmethod
    def find_files(directory: str, pattern: str = "*", recursive: bool = True) -> List[str]:
        """
        Trova file in una directory
        
        Args:
            directory: Directory di ricerca
            pattern: Pattern di ricerca (es. "*.obj")
            recursive: Se cercare ricorsivamente
            
        Returns:
            Lista di path ai file trovati
        """
        try:
            path_obj = Path(directory)
            
            if not path_obj.exists():
                return []
            
            if recursive:
                return [str(p) for p in path_obj.rglob(pattern) if p.is_file()]
            else:
                return [str(p) for p in path_obj.glob(pattern) if p.is_file()]
                
        except Exception as e:
            print(f"OpenShelf: Error finding files: {e}")
            return []
    
    @staticmethod
    def get_directory_size(directory: str) -> int:
        """
        Calcola dimensione totale di una directory
        
        Args:
            directory: Path alla directory
            
        Returns:
            Dimensione in bytes
        """
        try:
            total_size = 0
            for root, dirs, files in os.walk(directory):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            return total_size
            
        except Exception as e:
            print(f"OpenShelf: Error calculating directory size: {e}")
            return 0
    
    @staticmethod
    def cleanup_temp_files(max_age_hours: int = 24):
        """
        Pulisce file temporanei vecchi
        
        Args:
            max_age_hours: Età massima in ore
        """
        try:
            import time
            
            temp_dir = tempfile.gettempdir()
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.startswith("openshelf_"):
                        filepath = os.path.join(root, file)
                        try:
                            file_age = current_time - os.path.getmtime(filepath)
                            if file_age > max_age_seconds:
                                os.remove(filepath)
                        except:
                            continue
                            
                for dir in dirs:
                    if dir.startswith("openshelf_"):
                        dirpath = os.path.join(root, dir)
                        try:
                            dir_age = current_time - os.path.getmtime(dirpath)
                            if dir_age > max_age_seconds:
                                shutil.rmtree(dirpath)
                        except:
                            continue
                            
        except Exception as e:
            print(f"OpenShelf: Error cleaning temp files: {e}")

class URLUtils:
    """Utility per operazioni su URL"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Verifica se un URL è valido
        
        Args:
            url: URL da verificare
            
        Returns:
            True se URL valido
        """
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def get_filename_from_url(url: str) -> str:
        """
        Estrae nome file da URL
        
        Args:
            url: URL
            
        Returns:
            Nome file estratto
        """
        try:
            parsed = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed.path)
            
            if not filename:
                return "download"
            
            # Rimuovi parametri query
            filename = filename.split('?')[0]
            
            return filename
            
        except Exception as e:
            print(f"OpenShelf: Error extracting filename from URL: {e}")
            return "download"
    
    @staticmethod
    def encode_url_component(component: str) -> str:
        """
        Codifica un componente URL
        
        Args:
            component: Componente da codificare
            
        Returns:
            Componente codificato
        """
        return urllib.parse.quote(component, safe='')
    
    @staticmethod
    def decode_url_component(component: str) -> str:
        """
        Decodifica un componente URL
        
        Args:
            component: Componente da decodificare
            
        Returns:
            Componente decodificato
        """
        return urllib.parse.unquote(component)
    
    @staticmethod
    def build_url(base_url: str, path: str = "", params: Dict[str, str] = None) -> str:
        """
        Costruisce un URL completo
        
        Args:
            base_url: URL base
            path: Path da aggiungere
            params: Parametri query
            
        Returns:
            URL completo
        """
        try:
            # Rimuovi slash finale da base_url
            base_url = base_url.rstrip('/')
            
            # Assicurati che path inizi con slash
            if path and not path.startswith('/'):
                path = '/' + path
            
            url = base_url + path
            
            # Aggiungi parametri query
            if params:
                query_string = urllib.parse.urlencode(params)
                url += '?' + query_string
            
            return url
            
        except Exception as e:
            print(f"OpenShelf: Error building URL: {e}")
            return base_url

class PathUtils:
    """Utility per operazioni su path"""
    
    @staticmethod
    def get_relative_path(filepath: str, base_path: str) -> str:
        """
        Ottiene path relativo
        
        Args:
            filepath: Path completo
            base_path: Path base
            
        Returns:
            Path relativo
        """
        try:
            return os.path.relpath(filepath, base_path)
        except:
            return filepath
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalizza un path
        
        Args:
            path: Path da normalizzare
            
        Returns:
            Path normalizzato
        """
        try:
            return os.path.normpath(path)
        except:
            return path
    
    @staticmethod
    def join_paths(*paths) -> str:
        """
        Unisce path in modo sicuro
        
        Args:
            paths: Path da unire
            
        Returns:
            Path unito
        """
        try:
            return os.path.join(*paths)
        except:
            return ""
    
    @staticmethod
    def get_common_path(paths: List[str]) -> str:
        """
        Trova path comune a una lista di path
        
        Args:
            paths: Lista di path
            
        Returns:
            Path comune
        """
        try:
            if not paths:
                return ""
            
            return os.path.commonpath(paths)
            
        except:
            return ""
