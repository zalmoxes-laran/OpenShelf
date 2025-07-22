"""
OpenShelf Search Panel - VERSIONE CORRETTA
Pannello principale per ricerca asset culturali
FIX: Rimosso import_op.repository e aggiunti operatori mancanti
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


class OPENSHELF_PT_progress_panel_colored(Panel):
    """Pannello progress con colori veri (usando props per colorare)"""
    bl_label = "Download Progress"
    bl_idname = "OPENSHELF_PT_progress_panel_colored"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return getattr(scene, 'openshelf_is_downloading', False)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Downloading Asset", icon='IMPORT')

        # Status message
        status_msg = getattr(scene, 'openshelf_status_message', 'Downloading...')
        box.label(text=status_msg)

        progress = getattr(scene, 'openshelf_download_progress', 0)

        # Progress bar usando split layout con colori
        col = box.column()

        # Background grigio
        bg_row = col.row(align=True)
        bg_row.scale_y = 2.0

        # Calcola larghezza barra (in steps di 5%)
        progress_width = max(1, progress // 5)  # 1-20 steps
        remaining_width = 20 - progress_width

        # Parte riempita (verde)
        if progress_width > 0:
            filled_row = bg_row.row(align=True)
            filled_row.alert = False  # Verde/normale
            filled_row.enabled = True
            for i in range(progress_width):
                filled_row.label(text="█")

        # Parte vuota (grigia)
        if remaining_width > 0:
            empty_row = bg_row.row(align=True)
            empty_row.enabled = False  # Grigia
            for i in range(remaining_width):
                empty_row.label(text="█")

        # Percentuale
        perc_row = col.row()
        perc_row.scale_y = 1.5
        perc_row.label(text=f"{progress}% Complete", icon='INFO')

        # Cancel button
        col.operator("openshelf.cancel_import", text="Cancel Download", icon='CANCEL')


class OPENSHELF_PT_results_panel(Panel):
    """Pannello risultati ricerca"""
    bl_label = "Results"
    bl_idname = "OPENSHELF_PT_results_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 3

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

            # Azioni e info su risultato selezionato
            if len(scene.openshelf_search_results) > 0:
                selected_index = getattr(scene, 'openshelf_selected_result_index', 0)
                if 0 <= selected_index < len(scene.openshelf_search_results):
                    selected_result = scene.openshelf_search_results[selected_index]

                    # PULSANTI AZIONE
                    actions_box = box.box()
                    actions_row = actions_box.row(align=True)

                    # Pulsante Import
                    import_op = actions_row.operator("openshelf.import_asset", text="Import", icon='IMPORT')
                    import_op.asset_id = selected_result.asset_id

                    # Pulsante Preview
                    preview_op = actions_row.operator("openshelf.preview_asset", text="Info", icon='INFO')
                    preview_op.asset_id = selected_result.asset_id

                    # Pulsante Validate
                    validate_op = actions_row.operator("openshelf.validate_asset", text="Check", icon='CHECKMARK')
                    validate_op.asset_id = selected_result.asset_id

                    # NUOVA SEZIONE: DETTAGLI ASSET SELEZIONATO
                    details_box = layout.box()
                    details_box.label(text="Selected Asset Details", icon='TEXT')

                    # Titolo asset
                    title_row = details_box.row()
                    title_row.scale_y = 1.2
                    title_row.label(text=selected_result.name, icon='OBJECT_DATA')

                    # Info compatte in colonne
                    info_split = details_box.split(factor=0.3)

                    # Colonna sinistra: labels
                    left_col = info_split.column()
                    left_col.scale_y = 0.8
                    left_col.alignment = 'RIGHT'
                    left_col.label(text="Type:")
                    left_col.label(text="Inventory:")
                    if selected_result.materials:
                        left_col.label(text="Materials:")
                    if selected_result.chronology:
                        left_col.label(text="Period:")
                    if selected_result.quality_score > 0:
                        left_col.label(text="Quality:")

                    # Colonna destra: valori
                    right_col = info_split.column()
                    right_col.scale_y = 0.8
                    right_col.label(text=selected_result.object_type or "Unknown")
                    right_col.label(text=selected_result.inventory_number or "N/A")
                    if selected_result.materials:
                        # Tronca materiali se troppo lunghi
                        materials = selected_result.materials
                        if len(materials) > 30:
                            materials = materials[:30] + "..."
                        right_col.label(text=materials)
                    if selected_result.chronology:
                        chronology = selected_result.chronology
                        if len(chronology) > 25:
                            chronology = chronology[:25] + "..."
                        right_col.label(text=chronology)
                    if selected_result.quality_score > 0:
                        right_col.label(text=f"{selected_result.quality_score}%", icon='KEYTYPE_JITTER_VEC')

                    # DESCRIZIONE (se presente)
                    if selected_result.description and selected_result.description.strip():
                        desc_box = details_box.box()
                        desc_box.label(text="Description:", icon='TEXT')

                        # Spezza descrizione in righe
                        description = selected_result.description.strip()

                        # Limita lunghezza per evitare pannello troppo alto
                        if len(description) > 200:
                            description = description[:200] + "..."

                        # Spezza in parole e raggruppa per righe
                        words = description.split()
                        current_line = ""
                        line_length = 35  # Caratteri per riga

                        desc_col = desc_box.column(align=True)
                        desc_col.scale_y = 0.8

                        for word in words:
                            if len(current_line + " " + word) <= line_length:
                                current_line += " " + word if current_line else word
                            else:
                                if current_line:
                                    desc_col.label(text=current_line)
                                current_line = word

                        # Ultima riga
                        if current_line:
                            desc_col.label(text=current_line)
                    else:
                        # Nessuna descrizione
                        details_box.label(text="No description available", icon='INFO')

                    # Info tecniche compatte
                    tech_row = details_box.row(align=True)
                    tech_row.scale_y = 0.7
                    tech_row.label(text=f"Repository: {selected_result.repository}", icon='BOOKMARKS')

                    # Controlla se ha modelli 3D
                    has_models = False
                    try:
                        import json
                        if selected_result.model_urls:
                            urls = json.loads(selected_result.model_urls)
                            has_models = len(urls) > 0 if isinstance(urls, list) else bool(urls)
                    except:
                        pass

                    model_icon = 'CHECKMARK' if has_models else 'X'
                    model_text = "3D Available" if has_models else "No 3D Models"
                    tech_row.label(text=model_text, icon=model_icon)

        else:
            # Nessun risultato - suggerimenti
            if hasattr(scene, 'openshelf_search_count') and scene.openshelf_search_count == 0:
                box = layout.box()
                box.label(text="No results found", icon='INFO')
                box.label(text="Try different search terms")
                box.label(text="or check repository status")
            else:
                box = layout.box()
                box.label(text="Run a search to see results", icon='ZOOM_SELECTED')


class OPENSHELF_PT_filter_results_panel(Panel):
    """Pannello filtri - SPOSTATO DOPO I RISULTATI"""
    bl_label = "Filter Results"
    bl_idname = "OPENSHELF_PT_filter_results_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 4
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
                sub.label(text=f"{item.quality_score}%", icon='KEYTYPE_JITTER_VEC')

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon=type_icon)


# NUOVO: Operatore missing per show_asset_info (era il problema!)
class OPENSHELF_OT_show_asset_info(bpy.types.Operator):
    """Mostra informazioni dettagliate asset"""
    bl_idname = "openshelf.show_asset_info"
    bl_label = "Show Asset Info"
    bl_description = "Show detailed information about the asset"
    bl_options = {'REGISTER'}

    asset_id: bpy.props.StringProperty(
        name="Asset ID",
        description="ID of the asset to show info for",
        default=""
    )

    def execute(self, context):
        # Reindirizza al preview_asset che fa la stessa cosa
        bpy.ops.openshelf.preview_asset(asset_id=self.asset_id)
        return {'FINISHED'}


# Registrazione pannelli
panels = [
    OPENSHELF_PT_main_panel,
    OPENSHELF_PT_search_panel,
    OPENSHELF_PT_progress_panel_colored,
    OPENSHELF_PT_results_panel,
    OPENSHELF_PT_filter_results_panel,
    OPENSHELF_UL_search_results,
    OPENSHELF_OT_show_asset_info,  # AGGIUNTO operatore mancante
]

def register():
    """Registra i pannelli search"""
    for panel in panels:
        bpy.utils.register_class(panel)

def unregister():
    """Deregistra i pannelli search"""
    for panel in reversed(panels):
        bpy.utils.unregister_class(panel)
