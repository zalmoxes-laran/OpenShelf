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

    def get_total_count_from_api(self) -> int:
        """Ottiene il numero totale di record dal JSON API"""
        try:
            req = urllib.request.Request(
                self.json_url,
                headers={
                    'User-Agent': 'OpenShelf/1.0 (Blender Addon)',
                    'Accept': 'application/json'
                }
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                raw_data = json.loads(content.decode('utf-8'))

            # Estrai totRecord dal JSON
            if isinstance(raw_data, dict) and "jsonData" in raw_data:
                json_data = raw_data["jsonData"]
                total_records = json_data.get("totRecord", 0)
                print(f"OpenShelf: Total records from API: {total_records}")
                return total_records

            return 0

        except Exception as e:
            print(f"OpenShelf: Error getting total count: {e}")
            return 0



    def fetch_assets(self, limit: int = 100) -> List[CulturalAsset]:
        """Scarica gli asset da Ercolano"""

        # Determina se stiamo fetchando per statistiche (limit alto) o per UI normale
        is_stats_fetch = limit > 1000
        cache_key = f"ercolano_assets_all" if is_stats_fetch else f"ercolano_assets_{limit}"

        # Controlla cache
        if (cache_key in self._cache and
            self._last_fetch_time and
            time.time() - self._last_fetch_time < self._cache_duration):
            print(f"OpenShelf: Using cached Ercolano data ({'all assets' if is_stats_fetch else f'{limit} assets'})")
            cached_assets = self._cache[cache_key]
            # Per richieste normali, limita comunque il risultato
            return cached_assets if is_stats_fetch else cached_assets[:limit]

        try:
            if is_stats_fetch:
                print(f"OpenShelf: Fetching ALL assets from Ercolano for statistics...")
            else:
                print(f"OpenShelf: Fetching {limit} assets from Ercolano...")

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

            # Parsa TUTTI i dati (senza limit qui)
            all_assets = self.parse_raw_data(raw_data)

            # Salva TUTTI gli asset in cache per statistiche
            self._cache["ercolano_assets_all"] = all_assets

            # Per richieste normali, salva anche la versione limitata
            if not is_stats_fetch:
                limited_assets = all_assets[:limit]
                self._cache[cache_key] = limited_assets

            self._last_fetch_time = time.time()

            # Restituisci risultato appropriato
            result_assets = all_assets if is_stats_fetch else all_assets[:limit]

            print(f"OpenShelf: Fetched {len(result_assets)} assets from Ercolano (total available: {len(all_assets)})")
            return result_assets

        except urllib.error.URLError as e:
            print(f"OpenShelf: Network error fetching from Ercolano: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"OpenShelf: JSON decode error from Ercolano: {e}")
            return []
        except Exception as e:
            print(f"OpenShelf: Error fetching from Ercolano: {e}")
            return []

    def get_total_assets_count(self) -> int:
        """Ottiene il numero totale di asset senza caricarli tutti"""
        try:
            # Se abbiamo la cache completa, usa quella
            if "ercolano_assets_all" in self._cache:
                return len(self._cache["ercolano_assets_all"])

            # Altrimenti, fai una richiesta per ottenere il count
            # (questo metodo è più veloce per ottenere solo il numero)
            req = urllib.request.Request(
                self.json_url,
                headers={
                    'User-Agent': 'OpenShelf/1.0 (Blender Addon)',
                    'Accept': 'application/json'
                }
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                raw_data = json.loads(content.decode('utf-8'))

            # Conta i record senza parserarli completamente
            records = []
            if isinstance(raw_data, list):
                records = raw_data
            elif isinstance(raw_data, dict):
                for key in ['records', 'data', 'result', 'items', 'assets', 'objects']:
                    if key in raw_data and isinstance(raw_data[key], list):
                        records = raw_data[key]
                        break

            return len(records)

        except Exception as e:
            print(f"OpenShelf: Error getting asset count: {e}")
            return 0


    def parse_raw_data(self, raw_data: Dict[str, Any]) -> List[CulturalAsset]:
        """Converte i dati di Ercolano in CulturalAsset standardizzati"""
        assets = []

        print(f"OpenShelf: Parsing Ercolano JSON structure...")

        # STRUTTURA CORRETTA dal JSON mostrato:
        # {
        #   "messageBean": {...},
        #   "jsonData": {
        #     "totRecord": 2124,
        #     "page": 0,
        #     "maxItemPage": 0,
        #     "idNormativa": "SIPA1",
        #     "records": [ ... array di record ... ]
        #   }
        # }

        records = []
        total_records = 0

        # Trova la struttura jsonData.records
        if isinstance(raw_data, dict) and "jsonData" in raw_data:
            json_data = raw_data["jsonData"]

            if isinstance(json_data, dict):
                # Ottieni informazioni totali
                total_records = json_data.get("totRecord", 0)
                print(f"OpenShelf: Total records available in Ercolano: {total_records}")

                # Ottieni array records
                if "records" in json_data and isinstance(json_data["records"], list):
                    records = json_data["records"]
                    print(f"OpenShelf: Found {len(records)} records in this response")
                else:
                    print("OpenShelf: No 'records' array found in jsonData")
            else:
                print("OpenShelf: jsonData is not a dictionary")
        else:
            print("OpenShelf: No 'jsonData' key found in response")
            print(f"OpenShelf: Available keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")
            return assets

        if not records:
            print("OpenShelf: No records found to process")
            return assets

        # Debug: mostra struttura del primo record
        if records and len(records) > 0:
            sample_record = records[0]
            print(f"OpenShelf: Sample record keys: {list(sample_record.keys()) if isinstance(sample_record, dict) else 'Not a dict'}")

            # Verifica presenza campi chiave
            key_fields = ["id", "nrInventario", "oggetto", "materiaTecnicas", "cronologias", "modelli3D_hr"]
            missing_fields = []
            for field in key_fields:
                if field not in sample_record:
                    missing_fields.append(field)

            if missing_fields:
                print(f"OpenShelf: Warning - Missing expected fields: {missing_fields}")
            else:
                print("OpenShelf: ✓ All expected fields found in sample record")

        # Processa ogni record
        processed_count = 0
        error_count = 0

        for i, record in enumerate(records):
            try:
                # Valida record
                if not isinstance(record, dict):
                    print(f"OpenShelf: Skipping non-dict record {i}")
                    error_count += 1
                    continue

                # Verifica campi minimi
                if not record.get("id"):
                    print(f"OpenShelf: Skipping record {i} - missing ID")
                    error_count += 1
                    continue

                # Trasforma il formato di Ercolano in formato standardizzato
                standardized_data = self.standardize_ercolano_record(record)

                # Crea asset
                asset = CulturalAsset(standardized_data, self.name)
                assets.append(asset)
                processed_count += 1

                # Debug per primi 3 record
                if i < 3:
                    print(f"OpenShelf: Record {i+1}: {asset.inventory_number} - {asset.object_type}")
                    print(f"  - Materials: {asset.materials}")
                    print(f"  - Model URLs: {len(asset.model_urls)} found")
                    if asset.model_urls:
                        print(f"    First URL: {asset.model_urls[0]}")

            except Exception as e:
                print(f"OpenShelf: Error processing Ercolano record {i}: {e}")
                error_count += 1
                continue

        print(f"OpenShelf: Processing complete:")
        print(f"  - Total available: {total_records}")
        print(f"  - Successfully processed: {processed_count}")
        print(f"  - Errors: {error_count}")
        print(f"  - Assets with 3D models: {len([a for a in assets if a.has_3d_model()])}")

        return assets

    def standardize_ercolano_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Converte un record Ercolano nel formato standardizzato"""

        # MAPPING CORRETTO basato sul JSON reale:
        # "id": "MU159644"
        # "nrInventario": "77445"
        # "oggetto": "anello/ digitale"
        # "materiaTecnicas": ["oro/ laminatura"]
        # "cronologias": ["sec. I d.C."]
        # "modelli3D_hr": ["http://opendata-ercolano.cultura.gov.it/pub/modelli_3d_hr/77445.zip"]

        asset_id = str(record.get("id", ""))

        # Numero inventario (CAMPO CORRETTO)
        inventory_number = str(record.get("nrInventario", ""))

        # Tipo oggetto (CAMPO CORRETTO)
        object_type = str(record.get("oggetto", ""))

        # Nome descrittivo
        name = record.get("descrizione", "")
        if not name and inventory_number and object_type:
            name = f"{inventory_number} - {object_type}"
        elif not name and inventory_number:
            name = inventory_number
        elif not name and object_type:
            name = object_type
        else:
            name = f"Asset {asset_id}"

        # Descrizione
        description = str(record.get("descrizione", ""))

        # Materiali (CAMPO CORRETTO)
        materials = []
        material_data = record.get("materiaTecnicas", [])
        if isinstance(material_data, list):
            materials = [str(m).strip() for m in material_data if m]
        elif isinstance(material_data, str):
            materials = [material_data.strip()] if material_data.strip() else []

        # Cronologia (CAMPO CORRETTO)
        chronology = []
        chronology_data = record.get("cronologias", [])
        if isinstance(chronology_data, list):
            chronology = [str(c).strip() for c in chronology_data if c]
        elif isinstance(chronology_data, str):
            chronology = [chronology_data.strip()] if chronology_data.strip() else []

        # URLs modelli 3D (CAMPO CORRETTO)
        model_urls = []
        model_data = record.get("modelli3D_hr", [])
        if isinstance(model_data, list):
            model_urls = [str(url).strip() for url in model_data if url and str(url).strip()]
        elif isinstance(model_data, str) and model_data.strip():
            model_urls = [model_data.strip()]

        # Provenienza
        provenance = str(record.get("provenienza", "N/D"))

        # Nome inventario
        nome_inventario = str(record.get("nomeInventario", ""))

        # Link dettaglio e ICCD
        detail_url = str(record.get("linkDettaglio", ""))
        catalog_url = str(record.get("linkICCD", ""))

        # Calcola qualità basata sui dati reali
        quality_score = self.calculate_quality_score_updated(record, {
            'name': bool(name),
            'description': bool(description),
            'materials': bool(materials),
            'chronology': bool(chronology),
            'model_urls': bool(model_urls),
            'inventory_number': bool(inventory_number),
            'detail_url': bool(detail_url)
        })

        # Stima dimensione file dai modelli
        file_size = self.estimate_file_size_from_urls(model_urls)

        return {
            "id": asset_id,
            "name": name,
            "description": description,
            "object_type": object_type,
            "materials": materials,
            "chronology": chronology,
            "inventory_number": inventory_number,
            "provenance": provenance,
            "tags": ["Ercolano", "MAV", nome_inventario] if nome_inventario else ["Ercolano", "MAV"],
            "model_urls": model_urls,
            "thumbnail_url": "",  # Non disponibile nel JSON
            "license_info": self.license,
            "metadata": {
                "source": "Ercolano OpenData",
                "nome_inventario": nome_inventario,
                "detail_url": detail_url,
                "catalog_url": catalog_url,
                "original_data": record
            },
            "detail_url": detail_url,
            "catalog_url": catalog_url,
            "quality_score": quality_score,
            "has_textures": True,  # Assumiamo che i modelli abbiano texture
            "file_format": "zip",  # I modelli sono in ZIP
            "file_size": file_size
        }

    def calculate_quality_score_updated(self, record: Dict[str, Any], parsed_fields: Dict[str, bool]) -> int:
        """Calcola punteggio qualità aggiornato"""
        score = 20  # Base score

        # Bonus per campi essenziali
        if parsed_fields.get('inventory_number'):
            score += 15
        if parsed_fields.get('name'):
            score += 10
        if parsed_fields.get('description') and len(record.get("descrizione", "")) > 20:
            score += 20
        if parsed_fields.get('materials'):
            score += 15
        if parsed_fields.get('chronology'):
            score += 10
        if parsed_fields.get('model_urls'):
            score += 20  # Molto importante
        if parsed_fields.get('detail_url'):
            score += 5

        # Bonus per completezza descrizione
        description = record.get("descrizione", "")
        if len(description) > 50:
            score += 5
        if len(description) > 100:
            score += 5

        return min(score, 100)

    def estimate_file_size_from_urls(self, model_urls: List[str]) -> int:
        """Stima dimensione file dai nomi degli URL"""
        if not model_urls:
            return 0

        # Estrai numero inventario dall'URL per stimare dimensione
        # es: "http://opendata-ercolano.cultura.gov.it/pub/modelli_3d_hr/77445.zip"
        total_size = 0
        for url in model_urls:
            if url and ".zip" in url:
                # Stima basata su pattern tipici dei modelli Ercolano
                if "anello" in url.lower() or "77445" in url:
                    total_size += 500  # KB per anelli
                elif "fritillus" in url.lower() or "77028" in url:
                    total_size += 800  # KB per fritillus
                else:
                    total_size += 1000  # KB default

        return total_size if total_size > 0 else 1000

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
