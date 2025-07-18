"""
OpenShelf Base Repository
Classe base per tutti i repository di asset culturali
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json

class CulturalAsset:
    """Rappresentazione standardizzata di un asset culturale"""

    def __init__(self, data: Dict[str, Any], repository_name: str):
        self.repository = repository_name
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.object_type = data.get("object_type", "")
        self.materials = data.get("materials", [])
        self.chronology = data.get("chronology", [])
        self.inventory_number = data.get("inventory_number", "")
        self.provenance = data.get("provenance", "")
        self.tags = data.get("tags", [])
        self.model_urls = data.get("model_urls", [])
        self.thumbnail_url = data.get("thumbnail_url", "")
        self.license_info = data.get("license_info", "")
        self.metadata = data.get("metadata", {})

        # URLs di dettaglio
        self.detail_url = data.get("detail_url", "")
        self.catalog_url = data.get("catalog_url", "")

        # Informazioni qualitative
        self.quality_score = data.get("quality_score", 0)
        self.has_textures = data.get("has_textures", False)
        self.file_format = data.get("file_format", "obj")
        self.file_size = data.get("file_size", 0)

    def __str__(self):
        return f"{self.inventory_number} - {self.object_type} ({self.repository})"

    def get_display_name(self) -> str:
        """Restituisce nome per visualizzazione nell'UI"""
        if self.inventory_number:
            return f"[{self.inventory_number}] {self.name}"
        return self.name

    def get_short_description(self, max_length: int = 80) -> str:
        """Restituisce descrizione abbreviata"""
        if len(self.description) <= max_length:
            return self.description
        return self.description[:max_length-3] + "..."

    def get_search_text(self) -> str:
        """Restituisce testo completo per ricerca"""
        search_parts = [
            self.name,
            self.description,
            self.object_type,
            self.inventory_number,
            self.provenance,
            ' '.join(self.materials),
            ' '.join(self.chronology),
            ' '.join(self.tags)
        ]
        return ' '.join(filter(None, search_parts)).lower()

    def matches_filter(self, filter_dict: Dict[str, str]) -> bool:
        """Verifica se l'asset corrisponde ai filtri specificati"""
        search_text = self.get_search_text()

        for field, value in filter_dict.items():
            if not value or not value.strip():
                continue

            value_lower = value.lower().strip()

            if field == "search":
                if value_lower not in search_text:
                    return False

            elif field == "object_type":
                if value_lower not in self.object_type.lower():
                    return False

            elif field == "material":
                material_match = any(value_lower in mat.lower() for mat in self.materials)
                if not material_match:
                    return False

            elif field == "chronology":
                chronology_match = any(value_lower in chron.lower() for chron in self.chronology)
                if not chronology_match:
                    return False

            elif field == "inventory":
                if value_lower not in self.inventory_number.lower():
                    return False

            elif field == "provenance":
                if value_lower not in self.provenance.lower():
                    return False

        return True

    def has_3d_model(self) -> bool:
        """Verifica se l'asset ha modelli 3D disponibili"""
        return len(self.model_urls) > 0

    def get_model_info(self) -> Dict[str, Any]:
        """Restituisce informazioni sui modelli 3D disponibili"""
        return {
            "has_model": self.has_3d_model(),
            "model_count": len(self.model_urls),
            "model_urls": self.model_urls,
            "file_format": self.file_format,
            "file_size": self.file_size,
            "has_textures": self.has_textures
        }

    def to_dict(self) -> Dict[str, Any]:
        """Converte l'asset in dizionario per serializzazione"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "object_type": self.object_type,
            "materials": self.materials,
            "chronology": self.chronology,
            "inventory_number": self.inventory_number,
            "provenance": self.provenance,
            "tags": self.tags,
            "model_urls": self.model_urls,
            "thumbnail_url": self.thumbnail_url,
            "license_info": self.license_info,
            "metadata": self.metadata,
            "detail_url": self.detail_url,
            "catalog_url": self.catalog_url,
            "quality_score": self.quality_score,
            "has_textures": self.has_textures,
            "file_format": self.file_format,
            "file_size": self.file_size,
            "repository": self.repository
        }

class BaseRepository(ABC):
    """Classe base per tutti i repository di asset culturali"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.base_url = config.get("base_url", "")
        self.api_url = config.get("api_url", "")
        self.description = config.get("description", "")
        self.supported_formats = config.get("supported_formats", ["obj"])
        self.language = config.get("language", "en")
        self.license = config.get("default_license", "unknown")

        # Cache per i risultati
        self._cache = {}
        self._last_fetch_time = None
        self._cache_duration = 3600  # 1 ora

    def __str__(self):
        return f"{self.name} Repository ({self.description})"

    @abstractmethod
    def fetch_assets(self, limit: int = 100) -> List[CulturalAsset]:
        """Scarica e parsa gli asset dal repository"""
        pass

    @abstractmethod
    def parse_raw_data(self, raw_data: Dict[str, Any]) -> List[CulturalAsset]:
        """Converte i dati raw in oggetti CulturalAsset standardizzati"""
        pass

    def search_assets(self, query: str, filters: Dict[str, str] = None, limit: int = 100) -> List[CulturalAsset]:
        """
        Cerca asset nel repository con query e filtri

        Args:
            query: Testo di ricerca
            filters: Dizionario con filtri (object_type, material, chronology, etc.)
            limit: Numero massimo di risultati

        Returns:
            Lista di CulturalAsset che corrispondono ai criteri
        """
        if filters is None:
            filters = {}

        # Aggiungi la query ai filtri se fornita
        if query and query.strip():
            filters["search"] = query.strip()

        # Fetch tutti gli asset (con cache)
        all_assets = self.fetch_assets(limit * 2)  # Fetch più asset per compensare il filtering

        # Applica filtri
        filtered_assets = []
        for asset in all_assets:
            if asset.matches_filter(filters):
                filtered_assets.append(asset)

            # Limita i risultati
            if len(filtered_assets) >= limit:
                break

        return filtered_assets

    def get_asset_by_id(self, asset_id: str) -> Optional[CulturalAsset]:
        """Ottiene un asset specifico per ID"""
        all_assets = self.fetch_assets()
        for asset in all_assets:
            if asset.id == asset_id:
                return asset
        return None

    def get_download_info(self, asset: CulturalAsset) -> Dict[str, Any]:
        """Restituisce informazioni per il download dell'asset"""
        return {
            "urls": asset.model_urls,
            "formats": self.supported_formats,
            "filename": f"{asset.inventory_number}_{asset.name}".replace(" ", "_"),
            "has_textures": asset.has_textures,
            "file_size": asset.file_size,
            "license": asset.license_info or self.license
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Restituisce statistiche sul repository"""
        try:
            # Per repository che supportano il conteggio totale dall'API (come Ercolano)
            api_total = 0
            if hasattr(self, 'get_total_count_from_api'):
                api_total = self.get_total_count_from_api()

            # Fetch un campione per le statistiche dettagliate
            # Se abbiamo un totale dall'API molto grande, usa un campione
            if api_total > 500:
                sample_limit = 300  # Campione rappresentativo
            else:
                sample_limit = 10000  # Prendi tutto se il dataset è piccolo

            sample_assets = self.fetch_assets(limit=sample_limit)

            if not sample_assets:
                return {
                    "total_assets": api_total,
                    "error": "No assets found for statistics",
                    "repository_info": {
                        "name": self.name,
                        "description": self.description
                    }
                }

            # Calcola statistiche dal campione
            object_types = {}
            materials = {}
            chronologies = {}
            total_with_3d = 0
            total_with_textures = 0
            quality_scores = []
            file_sizes = []

            for asset in sample_assets:
                # Tipo oggetto
                obj_type = asset.object_type or "N/D"
                object_types[obj_type] = object_types.get(obj_type, 0) + 1

                # Materiali
                for material in asset.materials:
                    if material and material.strip():
                        materials[material] = materials.get(material, 0) + 1

                # Cronologie
                for chron in asset.chronology:
                    if chron and chron.strip():
                        chronologies[chron] = chronologies.get(chron, 0) + 1

                # Contatori
                if asset.has_3d_model():
                    total_with_3d += 1

                if asset.has_textures:
                    total_with_textures += 1

                if asset.quality_score > 0:
                    quality_scores.append(asset.quality_score)

                if asset.file_size > 0:
                    file_sizes.append(asset.file_size)

            # Calcola valori proiettati se necessario
            sample_size = len(sample_assets)
            total_assets = api_total if api_total > 0 else sample_size

            if api_total > sample_size:
                # Proietta i risultati sul totale
                projection_factor = api_total / sample_size
                projected_3d = int(total_with_3d * projection_factor)
                projected_textures = int(total_with_textures * projection_factor)
                is_projected = True
            else:
                projected_3d = total_with_3d
                projected_textures = total_with_textures
                is_projected = False

            # Statistiche aggregate
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            avg_file_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0

            # Top 10 per categoria
            top_object_types = dict(sorted(object_types.items(), key=lambda x: x[1], reverse=True)[:10])
            top_materials = dict(sorted(materials.items(), key=lambda x: x[1], reverse=True)[:10])
            top_chronologies = dict(sorted(chronologies.items(), key=lambda x: x[1], reverse=True)[:10])

            return {
                "total_assets": total_assets,
                "sample_size": sample_size,
                "assets_with_3d": projected_3d,
                "assets_with_textures": projected_textures,
                "object_types": top_object_types,
                "object_types_total": len(object_types),
                "materials": top_materials,
                "materials_total": len(materials),
                "chronologies": top_chronologies,
                "chronologies_total": len(chronologies),
                "avg_quality_score": int(avg_quality),
                "avg_file_size_kb": int(avg_file_size),
                "is_projected": is_projected,
                "projection_note": f"Statistics projected from {sample_size} sample to {total_assets} total" if is_projected else f"Complete analysis of {sample_size} assets",
                "supported_formats": self.supported_formats,
                "repository_info": {
                    "name": self.name,
                    "description": self.description,
                    "base_url": self.base_url,
                    "language": self.language,
                    "license": self.license
                }
            }

        except Exception as e:
            return {
                "error": str(e),
                "total_assets": 0,
                "repository_info": {
                    "name": getattr(self, 'name', 'Unknown'),
                    "description": getattr(self, 'description', 'Unknown')
                }
            }

    def validate_asset_data(self, asset_data: Dict[str, Any]) -> bool:
        """Valida i dati di un asset prima di creare l'oggetto CulturalAsset"""
        required_fields = ["id", "name"]
        return all(field in asset_data for field in required_fields)

    def clear_cache(self):
        """Pulisce la cache del repository"""
        self._cache.clear()
        self._last_fetch_time = None
