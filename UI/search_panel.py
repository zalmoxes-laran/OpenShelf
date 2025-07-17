"""
OpenShelf Search Panel
Pannello principale di ricerca nel viewport 3D
"""

import bpy
from bpy.types import Panel

class OPENSHELF_PT_main_panel(Panel):
    """Pannello principale OpenShelf"""
    bl_label = "OpenShelf"
    bl_idname = "OPENSHELF_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Header con logo/nome
        row = layout.row()
        row.label(text="OpenShelf", icon='BOOKMARKS')
        
        # Mostra stato corrente
        if hasattr(scene, 'openshelf_status_message'):
            box = layout.box()
            box.label(text=scene.openshelf_status_message, icon='INFO')
        
        # Repository selector
        box = layout.box()
        box.label(text="Repository", icon='WORLD_DATA')
        
        if hasattr(scene, 'openshelf_active_repository'):
            box.prop(scene, 'openshelf_active_repository', text="")
        
        # Pulsanti repository
        row = box.row(align=True)
        row.operator("openshelf.refresh_repositories", text="Refresh", icon='FILE_REFRESH')
        row.operator("openshelf.test_repository", text="Test", icon='CHECKMARK')
        row.operator("openshelf.repository_info", text="Info", icon='INFO')

class OPENSHELF_PT_search_panel(Panel):
    """Pannello di ricerca"""
    bl_label = "Search"
    bl_idname = "OPENSHELF_PT_search_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Search box principale
        box = layout.box()
        box.label(text="Search Query", icon='VIEWZOOM')
        
        col = box.column()
        col.prop(scene, 'openshelf_search_text', text="", icon='VIEWZOOM')
        
        # Impostazioni ricerca
        row = col.row()
        row.prop(scene, 'openshelf_search_limit', text="Limit")
        row.prop(scene, 'openshelf_auto_search', text="Auto")
        
        # Filtri
        box = layout.box()
        box.label(text="Filters", icon='FILTER')
        
        col = box.column()
        col.prop(scene, 'openshelf_filter_type', text="Type", icon='OBJECT_DATA')
        col.prop(scene, 'openshelf_filter_material', text="Material", icon='MATERIAL')
        col.prop(scene, 'openshelf_filter_chronology', text="Period", icon='TIME')
        col.prop(scene, 'openshelf_filter_inventory', text="Inventory", icon='LINENUMBERS_ON')
        
        # Bottoni azione ricerca
        box = layout.box()
        row = box.row(align=True)
        
        # Disabilita ricerca se già in corso
        search_disabled = getattr(scene, 'openshelf_is_searching', False)
        
        search_op = row.operator("openshelf.search_assets", text="Search", icon='ZOOM_SELECTED')
        search_op.enabled = not search_disabled
        
        row.operator("openshelf.clear_search", text="Clear", icon='X')
        
        # Mostra progresso se ricerca in corso
        if search_disabled:
            box.label(text="Searching...", icon='TIME')
        
        # Bottoni filtri avanzati
        row = box.row(align=True)
        row.operator("openshelf.apply_filters", text="Apply Filters", icon='FILTER')
        row.operator("openshelf.save_search", text="Save", icon='FILE_TICK')

class OPENSHELF_PT_results_panel(Panel):
    """Pannello risultati ricerca"""
    bl_label = "Results"
    bl_idname = "OPENSHELF_PT_results_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Statistiche risultati
        if hasattr(scene, 'openshelf_search_count'):
            box = layout.box()
            box.label(text=f"Found: {scene.openshelf_search_count} assets", icon='PRESET')
            
            # Mostra repository e ultima ricerca
            if hasattr(scene, 'openshelf_last_repository') and scene.openshelf_last_repository:
                if scene.openshelf_last_repository == 'all':
                    box.label(text="Repository: All", icon='WORLD_DATA')
                else:
                    box.label(text=f"Repository: {scene.openshelf_last_repository}", icon='BOOKMARKS')
            
            if hasattr(scene, 'openshelf_last_search') and scene.openshelf_last_search:
                box.label(text=f"Query: '{scene.openshelf_last_search}'", icon='VIEWZOOM')
        
        # Lista risultati
        if hasattr(scene, 'openshelf_search_results') and scene.openshelf_search_results:
            
            # Controlli batch
            box = layout.box()
            box.label(text="Batch Operations", icon='MODIFIER')
            row = box.row(align=True)
            row.operator("openshelf.batch_import", text="Import All", icon='IMPORT')
            row.operator("openshelf.repository_statistics", text="Stats", icon='GRAPH')
            
            # Risultati individuali
            box = layout.box()
            box.label(text="Individual Assets", icon='OBJECT_DATA')
            
            # Mostra primi N risultati
            max_results = 15
            results = scene.openshelf_search_results
            
            for i, result in enumerate(results[:max_results]):
                self.draw_result_item(box, result, i)
            
            # Mostra contatore se ci sono più risultati
            if len(results) > max_results:
                box.label(text=f"... and {len(results) - max_results} more assets")
                box.operator("openshelf.clear_search", text="Clear to see all", icon='X')
        
        else:
            # Nessun risultato
            box = layout.box()
            box.label(text="No results", icon='INFO')
            box.label(text="Try searching for cultural assets")
    
    def draw_result_item(self, layout, result, index):
        """Disegna un singolo risultato"""
        
        # Container per risultato
        box = layout.box()
        
        # Header con nome e tipo
        row = box.row()
        col = row.column()
        col.scale_y = 0.8
        
        # Nome principale
        name_text = result.name if result.name else f"Asset {result.asset_id}"
        col.label(text=name_text[:45] + ("..." if len(name_text) > 45 else ""))
        
        # Informazioni secondarie
        info_parts = []
        if result.object_type:
            info_parts.append(result.object_type)
        if result.inventory_number:
            info_parts.append(f"#{result.inventory_number}")
        if result.repository:
            info_parts.append(f"({result.repository})")
        
        if info_parts:
            info_text = " • ".join(info_parts)
            col.label(text=info_text[:50] + ("..." if len(info_text) > 50 else ""))
        
        # Descrizione se disponibile
        if result.description:
            desc_text = result.description[:60] + ("..." if len(result.description) > 60 else "")
            col.label(text=desc_text)
        
        # Colonna pulsanti
        col = row.column()
        col.scale_x = 0.6
        
        # Pulsante import principale
        import_disabled = getattr(bpy.context.scene, 'openshelf_is_downloading', False)
        
        import_op = col.operator("openshelf.import_asset", text="Import", icon='IMPORT')
        import_op.asset_id = result.asset_id
        import_op.enabled = not import_disabled
        
        # Pulsanti secondari
        row = col.row(align=True)
        row.scale_y = 0.7
        
        preview_op = row.operator("openshelf.preview_asset", text="", icon='HIDE_OFF')
        preview_op.asset_id = result.asset_id
        
        validate_op = row.operator("openshelf.validate_asset", text="", icon='CHECKMARK')
        validate_op.asset_id = result.asset_id
        
        # Indicatore qualità
        if result.quality_score > 0:
            quality_color = 'GOOD' if result.quality_score >= 80 else 'WARNING' if result.quality_score >= 50 else 'ERROR'
            quality_icon = 'CHECKMARK' if result.quality_score >= 80 else 'ERROR' if result.quality_score < 50 else 'QUESTION'
            
            quality_row = box.row()
            quality_row.scale_y = 0.7
            quality_row.label(text=f"Quality: {result.quality_score}%", icon=quality_icon)

class OPENSHELF_PT_import_panel(Panel):
    """Pannello controlli import"""
    bl_label = "Import Settings"
    bl_idname = "OPENSHELF_PT_import_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Impostazioni import
        box = layout.box()
        box.label(text="Import Options", icon='IMPORT')
        
        col = box.column()
        col.prop(scene, 'openshelf_import_scale', text="Scale %")
        col.prop(scene, 'openshelf_auto_center', text="Auto Center")
        col.prop(scene, 'openshelf_apply_materials', text="Apply Materials")
        col.prop(scene, 'openshelf_add_metadata', text="Add Metadata")
        
        # Stato download
        if hasattr(scene, 'openshelf_is_downloading') and scene.openshelf_is_downloading:
            box = layout.box()
            box.label(text="Download in Progress", icon='TIME')
            
            if hasattr(scene, 'openshelf_download_progress'):
                progress = scene.openshelf_download_progress
                box.label(text=f"Progress: {progress}%")
                
                # Barra progresso semplice
                progress_row = box.row()
                progress_row.scale_y = 0.5
                for i in range(10):
                    filled = i < (progress / 10)
                    icon = 'SEQUENCE_COLOR_04' if filled else 'SEQUENCE_COLOR_01'
                    progress_row.label(text="", icon=icon)
            
            # Pulsante cancella
            box.operator("openshelf.cancel_import", text="Cancel", icon='CANCEL')
        
        # Cache info
        box = layout.box()
        box.label(text="Cache", icon='FILE_CACHE')
        
        # TODO: Mostra statistiche cache
        row = box.row()
        row.label(text="Cache: Active")
        row.operator("openshelf.clear_repository_cache", text="Clear", icon='TRASH')

# Lista pannelli da registrare
panels = [
    OPENSHELF_PT_main_panel,
    OPENSHELF_PT_search_panel,
    OPENSHELF_PT_results_panel,
    OPENSHELF_PT_import_panel,
]

def register():
    """Registra i pannelli di ricerca"""
    for panel in panels:
        bpy.utils.register_class(panel)

def unregister():
    """Deregistra i pannelli di ricerca"""
    for panel in reversed(panels):
        bpy.utils.unregister_class(panel)
