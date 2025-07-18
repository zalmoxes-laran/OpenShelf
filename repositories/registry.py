"""
OpenShelf Repository Registry
Registry centralizzato per gestire tutti i repository di asset culturali
"""

from typing import Dict, List, Optional, Any
from .base_repository import BaseRepository
from .ercolano_repository import ErcolanoRepository

class RepositoryRegistry:
    """Registry centralizzato per gestire tutti i repository"""

    _repositories: Dict[str, BaseRepository] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """Inizializza il registry con i repository di default"""
        if cls._initialized:
            return

        print("OpenShelf: Initializing repository registry...")

        try:
            # Registra repository di default
            cls.register_repository(ErcolanoRepository())

            # In futuro: carica repository da file di configurazione
            # cls._load_from_config()

            cls._initialized = True
            print(f"OpenShelf: Registry initialized with {len(cls._repositories)} repositories")

        except Exception as e:
            print(f"OpenShelf: Error initializing registry: {e}")
            cls._initialized = False

    @classmethod
    def register_repository(cls, repository: BaseRepository):
        """Registra un nuovo repository"""
        try:
            cls._repositories[repository.name] = repository
            print(f"OpenShelf: Registered repository '{repository.name}'")
        except Exception as e:
            print(f"OpenShelf: Error registering repository: {e}")

    @classmethod
    def unregister_repository(cls, name: str):
        """Deregistra un repository"""
        if name in cls._repositories:
            del cls._repositories[name]
            print(f"OpenShelf: Unregistered repository '{name}'")

    @classmethod
    def get_repository(cls, name: str) -> Optional[BaseRepository]:
        """Ottiene un repository per nome (case-insensitive)"""
        cls.initialize()

        # Prima prova il nome esatto
        if name in cls._repositories:
            return cls._repositories[name]

        # Poi prova case-insensitive
        name_lower = name.lower()
        for repo_name, repo in cls._repositories.items():
            if repo_name.lower() == name_lower:
                return repo

        return None

    @classmethod
    def get_all_repositories(cls) -> List[BaseRepository]:
        """Ottiene tutti i repository registrati"""
        cls.initialize()
        return list(cls._repositories.values())

    @classmethod
    def get_available_repositories(cls) -> List[str]:
        """Ottiene i nomi dei repository disponibili"""
        cls.initialize()
        return list(cls._repositories.keys())

    @classmethod
    def search_all_repositories(cls, query: str, filters: Dict[str, str] = None, limit: int = 100) -> List[Any]:
        """Cerca in tutti i repository"""
        cls.initialize()

        if filters is None:
            filters = {}

        all_results = []

        for repo in cls._repositories.values():
            try:
                results = repo.search_assets(query, filters, limit)
                all_results.extend(results)
            except Exception as e:
                print(f"OpenShelf: Error searching in repository '{repo.name}': {e}")

        # Ordina per qualità e limita risultati
        all_results.sort(key=lambda x: x.quality_score, reverse=True)
        return all_results[:limit]

    @classmethod
    def get_repository_statistics(cls) -> Dict[str, Any]:
        """Ottiene statistiche su tutti i repository"""
        cls.initialize()

        stats = {
            "total_repositories": len(cls._repositories),
            "repositories": {}
        }

        for name, repo in cls._repositories.items():
            try:
                repo_stats = repo.get_statistics()
                stats["repositories"][name] = repo_stats
            except Exception as e:
                stats["repositories"][name] = {"error": str(e)}

        return stats

    @classmethod
    def refresh_repository(cls, name: str):
        """Aggiorna la cache di un repository specifico"""
        cls.initialize()

        repo = cls.get_repository(name)
        if repo:
            try:
                repo.clear_cache()
                print(f"OpenShelf: Refreshed repository '{repo.name}'")
            except Exception as e:
                print(f"OpenShelf: Error refreshing repository '{name}': {e}")
        else:
            print(f"OpenShelf: Repository '{name}' not found for refresh")

    @classmethod
    def refresh_all_repositories(cls):
        """Aggiorna la cache di tutti i repository"""
        cls.initialize()

        for name in cls._repositories:
            cls.refresh_repository(name)

    @classmethod
    def test_repository_connection(cls, name: str) -> Dict[str, Any]:
        """Testa la connessione a un repository (case-insensitive)"""
        cls.initialize()

        repo = cls.get_repository(name)
        if repo is None:
            available_names = list(cls._repositories.keys())
            return {
                "status": "error",
                "message": f"Repository '{name}' not found. Available: {available_names}"
            }

        try:
            # Tenta di fetch un numero limitato di asset
            test_assets = repo.fetch_assets(limit=1)

            if test_assets:
                return {
                    "status": "success",
                    "message": f"Successfully connected to '{repo.name}'",
                    "test_asset": test_assets[0].name
                }
            else:
                return {
                    "status": "warning",
                    "message": f"Connected to '{repo.name}' but no assets found"
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to connect to '{repo.name}': {str(e)}"
            }

    @classmethod
    def get_repository_info(cls, name: str) -> Dict[str, Any]:
        """Ottiene informazioni dettagliate su un repository (case-insensitive)"""
        cls.initialize()

        repo = cls.get_repository(name)
        if repo is None:
            available_names = list(cls._repositories.keys())
            return {
                "error": f"Repository '{name}' not found. Available: {available_names}"
            }

        return {
            "name": repo.name,
            "description": repo.description,
            "base_url": repo.base_url,
            "api_url": getattr(repo, 'api_url', ''),
            "supported_formats": repo.supported_formats,
            "language": repo.language,
            "license": repo.license,
            "config": repo.config
        }

    @classmethod
    def validate_repository_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Valida la configurazione di un repository"""
        required_fields = ["name", "description", "base_url"]
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            return {
                "valid": False,
                "errors": [f"Missing required field: {field}" for field in missing_fields]
            }

        return {"valid": True, "errors": []}

    @classmethod
    def cleanup(cls):
        """Pulisce il registry"""
        cls._repositories.clear()
        cls._initialized = False
        print("OpenShelf: Repository registry cleaned up")

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Ottiene lo status del registry"""
        cls.initialize()

        return {
            "initialized": cls._initialized,
            "repository_count": len(cls._repositories),
            "available_repositories": list(cls._repositories.keys())
        }

    @classmethod
    def _load_from_config(cls):
        """Carica repository da file di configurazione (futuro)"""
        # TODO: Implementare caricamento da file JSON di configurazione
        # per permettere agli utenti di aggiungere repository custom
        pass

    @classmethod
    def export_config(cls) -> Dict[str, Any]:
        """Esporta la configurazione attuale (futuro)"""
        cls.initialize()

        config = {
            "repositories": {}
        }

        for name, repo in cls._repositories.items():
            config["repositories"][name] = {
                "name": repo.name,
                "description": repo.description,
                "base_url": repo.base_url,
                "supported_formats": repo.supported_formats,
                "language": repo.language,
                "license": repo.license
            }

        return config
