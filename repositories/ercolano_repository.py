"""
OpenShelf Ercolano Repository
Repository per gli asset 3D del Museo Archeologico Virtuale di Ercolano
"""

import urllib.request
import json
import time
from typing import List, Dict, Any
from .base_repository import BaseRepository, CulturalAsset

class ErcolanoRepository(BaseRepository):
    """Repository per gli asset 3D di Ercolano"""
    
    def __init__(self):
        config = {
            "name": "Ercolano",
            "description": "Museo Archeologico Virtuale di Ercolano",
            "base_url": "https://mude.cultura.gov.it",
            "api_url": "https://mude.cultura.gov.it/searchInv/iv/json/lista",
            "supported_formats": ["obj"],
            "language": "it",
            "default_license": "Unknown (Public Institution)"
        }
        super().__init__("Ercolano", config)
        
        # URL completo per l'API di Ercolano
        self.json_url = (
            "https://mude.cultura.gov.it/searchInv/iv/json/lista"
            "?from=0&to=2125&ordering=nrInventario&orderingType=ASC&idNormativa=SIPA1"
        )
    
    def fetch_assets(self, limit: int = 100) -> List[CulturalAsset]:
        """Scarica gli asset da Ercolano"""
        
        # Controlla cache
        cache_key = f"ercolano_assets_{limit}"
        if (cache_key in self._cache and 
            self._last_fetch_time and 
            time.time() - self._last_fetch_time < self._cache_duration):
            print(f"OpenShelf: Using cached Ercolano data")
            return self._cache[cache_key]
        
        try:
            print(f"OpenShelf: Fetching assets from Ercolano...")
            
            # Configurazione richiesta
            req = urllib.request.Request(
                self.json_url,
                headers={
                    'User-Agent': 'OpenShelf/1.0 (Blender Addon)',
                    'Accept': 'application/json'
                }
            )
            
            # Esegui richiesta
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                raw_data = json.loads(response.read().decode('utf-8'))
            
            # Parsa i dati
            assets = self.parse_raw_data(raw_data)
            
            # Limita i risultati se richiesto
            if limit > 0:
                assets = assets[:limit]
            
            # Salva in cache
            self._cache[cache_key] = assets
            self._last_fetch_time = time.time()
            
            print(f"OpenShelf: Fetched {len(assets)} assets from Ercolano")
            return assets
            
        except urllib.error.URLError as e:
            print(f"OpenShelf: Network error fetching from Ercolano: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"OpenShelf: JSON decode error from Ercolano: {e}")
            return []
        except Exception as e:
            print(f"OpenShelf: Error fetching from Ercolano: {e}")
            return []
    
    def parse_raw_data(self, raw_data: Dict[str, Any]) -> List[CulturalAsset]:
        """Converte i dati di Ercolano in CulturalAsset standardizzati"""
        assets = []
        
        if 'jsonData' not in raw_data:
            print("OpenShelf: No 'jsonData' in Ercolano response")
            return assets
            
        json_data = raw_data['jsonData']
        
        if 'records' not in json_data:
            print("OpenShelf: No 'records' in Ercolano jsonData")
            return assets
        
        records = json_data['records']
        total_records = json_data.get('totRecord', len(records))
        
        print(f"OpenShelf: Processing {len(records)} records from Ercolano (total available: {total_records})")
        
        for i, record in enumerate(records):
            try:
                # Valida record
                if not self.validate_ercolano_record(record):
                    print(f"OpenShelf: Skipping invalid record {i}")
                    continue
                
                # Trasforma il formato Ercolano in formato standardizzato
                standardized_data = self.standardize_ercolano_record(record)
                
                # Crea asset
                asset = CulturalAsset(standardized_data, self.name)
                assets.append(asset)
                
            except Exception as e:
                print(f"OpenShelf: Error processing Ercolano record {i}: {e}")
                continue
        
        print(f"OpenShelf: Successfully processed {len(assets)} Ercolano assets")
        return assets
    
    def validate_ercolano_record(self, record: Dict[str, Any]) -> bool:
        """Valida un record di Ercolano"""
        required_fields = ["id", "nrInventario"]
        return all(field in record and record[field] for field in required_fields)
    
    def standardize_ercolano_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Converte un record Ercolano nel formato standardizzato"""
        
        # Estrai dati base
        asset_id = record.get("id", "")
        inventory_number = record.get("nrInventario", "")
        object_type = record.get("oggetto", "")
        description = record.get("descrizione", "")
        
        # Costruisci nome display
        if inventory_number and object_type:
            display_name = f"{inventory_number} - {object_type}"
        elif inventory_number:
            display_name = inventory_number
        elif object_type:
            display_name = object_type
        else:
            display_name = f"Asset {asset_id}"
        
        # Estrai materiali e cronologie
        materials = record.get("materiaTecnicas", [])
        if isinstance(materials, str):
            materials = [materials]
        
        chronology = record.get("cronologias", [])
        if isinstance(chronology, str):
            chronology = [chronology]
        
        # Estrai URLs modelli 3D
        model_urls = record.get("modelli3D_hr", [])
        if isinstance(model_urls, str):
            model_urls = [model_urls]
        
        # Determina qualità e informazioni file
        quality_score = self.calculate_quality_score(record)
        file_size = self.estimate_file_size(record)
        
        return {
            "id": asset_id,
            "name": display_name,
            "description": description,
            "object_type": object_type,
            "materials": materials,
            "chronology": chronology,
            "inventory_number": inventory_number,
            "provenance": record.get("provenienza", "N/D"),
            "tags": [record.get("nomeInventario", "Inventario Ercolano")],
            "model_urls": model_urls,
            "thumbnail_url": "",  # Ercolano non fornisce thumbnail
            "license_info": self.license,
            "metadata": {
                "source": "Ercolano",
                "inventory_name": record.get("nomeInventario", ""),
                "original_data": record
            },
            "detail_url": record.get("linkDettaglio", ""),
            "catalog_url": record.get("linkICCD", ""),
            "quality_score": quality_score,
            "has_textures": True,  # Assumiamo che i modelli abbiano texture
            "file_format": "obj",
            "file_size": file_size
        }
    
    def calculate_quality_score(self, record: Dict[str, Any]) -> int:
        """Calcola un punteggio di qualità per un record Ercolano"""
        score = 0
        
        # Punteggio base
        score += 20
        
        # Bonus per descrizione
        if record.get("descrizione"):
            score += 20
        
        # Bonus per materiali
        materials = record.get("materiaTecnicas", [])
        if materials:
            score += 15
        
        # Bonus per cronologia
        chronology = record.get("cronologias", [])
        if chronology:
            score += 15
        
        # Bonus per modelli 3D
        models = record.get("modelli3D_hr", [])
        if models:
            score += 20
        
        # Bonus per link dettaglio
        if record.get("linkDettaglio"):
            score += 5
        
        # Bonus per link ICCD
        if record.get("linkICCD"):
            score += 5
        
        return min(score, 100)
    
    def estimate_file_size(self, record: Dict[str, Any]) -> int:
        """Stima la dimensione del file per un record (in KB)"""
        # Stime basate sul tipo di oggetto
        object_type = record.get("oggetto", "").lower()
        
        size_estimates = {
            "anello": 500,     # Oggetti piccoli
            "moneta": 300,
            "gemma": 200,
            "vaso": 1500,      # Oggetti medi
            "coppa": 1000,
            "statua": 5000,    # Oggetti grandi
            "rilievo": 3000,
            "affresco": 2000
        }
        
        # Cerca corrispondenze parziali
        for obj_type, size in size_estimates.items():
            if obj_type in object_type:
                return size
        
        # Default per oggetti sconosciuti
        return 1000
    
    def get_asset_detail(self, asset_id: str) -> Dict[str, Any]:
        """Ottiene dettagli estesi per un asset specifico"""
        asset = self.get_asset_by_id(asset_id)
        if not asset:
            return {}
        
        # Se disponibile, usa l'URL di dettaglio per ottenere più informazioni
        if asset.detail_url:
            try:
                with urllib.request.urlopen(asset.detail_url, timeout=10) as response:
                    detail_data = json.loads(response.read().decode('utf-8'))
                    return detail_data
            except Exception as e:
                print(f"OpenShelf: Error fetching asset details: {e}")
        
        return asset.to_dict()
    
    def search_by_inventory_number(self, inventory_number: str) -> List[CulturalAsset]:
        """Cerca asset per numero di inventario"""
        return self.search_assets("", {"inventory": inventory_number})
    
    def search_by_object_type(self, object_type: str) -> List[CulturalAsset]:
        """Cerca asset per tipo di oggetto"""
        return self.search_assets("", {"object_type": object_type})
    
    def get_available_object_types(self) -> List[str]:
        """Ottiene la lista dei tipi di oggetto disponibili"""
        try:
            assets = self.fetch_assets()
            object_types = set()
            for asset in assets:
                if asset.object_type:
                    object_types.add(asset.object_type)
            return sorted(list(object_types))
        except Exception as e:
            print(f"OpenShelf: Error getting object types: {e}")
            return []
    
    def get_available_materials(self) -> List[str]:
        """Ottiene la lista dei materiali disponibili"""
        try:
            assets = self.fetch_assets()
            materials = set()
            for asset in assets:
                for material in asset.materials:
                    materials.add(material)
            return sorted(list(materials))
        except Exception as e:
            print(f"OpenShelf: Error getting materials: {e}")
            return []
    
    def get_available_chronologies(self) -> List[str]:
        """Ottiene la lista delle cronologie disponibili"""
        try:
            assets = self.fetch_assets()
            chronologies = set()
            for asset in assets:
                for chron in asset.chronology:
                    chronologies.add(chron)
            return sorted(list(chronologies))
        except Exception as e:
            print(f"OpenShelf: Error getting chronologies: {e}")
            return []
