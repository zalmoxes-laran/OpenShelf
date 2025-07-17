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
            "base_url": "https://opendata-ercolano.cultura.gov.it",
            "api_url": "https://opendata-ercolano.cultura.gov.it/dataset/55608c19-2406-419f-84db-fa3d0b9cd033/resource/64324e26-a659-4c96-8958-98dbc5ecd3a9/download/modelli_3d_hig_res.json",
            "supported_formats": ["obj"],
            "language": "it",
            "default_license": "Unknown (Public Institution)"
        }
        super().__init__("Ercolano", config)

        # URL aggiornato per il dataset JSON
        self.json_url = "https://opendata-ercolano.cultura.gov.it/dataset/55608c19-2406-419f-84db-fa3d0b9cd033/resource/64324e26-a659-4c96-8958-98dbc5ecd3a9/download/modelli_3d_hig_res.json"

        # URL alternativo della pagina dataset
        self.dataset_page_url = "https://opendata-ercolano.cultura.gov.it/dataset/modelli-3d-lr/resource/64324e26-a659-4c96-8958-98dbc5ecd3a9"

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
            print(f"OpenShelf: Using URL: {self.json_url}")

            # Configurazione richiesta
            req = urllib.request.Request(
                self.json_url,
                headers={
                    'User-Agent': 'OpenShelf/1.0 (Blender Addon)',
                    'Accept': 'application/json',
                    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
                }
            )

            # Esegui richiesta
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")

                content = response.read()
                print(f"OpenShelf: Downloaded {len(content)} bytes from Ercolano")

                raw_data = json.loads(content.decode('utf-8'))

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

        # Il nuovo formato potrebbe essere diverso, dobbiamo esplorare la struttura
        print(f"OpenShelf: Exploring JSON structure...")
        print(f"OpenShelf: JSON root keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")

        # Gestisci diversi formati possibili
        records = []

        if isinstance(raw_data, list):
            # Se è direttamente una lista di record
            records = raw_data
            print(f"OpenShelf: Found direct list with {len(records)} records")

        elif isinstance(raw_data, dict):
            # Se è un dizionario, cerca possibili chiavi per i record
            possible_keys = ['records', 'data', 'result', 'items', 'assets', 'objects']

            for key in possible_keys:
                if key in raw_data:
                    records = raw_data[key]
                    print(f"OpenShelf: Found records under key '{key}' with {len(records)} items")
                    break

            # Se non trova chiavi note, usa tutti i valori che sono liste
            if not records:
                for key, value in raw_data.items():
                    if isinstance(value, list) and len(value) > 0:
                        records = value
                        print(f"OpenShelf: Using list from key '{key}' with {len(records)} items")
                        break

        if not records:
            print("OpenShelf: No records found in JSON data")
            return assets

        # Esamina struttura del primo record per debug
        if records and len(records) > 0:
            sample_record = records[0]
            print(f"OpenShelf: Sample record keys: {list(sample_record.keys()) if isinstance(sample_record, dict) else 'Not a dict'}")

        # Processa ogni record
        for i, record in enumerate(records):
            try:
                # Valida record
                if not isinstance(record, dict):
                    print(f"OpenShelf: Skipping non-dict record {i}")
                    continue

                # Trasforma il formato di Ercolano in formato standardizzato
                standardized_data = self.standardize_ercolano_record(record)

                # Crea asset
                asset = CulturalAsset(standardized_data, self.name)
                assets.append(asset)

            except Exception as e:
                print(f"OpenShelf: Error processing Ercolano record {i}: {e}")
                continue

        print(f"OpenShelf: Successfully processed {len(assets)} Ercolano assets")
        return assets

    def standardize_ercolano_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Converte un record Ercolano nel formato standardizzato"""

        # Esplora possibili mappature per i campi
        # Il nuovo dataset potrebbe avere campi diversi

        # Prova a mappare campi comuni
        asset_id = str(record.get("id", record.get("ID", record.get("identifier", ""))))

        # Nome - prova diverse varianti
        name_fields = ["nome", "name", "title", "titolo", "denominazione", "oggetto"]
        name = ""
        for field in name_fields:
            if field in record and record[field]:
                name = str(record[field])
                break

        # Numero inventario
        inventory_fields = ["numero_inventario", "nrInventario", "inventario", "inventory_number", "inv_num"]
        inventory_number = ""
        for field in inventory_fields:
            if field in record and record[field]:
                inventory_number = str(record[field])
                break

        # Tipo oggetto
        type_fields = ["tipo", "type", "oggetto", "categoria", "category"]
        object_type = ""
        for field in type_fields:
            if field in record and record[field]:
                object_type = str(record[field])
                break

        # Descrizione
        desc_fields = ["descrizione", "description", "desc", "note"]
        description = ""
        for field in desc_fields:
            if field in record and record[field]:
                description = str(record[field])
                break

        # Materiali
        material_fields = ["materiale", "materiali", "material", "materials", "materiaTecnicas"]
        materials = []
        for field in material_fields:
            if field in record and record[field]:
                mat = record[field]
                if isinstance(mat, list):
                    materials = [str(m) for m in mat]
                else:
                    materials = [str(mat)]
                break

        # Cronologia
        chrono_fields = ["cronologia", "chronology", "periodo", "period", "datazione", "dating", "cronologias"]
        chronology = []
        for field in chrono_fields:
            if field in record and record[field]:
                chron = record[field]
                if isinstance(chron, list):
                    chronology = [str(c) for c in chron]
                else:
                    chronology = [str(chron)]
                break

        # URLs modelli 3D
        model_fields = ["modelli_3d", "model_3d", "model_url", "file_url", "download_url", "modelli3D_hr"]
        model_urls = []
        for field in model_fields:
            if field in record and record[field]:
                urls = record[field]
                if isinstance(urls, list):
                    model_urls = [str(url) for url in urls if url]
                else:
                    model_urls = [str(urls)]
                break

        # Provenienza
        prov_fields = ["provenienza", "provenance", "luogo", "location", "sito", "site"]
        provenance = ""
        for field in prov_fields:
            if field in record and record[field]:
                provenance = str(record[field])
                break

        # Costruisci nome display
        if inventory_number and object_type:
            display_name = f"{inventory_number} - {object_type}"
        elif inventory_number:
            display_name = inventory_number
        elif name:
            display_name = name
        elif object_type:
            display_name = object_type
        else:
            display_name = f"Asset {asset_id}"

        # Calcola qualità e informazioni file
        quality_score = self.calculate_quality_score_new(record, {
            'name': bool(name),
            'description': bool(description),
            'materials': bool(materials),
            'chronology': bool(chronology),
            'model_urls': bool(model_urls),
            'inventory_number': bool(inventory_number)
        })

        file_size = self.estimate_file_size_new(record)

        return {
            "id": asset_id,
            "name": display_name,
            "description": description,
            "object_type": object_type,
            "materials": materials,
            "chronology": chronology,
            "inventory_number": inventory_number,
            "provenance": provenance,
            "tags": ["Ercolano", "MAV"],
            "model_urls": model_urls,
            "thumbnail_url": "",  # Da implementare se disponibile
            "license_info": self.license,
            "metadata": {
                "source": "Ercolano OpenData",
                "original_data": record
            },
            "detail_url": self.dataset_page_url,
            "catalog_url": "",
            "quality_score": quality_score,
            "has_textures": True,  # Assumiamo che i modelli abbiano texture
            "file_format": "obj",
            "file_size": file_size
        }

    def calculate_quality_score_new(self, record: Dict[str, Any], parsed_fields: Dict[str, bool]) -> int:
        """Calcola un punteggio di qualità per un record Ercolano"""
        score = 0

        # Punteggio base
        score += 20

        # Bonus per campi parsati correttamente
        if parsed_fields.get('name'):
            score += 15
        if parsed_fields.get('description'):
            score += 20
        if parsed_fields.get('materials'):
            score += 15
        if parsed_fields.get('chronology'):
            score += 15
        if parsed_fields.get('model_urls'):
            score += 20
        if parsed_fields.get('inventory_number'):
            score += 10

        # Bonus per campi aggiuntivi nel record originale
        if len(record.keys()) > 5:
            score += 5

        return min(score, 100)

    def estimate_file_size_new(self, record: Dict[str, Any]) -> int:
        """Stima la dimensione del file per un record (in KB)"""
        # Se disponibile nel record, usa quello
        size_fields = ["file_size", "size", "dimensione", "weight"]
        for field in size_fields:
            if field in record and record[field]:
                try:
                    return int(record[field])
                except:
                    pass

        # Altrimenti usa stime basate sul tipo
        object_type = str(record.get("tipo", record.get("oggetto", ""))).lower()

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
