"""
OpenShelf Search Operators - VERSIONE COMPLETA CORRETTA
Operatori per ricerca e filtri negli asset culturali
FIX: Timer standalone per evitare ReferenceError
AGGIUNTO: OPENSHELF_OT_clear_filters e tutti gli operatori completi
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, IntProperty
import threading
import time
import json
from ..repositories.registry import RepositoryRegistry

# FUNZIONE STANDALONE PER TIMER (SOLUZIONE AL BUG)
def _check_search_progress_standalone(context):
    """Controlla progresso ricerca e aggiorna UI - STANDALONE"""
    try:
        scene = context.scene

        # Controlla se il context è ancora valido
        if not scene:
            return None

        # Forza aggiornamento UI
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        # Continua timer solo se ricerca in corso
        return 0.1 if getattr(scene, 'openshelf_is_searching', False) else None

    except (ReferenceError, AttributeError):
        return None
    except Exception as e:
        print(f"OpenShelf: Timer error: {e}")
        return None


class OPENSHELF_OT_search_assets(Operator):
    """Cerca asset nei repository"""
    bl_idname = "openshelf.search_assets"
    bl_label = "Search Assets"
    bl_description = "Search for cultural heritage assets in repositories"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        # Impedisci ricerche multiple simultanee
        if scene.openshelf_is_searching:
            self.report({'INFO'}, "Search already in progress")
            return {'CANCELLED'}

        # Costruisci filtri
        filters = {
            'search': scene.openshelf_search_text,
            'object_type': scene.openshelf_filter_type,
            'material': scene.openshelf_filter_material,
            'chronology': scene.openshelf_filter_chronology,
            'inventory': scene.openshelf_filter_inventory,
        }

        # Rimuovi filtri vuoti
        filters = {k: v for k, v in filters.items() if v.strip()}

        # Controlla se ci sono criteri di ricerca
        if not filters:
            self.report({'WARNING'}, "Please enter search criteria")
            return {'CANCELLED'}

        # Avvia ricerca in thread separato
        search_thread = threading.Thread(
            target=self._search_thread,
            args=(context, filters)
        )
        search_thread.daemon = True
        search_thread.start()

        # FIX: USA FUNZIONE STANDALONE PER TIMER
        bpy.app.timers.register(
            lambda: _check_search_progress_standalone(context),
            first_interval=0.1
        )

        return {'FINISHED'}

    def _search_thread(self, context, filters):
        """Thread per eseguire ricerca senza bloccare UI"""
        scene = context.scene

        try:
            # Imposta stato ricerca
            scene.openshelf_is_searching = True
            scene.openshelf_status_message = "Searching..."

            # Ottieni repository attivo
            repo_id = scene.openshelf_active_repository
            limit = scene.openshelf_search_limit

            # Cerca negli asset
            if repo_id == 'all':
                # Cerca in tutti i repository
                results = RepositoryRegistry.search_all_repositories(
                    query=filters.get('search', ''),
                    filters=filters,
                    limit=limit
                )
            else:
                # Cerca in repository specifico
                repository = RepositoryRegistry.get_repository(repo_id)
                if not repository:
                    scene.openshelf_status_message = f"Repository '{repo_id}' not found"
                    return

                results = repository.search_assets(
                    query=filters.get('search', ''),
                    filters=filters,
                    limit=limit
                )

            # Aggiorna risultati nella UI (thread-safe)
            self._update_search_results(scene, results, filters)

        except Exception as e:
            print(f"OpenShelf: Search error: {e}")
            scene.openshelf_status_message = f"Search error: {str(e)}"
        finally:
            scene.openshelf_is_searching = False

    def _update_search_results(self, scene, results, filters):
        """Aggiorna i risultati nella UI"""
        try:
            # Pulisci risultati precedenti
            scene.openshelf_search_results.clear()
            scene.openshelf_assets_cache.clear()

            # Aggiungi nuovi risultati
            for asset in results:
                # Aggiungi a cache
                cache_item = scene.openshelf_assets_cache.add()
                cache_item.asset_id = asset.id
                cache_item.name = asset.name
                cache_item.description = asset.description
                cache_item.repository = asset.repository
                cache_item.object_type = asset.object_type
                cache_item.materials = ', '.join(asset.materials)
                cache_item.chronology = ', '.join(asset.chronology)
                cache_item.inventory_number = asset.inventory_number
                cache_item.model_urls = json.dumps(asset.model_urls) if asset.model_urls else "[]"
                cache_item.thumbnail_url = asset.thumbnail_url
                cache_item.quality_score = asset.quality_score

                # Aggiungi ai risultati visibili
                result_item = scene.openshelf_search_results.add()
                result_item.asset_id = asset.id
                result_item.name = asset.name
                result_item.description = asset.description
                result_item.repository = asset.repository
                result_item.object_type = asset.object_type
                result_item.inventory_number = asset.inventory_number
                result_item.quality_score = asset.quality_score
                result_item.model_urls = json.dumps(asset.model_urls) if asset.model_urls else "[]"
                result_item.thumbnail_url = asset.thumbnail_url
                result_item.materials = ', '.join(asset.materials)
                result_item.chronology = ', '.join(asset.chronology)

            # Aggiorna statistiche
            scene.openshelf_search_count = len(results)
            scene.openshelf_last_search = filters.get('search', '')
            scene.openshelf_last_repository = scene.openshelf_active_repository
            scene.openshelf_status_message = f"Found {len(results)} assets"

        except Exception as e:
            print(f"OpenShelf: Error updating search results: {e}")
            scene.openshelf_status_message = f"Error updating results: {str(e)}"


class OPENSHELF_OT_clear_search(Operator):
    """Pulisce i risultati di ricerca"""
    bl_idname = "openshelf.clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear search results and filters"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        try:
            # Ferma ricerca in corso
            scene.openshelf_is_searching = False

            # Pulisci campi ricerca
            scene.openshelf_search_text = ""
            scene.openshelf_filter_type = ""
            scene.openshelf_filter_material = ""
            scene.openshelf_filter_chronology = ""
            scene.openshelf_filter_inventory = ""

            # Pulisci risultati
            scene.openshelf_search_results.clear()
            scene.openshelf_assets_cache.clear()
            scene.openshelf_search_count = 0
            scene.openshelf_last_search = ""
            scene.openshelf_last_repository = ""

            # Reset stato
            scene.openshelf_status_message = "Ready"

            self.report({'INFO'}, "Search cleared")

        except Exception as e:
            print(f"OpenShelf: Error clearing search: {e}")
            self.report({'ERROR'}, f"Error clearing search: {str(e)}")

        return {'FINISHED'}


class OPENSHELF_OT_clear_filters(Operator):
    """Pulisce solo i filtri senza toccare ricerca e risultati"""
    bl_idname = "openshelf.clear_filters"
    bl_label = "Clear Filters"
    bl_description = "Clear filter criteria without affecting search results"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        try:
            # Pulisci SOLO i campi filtro
            scene.openshelf_filter_type = ""
            scene.openshelf_filter_material = ""
            scene.openshelf_filter_chronology = ""
            scene.openshelf_filter_inventory = ""

            # Ripristina i risultati originali dalla cache (rimuove filtri applicati)
            if hasattr(scene, 'openshelf_assets_cache') and len(scene.openshelf_assets_cache) > 0:
                # Ripristina tutti i risultati dalla cache
                scene.openshelf_search_results.clear()

                for cached_item in scene.openshelf_assets_cache:
                    result_item = scene.openshelf_search_results.add()
                    result_item.asset_id = cached_item.asset_id
                    result_item.name = cached_item.name
                    result_item.description = cached_item.description
                    result_item.repository = cached_item.repository
                    result_item.object_type = cached_item.object_type
                    result_item.inventory_number = cached_item.inventory_number
                    result_item.quality_score = cached_item.quality_score
                    result_item.model_urls = cached_item.model_urls
                    result_item.thumbnail_url = cached_item.thumbnail_url
                    result_item.materials = cached_item.materials
                    result_item.chronology = cached_item.chronology

                # Aggiorna conteggio
                scene.openshelf_search_count = len(scene.openshelf_assets_cache)
                scene.openshelf_status_message = f"Showing all {len(scene.openshelf_assets_cache)} results"

            self.report({'INFO'}, "Filters cleared - showing all search results")

        except Exception as e:
            print(f"OpenShelf: Error clearing filters: {e}")
            self.report({'ERROR'}, f"Error clearing filters: {str(e)}")

        return {'FINISHED'}


class OPENSHELF_OT_apply_filters(Operator):
    """Filtra i risultati di ricerca esistenti"""
    bl_idname = "openshelf.apply_filters"
    bl_label = "Filter Results"
    bl_description = "Filter the current search results using the specified criteria"
    bl_options = {'REGISTER'}

    filter_object_type: StringProperty(
        name="Object Type",
        description="Filter by object type",
        default=""
    )

    filter_material: StringProperty(
        name="Material",
        description="Filter by material",
        default=""
    )

    filter_chronology: StringProperty(
        name="Chronology",
        description="Filter by chronological period",
        default=""
    )

    filter_inventory: StringProperty(
        name="Inventory Number",
        description="Filter by inventory number",
        default=""
    )

    def execute(self, context):
        scene = context.scene

        # Verifica che ci siano risultati da filtrare
        if not hasattr(scene, 'openshelf_assets_cache') or len(scene.openshelf_assets_cache) == 0:
            self.report({'WARNING'}, "No search results to filter. Run a search first.")
            return {'CANCELLED'}

        try:
            # Costruisci filtri
            filters = {
                'object_type': self.filter_object_type,
                'material': self.filter_material,
                'chronology': self.filter_chronology,
                'inventory': self.filter_inventory,
            }

            # Rimuovi filtri vuoti
            filters = {k: v for k, v in filters.items() if v.strip()}

            if not filters:
                self.report({'WARNING'}, "No filter criteria specified")
                return {'CANCELLED'}

            filtered_results = []

            # Filtra risultati esistenti dalla cache
            for cached_item in scene.openshelf_assets_cache:
                # Ricostruisci asset per test filtri
                asset_data = {
                    'object_type': cached_item.object_type,
                    'materials': cached_item.materials.split(', ') if cached_item.materials else [],
                    'chronology': cached_item.chronology.split(', ') if cached_item.chronology else [],
                    'inventory_number': cached_item.inventory_number,
                }

                # Testa filtri
                matches = True
                for filter_key, filter_value in filters.items():
                    if filter_key == 'object_type' and filter_value.lower() not in asset_data['object_type'].lower():
                        matches = False
                        break
                    elif filter_key == 'material':
                        material_match = any(filter_value.lower() in mat.lower() for mat in asset_data['materials'])
                        if not material_match:
                            matches = False
                            break
                    elif filter_key == 'chronology':
                        chronology_match = any(filter_value.lower() in chron.lower() for chron in asset_data['chronology'])
                        if not chronology_match:
                            matches = False
                            break
                    elif filter_key == 'inventory' and filter_value.lower() not in asset_data['inventory_number'].lower():
                        matches = False
                        break

                if matches:
                    filtered_results.append(cached_item)

            # Aggiorna risultati filtrati
            scene.openshelf_search_results.clear()

            for result in filtered_results:
                result_item = scene.openshelf_search_results.add()
                result_item.asset_id = result.asset_id
                result_item.name = result.name
                result_item.description = result.description
                result_item.repository = result.repository
                result_item.object_type = result.object_type
                result_item.inventory_number = result.inventory_number
                result_item.quality_score = result.quality_score
                result_item.model_urls = result.model_urls
                result_item.thumbnail_url = result.thumbnail_url
                result_item.materials = result.materials
                result_item.chronology = result.chronology

            # Aggiorna statistiche
            original_count = len(scene.openshelf_assets_cache)
            filtered_count = len(filtered_results)
            scene.openshelf_search_count = filtered_count

            if filtered_count == original_count:
                scene.openshelf_status_message = f"No results filtered out ({filtered_count} total)"
            else:
                scene.openshelf_status_message = f"Filtered to {filtered_count} of {original_count} results"

            self.report({'INFO'}, f"Filter applied - showing {filtered_count} of {original_count} results")

        except Exception as e:
            print(f"OpenShelf: Error filtering results: {e}")
            self.report({'ERROR'}, f"Error filtering results: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        # Popola filtri con valori correnti dalla UI
        scene = context.scene
        self.filter_object_type = scene.openshelf_filter_type
        self.filter_material = scene.openshelf_filter_material
        self.filter_chronology = scene.openshelf_filter_chronology
        self.filter_inventory = scene.openshelf_filter_inventory

        return context.window_manager.invoke_props_dialog(self)


class OPENSHELF_OT_search_suggestions(Operator):
    """Ottiene suggerimenti per la ricerca"""
    bl_idname = "openshelf.search_suggestions"
    bl_label = "Get Search Suggestions"
    bl_description = "Get search suggestions from repositories"
    bl_options = {'REGISTER'}

    suggestion_type: StringProperty(
        name="Suggestion Type",
        description="Type of suggestions to get",
        default="object_type"  # object_type, material, chronology
    )

    def execute(self, context):
        scene = context.scene

        try:
            # Ottieni repository attivo
            repo_id = scene.openshelf_active_repository
            suggestions = []

            if repo_id == 'all':
                # Ottieni suggerimenti da tutti i repository
                for repo in RepositoryRegistry.get_all_repositories():
                    repo_suggestions = self._get_repo_suggestions(repo)
                    suggestions.extend(repo_suggestions)
            else:
                # Ottieni suggerimenti da repository specifico
                repository = RepositoryRegistry.get_repository(repo_id)
                if repository:
                    suggestions = self._get_repo_suggestions(repository)

            # Rimuovi duplicati e ordina
            suggestions = sorted(list(set(suggestions)))

            # Salva suggerimenti (per ora solo stampa)
            print(f"OpenShelf: {self.suggestion_type} suggestions: {suggestions[:20]}")

            self.report({'INFO'}, f"Found {len(suggestions)} {self.suggestion_type} suggestions")

        except Exception as e:
            print(f"OpenShelf: Error getting suggestions: {e}")
            self.report({'ERROR'}, f"Error getting suggestions: {str(e)}")

        return {'FINISHED'}

    def _get_repo_suggestions(self, repository):
        """Ottiene suggerimenti da un repository"""
        try:
            if self.suggestion_type == "object_type":
                return repository.get_available_object_types()
            elif self.suggestion_type == "material":
                return repository.get_available_materials()
            elif self.suggestion_type == "chronology":
                return repository.get_available_chronologies()
            else:
                return []
        except Exception as e:
            print(f"OpenShelf: Error getting suggestions from {repository.name}: {e}")
            return []


class OPENSHELF_OT_quick_search(Operator):
    """Ricerca rapida con termine specifico"""
    bl_idname = "openshelf.quick_search"
    bl_label = "Quick Search"
    bl_description = "Perform quick search with specified term"
    bl_options = {'REGISTER'}

    search_term: StringProperty(
        name="Search Term",
        description="Term to search for",
        default=""
    )

    search_field: StringProperty(
        name="Search Field",
        description="Field to search in",
        default="search"  # search, object_type, material, chronology
    )

    def execute(self, context):
        scene = context.scene

        if not self.search_term:
            self.report({'ERROR'}, "No search term specified")
            return {'CANCELLED'}

        try:
            # Imposta campo appropriato
            if self.search_field == "search":
                scene.openshelf_search_text = self.search_term
            elif self.search_field == "object_type":
                scene.openshelf_filter_type = self.search_term
            elif self.search_field == "material":
                scene.openshelf_filter_material = self.search_term
            elif self.search_field == "chronology":
                scene.openshelf_filter_chronology = self.search_term

            # Esegui ricerca
            bpy.ops.openshelf.search_assets()

        except Exception as e:
            print(f"OpenShelf: Error in quick search: {e}")
            self.report({'ERROR'}, f"Quick search error: {str(e)}")

        return {'FINISHED'}


class OPENSHELF_OT_save_search(Operator):
    """Salva ricerca corrente"""
    bl_idname = "openshelf.save_search"
    bl_label = "Save Search"
    bl_description = "Save current search parameters"
    bl_options = {'REGISTER'}

    search_name: StringProperty(
        name="Search Name",
        description="Name for this search",
        default="My Search"
    )

    def execute(self, context):
        scene = context.scene

        try:
            # Salva parametri ricerca (per ora solo stampa)
            search_params = {
                'name': self.search_name,
                'search_text': scene.openshelf_search_text,
                'repository': scene.openshelf_active_repository,
                'filters': {
                    'object_type': scene.openshelf_filter_type,
                    'material': scene.openshelf_filter_material,
                    'chronology': scene.openshelf_filter_chronology,
                    'inventory': scene.openshelf_filter_inventory,
                }
            }

            print(f"OpenShelf: Saved search: {search_params}")

            self.report({'INFO'}, f"Search '{self.search_name}' saved")

        except Exception as e:
            print(f"OpenShelf: Error saving search: {e}")
            self.report({'ERROR'}, f"Error saving search: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class OPENSHELF_OT_debug_model_urls(Operator):
    """Debug operatore per testare URL modelli"""
    bl_idname = "openshelf.debug_model_urls"
    bl_label = "Debug Model URLs"
    bl_description = "Debug model URLs in cache"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        print("\n" + "="*50)
        print("OpenShelf: DEBUG Model URLs")
        print("="*50)

        if not scene.openshelf_assets_cache:
            print("No assets in cache")
            self.report({'INFO'}, "No assets in cache to debug")
            return {'FINISHED'}

        for i, asset in enumerate(scene.openshelf_assets_cache):
            print(f"\nAsset {i+1}: {asset.name}")
            print(f"  - ID: {asset.asset_id}")
            print(f"  - Repository: {asset.repository}")
            print(f"  - model_urls (raw): {repr(asset.model_urls)}")

            # Prova a fare il parsing
            try:
                if asset.model_urls:
                    parsed_urls = json.loads(asset.model_urls)
                    print(f"  - Parsed URLs: {parsed_urls}")
                    print(f"  - Type: {type(parsed_urls)}")
                    if parsed_urls:
                        print(f"  - First URL: {parsed_urls[0]}")
                else:
                    print("  - No URLs")
            except Exception as e:
                print(f"  - ERROR parsing URLs: {e}")

            if i >= 4:  # Limita output
                break

        print("="*50)
        self.report({'INFO'}, f"Debugged {min(5, len(scene.openshelf_assets_cache))} assets")
        return {'FINISHED'}


# Lista operatori da registrare
operators = [
    OPENSHELF_OT_search_assets,
    OPENSHELF_OT_clear_search,
    OPENSHELF_OT_clear_filters,
    OPENSHELF_OT_apply_filters,
    OPENSHELF_OT_search_suggestions,
    OPENSHELF_OT_quick_search,
    OPENSHELF_OT_save_search,
    OPENSHELF_OT_debug_model_urls,
]

def register():
    """Registra gli operatori di ricerca"""
    for op in operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra gli operatori di ricerca"""
    for op in reversed(operators):
        bpy.utils.unregister_class(op)
