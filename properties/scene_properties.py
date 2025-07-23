"""
OpenShelf Scene Properties - VERSIONE ROBUSTA PER SVILUPPO
Definisce le proprietà scene per ricerca, filtri e risultati
FIX: Registrazione robusta che gestisce reload durante sviluppo
"""

import bpy
from bpy.props import (
    StringProperty,
    EnumProperty,
    CollectionProperty,
    IntProperty,
    BoolProperty
)
from bpy.types import PropertyGroup

class OpenShelfAssetProperty(PropertyGroup):
    """Proprietà per un singolo asset culturale"""

    asset_id: StringProperty(
        name="Asset ID",
        description="Unique identifier for the asset",
        default=""
    )

    name: StringProperty(
        name="Name",
        description="Display name of the asset",
        default=""
    )

    description: StringProperty(
        name="Description",
        description="Detailed description of the asset",
        default=""
    )

    repository: StringProperty(
        name="Repository",
        description="Source repository name",
        default=""
    )

    object_type: StringProperty(
        name="Object Type",
        description="Type of cultural object",
        default=""
    )

    materials: StringProperty(
        name="Materials",
        description="Materials used in the object",
        default=""
    )

    chronology: StringProperty(
        name="Chronology",
        description="Chronological period",
        default=""
    )

    inventory_number: StringProperty(
        name="Inventory Number",
        description="Museum inventory number",
        default=""
    )

    model_urls: StringProperty(
        name="Model URLs",
        description="URLs to 3D models (JSON string)",
        default=""
    )

    thumbnail_url: StringProperty(
        name="Thumbnail URL",
        description="URL to thumbnail image",
        default=""
    )

    license_info: StringProperty(
        name="License",
        description="License information",
        default=""
    )

    quality_score: IntProperty(
        name="Quality Score",
        description="Quality assessment score (0-100)",
        default=0,
        min=0,
        max=100
    )

def get_repository_items(self, context):
    """Callback per ottenere lista repository disponibili"""
    try:
        from ..repositories.registry import RepositoryRegistry

        items = [('all', 'All Repositories', 'Search in all repositories', 'WORLD_DATA', 0)]

        available_repos = RepositoryRegistry.get_available_repositories()
        for i, repo_name in enumerate(available_repos):
            items.append((
                repo_name.lower(),
                repo_name,
                f'Search in {repo_name} repository',
                'BOOKMARKS',
                i + 1
            ))
    except Exception as e:
        print(f"OpenShelf: Error getting repositories: {e}")
        # Fallback se registry non disponibile
        items = [('all', 'All Repositories', 'Search in all repositories', 'WORLD_DATA', 0)]

    return items

def search_update_callback(self, context):
    """Callback quando cambia il testo di ricerca"""
    pass

def selection_update_callback(self, context):
    """Callback quando cambia la selezione asset"""
    scene = context.scene

    try:
        selected_index = scene.openshelf_selected_result_index
        if hasattr(scene, 'openshelf_search_results') and len(scene.openshelf_search_results) > selected_index:
            selected_asset = scene.openshelf_search_results[selected_index]
            print(f"OpenShelf: Selected asset changed to: {selected_asset.name} (ID: {selected_asset.asset_id})")

        # Force UI redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    except Exception as e:
        print(f"OpenShelf: Error in selection update callback: {e}")

def safe_register_class(cls):
    """Registra classe solo se non è già registrata"""
    try:
        # Controlla se la classe è già registrata
        if hasattr(bpy.types, cls.__name__):
            print(f"OpenShelf: Class {cls.__name__} already registered, skipping")
            return False

        bpy.utils.register_class(cls)
        print(f"OpenShelf: Registered class {cls.__name__}")
        return True

    except ValueError as e:
        if "already registered" in str(e):
            print(f"OpenShelf: Class {cls.__name__} already registered (caught exception)")
            return False
        else:
            print(f"OpenShelf: Error registering {cls.__name__}: {e}")
            raise

def safe_unregister_class(cls):
    """Deregistra classe solo se è registrata"""
    try:
        # Controlla se la classe è registrata
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
            print(f"OpenShelf: Unregistered class {cls.__name__}")
            return True
        else:
            print(f"OpenShelf: Class {cls.__name__} not registered, skipping unregister")
            return False

    except Exception as e:
        print(f"OpenShelf: Error unregistering {cls.__name__}: {e}")
        return False

def safe_add_scene_property(prop_name, prop_value):
    """Aggiunge proprietà alla scena solo se non esiste già"""
    try:
        if hasattr(bpy.types.Scene, prop_name):
            print(f"OpenShelf: Scene property {prop_name} already exists, skipping")
            return False

        setattr(bpy.types.Scene, prop_name, prop_value)
        print(f"OpenShelf: Added scene property {prop_name}")
        return True

    except Exception as e:
        print(f"OpenShelf: Error adding scene property {prop_name}: {e}")
        return False

def safe_remove_scene_property(prop_name):
    """Rimuove proprietà dalla scena solo se exists"""
    try:
        if hasattr(bpy.types.Scene, prop_name):
            delattr(bpy.types.Scene, prop_name)
            print(f"OpenShelf: Removed scene property {prop_name}")
            return True
        else:
            print(f"OpenShelf: Scene property {prop_name} not found, skipping removal")
            return False

    except Exception as e:
        print(f"OpenShelf: Error removing scene property {prop_name}: {e}")
        return False

def register():
    """Registra le proprietà scene - VERSIONE ROBUSTA"""

    print("OpenShelf: Registering scene properties...")

    # Registra il PropertyGroup con controllo
    safe_register_class(OpenShelfAssetProperty)

    # === RICERCA E FILTRI ===
    safe_add_scene_property('openshelf_search_text', StringProperty(
        name="Search",
        description="Search in asset names and descriptions",
        default="",
        update=search_update_callback
    ))

    safe_add_scene_property('openshelf_active_repository', EnumProperty(
        name="Repository",
        description="Select repository to search",
        items=get_repository_items,
        default=0
    ))

    safe_add_scene_property('openshelf_filter_type', StringProperty(
        name="Object Type",
        description="Filter by object type (e.g., 'anello', 'fritillus')",
        default=""
    ))

    safe_add_scene_property('openshelf_filter_material', StringProperty(
        name="Material",
        description="Filter by material (e.g., 'oro', 'argilla')",
        default=""
    ))

    safe_add_scene_property('openshelf_filter_chronology', StringProperty(
        name="Chronology",
        description="Filter by chronological period (e.g., 'sec. I')",
        default=""
    ))

    safe_add_scene_property('openshelf_filter_inventory', StringProperty(
        name="Inventory Number",
        description="Filter by inventory number",
        default=""
    ))

    # === OPZIONI RICERCA ===
    safe_add_scene_property('openshelf_search_limit', IntProperty(
        name="Search Limit",
        description="Maximum number of results to show",
        default=50,
        min=10,
        max=500
    ))

    safe_add_scene_property('openshelf_auto_search', BoolProperty(
        name="Auto Search",
        description="Search automatically while typing",
        default=False
    ))

    # === RISULTATI E CACHE ===
    safe_add_scene_property('openshelf_search_results', CollectionProperty(
        type=OpenShelfAssetProperty,
        name="Search Results",
        description="Current search results"
    ))

    safe_add_scene_property('openshelf_assets_cache', CollectionProperty(
        type=OpenShelfAssetProperty,
        name="Assets Cache",
        description="Cache of all fetched assets"
    ))

    # INDICE SELEZIONE CON CALLBACK
    safe_add_scene_property('openshelf_selected_result_index', IntProperty(
        name="Selected Result Index",
        description="Index of currently selected search result",
        default=0,
        min=0,
        update=selection_update_callback
    ))

    # === STATISTICHE ===
    safe_add_scene_property('openshelf_search_count', IntProperty(
        name="Search Results Count",
        description="Number of search results",
        default=0
    ))

    safe_add_scene_property('openshelf_total_available', IntProperty(
        name="Total Available",
        description="Total number of assets available in repositories",
        default=0
    ))

    safe_add_scene_property('openshelf_last_search', StringProperty(
        name="Last Search",
        description="Last search query performed",
        default=""
    ))

    safe_add_scene_property('openshelf_last_repository', StringProperty(
        name="Last Repository",
        description="Last repository searched",
        default=""
    ))

    # === STATO APPLICAZIONE ===
    safe_add_scene_property('openshelf_is_searching', BoolProperty(
        name="Is Searching",
        description="Whether a search is currently in progress",
        default=False
    ))

    safe_add_scene_property('openshelf_is_downloading', BoolProperty(
        name="Is Downloading",
        description="Whether a download is currently in progress",
        default=False
    ))

    safe_add_scene_property('openshelf_download_progress', IntProperty(
        name="Download Progress",
        description="Current download progress (0-100)",
        default=0,
        min=0,
        max=100
    ))

    safe_add_scene_property('openshelf_status_message', StringProperty(
        name="Status Message",
        description="Current status message",
        default="Ready"
    ))

    # === PREFERENZE UTENTE ===
    safe_add_scene_property('openshelf_import_scale', IntProperty(
        name="Import Scale",
        description="Scale factor for imported objects (percentage)",
        default=100,
        min=1,
        max=1000
    ))

    safe_add_scene_property('openshelf_auto_center', BoolProperty(
        name="Auto Center",
        description="Automatically center imported objects",
        default=True
    ))

    safe_add_scene_property('openshelf_apply_materials', BoolProperty(
        name="Apply Materials",
        description="Automatically apply materials when importing",
        default=True
    ))

    safe_add_scene_property('openshelf_add_metadata', BoolProperty(
        name="Add Metadata",
        description="Add cultural metadata as custom properties",
        default=True
    ))

    print("OpenShelf: Scene properties registration completed")

def unregister():
    """Rimuove le proprietà scene - VERSIONE ROBUSTA"""

    print("OpenShelf: Unregistering scene properties...")

    # Lista di tutte le proprietà da rimuovere
    properties = [
        'openshelf_search_text',
        'openshelf_active_repository',
        'openshelf_filter_type',
        'openshelf_filter_material',
        'openshelf_filter_chronology',
        'openshelf_filter_inventory',
        'openshelf_search_limit',
        'openshelf_auto_search',
        'openshelf_search_results',
        'openshelf_assets_cache',
        'openshelf_selected_result_index',
        'openshelf_search_count',
        'openshelf_total_available',
        'openshelf_last_search',
        'openshelf_last_repository',
        'openshelf_is_searching',
        'openshelf_is_downloading',
        'openshelf_download_progress',
        'openshelf_status_message',
        'openshelf_import_scale',
        'openshelf_auto_center',
        'openshelf_apply_materials',
        'openshelf_add_metadata',
    ]

    # Rimuovi proprietà scene
    for prop in properties:
        safe_remove_scene_property(prop)

    # Deregistra il PropertyGroup
    safe_unregister_class(OpenShelfAssetProperty)

    print("OpenShelf: Scene properties unregistration completed")
