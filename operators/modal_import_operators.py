"""
OpenShelf Modal Import Operators - VERSIONE CORRETTA
Operatore modal per import stabile con timeout esteso e progress feedback
FIX: Timeout esteso, progress callback attivo, migliore gestione errori
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, FloatProperty
import os
import json
import time
from ..utils.download_manager import get_download_manager
from ..utils.obj_loader import OBJLoader

class OPENSHELF_OT_modal_import_asset(Operator):
    """Import asset usando operatore modal sicuro (no freeze) - VERSIONE CORRETTA"""
    bl_idname = "openshelf.modal_import_asset"
    bl_label = "Import Asset (Modal)"
    bl_description = "Download and import selected 3D asset using stable modal operator"
    bl_options = {'REGISTER', 'UNDO'}

    asset_id: StringProperty(
        name="Asset ID",
        description="ID of the asset to import",
        default=""
    )

    # Impostazioni import (ereditate dalle scene properties)
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

    # Variabili di stato interne (private)
    _timer = None
    _download_manager = None
    _current_step = 'INIT'
    _progress = 0
    _asset_data = None
    _model_path = None
    _error_message = None
    _start_time = 0
    _timeout = 180  # FIX: Aumentato a 3 minuti (era 60)
    _step_start_time = 0  # FIX: Track tempo per ogni step

    def invoke(self, context, event):
        """Inizializza e avvia l'operatore modal"""
        scene = context.scene

        # Verifica asset ID
        if not self.asset_id:
            self.report({'ERROR'}, "No asset ID specified")
            return {'CANCELLED'}

        # Trova asset nella cache scene
        self._asset_data = None
        for cached_asset in scene.openshelf_assets_cache:
            if cached_asset.asset_id == self.asset_id:
                self._asset_data = cached_asset
                break

        if not self._asset_data:
            self.report({'ERROR'}, f"Asset '{self.asset_id}' not found in cache")
            return {'CANCELLED'}

        # Eredita impostazioni dalle scene properties
        self.import_scale = scene.openshelf_import_scale / 100.0
        self.auto_center = scene.openshelf_auto_center
        self.apply_materials = scene.openshelf_apply_materials
        self.add_metadata = scene.openshelf_add_metadata

        # Inizializza stato interno
        self._current_step = 'DOWNLOAD'
        self._progress = 0
        self._start_time = time.time()
        self._step_start_time = time.time()  # FIX: Track step time
        self._download_manager = get_download_manager()
        self._error_message = None

        # Imposta UI state
        scene.openshelf_is_downloading = True
        scene.openshelf_download_progress = 0
        scene.openshelf_status_message = "Starting import..."

        # Avvia timer modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        print(f"OpenShelf: Starting modal import for asset {self.asset_id}")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Gestisce il loop principale del modal operator"""
        scene = context.scene

        # Check timeout globale
        elapsed_time = time.time() - self._start_time
        if elapsed_time > self._timeout:
            print(f"OpenShelf: Global timeout after {elapsed_time:.1f}s")
            self._cleanup_and_finish(context, 'TIMEOUT')
            return {'CANCELLED'}

        # Check timeout per step (FIX: Timeout per step individuali)
        step_elapsed = time.time() - self._step_start_time
        step_timeout = 90  # 90 secondi per step
        if step_elapsed > step_timeout:
            print(f"OpenShelf: Step {self._current_step} timeout after {step_elapsed:.1f}s")
            self._error_message = f"Step {self._current_step} timed out"
            self._current_step = 'ERROR'

        # Gestione eventi
        if event.type == 'TIMER':
            return self._handle_timer_step(context)
        elif event.type in {'ESC'}:
            self._cleanup_and_finish(context, 'CANCELLED')
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def _handle_timer_step(self, context):
        """Gestisce ogni step del processo di import"""
        try:
            if self._current_step == 'DOWNLOAD':
                return self._step_download(context)
            elif self._current_step == 'EXTRACT':
                return self._step_extract(context)
            elif self._current_step == 'IMPORT':
                return self._step_import(context)
            elif self._current_step == 'COMPLETE':
                return self._step_complete(context)
            elif self._current_step == 'ERROR':
                return self._step_error(context)

        except Exception as e:
            print(f"OpenShelf: Modal step error: {e}")
            import traceback
            traceback.print_exc()
            self._error_message = str(e)
            self._current_step = 'ERROR'
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def _step_download(self, context):
        """Step 1: Download del file model - CON PROGRESS CALLBACK E FORCE UI UPDATE"""
        scene = context.scene

        try:
            # Parse model URLs
            model_urls = self._parse_model_urls()
            if not model_urls:
                self._error_message = "No valid 3D model URLs found"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            scene.openshelf_status_message = "Step 1/3: Downloading model files..."
            scene.openshelf_download_progress = 5
            self._force_ui_update(context)  # FIX: Force immediate UI update

            # FIX: Progress callback attivo con force UI update
            def progress_callback(downloaded, total):
                if total > 0:
                    progress = 5 + int((downloaded / total) * 50)  # 5-55% per download
                    scene.openshelf_download_progress = progress

                    # Update status con dimensioni
                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    scene.openshelf_status_message = f"Step 1/3: Downloading {downloaded_mb:.1f}/{total_mb:.1f} MB"
                else:
                    # Fallback per download senza dimensione nota
                    progress = min(55, scene.openshelf_download_progress + 1)
                    scene.openshelf_download_progress = progress
                    scene.openshelf_status_message = f"Step 1/3: Downloading {downloaded / 1024:.0f} KB"

                # FIX: Force UI update durante download
                self._force_ui_update(context)

            # Prova download da ogni URL
            archive_path = None
            for i, url in enumerate(model_urls):
                print(f"OpenShelf: Trying download {i+1}/{len(model_urls)}: {url}")

                try:
                    archive_path = self._download_manager.download_file(
                        url,
                        use_cache=True,
                        progress_callback=progress_callback  # FIX: Callback attivo
                    )

                    if archive_path and os.path.exists(archive_path):
                        print(f"OpenShelf: Download successful: {archive_path}")
                        break
                except Exception as e:
                    print(f"OpenShelf: Download failed for {url}: {e}")
                    continue

            if not archive_path:
                self._error_message = "Failed to download asset from any URL"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            # Successo - passa al prossimo step
            self._model_path = archive_path
            scene.openshelf_download_progress = 60
            scene.openshelf_status_message = "Step 1/3: Download complete"
            self._force_ui_update(context)  # FIX: Force UI update
            self._current_step = 'EXTRACT'
            self._step_start_time = time.time()  # FIX: Reset step timer
            print(f"OpenShelf: Download step completed, moving to extract")

        except Exception as e:
            print(f"OpenShelf: Download step error: {e}")
            self._error_message = f"Download error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _step_extract(self, context):
        """Step 2: Estrazione archivio - CON STEP MESSAGES E UI UPDATE"""
        scene = context.scene

        try:
            scene.openshelf_status_message = "Step 2/3: Extracting archive..."
            scene.openshelf_download_progress = 70
            self._force_ui_update(context)  # FIX: Force UI update
            print(f"OpenShelf: Starting extraction of {self._model_path}")

            # Estrai archivio con progress callback
            def extract_progress_callback(extracted, total):
                if total > 0:
                    progress = 70 + int((extracted / total) * 15)  # 70-85%
                    scene.openshelf_download_progress = progress
                    scene.openshelf_status_message = f"Step 2/3: Extracting {extracted}/{total} files"
                    self._force_ui_update(context)  # FIX: Force UI update

            extract_dir = self._download_manager.extract_archive(
                self._model_path,
                progress_callback=extract_progress_callback
            )

            if not extract_dir or not os.path.exists(extract_dir):
                self._error_message = "Failed to extract archive"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            print(f"OpenShelf: Archive extracted to: {extract_dir}")

            # Trova file 3D supportati
            supported_extensions = ['.obj', '.gltf', '.glb']
            found_files = self._download_manager.find_files_by_extension(
                extract_dir, supported_extensions
            )

            print(f"OpenShelf: Found {len(found_files)} supported files: {found_files}")

            if not found_files:
                # FIX: Lista tutti i file trovati per debug
                try:
                    all_files = []
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            all_files.append(os.path.join(root, file))
                    print(f"OpenShelf: All files in archive: {all_files}")
                except:
                    pass

                self._error_message = "No supported 3D files found in archive"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            # Successo - usa il primo file trovato
            self._model_path = found_files[0]
            print(f"OpenShelf: Selected 3D file: {self._model_path}")
            scene.openshelf_download_progress = 90
            scene.openshelf_status_message = "Step 2/3: Extraction complete"
            self._force_ui_update(context)  # FIX: Force UI update
            self._current_step = 'IMPORT'
            self._step_start_time = time.time()  # FIX: Reset step timer

        except Exception as e:
            print(f"OpenShelf: Extract step error: {e}")
            self._error_message = f"Extract error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _step_import(self, context):
        """Step 3: Import 3D model nel main thread (sicuro) - CON STEP MESSAGES"""
        scene = context.scene

        try:
            scene.openshelf_status_message = "Step 3/3: Importing 3D model..."
            scene.openshelf_download_progress = 95
            self._force_ui_update(context)  # FIX: Force UI update

            # Determina tipo file
            file_ext = os.path.splitext(self._model_path)[1].lower()
            print(f"OpenShelf: Importing {file_ext} file: {self._model_path}")

            # Verifica che il file esiste
            if not os.path.exists(self._model_path):
                self._error_message = f"Model file not found: {self._model_path}"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            # Verifica dimensione file
            file_size = os.path.getsize(self._model_path)
            print(f"OpenShelf: Model file size: {file_size} bytes")

            if file_size == 0:
                self._error_message = "Model file is empty"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            # Prepara impostazioni import
            import_settings = {
                'import_scale': self.import_scale,
                'auto_center': self.auto_center,
                'apply_materials': self.apply_materials,
                'add_metadata': self.add_metadata
            }

            print(f"OpenShelf: Import settings: {import_settings}")

            # Import con il loader appropriato
            imported_obj = None

            if file_ext == '.obj':
                # Import OBJ sicuro
                imported_obj = self._safe_obj_import(context, import_settings)

            elif file_ext in ['.gltf', '.glb']:
                # Import GLTF/GLB se disponibile
                try:
                    from ..utils.gltf_loader import GLTFLoader
                    imported_obj = GLTFLoader.import_gltf(self._model_path, **import_settings)
                except ImportError:
                    self._error_message = "GLTF loader not available"
                    self._current_step = 'ERROR'
                    return {'RUNNING_MODAL'}

            else:
                self._error_message = f"Unsupported file format: {file_ext}"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            # Verifica successo import
            if imported_obj:
                print(f"OpenShelf: Import successful: {imported_obj.name}")

                # Applica metadati culturali se richiesto
                if self.add_metadata:
                    self._apply_cultural_metadata(imported_obj)

                # Seleziona oggetto importato
                try:
                    context.view_layer.objects.active = imported_obj
                    imported_obj.select_set(True)
                except Exception as e:
                    print(f"OpenShelf: Warning - could not select imported object: {e}")

                # Successo!
                self._current_step = 'COMPLETE'
                scene.openshelf_download_progress = 100
                scene.openshelf_status_message = f"Step 3/3: Successfully imported {imported_obj.name}"
                self._force_ui_update(context)  # FIX: Force final UI update

            else:
                self._error_message = "Import returned no object"
                self._current_step = 'ERROR'

        except Exception as e:
            print(f"OpenShelf: Import step error: {e}")
            import traceback
            traceback.print_exc()
            self._error_message = f"Import error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _force_ui_update(self, context):
        """Force immediate UI update - FIX PER PROGRESS BAR"""
        try:
            # Force redraw di tutte le aree 3D view
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            # Force update del window manager
            context.window_manager.update_tag()

            # Process eventi pending (questo forza l'aggiornamento immediato)
            bpy.app.timers.register(lambda: None, first_interval=0.001)

        except Exception as e:
            print(f"OpenShelf: Error forcing UI update: {e}")

    def _safe_obj_import(self, context, import_settings):
        """Import OBJ sicuro nel main thread - FIX ORIENTAMENTO MODELLI"""
        try:
            # Salva stato selezione corrente
            original_selection = []
            original_active = None

            try:
                original_selection = list(context.selected_objects)
                original_active = context.view_layer.objects.active
            except:
                print("OpenShelf: Could not save selection state")

            # Deseleziona tutto
            bpy.ops.object.select_all(action='DESELECT')

            print(f"OpenShelf: Importing OBJ: {self._model_path}")

            # FIX: Parametri corretti per orientamento (testare diverse combinazioni)
            import_params = {
                'filepath': self._model_path,
                'use_split_objects': True,
                'use_split_groups': False,
                # FIX ORIENTAMENTO: Prova questi parametri per evitare capovolgimento
                'forward_axis': 'NEGATIVE_Y',  # Cambiato da NEGATIVE_Z
                'up_axis': 'Z',                # Cambiato da Y
            }

            # Esegui import OBJ
            print(f"OpenShelf: Calling bpy.ops.wm.obj_import with {list(import_params.keys())}")
            result = bpy.ops.wm.obj_import(**import_params)
            print(f"OpenShelf: OBJ import result: {result}")

            # Trova oggetti importati
            new_objects = []
            try:
                new_objects = [obj for obj in context.selected_objects
                              if obj not in original_selection]
                print(f"OpenShelf: Found {len(new_objects)} new objects after import")
            except Exception as e:
                print(f"OpenShelf: Error finding imported objects: {e}")
                # Fallback: trova oggetti con nomi che contengono il nome del file
                base_name = os.path.splitext(os.path.basename(self._model_path))[0]
                new_objects = [obj for obj in bpy.data.objects if base_name in obj.name]
                print(f"OpenShelf: Fallback found {len(new_objects)} objects with base name")

            if new_objects:
                main_object = new_objects[0]
                print(f"OpenShelf: Main imported object: {main_object.name}")

                # Applica post-processing
                if import_settings['auto_center']:
                    self._center_object(main_object)

                if import_settings['import_scale'] != 1.0:
                    scale = import_settings['import_scale']
                    main_object.scale = (scale, scale, scale)
                    print(f"OpenShelf: Applied scale {scale} to {main_object.name}")

                return main_object

            else:
                print("OpenShelf: No objects found after import")
                return None

        except Exception as e:
            print(f"OpenShelf: OBJ import error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _center_object(self, obj):
        """Centra oggetto all'origine"""
        try:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
            obj.location = (0, 0, 0)
            print(f"OpenShelf: Centered object {obj.name}")
        except Exception as e:
            print(f"OpenShelf: Error centering object: {e}")

    def _apply_cultural_metadata(self, obj):
        """Applica metadati culturali all'oggetto"""
        try:
            if not obj or not self._asset_data:
                return

            prefix = "openshelf_"

            # Metadati base
            metadata = {
                "id": self._asset_data.asset_id,
                "name": self._asset_data.name,
                "description": self._asset_data.description,
                "repository": self._asset_data.repository,
                "object_type": self._asset_data.object_type,
                "inventory_number": self._asset_data.inventory_number,
                "materials": self._asset_data.materials,
                "chronology": self._asset_data.chronology,
                "quality_score": self._asset_data.quality_score,
                "import_timestamp": str(int(time.time()))
            }

            # Applica come custom properties
            for key, value in metadata.items():
                if value and str(value).strip():
                    obj[f"{prefix}{key}"] = str(value)

            print(f"OpenShelf: Applied cultural metadata to {obj.name}")

        except Exception as e:
            print(f"OpenShelf: Error applying metadata: {e}")

    def _parse_model_urls(self):
        """Parse URLs dei modelli 3D"""
        if not self._asset_data or not self._asset_data.model_urls:
            return []

        try:
            # Prova parsing JSON
            model_urls = json.loads(self._asset_data.model_urls)
            if isinstance(model_urls, list):
                return [str(url).strip() for url in model_urls if url and str(url).strip()]
            elif isinstance(model_urls, str) and model_urls.strip():
                return [model_urls.strip()]
        except json.JSONDecodeError:
            # Fallback: tratta come stringa singola
            if self._asset_data.model_urls.strip():
                return [self._asset_data.model_urls.strip()]

        return []

    def _step_complete(self, context):
        """Step finale - successo"""
        scene = context.scene
        asset_name = self._asset_data.name if self._asset_data else "asset"
        scene.openshelf_status_message = f"Successfully imported {asset_name}"
        self._cleanup_and_finish(context, 'FINISHED')
        return {'FINISHED'}

    def _step_error(self, context):
        """Step finale - errore"""
        error_msg = self._error_message or "Import failed"
        self._cleanup_and_finish(context, 'ERROR', error_msg)
        return {'CANCELLED'}

    def _cleanup_and_finish(self, context, result_type, message=None):
        """Cleanup finale e aggiornamento UI"""
        scene = context.scene

        # Remove timer
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None

        # Update UI state
        scene.openshelf_is_downloading = False

        if result_type == 'FINISHED':
            # Successo - mantieni progress al 100%
            scene.openshelf_download_progress = 100
            if message:
                scene.openshelf_status_message = message
            self.report({'INFO'}, scene.openshelf_status_message)

        elif result_type == 'TIMEOUT':
            scene.openshelf_download_progress = 0
            scene.openshelf_status_message = "Import timed out"
            self.report({'ERROR'}, "Import timed out - try again or check network connection")

        elif result_type == 'CANCELLED':
            scene.openshelf_download_progress = 0
            scene.openshelf_status_message = "Import cancelled"
            self.report({'INFO'}, "Import cancelled by user")

        else:  # ERROR
            scene.openshelf_download_progress = 0
            scene.openshelf_status_message = message or "Import failed"
            self.report({'ERROR'}, scene.openshelf_status_message)

        # Force UI redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        # FIX: Logging più dettagliato per debug
        total_time = time.time() - self._start_time
        print(f"OpenShelf: Modal import finished with result: {result_type} (total time: {total_time:.1f}s)")

# Lista operatori da registrare
operators = [
    OPENSHELF_OT_modal_import_asset,
]

def register():
    """Registra gli operatori modal"""
    for op in operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra gli operatori modal"""
    for op in reversed(operators):
        bpy.utils.unregister_class(op)
