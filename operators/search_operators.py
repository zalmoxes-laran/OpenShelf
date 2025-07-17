"""
OpenShelf Search Operators
Operatori per ricerca e filtri negli asset culturali
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, IntProperty
import threading
import time
from ..repositories.registry import RepositoryRegistry

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
        
        # Avvia timer per controllare progresso
        bpy.app.timers.register(
            lambda: self._check_search_progress(context),
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
                cache_item.model_urls = str(asset.model_urls)  # Converti in stringa
                cache_item.thumbnail_url = asset.thumbnail_url
                cache_item.license_info = asset.license_info
                cache_item.quality_score = asset.quality_score
                
                # Aggiungi a risultati
                result_item = scene.openshelf_search_results.add()
                result_item.asset_id = asset.id
                result_item.name = asset.name
                result_item.description = asset.description
                result_item.repository = asset.repository
                result_item.object_type = asset.object_type
                result_item.inventory_number = asset.inventory_number
                result_item.quality_score = asset.quality_score
            
            # Aggiorna statistiche
            scene.openshelf_search_count = len(results)
            scene.openshelf_last_search = filters.get('search', '')
            scene.openshelf_last_repository = scene.openshelf_active_repository
            
            # Aggiorna stato
            if results:
                scene.openshelf_status_message = f"Found {len(results)} assets"
            else:
                scene.openshelf_status_message = "No assets found"
                
        except Exception as e:
            print(f"OpenShelf: Error updating search results: {e}")
            scene.openshelf_status_message = f"Error updating results: {str(e)}"
    
    def _check_search_progress(self, context):
        """Controlla progresso ricerca (chiamato da timer)"""
        scene = context.scene
        
        # Forza aggiornamento UI
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        # Continua timer solo se ricerca in corso
        return 0.1 if scene.openshelf_is_searching else None

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

class OPENSHELF_OT_apply_filters(Operator):
    """Applica filtri ai risultati esistenti"""
    bl_idname = "openshelf.apply_filters"
    bl_label = "Apply Filters"
    bl_description = "Apply filters to current search results"
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
        
        try:
            # Applica filtri ai risultati nella cache
            filters = {
                'object_type': self.filter_object_type,
                'material': self.filter_material,
                'chronology': self.filter_chronology,
                'inventory': self.filter_inventory,
            }
            
            # Rimuovi filtri vuoti
            filters = {k: v for k, v in filters.items() if v.strip()}
            
            filtered_results = []
            
            # Filtra risultati esistenti
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
            
            # Aggiorna statistiche
            scene.openshelf_search_count = len(filtered_results)
            scene.openshelf_status_message = f"Filtered to {len(filtered_results)} assets"
            
            self.report({'INFO'}, f"Applied filters - {len(filtered_results)} assets shown")
            
        except Exception as e:
            print(f"OpenShelf: Error applying filters: {e}")
            self.report({'ERROR'}, f"Error applying filters: {str(e)}")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Popola filtri con valori correnti
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

# Lista operatori da registrare
operators = [
    OPENSHELF_OT_search_assets,
    OPENSHELF_OT_clear_search,
    OPENSHELF_OT_apply_filters,
    OPENSHELF_OT_search_suggestions,
    OPENSHELF_OT_quick_search,
    OPENSHELF_OT_save_search,
]

def register():
    """Registra gli operatori di ricerca"""
    for op in operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra gli operatori di ricerca"""
    for op in reversed(operators):
        bpy.utils.unregister_class(op)
