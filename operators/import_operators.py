"""
OpenShelf Import Operators - VERSIONE THREAD-SAFE CORRETTA
Operatori per importare asset 3D dai repository
CORREZIONE: Comunicazione thread-safe senza scrivere direttamente nelle proprietà della scena
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty
import threading
import json
import os
import time
from ..utils.download_manager import get_download_manager
from ..utils.obj_loader import OBJLoader
from ..utils.gltf_loader import GLTFLoader
from ..repositories.registry import RepositoryRegistry

class ImportThreadState:
    """Stato condiviso thread-safe per l'import"""
    def __init__(self):
        self.is_downloading = False
        self.download_progress = 0
        self.status_message = "Ready"
        self.pending_import_data = None
        self.error_message = None
        self.completed = False
        self.lock = threading.Lock()

# Istanza globale per lo stato
_import_state = ImportThreadState()

class OPENSHELF_OT_import_asset(Operator):
    """Importa un asset 3D specifico (LEGACY - reindirizza al modal per sicurezza)"""
    bl_idname = "openshelf.import_asset"
    bl_label = "Import Asset"
    bl_description = "Download and import selected 3D asset (redirects to modal import for stability)"
    bl_options = {'REGISTER', 'UNDO'}

    asset_id: StringProperty(
        name="Asset ID",
        description="ID of the asset to import",
        default=""
    )

    use_cache: BoolProperty(
        name="Use Cache",
        description="Use cached files if available",
        default=True
    )

    import_scale: FloatProperty(
        name="Import Scale",
        description="Scale factor for imported object",
        default=1.0,
        min=0.01,
        max=100.0
    )

    auto_center: BoolProperty(
        name="Auto Center",
        description="Center object at origin",
        default=True
    )

    apply_materials: BoolProperty(
        name="Apply Materials",
        description="Apply materials to imported object",
        default=True
    )

    add_metadata: BoolProperty(
        name="Add Metadata",
        description="Add cultural metadata as custom properties",
        default=True
    )

    def execute(self, context):
        """REINDIRIZZAMENTO AUTOMATICO al modal operator più sicuro"""

        print("OpenShelf: Legacy import operator - redirecting to modal import for stability")

        # Reindirizza al modal operator che è più sicuro
        try:
            return bpy.ops.openshelf.modal_import_asset(
                asset_id=self.asset_id,
                import_scale=self.import_scale,
                auto_center=self.auto_center,
                apply_materials=self.apply_materials,
                add_metadata=self.add_metadata
            )
        except Exception as e:
            print(f"OpenShelf: Error redirecting to modal import: {e}")
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        # Popola proprietà con valori dalle preferenze scene
        scene = context.scene
        self.import_scale = scene.openshelf_import_scale / 100.0  # Converti in float
        self.auto_center = scene.openshelf_auto_center
        self.apply_materials = scene.openshelf_apply_materials
        self.add_metadata = scene.openshelf_add_metadata

        return self.execute(context)

class OPENSHELF_OT_import_asset_old_threading(Operator):
    """Import con vecchio sistema threading (SOLO PER BACKUP - NON USARE)"""
    bl_idname = "openshelf.import_asset_old_threading"
    bl_label = "Import Asset (Old Threading - DO NOT USE)"
    bl_description = "Old threading import - kept for reference only, DO NOT USE"
    bl_options = {'REGISTER', 'UNDO'}

    asset_id: StringProperty(default="")
    use_cache: BoolProperty(default=True)
    import_scale: FloatProperty(default=1.0, min=0.01, max=100.0)
    auto_center: BoolProperty(default=True)
    apply_materials: BoolProperty(default=True)
    add_metadata: BoolProperty(default=True)

    def execute(self, context):
        """METODO DEPRECATO - Non usare, mantenuto solo per reference"""
        self.report({'ERROR'}, "This operator is deprecated - use modal_import_asset instead")
        return {'CANCELLED'}

    def _download_thread(self, context, asset_data, thread_params):
        """Thread per download - VERSIONE ORIGINALE (DEPRECATA)"""
        try:
            # Aggiorna stato thread-safe
            with _import_state.lock:
                _import_state.status_message = "Downloading asset..."

            # Ottieni repository
            repository = RepositoryRegistry.get_repository(asset_data.repository)
            if not repository:
                with _import_state.lock:
                    _import_state.error_message = f"Repository '{asset_data.repository}' not available"
                return

            # PARSING URL (stesso codice di prima)
            model_urls = []

            print(f"OpenShelf: Parsing URLs for asset {asset_data.asset_id}")
            print(f"OpenShelf: Raw model_urls: {repr(asset_data.model_urls)}")

            if asset_data.model_urls:
                try:
                    parsed = json.loads(asset_data.model_urls)
                    if isinstance(parsed, list):
                        model_urls = [str(url).strip() for url in parsed if url]
                        print(f"OpenShelf: JSON parsing successful: {model_urls}")
                    elif isinstance(parsed, str):
                        model_urls = [parsed.strip()] if parsed.strip() else []
                except json.JSONDecodeError as e:
                    print(f"OpenShelf: JSON parsing failed: {e}")
                    # Fallback methods...

            # Valida URLs
            valid_urls = []
            for url in model_urls:
                if url and isinstance(url, str) and url.strip():
                    clean_url = url.strip()
                    if clean_url.startswith('http'):
                        valid_urls.append(clean_url)

            if not valid_urls:
                with _import_state.lock:
                    _import_state.error_message = "No valid 3D model URLs found"
                return

            # Download
            download_manager = get_download_manager()
            archive_path = None

            for i, model_url in enumerate(valid_urls):
                print(f"OpenShelf: Trying download {i+1}/{len(valid_urls)}: {model_url}")

                with _import_state.lock:
                    _import_state.status_message = f"Downloading from {model_url}..."

                def progress_callback(downloaded, total):
                    if total > 0:
                        progress = int((downloaded / total) * 80)  # 80% per download
                        with _import_state.lock:
                            _import_state.download_progress = progress

                archive_path = download_manager.download_file(
                    model_url,
                    use_cache=thread_params['use_cache'],
                    progress_callback=progress_callback
                )

                if archive_path:
                    print(f"OpenShelf: Download successful: {archive_path}")
                    break

            if not archive_path:
                with _import_state.lock:
                    _import_state.error_message = "Failed to download any asset"
                return

            # Estrai archivio
            with _import_state.lock:
                _import_state.status_message = "Extracting archive..."
                _import_state.download_progress = 85

            def extract_progress_callback(extracted, total):
                if total > 0:
                    progress = 85 + int((extracted / total) * 10)
                    with _import_state.lock:
                        _import_state.download_progress = progress

            extract_dir = download_manager.extract_archive(
                archive_path,
                progress_callback=extract_progress_callback
            )

            if not extract_dir:
                with _import_state.lock:
                    _import_state.error_message = "Failed to extract archive"
                return

            # Trova file 3D supportati
            with _import_state.lock:
                _import_state.status_message = "Finding 3D files..."
                _import_state.download_progress = 95

            supported_extensions = ['.obj', '.gltf', '.glb']
            found_files = download_manager.find_files_by_extension(extract_dir, supported_extensions)

            if not found_files:
                with _import_state.lock:
                    _import_state.error_message = "No supported 3D files found"
                return

            # Prepara dati per import nel main thread
            import_data = {
                'model_path': found_files[0],
                'asset_data': asset_data,
                'import_settings': {
                    'import_scale': thread_params['import_scale'],
                    'auto_center': thread_params['auto_center'],
                    'apply_materials': thread_params['apply_materials'],
                    'add_metadata': thread_params['add_metadata']
                }
            }

            with _import_state.lock:
                _import_state.download_progress = 100
                _import_state.status_message = "Download complete, preparing import..."
                _import_state.pending_import_data = import_data

        except Exception as e:
            print(f"OpenShelf: Download error: {e}")
            import traceback
            traceback.print_exc()
            with _import_state.lock:
                _import_state.error_message = f"Download error: {str(e)}"

    def _update_ui_state(self):
        """Aggiorna UI con stato dal thread - eseguito nel main thread"""
        try:
            context = bpy.context
            scene = context.scene

            with _import_state.lock:
                # Copia stato dal thread alle proprietà della scena
                scene.openshelf_is_downloading = _import_state.is_downloading
                scene.openshelf_download_progress = _import_state.download_progress
                scene.openshelf_status_message = _import_state.status_message

                # Controlla se c'è un import da eseguire
                if _import_state.pending_import_data:
                    import_data = _import_state.pending_import_data
                    _import_state.pending_import_data = None  # Consuma dati

                    # Esegui import nel main thread
                    self._do_import_in_main_thread(context, import_data)
                    return None  # Non ripetere timer

                # Controlla errori
                if _import_state.error_message:
                    scene.openshelf_status_message = _import_state.error_message
                    scene.openshelf_is_downloading = False
                    scene.openshelf_download_progress = 0
                    _import_state.is_downloading = False
                    return None  # Non ripetere timer

                # Controlla se completato
                if _import_state.completed:
                    scene.openshelf_is_downloading = False
                    _import_state.is_downloading = False
                    return None  # Non ripetere timer

            # Forza aggiornamento UI
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            # Continua timer se download in corso
            return 0.1 if _import_state.is_downloading else None

        except Exception as e:
            print(f"OpenShelf: UI update error: {e}")
            return None

    def _do_import_in_main_thread(self, context, import_data):
        """Esegue l'import nel main thread"""
        scene = context.scene

        try:
            model_path = import_data['model_path']
            asset_data = import_data['asset_data']
            import_settings = import_data['import_settings']

            scene.openshelf_status_message = "Importing 3D model..."

            file_ext = os.path.splitext(model_path)[1].lower()

            # Prepara dati asset per loader
            asset_dict = {
                'id': asset_data.asset_id,
                'name': asset_data.name,
                'description': asset_data.description,
                'repository': asset_data.repository,
                'object_type': asset_data.object_type,
                'inventory_number': asset_data.inventory_number,
                'materials': asset_data.materials.split(', ') if asset_data.materials else [],
                'chronology': asset_data.chronology.split(', ') if asset_data.chronology else [],
                'license_info': asset_data.license_info,
                'quality_score': asset_data.quality_score,
                'metadata': import_settings
            }

            # Import con loader appropriato
            imported_obj = None

            if file_ext == '.obj':
                imported_obj = OBJLoader.import_obj(model_path, **import_settings)
                if imported_obj and import_settings['add_metadata']:
                    OBJLoader.apply_cultural_metadata(imported_obj, asset_dict)

            elif file_ext in ['.gltf', '.glb']:
                imported_obj = GLTFLoader.import_gltf(model_path, **import_settings)
                if imported_obj and import_settings['add_metadata']:
                    all_objects = [obj for obj in context.scene.objects if obj.get('openshelf_import_batch')]
                    GLTFLoader.apply_cultural_metadata(imported_obj, all_objects, asset_dict)

            # Finalizza import
            if imported_obj:
                scene.openshelf_status_message = f"Successfully imported {asset_data.name}"

                # Seleziona oggetto importato
                context.view_layer.objects.active = imported_obj
                imported_obj.select_set(True)

                print(f"OpenShelf: Successfully imported {asset_data.name}")

                with _import_state.lock:
                    _import_state.completed = True
            else:
                scene.openshelf_status_message = "Failed to import 3D model"
                with _import_state.lock:
                    _import_state.error_message = "Failed to import 3D model"

        except Exception as e:
            print(f"OpenShelf: Import error in main thread: {e}")
            import traceback
            traceback.print_exc()
            scene.openshelf_status_message = f"Import error: {str(e)}"
            with _import_state.lock:
                _import_state.error_message = f"Import error: {str(e)}"

class OPENSHELF_OT_batch_import(Operator):
    """Importa multipli asset in batch"""
    bl_idname = "openshelf.batch_import"
    bl_label = "Batch Import"
    bl_description = "Import multiple assets at once"
    bl_options = {'REGISTER', 'UNDO'}

    max_concurrent: IntProperty(
        name="Max Concurrent",
        description="Maximum number of concurrent imports",
        default=3,
        min=1,
        max=10
    )

    import_spacing: FloatProperty(
        name="Import Spacing",
        description="Distance between imported objects",
        default=5.0,
        min=0.0,
        max=100.0
    )

    def execute(self, context):
        scene = context.scene

        # Ottieni asset selezionati (per ora importa tutti i risultati)
        selected_assets = []
        for result in scene.openshelf_search_results:
            if result.asset_id:
                selected_assets.append(result.asset_id)

        if not selected_assets:
            self.report({'ERROR'}, "No assets to import")
            return {'CANCELLED'}

        if len(selected_assets) > 20:
            self.report({'ERROR'}, "Too many assets selected (max 20)")
            return {'CANCELLED'}

        # Batch import usando modal operators
        self.report({'INFO'}, f"Batch import of {len(selected_assets)} assets using stable modal import")

        imported_count = 0
        failed_count = 0

        # Importa uno alla volta usando modal operator (più sicuro)
        for i, asset_id in enumerate(selected_assets[:5]):  # Limita a 5 per evitare sovraccarico
            try:
                print(f"OpenShelf: Batch import {i+1}/{len(selected_assets[:5])}: {asset_id}")

                # Usa modal import per ogni asset
                result = bpy.ops.openshelf.modal_import_asset(asset_id=asset_id)

                if result == {'FINISHED'}:
                    imported_count += 1
                    # Piccola pausa tra import per stabilità
                    time.sleep(0.5)
                else:
                    failed_count += 1

            except Exception as e:
                print(f"OpenShelf: Batch import error for {asset_id}: {e}")
                failed_count += 1
                continue

        # Raggruppa oggetti importati se richiesto
        if imported_count > 1 and self.import_spacing > 0:
            self._arrange_imported_objects(context, self.import_spacing)

        # Report finale
        total_attempted = len(selected_assets[:5])
        self.report({'INFO'}, f"Batch import completed: {imported_count} success, {failed_count} failed of {total_attempted} total")

        return {'FINISHED'}

    def _arrange_imported_objects(self, context, spacing):
        """Arrangia oggetti importati in griglia"""
        try:
            # Trova oggetti recentemente importati (con metadati OpenShelf)
            imported_objects = []
            for obj in context.scene.objects:
                if obj.get('openshelf_id'):
                    imported_objects.append(obj)

            if len(imported_objects) <= 1:
                return

            # Arrangia in griglia
            import math
            cols = math.ceil(math.sqrt(len(imported_objects)))

            for i, obj in enumerate(imported_objects[-5:]):  # Ultimi 5 importati
                row = i // cols
                col = i % cols
                obj.location = (col * spacing, row * spacing, 0)

            print(f"OpenShelf: Arranged {len(imported_objects[-5:])} objects in grid")

        except Exception as e:
            print(f"OpenShelf: Error arranging objects: {e}")

class OPENSHELF_OT_preview_asset(Operator):
    """Anteprima asset senza importarlo"""
    bl_idname = "openshelf.preview_asset"
    bl_label = "Preview Asset"
    bl_description = "Preview asset without importing"
    bl_options = {'REGISTER'}

    asset_id: StringProperty(
        name="Asset ID",
        description="ID of the asset to preview",
        default=""
    )

    def execute(self, context):
        scene = context.scene

        if not self.asset_id:
            self.report({'ERROR'}, "No asset ID specified")
            return {'CANCELLED'}

        # Trova asset nella cache
        asset_data = None
        for cached_asset in scene.openshelf_assets_cache:
            if cached_asset.asset_id == self.asset_id:
                asset_data = cached_asset
                break

        if not asset_data:
            self.report({'ERROR'}, f"Asset '{self.asset_id}' not found in cache")
            return {'CANCELLED'}

        # Mostra informazioni asset in popup esteso
        def draw_preview_popup(self, context):
            layout = self.layout

            # Header
            layout.label(text=f"Asset Preview", icon='INFO')
            layout.separator()

            # Informazioni base
            box = layout.box()
            box.label(text="Basic Information", icon='OBJECT_DATA')

            col = box.column(align=True)
            col.scale_y = 0.8
            col.label(text=f"Name: {asset_data.name}")
            col.label(text=f"ID: {asset_data.asset_id}")
            col.label(text=f"Type: {asset_data.object_type}")
            col.label(text=f"Repository: {asset_data.repository}")
            col.label(text=f"Inventory: {asset_data.inventory_number}")

            # Dettagli culturali
            if asset_data.materials or asset_data.chronology:
                box = layout.box()
                box.label(text="Cultural Details", icon='BOOKMARKS')

                col = box.column(align=True)
                col.scale_y = 0.8
                if asset_data.materials:
                    col.label(text=f"Materials: {asset_data.materials}")
                if asset_data.chronology:
                    col.label(text=f"Period: {asset_data.chronology}")

            # Qualità e dimensioni
            box = layout.box()
            box.label(text="Technical Info", icon='SETTINGS')

            col = box.column(align=True)
            col.scale_y = 0.8
            col.label(text=f"Quality Score: {asset_data.quality_score}%")

            # Check model URLs
            has_models = False
            try:
                if asset_data.model_urls:
                    urls = json.loads(asset_data.model_urls)
                    has_models = len(urls) > 0 if isinstance(urls, list) else bool(urls)
                    col.label(text=f"3D Models: {len(urls) if isinstance(urls, list) else 1}")
            except:
                pass

            if not has_models:
                col.label(text="3D Models: None available", icon='ERROR')

            # Descrizione (se presente)
            if asset_data.description and asset_data.description.strip():
                box = layout.box()
                box.label(text="Description", icon='TEXT')

                # Limita descrizione per popup
                desc = asset_data.description.strip()
                if len(desc) > 150:
                    desc = desc[:150] + "..."

                # Spezza in righe
                words = desc.split()
                current_line = ""
                col = box.column(align=True)
                col.scale_y = 0.8

                for word in words:
                    if len(current_line + " " + word) <= 40:
                        current_line += " " + word if current_line else word
                    else:
                        if current_line:
                            col.label(text=current_line)
                        current_line = word

                if current_line:
                    col.label(text=current_line)

        context.window_manager.popup_menu(
            draw_preview_popup,
            title=f"Preview: {asset_data.name[:30]}...",
            icon='INFO'
        )

        return {'FINISHED'}

class OPENSHELF_OT_validate_asset(Operator):
    """Valida un asset prima dell'import"""
    bl_idname = "openshelf.validate_asset"
    bl_label = "Validate Asset"
    bl_description = "Validate asset files before import"
    bl_options = {'REGISTER'}

    asset_id: StringProperty(
        name="Asset ID",
        description="ID of the asset to validate",
        default=""
    )

    def execute(self, context):
        scene = context.scene

        if not self.asset_id:
            self.report({'ERROR'}, "No asset ID specified")
            return {'CANCELLED'}

        # Trova asset nella cache
        asset_data = None
        for cached_asset in scene.openshelf_assets_cache:
            if cached_asset.asset_id == self.asset_id:
                asset_data = cached_asset
                break

        if not asset_data:
            self.report({'ERROR'}, f"Asset '{self.asset_id}' not found in cache")
            return {'CANCELLED'}

        try:
            validation_results = []

            # 1. VALIDA URL MODELLI
            try:
                model_urls = json.loads(asset_data.model_urls) if asset_data.model_urls else []
            except:
                model_urls = [asset_data.model_urls] if asset_data.model_urls else []

            if not model_urls:
                validation_results.append("❌ No model URLs available")
                model_files_info = []
            else:
                validation_results.append(f"✅ Found {len(model_urls)} model URL(s)")

                # 2. CONTROLLA DIMENSIONI FILE (NUOVO!)
                from ..utils.download_manager import get_download_manager
                dm = get_download_manager()

                model_files_info = []
                total_size = 0

                for i, url in enumerate(model_urls):
                    if not url or not url.strip():
                        validation_results.append(f"❌ Model {i+1}: Empty URL")
                        continue

                    url = url.strip()
                    validation_results.append(f"🔍 Checking model {i+1}: {url.split('/')[-1]}")

                    # Ottieni info file senza scaricarlo
                    file_info = dm.get_file_info_quick(url)
                    model_files_info.append(file_info)

                    if file_info["available"]:
                        size_human = file_info["size_human"]
                        total_size += file_info["size_bytes"]
                        validation_results.append(f"✅ Model {i+1}: {size_human} - Available")

                        # Avvisi per dimensioni
                        if file_info["size_bytes"] > 50 * 1024 * 1024:  # > 50MB
                            validation_results.append(f"⚠️ Model {i+1}: Large file ({size_human})")
                        elif file_info["size_bytes"] == 0:
                            validation_results.append(f"❓ Model {i+1}: Size unknown")

                    else:
                        validation_results.append(f"❌ Model {i+1}: Not accessible - {file_info.get('error', 'Unknown error')}")

                # Riepilogo dimensioni
                if total_size > 0:
                    total_human = dm.format_file_size(total_size)
                    validation_results.append(f"📊 Total download size: {total_human}")

                    # Stima tempo download (ipotizzando 1MB/s)
                    if total_size > 1024 * 1024:  # > 1MB
                        time_seconds = total_size / (1024 * 1024)  # Stima pessimistica
                        validation_results.append(f"⏱️ Estimated download time: ~{time_seconds:.0f}s")

            # 3. VALIDA METADATI
            metadata_score = 0
            total_checks = 6

            if asset_data.name and asset_data.name.strip():
                validation_results.append("✅ Name: Present")
                metadata_score += 1
            else:
                validation_results.append("❌ Name: Missing")

            if asset_data.description and len(asset_data.description.strip()) > 10:
                validation_results.append("✅ Description: Adequate")
                metadata_score += 1
            else:
                validation_results.append("⚠️ Description: Too short or missing")

            if asset_data.object_type and asset_data.object_type.strip():
                validation_results.append("✅ Object type: Present")
                metadata_score += 1
            else:
                validation_results.append("❌ Object type: Missing")

            if asset_data.inventory_number and asset_data.inventory_number.strip():
                validation_results.append("✅ Inventory number: Present")
                metadata_score += 1
            else:
                validation_results.append("⚠️ Inventory number: Missing")

            if asset_data.materials and asset_data.materials.strip():
                validation_results.append("✅ Materials: Present")
                metadata_score += 1
            else:
                validation_results.append("⚠️ Materials: Missing")

            if asset_data.chronology and asset_data.chronology.strip():
                validation_results.append("✅ Chronology: Present")
                metadata_score += 1
            else:
                validation_results.append("⚠️ Chronology: Missing")

            # 4. RIEPILOGO FINALE
            quality_percentage = (metadata_score / total_checks) * 100

            if asset_data.quality_score > 0:
                validation_results.append(f"📊 Repository quality score: {asset_data.quality_score}%")

            validation_results.append(f"📈 Metadata completeness: {quality_percentage:.0f}%")

            # 5. MOSTRA RISULTATI IN POPUP MIGLIORATO
            def draw_validation_popup(self, context):
                layout = self.layout
                layout.label(text=f"Validation: {asset_data.name[:30]}...", icon='CHECKMARK')
                layout.separator()

                # Box per file info
                if model_files_info:
                    box = layout.box()
                    box.label(text="File Information", icon='FILE')
                    for i, file_info in enumerate(model_files_info):
                        row = box.row()
                        if file_info["available"]:
                            icon = 'CHECKMARK'
                            text = f"Model {i+1}: {file_info['size_human']}"
                        else:
                            icon = 'CANCEL'
                            text = f"Model {i+1}: Not available"
                        row.label(text=text, icon=icon)

                    if total_size > 0:
                        box.label(text=f"Total: {dm.format_file_size(total_size)}", icon='INFO')

                # Box per risultati validazione
                box = layout.box()
                box.label(text="Validation Results", icon='TOOL_SETTINGS')

                # Mostra primi N risultati (per evitare popup troppo lungo)
                for line in validation_results[-10:]:  # Ultimi 10 risultati più importanti
                    if line.startswith("✅"):
                        box.label(text=line[2:], icon='CHECKMARK')
                    elif line.startswith("❌"):
                        box.label(text=line[2:], icon='CANCEL')
                    elif line.startswith("⚠️"):
                        box.label(text=line[2:], icon='ERROR')
                    elif line.startswith("📊") or line.startswith("📈") or line.startswith("⏱️"):
                        box.label(text=line[2:], icon='INFO')
                    else:
                        box.label(text=line)

            context.window_manager.popup_menu(
                draw_validation_popup,
                title="Asset Validation Results",
                icon='CHECKMARK'
            )

            # 6. DETERMINA RISULTATO FINALE
            has_models = len([f for f in model_files_info if f.get("available", False)]) > 0
            has_basic_metadata = metadata_score >= 3

            if has_models and has_basic_metadata:
                if total_size > 0:
                    self.report({'INFO'}, f"✅ Validation passed - {dm.format_file_size(total_size)} to download")
                else:
                    self.report({'INFO'}, f"✅ Validation passed ({quality_percentage:.0f}% complete)")
            elif has_models:
                self.report({'WARNING'}, f"⚠️ Models available but incomplete metadata ({quality_percentage:.0f}%)")
            else:
                self.report({'ERROR'}, "❌ Validation failed - no accessible models found")

        except Exception as e:
            print(f"OpenShelf: Error validating asset: {e}")
            self.report({'ERROR'}, f"Validation error: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_cancel_import(Operator):
    """Cancella import in corso"""
    bl_idname = "openshelf.cancel_import"
    bl_label = "Cancel Import"
    bl_description = "Cancel current import operation"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        # Reset immediato dell'UI
        scene.openshelf_is_downloading = False
        scene.openshelf_download_progress = 0
        scene.openshelf_status_message = "Import cancelled"

        # Reset anche lo stato globale
        with _import_state.lock:
            _import_state.is_downloading = False
            _import_state.download_progress = 0
            _import_state.status_message = "Import cancelled"
            _import_state.completed = True
            _import_state.error_message = "Cancelled by user"

        # Force UI redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        self.report({'INFO'}, "Import cancelled")
        return {'FINISHED'}

class OPENSHELF_OT_import_asset_with_options(Operator):
    """Importa asset con dialog opzioni"""
    bl_idname = "openshelf.import_asset_with_options"
    bl_label = "Import Asset with Options"
    bl_description = "Import asset with customizable options dialog"
    bl_options = {'REGISTER', 'UNDO'}

    asset_id: StringProperty(
        name="Asset ID",
        description="ID of the asset to import",
        default=""
    )

    use_cache: BoolProperty(
        name="Use Cache",
        description="Use cached files if available",
        default=True
    )

    import_scale: IntProperty(
        name="Import Scale (%)",
        description="Scale factor for imported object",
        default=100,
        min=1,
        max=1000
    )

    auto_center: BoolProperty(
        name="Auto Center",
        description="Center object at origin",
        default=True
    )

    apply_materials: BoolProperty(
        name="Apply Materials",
        description="Apply materials to imported object",
        default=True
    )

    add_metadata: BoolProperty(
        name="Add Cultural Metadata",
        description="Add cultural metadata as custom properties",
        default=True
    )

    # Opzioni avanzate aggiuntive
    recalculate_normals: BoolProperty(
        name="Recalculate Normals",
        description="Recalculate normals after import (OBJ only)",
        default=False
    )

    merge_duplicates: BoolProperty(
        name="Merge Duplicate Vertices",
        description="Merge duplicate vertices after import",
        default=False
    )

    def draw(self, context):
        """Disegna il dialog con le opzioni"""
        layout = self.layout

        # Sezione principale
        box = layout.box()
        box.label(text="Import Options", icon='IMPORT')

        # Scala e posizionamento
        col = box.column(align=True)
        col.prop(self, "import_scale")
        col.prop(self, "auto_center")

        layout.separator()

        # Materiali e metadati
        box = layout.box()
        box.label(text="Materials & Metadata", icon='MATERIAL')

        col = box.column(align=True)
        col.prop(self, "apply_materials")
        col.prop(self, "add_metadata")

        layout.separator()

        # Opzioni avanzate
        box = layout.box()
        box.label(text="Advanced Options", icon='SETTINGS')

        col = box.column(align=True)
        col.prop(self, "use_cache")
        col.prop(self, "recalculate_normals")
        col.prop(self, "merge_duplicates")

        layout.separator()

        # Anteprima
        box = layout.box()
        box.label(text="Preview", icon='HIDE_OFF')

        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text=f"Scale: {self.import_scale}%")
        col.label(text=f"Center: {'Yes' if self.auto_center else 'No'}")
        col.label(text=f"Materials: {'Apply' if self.apply_materials else 'Skip'}")
        col.label(text=f"Metadata: {'Add' if self.add_metadata else 'Skip'}")

    def invoke(self, context, event):
        """Mostra dialog con opzioni"""
        scene = context.scene

        # Popola proprietà con valori dalle impostazioni scene
        self.import_scale = scene.openshelf_import_scale
        self.auto_center = scene.openshelf_auto_center
        self.apply_materials = scene.openshelf_apply_materials
        self.add_metadata = scene.openshelf_add_metadata

        # Mostra dialog
        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        """Esegue l'import con le opzioni selezionate usando modal operator"""
        scene = context.scene

        if not self.asset_id:
            self.report({'ERROR'}, "No asset ID specified")
            return {'CANCELLED'}

        # Salva le impostazioni nelle proprietà scene per la prossima volta
        scene.openshelf_import_scale = self.import_scale
        scene.openshelf_auto_center = self.auto_center
        scene.openshelf_apply_materials = self.apply_materials
        scene.openshelf_add_metadata = self.add_metadata

        # Esegue l'import usando il modal operator sicuro
        try:
            return bpy.ops.openshelf.modal_import_asset(
                asset_id=self.asset_id,
                import_scale=self.import_scale / 100.0,  # Converti percentuale
                auto_center=self.auto_center,
                apply_materials=self.apply_materials,
                add_metadata=self.add_metadata
            )
        except Exception as e:
            self.report({'ERROR'}, f"Import with options failed: {str(e)}")
            return {'CANCELLED'}

# Lista operatori da registrare
operators = [
    OPENSHELF_OT_import_asset,
    OPENSHELF_OT_import_asset_old_threading,  # Mantenuto solo per reference
    OPENSHELF_OT_batch_import,
    OPENSHELF_OT_preview_asset,
    OPENSHELF_OT_validate_asset,
    OPENSHELF_OT_cancel_import,
    OPENSHELF_OT_import_asset_with_options,
]

def register():
    """Registra gli operatori di import"""
    for op in operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra gli operatori di import"""
    for op in reversed(operators):
        bpy.utils.unregister_class(op)
