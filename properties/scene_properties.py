"""
OpenShelf Scene Properties - VERSIONE CORRETTA
Definisce le proprietà scene per ricerca, filtri e risultati
AGGIUNTO: openshelf_selected_result_index
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
    from ..repositories.registry import RepositoryRegistry

    items = [('all', 'All Repositories', 'Search in all repositories', 'WORLD_DATA', 0)]

    try:
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

    return items

def search_update_callback(self, context):
    """Callback quando cambia il testo di ricerca"""
    # Implementa ricerca in tempo reale se desiderato
    # Per ora non facciamo nulla per evitare troppe chiamate
    pass

def register():
    """Registra le proprietà scene"""

    # Registra il PropertyGroup
    bpy.utils.register_class(OpenShelfAssetProperty)

    # === RICERCA E FILTRI ===
    bpy.types.Scene.openshelf_search_text = StringProperty(
        name="Search",
        description="Search in asset names and descriptions",
        default="",
        update=search_update_callback
    )

    bpy.types.Scene.openshelf_active_repository = EnumProperty(
        name="Repository",
        description="Select repository to search",
        items=get_repository_items,
        default=0
    )

    bpy.types.Scene.openshelf_filter_type = StringProperty(
        name="Object Type",
        description="Filter by object type (e.g., 'anello', 'fritillus')",
        default=""
    )

    bpy.types.Scene.openshelf_filter_material = StringProperty(
        name="Material",
        description="Filter by material (e.g., 'oro', 'argilla')",
        default=""
    )

    bpy.types.Scene.openshelf_filter_chronology = StringProperty(
        name="Chronology",
        description="Filter by chronological period (e.g., 'sec. I')",
        default=""
    )

    bpy.types.Scene.openshelf_filter_inventory = StringProperty(
        name="Inventory Number",
        description="Filter by inventory number",
        default=""
    )

    # === OPZIONI RICERCA ===
    bpy.types.Scene.openshelf_search_limit = IntProperty(
        name="Search Limit",
        description="Maximum number of results to show",
        default=50,
        min=10,
        max=500
    )

    bpy.types.Scene.openshelf_auto_search = BoolProperty(
        name="Auto Search",
        description="Search automatically while typing",
        default=False
    )

    # === RISULTATI E CACHE ===
    bpy.types.Scene.openshelf_search_results = CollectionProperty(
        type=OpenShelfAssetProperty,
        name="Search Results",
        description="Current search results"
    )

    bpy.types.Scene.openshelf_assets_cache = CollectionProperty(
        type=OpenShelfAssetProperty,
        name="Assets Cache",
        description="Cache of all fetched assets"
    )

    # FIX: AGGIUNTA PROPRIETÀ MANCANTE PER INDICE SELEZIONATO
    bpy.types.Scene.openshelf_selected_result_index = IntProperty(
        name="Selected Result Index",
        description="Index of currently selected search result",
        default=0,
        min=0
    )

    # === STATISTICHE ===
    bpy.types.Scene.openshelf_search_count = IntProperty(
        name="Search Results Count",
        description="Number of search results",
        default=0
    )

    bpy.types.Scene.openshelf_total_available = IntProperty(
        name="Total Available",
        description="Total number of assets available in repositories",
        default=0
    )

    bpy.types.Scene.openshelf_last_search = StringProperty(
        name="Last Search",
        description="Last search query performed",
        default=""
    )

    bpy.types.Scene.openshelf_last_repository = StringProperty(
        name="Last Repository",
        description="Last repository searched",
        default=""
    )

    # === STATO APPLICAZIONE ===
    bpy.types.Scene.openshelf_is_searching = BoolProperty(
        name="Is Searching",
        description="Whether a search is currently in progress",
        default=False
    )

    bpy.types.Scene.openshelf_is_downloading = BoolProperty(
        name="Is Downloading",
        description="Whether a download is currently in progress",
        default=False
    )

    bpy.types.Scene.openshelf_download_progress = IntProperty(
        name="Download Progress",
        description="Current download progress (0-100)",
        default=0,
        min=0,
        max=100
    )

    bpy.types.Scene.openshelf_status_message = StringProperty(
        name="Status Message",
        description="Current status message",
        default="Ready"
    )

    # === PREFERENZE UTENTE ===
    bpy.types.Scene.openshelf_import_scale = IntProperty(
        name="Import Scale",
        description="Scale factor for imported objects (percentage)",
        default=100,
        min=1,
        max=1000
    )

    bpy.types.Scene.openshelf_auto_center = BoolProperty(
        name="Auto Center",
        description="Automatically center imported objects",
        default=True
    )

    bpy.types.Scene.openshelf_apply_materials = BoolProperty(
        name="Apply Materials",
        description="Automatically apply materials when importing",
        default=True
    )

    bpy.types.Scene.openshelf_add_metadata = BoolProperty(
        name="Add Metadata",
        description="Add cultural metadata as custom properties",
        default=True
    )

def unregister():
    """Rimuove le proprietà scene"""

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
        'openshelf_selected_result_index',  # AGGIUNTO
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

    for prop in properties:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

    # Deregistra il PropertyGroup
    bpy.utils.unregister_class(OpenShelfAssetProperty)
