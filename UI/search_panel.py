"""
OpenShelf Search Panel - VERSIONE RIORGANIZZATA
Pannello principale per ricerca asset culturali
UX IMPROVEMENT: Filtri spostati dopo i risultati per chiarezza del workflow
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
    """Pannello ricerca principale"""
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

        # Repository selection
        box = layout.box()
        box.label(text="Repository", icon='WORLD_DATA')
        box.prop(scene, 'openshelf_active_repository', text="", icon='BOOKMARKS')

        # SEZIONE 1: RICERCA PRINCIPALE (solo campo principale)
        box = layout.box()
        box.label(text="Search", icon='ZOOM_SELECTED')

        # Campo ricerca principale
        col = box.column()
        col.prop(scene, 'openshelf_search_text', text="", icon='VIEWZOOM')

        # Bottoni azione ricerca
        row = box.row(align=True)

        # Disabilita ricerca se già in corso
        search_disabled = getattr(scene, 'openshelf_is_searching', False)
        row.enabled = not search_disabled

        row.operator("openshelf.search_assets", text="Search", icon='ZOOM_SELECTED')
        row.operator("openshelf.clear_search", text="Clear", icon='X')

        # Mostra progresso se ricerca in corso
        if search_disabled:
            progress_box = layout.box()
            progress_box.label(text="Searching...", icon='TIME')

        # Salva ricerca (se ha senso mantenerlo qui)
        if scene.openshelf_search_text:
            box.operator("openshelf.save_search", text="Save Search", icon='FILE_TICK')


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

        # Lista risultati (se ci sono)
        if hasattr(scene, 'openshelf_search_results') and len(scene.openshelf_search_results) > 0:

            # Scrollable list per i risultati
            box = layout.box()
            box.label(text="Assets", icon='OUTLINER_COLLECTION')

            # Template_list per risultati scorrevoli
            col = box.column()
            col.template_list(
                "OPENSHELF_UL_search_results", "",
                scene, "openshelf_search_results",
                scene, "openshelf_selected_result_index",
                rows=5
            )

            # Azioni su risultato selezionato
            if len(scene.openshelf_search_results) > 0:
                selected_index = getattr(scene, 'openshelf_selected_result_index', 0)
                if 0 <= selected_index < len(scene.openshelf_search_results):
                    selected_result = scene.openshelf_search_results[selected_index]

                    actions_box = box.box()
                    actions_row = actions_box.row(align=True)

                    # Pulsante Import
                    import_op = actions_row.operator("openshelf.import_asset", text="Import", icon='IMPORT')
                    import_op.asset_id = selected_result.asset_id
                    import_op.repository = selected_result.repository

                    # Pulsante Info
                    info_op = actions_row.operator("openshelf.show_asset_info", text="Info", icon='INFO')
                    info_op.asset_id = selected_result.asset_id


class OPENSHELF_PT_filter_results_panel(Panel):
    """Pannello filtri - SPOSTATO DOPO I RISULTATI"""
    bl_label = "Filter Results"
    bl_idname = "OPENSHELF_PT_filter_results_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 3  # DOPO i risultati
    bl_options = {'DEFAULT_CLOSED'}  # Chiuso di default

    def draw_header(self, context):
        # Icona speciale per indicare che filtra i risultati esistenti
        self.layout.label(icon='FILTER')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Mostra filtri solo se ci sono risultati da filtrare
        if not hasattr(scene, 'openshelf_search_results') or len(scene.openshelf_search_results) == 0:
            layout.label(text="No results to filter", icon='INFO')
            layout.label(text="Run a search first")
            return

        # Descrizione chiara del comportamento
        info_box = layout.box()
        info_box.scale_y = 0.8
        col = info_box.column(align=True)
        col.label(text="Filter current results:", icon='INFO')
        col.label(text="These filters work on")
        col.label(text="the search results above")

        # CAMPI FILTRO
        box = layout.box()
        box.label(text="Filter Criteria", icon='FILTER')

        col = box.column()
        col.prop(scene, 'openshelf_filter_type', text="Type", icon='OBJECT_DATA')
        col.prop(scene, 'openshelf_filter_material', text="Material", icon='MATERIAL')
        col.prop(scene, 'openshelf_filter_chronology', text="Period", icon='TIME')
        col.prop(scene, 'openshelf_filter_inventory', text="Inventory", icon='LINENUMBERS_ON')

        # BOTTONI AZIONE FILTRI
        actions_box = layout.box()
        row = actions_box.row(align=True)

        # Pulsante principale: "Filter Results" (rinominato da "Apply Filters")
        filter_op = row.operator("openshelf.apply_filters", text="Filter Results", icon='FILTER')

        # Pulsante per pulire solo i filtri
        clear_filters_op = row.operator("openshelf.clear_filters", text="Clear Filters", icon='X')

        # Informazioni sui filtri attivi
        active_filters = []
        if scene.openshelf_filter_type:
            active_filters.append(f"Type: {scene.openshelf_filter_type}")
        if scene.openshelf_filter_material:
            active_filters.append(f"Material: {scene.openshelf_filter_material}")
        if scene.openshelf_filter_chronology:
            active_filters.append(f"Period: {scene.openshelf_filter_chronology}")
        if scene.openshelf_filter_inventory:
            active_filters.append(f"Inventory: {scene.openshelf_filter_inventory}")

        if active_filters:
            info_box = layout.box()
            info_box.label(text="Active Filters:", icon='FILTER')
            col = info_box.column(align=True)
            col.scale_y = 0.8
            for filter_info in active_filters:
                col.label(text=f"• {filter_info}")


# Lista per i risultati di ricerca (resta uguale)
class OPENSHELF_UL_search_results(bpy.types.UIList):
    """Lista UI per risultati ricerca"""
    bl_idname = "OPENSHELF_UL_search_results"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Icona tipo oggetto
            type_icon = 'OBJECT_DATA'
            if 'vaso' in item.object_type.lower():
                type_icon = 'MESH_CYLINDER'
            elif 'moneta' in item.object_type.lower() or 'anello' in item.object_type.lower():
                type_icon = 'MESH_CIRCLE'
            elif 'statua' in item.object_type.lower():
                type_icon = 'OUTLINER_OB_ARMATURE'

            # Nome principale
            layout.label(text=item.name, icon=type_icon)

            # Info aggiuntive in sub-row
            sub = layout.row(align=True)
            sub.scale_x = 0.7
            sub.scale_y = 0.8

            # Repository
            sub.label(text=item.repository, icon='BOOKMARKS')

            # Qualità se disponibile
            if item.quality_score > 0:
                sub.label(text=f"{item.quality_score}%", icon='QUALITY')

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon=type_icon)


# Registrazione pannelli
panels = [
    OPENSHELF_PT_main_panel,           # AGGIUNTO: Pannello principale
    OPENSHELF_PT_search_panel,
    OPENSHELF_PT_results_panel,
    OPENSHELF_PT_filter_results_panel,
    OPENSHELF_UL_search_results,
]

def register():
    """Registra i pannelli search"""
    for panel in panels:
        bpy.utils.register_class(panel)

def unregister():
    """Deregistra i pannelli search"""
    for panel in reversed(panels):
        bpy.utils.unregister_class(panel)
