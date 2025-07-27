"""
OpenShelf Search Panel - FIX ROBUSTEZZA UI
Pannello principale per ricerca asset culturali
FIX: Gestione robusta operatori mancanti e selezione asset
"""

import bpy # type: ignore
from bpy.types import Panel # type: ignore
from ..utils.local_library_manager import get_library_manager

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
    """Pannello progress INLINE che funziona sempre"""
    bl_label = ""
    bl_idname = "OPENSHELF_PT_progress_panel_colored"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 1
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        scene = context.scene
        is_downloading = getattr(scene, 'openshelf_is_downloading', False)
        return is_downloading

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # LETTURA DIRETTA dalla scene property (sempre aggiornata)
        progress = scene.get('openshelf_download_progress', 0)
        status = scene.get('openshelf_status_message', 'Downloading...')

        # MAIN BOX molto evidente
        main_box = layout.box()
        main_box.alert = True

        # HEADER ANIMATO
        header_row = main_box.row()
        header_row.scale_y = 2.0

        # Icona che cambia per dare movimento
        icons = ['IMPORT', 'URL', 'PACKAGE', 'FILE_TICK', 'CHECKMARK']
        icon_index = min(int(progress / 25), len(icons) - 1)
        current_icon = icons[icon_index]

        header_row.label(text=f"📥 DOWNLOADING {progress}%", icon=current_icon)

        # PROGRESS BAR GIGANTE
        progress_box = main_box.box()

        # Barra visuale ENORME
        bar_row = progress_box.row()
        bar_row.scale_y = 2.5

        # Barra con 30 caratteri
        bar_length = 30
        filled_length = int((progress / 100) * bar_length)

        # Caratteri Unicode che funzionano sempre
        if filled_length == 0:
            bar_string = "░" * bar_length
        elif filled_length == bar_length:
            bar_string = "█" * bar_length
        else:
            bar_string = "█" * filled_length + "▓" + "░" * (bar_length - filled_length - 1)

        bar_row.alignment = 'CENTER'
        bar_row.label(text=f"[{bar_string}]")

        # PERCENTUALE GIGANTE
        perc_row = progress_box.row()
        perc_row.scale_y = 3.0
        perc_row.alignment = 'CENTER'
        perc_row.label(text=f"{progress}%")

        # STATUS DETTAGLIATO
        status_box = main_box.box()

        # Status principale
        status_row = status_box.row()
        status_row.scale_y = 1.3

        # Tronca status intelligentemente
        if len(status) > 40:
            # Cerca un punto di taglio intelligente
            if " - " in status:
                parts = status.split(" - ")
                if len(parts[0]) < 35:
                    display_status = parts[0]
                else:
                    display_status = status[:37] + "..."
            else:
                display_status = status[:37] + "..."
        else:
            display_status = status

        status_row.label(text=display_status)

        # INFO VELOCITÀ (se presente nel status)
        if " - " in status and ("MB/s" in status or "KB/s" in status):
            speed_parts = status.split(" - ")
            for part in speed_parts[1:]:
                if "MB/s" in part or "KB/s" in part:
                    speed_row = status_box.row()
                    speed_row.scale_y = 1.1
                    # Estrai solo la parte velocità
                    speed_text = part.split(" (")[0] if " (" in part else part
                    speed_row.label(text=f"⚡ {speed_text}", icon='TIME')
                    break

        # ETA (se presente)
        if "ETA:" in status:
            eta_match = status.split("ETA:")[-1].split(")")[0] if "ETA:" in status else ""
            if eta_match:
                eta_row = status_box.row()
                eta_row.scale_y = 1.1
                eta_row.label(text=f"⏰ ETA:{eta_match}", icon='SORTTIME')

        # CANCEL BUTTON prominente
        cancel_box = main_box.box()
        cancel_row = cancel_box.row()
        cancel_row.scale_y = 1.8
        cancel_row.alert = True

        if check_operator_available('openshelf.cancel_import'):
            cancel_row.operator("openshelf.cancel_import", text="❌ CANCEL DOWNLOAD", icon='CANCEL')

        # SEPARATOR per dividere dal resto
        layout.separator()
        sep_row = layout.row()
        sep_row.scale_y = 0.3
        sep_row.label(text="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

class OPENSHELF_PT_download_status_simple(Panel):
    """Pannello status download SEMPLICE sempre visibile"""
    bl_label = "Download Status"
    bl_idname = "OPENSHELF_PT_download_status_simple"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 0  # PRIMO pannello

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Sempre mostra lo stato corrente
        is_downloading = getattr(scene, 'openshelf_is_downloading', False)
        progress = getattr(scene, 'openshelf_download_progress', 0)
        status = getattr(scene, 'openshelf_status_message', 'Ready')

        # Status box
        box = layout.box()

        if is_downloading:
            box.alert = True
            box.label(text=f"⬇️ {progress}%", icon='IMPORT')
            box.label(text=status)
        else:
            box.label(text="✅ Ready", icon='CHECKMARK')
            if status and status != 'Ready':
                box.label(text=status)

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

                # NUOVO: Usa il nuovo operatore sincrono semplice
                try:
                    library_manager = get_library_manager()
                    if library_manager.is_asset_downloaded(selected_result.asset_id):
                        # Asset già in libreria - import diretto
                        print(f"OpenShelf UI: Asset {selected_result.asset_id} found in library")
                        import_op = actions_row.operator("openshelf.simple_sync_import", text="Import", icon='CHECKMARK')
                        import_op.asset_id = selected_result.asset_id
                    else:
                        # Asset non in libreria - download + import
                        print(f"OpenShelf UI: Asset {selected_result.asset_id} not in library, will download")
                        import_op = actions_row.operator("openshelf.simple_sync_import", text="Download", icon='IMPORT')
                        import_op.asset_id = selected_result.asset_id

                except Exception as e:
                    print(f"OpenShelf UI: Error checking library, using fallback: {e}")
                    # Fallback - usa sempre il nuovo operatore sincrono
                    import_op = actions_row.operator("openshelf.simple_sync_import", text="Import", icon='IMPORT')
                    import_op.asset_id = selected_result.asset_id

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
    bl_order = 6
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
    bl_order = 7
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

class OPENSHELF_UL_search_results(bpy.types.UIList):
    """Lista UI per risultati ricerca - UNA SOLA RIGA"""
    bl_idname = "OPENSHELF_UL_search_results"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # 🔹 Icona status libreria
            try:
                library_manager = get_library_manager()
                if library_manager.is_asset_downloaded(item.asset_id):
                    row.label(icon='CHECKMARK')  # ✓ Asset in libreria
                else:
                    row.label(icon='IMPORT')     # ⬇️ Asset da scaricare
            except:
                row.label(icon='OBJECT_DATAMODE')  # Fallback

            # 🔹 INVENTORY (6 caratteri max)
            inv = item.inventory_number[:6] if item.inventory_number else f"#{item.asset_id[:4]}"
            row.label(text=inv)

            # 🔹 OBJECT TYPE (8 caratteri max)
            obj_type = item.object_type[:8] if item.object_type else "N/D"
            row.label(text=obj_type)

            # 🔹 NAME principale (troncato se troppo lungo)
            display_name = item.name
            if len(display_name) > 25:
                display_name = display_name[:22] + "..."
            row.label(text=display_name)

            # 🔹 QUALITY (se presente)
            #if item.quality_score > 0:
            #    row.label(text=f"{item.quality_score}%", icon='SOLO_ON')

            # 🔹 REPOSITORY (abbreviato a 3 lettere)
            #repo_abbr = item.repository[:3].upper() if item.repository else "UNK"
            #row.label(text=repo_abbr)


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


"""
Aggiunta di accesso rapido alle impostazioni cache nel pannello principale
"""
class OPENSHELF_PT_cache_quick_panel(Panel):
    """Pannello accesso rapido cache - NUOVO"""
    bl_label = "Cache & Storage"
    bl_idname = "OPENSHELF_PT_cache_quick_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenShelf"
    bl_parent_id = "OPENSHELF_PT_main_panel"
    bl_order = 5  # Tra results e import settings
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(icon='FILE_CACHE')

    def draw(self, context):
        layout = self.layout

        # Info cache corrente con accesso rapido
        box = layout.box()
        box.label(text="Current Cache", icon='FOLDER_REDIRECT')

        try:
            # Ottieni directory cache corrente
            addon_name = __package__.split('.')[0]
            prefs = context.preferences.addons[addon_name].preferences

            current_cache_dir = None
            if hasattr(prefs, 'custom_cache_directory') and prefs.custom_cache_directory.strip():
                current_cache_dir = prefs.custom_cache_directory.strip()
                cache_type = "Custom"
            else:
                import tempfile
                current_cache_dir = os.path.join(tempfile.gettempdir(), "openshelf_cache")
                cache_type = "Default"

            # Mostra info directory corrente
            col = box.column(align=True)
            col.scale_y = 0.8
            col.label(text=f"Type: {cache_type}")

            # Mostra path abbreviato
            if current_cache_dir:
                if len(current_cache_dir) > 35:
                    display_path = "..." + current_cache_dir[-32:]
                else:
                    display_path = current_cache_dir
                col.label(text=f"Path: {display_path}")

                # Verifica se esiste
                if os.path.exists(current_cache_dir):
                    col.label(text="✓ Directory exists", icon='CHECKMARK')
                else:
                    col.label(text="⚠ Will be created when needed", icon='INFO')

        except Exception as e:
            box.label(text="Cache info unavailable", icon='ERROR')

        # Statistiche cache rapide
        box = layout.box()
        box.label(text="Cache Stats", icon='GRAPH')

        try:
            from ..utils.download_manager import get_download_manager
            dm = get_download_manager()
            cache_stats = dm.get_cache_statistics()

            col = box.column(align=True)
            col.scale_y = 0.8

            file_count = cache_stats['file_count']
            cache_size_mb = cache_stats['cache_size'] / (1024 * 1024)

            col.label(text=f"Files: {file_count}")

            if cache_size_mb < 1:
                col.label(text=f"Size: {cache_stats['cache_size'] / 1024:.0f} KB")
            else:
                col.label(text=f"Size: {cache_size_mb:.1f} MB")

        except Exception:
            col = box.column()
            col.label(text="Stats unavailable")

        # Azioni rapide cache
        box = layout.box()
        box.label(text="Quick Actions", icon='TOOL_SETTINGS')

        col = box.column(align=True)

        # Apri cartella cache
        if check_operator_available('openshelf.open_cache_directory'):
            col.operator("openshelf.open_cache_directory", text="Open Cache Folder", icon='FILE_FOLDER')

        # Pulisci cache
        if check_operator_available('openshelf.clear_repository_cache'):
            clear_op = col.operator("openshelf.clear_repository_cache", text="Clear Cache", icon='TRASH')
            clear_op.repository_name = "all"
            clear_op.confirm = True

        # Statistiche dettagliate
        if check_operator_available('openshelf.cache_statistics'):
            col.operator("openshelf.cache_statistics", text="Detailed Stats", icon='GRAPH')

        # NUOVO: Accesso rapido alle preferenze cache
        box = layout.box()
        box.label(text="Settings", icon='PREFERENCES')

        col = box.column()
        col.scale_y = 1.2

        # Pulsante per aprire preferenze direttamente al tab cache
        prefs_op = col.operator("screen.userpref_show", text="Open Cache Preferences", icon='SETTINGS')

        # Info che spiega dove si trova
        info_col = col.column(align=True)
        info_col.scale_y = 0.7
        info_col.label(text="Set custom cache directory,")
        info_col.label(text="size limits, and cleanup options")
        info_col.label(text="in Preferences > Add-ons > OpenShelf")

#  operatore per aprire direttamente le preferenze cache
class OPENSHELF_OT_open_cache_preferences(bpy.types.Operator):
    """Apre le preferenze addon direttamente al tab cache"""
    bl_idname = "openshelf.open_cache_preferences"
    bl_label = "Open Cache Preferences"
    bl_description = "Open OpenShelf preferences at Cache tab"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            # Apri preferences
            bpy.ops.screen.userpref_show('INVOKE_DEFAULT')

            # Vai al tab Add-ons
            context.preferences.active_section = 'ADDONS'

            # Cerca OpenShelf
            addon_name = __package__.split('.')[0]

            # Espandi l'addon se possibile
            if addon_name in context.preferences.addons:
                prefs = context.preferences.addons[addon_name].preferences
                # Imposta tab cache se la proprietà esiste
                if hasattr(prefs, 'prefs_tab'):
                    prefs.prefs_tab = 'CACHE'

            self.report({'INFO'}, "Opened OpenShelf preferences - go to Cache tab")

        except Exception as e:
            print(f"OpenShelf: Error opening cache preferences: {e}")
            self.report({'ERROR'}, f"Error opening preferences: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_select_result(bpy.types.Operator):
    """Seleziona un risultato specifico"""
    bl_idname = "openshelf.select_result"
    bl_label = "Select Result"
    bl_description = "Select this search result"
    bl_options = {'REGISTER'}

    result_index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        scene = context.scene

        if (hasattr(scene, 'openshelf_search_results') and
            0 <= self.result_index < len(scene.openshelf_search_results)):

            scene.openshelf_selected_result_index = self.result_index

            # Force UI redraw
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            selected_asset = scene.openshelf_search_results[self.result_index]
            print(f"OpenShelf: Selected asset {self.result_index}: {selected_asset.name}")

        return {'FINISHED'}

# Registrazione pannelli
panels = [
    OPENSHELF_PT_main_panel,
    #OPENSHELF_PT_download_status_simple,
    OPENSHELF_PT_search_panel,
    OPENSHELF_PT_progress_panel_colored,
    OPENSHELF_PT_results_panel,
    OPENSHELF_PT_cache_quick_panel,  # NUOVO pannello cache
    OPENSHELF_PT_import_settings_panel,
    OPENSHELF_PT_filter_results_panel,
    OPENSHELF_UL_search_results,
    OPENSHELF_OT_apply_import_preset,
    OPENSHELF_OT_reset_import_settings,
    OPENSHELF_OT_open_cache_preferences,  # NUOVO operatore
    OPENSHELF_OT_select_result,
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
