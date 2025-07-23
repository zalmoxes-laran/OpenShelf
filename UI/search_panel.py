"""
OpenShelf Search Panel - FIX ROBUSTEZZA UI
Pannello principale per ricerca asset culturali
FIX: Gestione robusta operatori mancanti e selezione asset
"""

import bpy
from bpy.types import Panel

def check_operator_available(operator_idname):
    """Controlla se un operatore è disponibile"""
    try:
        return hasattr(bpy.ops, operator_idname.split('.')[0]) and hasattr(getattr(bpy.ops, operator_idname.split('.')[0]), operator_idname.split('.')[1])
    except:
        return False

def safe_get_selected_result(scene):
    """Ottiene il risultato selezionato in modo sicuro"""
    try:
        if not hasattr(scene, 'openshelf_search_results') or not scene.openshelf_search_results:
            return None

        selected_index = getattr(scene, 'openshelf_selected_result_index', 0)

        if 0 <= selected_index < len(scene.openshelf_search_results):
            return scene.openshelf_search_results[selected_index]
        else:
            # Index fuori range, reset a 0
            scene.openshelf_selected_result_index = 0
            if len(scene.openshelf_search_results) > 0:
                return scene.openshelf_search_results[0]

    except Exception as e:
        print(f"OpenShelf: Error getting selected result: {e}")

    return None

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

        # Pulsanti repository con controllo disponibilità
        row = box.row(align=True)

        if check_operator_available('openshelf.refresh_repositories'):
            row.operator("openshelf.refresh_repositories", text="Refresh", icon='FILE_REFRESH')
        else:
            sub = row.row()
            sub.enabled = False
            sub.label(text="Refresh", icon='FILE_REFRESH')

        if check_operator_available('openshelf.test_repository'):
            row.operator("openshelf.test_repository", text="Test", icon='CHECKMARK')
        else:
            sub = row.row()
            sub.enabled = False
            sub.label(text="Test", icon='CHECKMARK')

        if check_operator_available('openshelf.repository_info'):
            row.operator("openshelf.repository_info", text="Info", icon='INFO')
        else:
            sub = row.row()
            sub.enabled = False
            sub.label(text="Info", icon='INFO')

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

        if hasattr(bpy.app, 'online_access') and not bpy.app.online_access:
            box = layout.box()
            box.alert = True
            col = box.column(align=True)
            col.scale_y = 0.8
            col.label(text="⚠️ Online Access Disabled", icon='ERROR')
            if hasattr(bpy.app, 'online_access_overridden') and bpy.app.online_access_overridden:
                col.label(text="Disabled by command line")
                col.label(text="Restart with --online-mode")
            else:
                col.label(text="Enable in Preferences > System")
                col.label(text="'Allow Online Access'")
            layout.separator()

        # Repository selection
        box = layout.box()
        box.label(text="Repository", icon='WORLD_DATA')
        box.prop(scene, 'openshelf_active_repository', text="", icon='BOOKMARKS')

        # SEZIONE RICERCA PRINCIPALE
        box = layout.box()
        box.label(text="Search", icon='ZOOM_SELECTED')

        # Campo ricerca principale
        col = box.column()
        col.prop(scene, 'openshelf_search_text', text="", icon='VIEWZOOM')

        # Bottoni azione ricerca con controllo disponibilità
        row = box.row(align=True)

        # Disabilita ricerca se già in corso
        search_disabled = getattr(scene, 'openshelf_is_searching', False)
        row.enabled = not search_disabled

        if check_operator_available('openshelf.search_assets'):
            row.operator("openshelf.search_assets", text="Search", icon='ZOOM_SELECTED')
        else:
            sub = row.row()
            sub.enabled = False
            sub.label(text="Search", icon='ERROR')

        if check_operator_available('openshelf.clear_search'):
            row.operator("openshelf.clear_search", text="Clear", icon='X')
        else:
            sub = row.row()
            sub.enabled = False
            sub.label(text="Clear", icon='X')

        # Mostra progresso se ricerca in corso
        if search_disabled:
            progress_box = layout.box()
            progress_box.label(text="Searching...", icon='TIME')

        # Salva ricerca se disponibile
        if scene.openshelf_search_text and check_operator_available('openshelf.save_search'):
            box.operator("openshelf.save_search", text="Save Search", icon='FILE_TICK')

class OPENSHELF_PT_progress_panel_colored(Panel):
    """Pannello progress con colori"""
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
        bg_row = col.row(align=True)
        bg_row.scale_y = 2.0

        # Calcola larghezza barra
        progress_width = max(1, progress // 5)  # 1-20 steps
        remaining_width = 20 - progress_width

        # Parte riempita (verde)
        if progress_width > 0:
            filled_row = bg_row.row(align=True)
            filled_row.alert = False
            filled_row.enabled = True
            for i in range(progress_width):
                filled_row.label(text="█")

        # Parte vuota (grigia)
        if remaining_width > 0:
            empty_row = bg_row.row(align=True)
            empty_row.enabled = False
            for i in range(remaining_width):
                empty_row.label(text="█")

        # Percentuale
        perc_row = col.row()
        perc_row.scale_y = 1.5
        perc_row.label(text=f"{progress}% Complete", icon='INFO')

        # Cancel button se disponibile
        if check_operator_available('openshelf.cancel_import'):
            col.operator("openshelf.cancel_import", text="Cancel Download", icon='CANCEL')

class OPENSHELF_PT_results_panel(Panel):
    """Pannello risultati ricerca - FIX ROBUSTEZZA"""
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

        # Lista risultati con controlli di sicurezza
        if hasattr(scene, 'openshelf_search_results') and len(scene.openshelf_search_results) > 0:
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

            # FIX: Ottieni risultato selezionato in modo sicuro
            selected_result = safe_get_selected_result(scene)

            if selected_result:
                # PULSANTI AZIONE - VERSIONE ROBUSTA
                actions_box = box.box()
                actions_row = actions_box.row(align=True)

                # FIX: Controlla se gli operatori sono disponibili prima di usarli
                if check_operator_available('openshelf.modal_import_asset'):
                    import_op = actions_row.operator("openshelf.modal_import_asset", text="Import", icon='IMPORT')
                    import_op.asset_id = selected_result.asset_id
                else:
                    # Mostra pulsante disabilitato se operatore non disponibile
                    sub = actions_row.row()
                    sub.enabled = False
                    sub.label(text="Import", icon='ERROR')
                    actions_box.label(text="⚠️ Import operators not available", icon='ERROR')

                # Import con opzioni se disponibile
                if check_operator_available('openshelf.import_asset_with_options'):
                    import_opts_op = actions_row.operator("openshelf.import_asset_with_options", text="Options", icon='TOOL_SETTINGS')
                    import_opts_op.asset_id = selected_result.asset_id

                # Seconda riga utility
                utils_row = actions_box.row(align=True)

                # Preview
                if check_operator_available('openshelf.preview_asset'):
                    preview_op = utils_row.operator("openshelf.preview_asset", text="Info", icon='INFO')
                    preview_op.asset_id = selected_result.asset_id

                # Validate
                if check_operator_available('openshelf.validate_asset'):
                    validate_op = utils_row.operator("openshelf.validate_asset", text="Check", icon='CHECKMARK')
                    validate_op.asset_id = selected_result.asset_id

                # DETTAGLI ASSET SELEZIONATO
                self._draw_asset_details(layout, selected_result)
            else:
                # Nessun asset selezionato o errore
                box.label(text="⚠️ No asset selected", icon='ERROR')

                # Info di debug se ci sono risultati ma selezione invalida
                if len(scene.openshelf_search_results) > 0:
                    selected_index = getattr(scene, 'openshelf_selected_result_index', -1)
                    box.label(text=f"Selected index: {selected_index}/{len(scene.openshelf_search_results)}")

        else:
            # Nessun risultato
            if hasattr(scene, 'openshelf_search_count') and scene.openshelf_search_count == 0:
                box = layout.box()
                box.label(text="No results found", icon='INFO')
                box.label(text="Try different search terms")
                box.label(text="or check repository status")
            else:
                box = layout.box()
                box.label(text="Run a search to see results", icon='ZOOM_SELECTED')

    def _draw_asset_details(self, layout, selected_result):
        """Disegna dettagli asset selezionato"""
        try:
            details_box = layout.box()
            details_box.label(text="Selected Asset Details", icon='TEXT')

            # Titolo asset
            title_row = details_box.row()
            title_row.scale_y = 1.2
            title_row.label(text=selected_result.name, icon='OBJECT_DATA')

            # Info compatte
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

            # Descrizione se presente
            if selected_result.description and selected_result.description.strip():
                desc_box = details_box.box()
                desc_box.label(text="Description:", icon='TEXT')

                description = selected_result.description.strip()
                if len(description) > 200:
                    description = description[:200] + "..."

                # Spezza in righe
                words = description.split()
                current_line = ""
                line_length = 35

                desc_col = desc_box.column(align=True)
                desc_col.scale_y = 0.8

                for word in words:
                    if len(current_line + " " + word) <= line_length:
                        current_line += " " + word if current_line else word
                    else:
                        if current_line:
                            desc_col.label(text=current_line)
                        current_line = word

                if current_line:
                    desc_col.label(text=current_line)
            else:
                details_box.label(text="No description available", icon='INFO')

            # Info tecniche
            tech_row = details_box.row(align=True)
            tech_row.scale_y = 0.7
            tech_row.label(text=f"Repository: {selected_result.repository}", icon='BOOKMARKS')

            # Controlla modelli 3D
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

        except Exception as e:
            print(f"OpenShelf: Error drawing asset details: {e}")
            details_box = layout.box()
            details_box.label(text="Error displaying asset details", icon='ERROR')

class OPENSHELF_PT_import_settings_panel(Panel):
    """Pannello impostazioni import"""
    bl_label = "Import Settings"
    bl_idname = "OPENSHELF_PT_import_settings_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 4
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(icon='IMPORT')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # SEZIONE SCALA E POSIZIONAMENTO
        box = layout.box()
        box.label(text="Scale & Position", icon='OBJECT_ORIGIN')

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(scene, 'openshelf_import_scale', text="Scale")
        row.label(text="%")
        col.prop(scene, 'openshelf_auto_center', text="Auto Center")

        # SEZIONE MATERIALI
        box = layout.box()
        box.label(text="Materials & Data", icon='MATERIAL')

        col = box.column(align=True)
        col.prop(scene, 'openshelf_apply_materials', text="Apply Materials")
        col.prop(scene, 'openshelf_add_metadata', text="Cultural Metadata")

        # SEZIONE PRESET
        box = layout.box()
        box.label(text="Quick Presets: original model is in", icon='PRESET')

        row = box.row(align=True)

        # Preset con controllo disponibilità
        if check_operator_available('openshelf.apply_import_preset'):
            meter_op = row.operator("openshelf.apply_import_preset", text="Meters")
            meter_op.preset_name = "meter"

            millimeter_op = row.operator("openshelf.apply_import_preset", text="Millimeters")
            millimeter_op.preset_name = "millimeter"
        else:
            sub = row.row()
            sub.enabled = False
            sub.label(text="Presets", icon='ERROR')

        # Reset settings
        reset_row = box.row()
        if check_operator_available('openshelf.reset_import_settings'):
            reset_row.operator("openshelf.reset_import_settings", text="Reset to Defaults", icon='FILE_REFRESH')
        else:
            sub = reset_row.row()
            sub.enabled = False
            sub.label(text="Reset", icon='ERROR')

        # Anteprima impostazioni
        info_box = layout.box()
        info_box.label(text="Current Settings", icon='INFO')

        col = info_box.column(align=True)
        col.scale_y = 0.8
        col.label(text=f"Scale: {scene.openshelf_import_scale}%")
        col.label(text=f"Center: {'Yes' if scene.openshelf_auto_center else 'No'}")
        col.label(text=f"Materials: {'Apply' if scene.openshelf_apply_materials else 'Skip'}")
        col.label(text=f"Metadata: {'Add' if scene.openshelf_add_metadata else 'Skip'}")

class OPENSHELF_PT_filter_results_panel(Panel):
    """Pannello filtri"""
    bl_label = "Filter Results"
    bl_idname = "OPENSHELF_PT_filter_results_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 5
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(icon='FILTER')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if not hasattr(scene, 'openshelf_search_results') or len(scene.openshelf_search_results) == 0:
            layout.label(text="No results to filter", icon='INFO')
            layout.label(text="Run a search first")
            return

        # Descrizione
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

        # BOTTONI AZIONE FILTRI con controllo disponibilità
        actions_box = layout.box()
        row = actions_box.row(align=True)

        if check_operator_available('openshelf.apply_filters'):
            row.operator("openshelf.apply_filters", text="Filter Results", icon='FILTER')
        else:
            sub = row.row()
            sub.enabled = False
            sub.label(text="Filter", icon='ERROR')

        if check_operator_available('openshelf.clear_filters'):
            row.operator("openshelf.clear_filters", text="Clear Filters", icon='X')
        else:
            sub = row.row()
            sub.enabled = False
            sub.label(text="Clear", icon='ERROR')

        # Informazioni filtri attivi
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

# Lista per i risultati di ricerca
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

            # Info aggiuntive
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

# Operatori per preset e utilità - con controlli robustezza
class OPENSHELF_OT_apply_import_preset(bpy.types.Operator):
    """Applica preset import"""
    bl_idname = "openshelf.apply_import_preset"
    bl_label = "Apply Import Preset"
    bl_description = "Apply predefined import settings"
    bl_options = {'REGISTER'}

    preset_name: bpy.props.StringProperty(default="default")

    def execute(self, context):
        scene = context.scene

        try:
            if self.preset_name == "meter":
                scene.openshelf_import_scale = 100
                scene.openshelf_auto_center = True
                scene.openshelf_apply_materials = True
                scene.openshelf_add_metadata = True
                self.report({'INFO'}, "Applied Meters preset")

            elif self.preset_name == "millimeter":
                scene.openshelf_import_scale = 10
                scene.openshelf_auto_center = True
                scene.openshelf_apply_materials = True
                scene.openshelf_add_metadata = True
                self.report({'INFO'}, "Applied Millimeters preset")

            else:
                self.report({'WARNING'}, f"Unknown preset: {self.preset_name}")

        except Exception as e:
            self.report({'ERROR'}, f"Error applying preset: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_reset_import_settings(bpy.types.Operator):
    """Reset impostazioni import"""
    bl_idname = "openshelf.reset_import_settings"
    bl_label = "Reset Import Settings"
    bl_description = "Reset import settings to default values"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        try:
            scene.openshelf_import_scale = 100
            scene.openshelf_auto_center = True
            scene.openshelf_apply_materials = True
            scene.openshelf_add_metadata = True
            self.report({'INFO'}, "Import settings reset to defaults")

        except Exception as e:
            self.report({'ERROR'}, f"Error resetting settings: {str(e)}")

        return {'FINISHED'}

# Registrazione pannelli
panels = [
    OPENSHELF_PT_main_panel,
    OPENSHELF_PT_search_panel,
    OPENSHELF_PT_progress_panel_colored,
    OPENSHELF_PT_results_panel,
    OPENSHELF_PT_import_settings_panel,
    OPENSHELF_PT_filter_results_panel,
    OPENSHELF_UL_search_results,
    OPENSHELF_OT_apply_import_preset,
    OPENSHELF_OT_reset_import_settings,
]

def register():
    """Registra i pannelli search"""
    for panel in panels:
        try:
            if not hasattr(bpy.types, panel.__name__):
                bpy.utils.register_class(panel)
                print(f"OpenShelf: Registered UI class {panel.__name__}")
            else:
                print(f"OpenShelf: UI class {panel.__name__} already registered")
        except Exception as e:
            print(f"OpenShelf: Error registering UI class {panel.__name__}: {e}")

def unregister():
    """Deregistra i pannelli search"""
    for panel in reversed(panels):
        try:
            if hasattr(bpy.types, panel.__name__):
                bpy.utils.unregister_class(panel)
                print(f"OpenShelf: Unregistered UI class {panel.__name__}")
        except Exception as e:
            print(f"OpenShelf: Error unregistering UI class {panel.__name__}: {e}")
