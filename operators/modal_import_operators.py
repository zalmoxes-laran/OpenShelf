"""
OpenShelf Modal Import Operators - SOLUZIONE SICURA AL FREEZE
Operatore modal per import stabile senza threading problematico
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
    """Import asset usando operatore modal sicuro (no freeze)"""
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
    _timeout = 60  # 60 secondi timeout

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

        # Check timeout
        if time.time() - self._start_time > self._timeout:
            self._cleanup_and_finish(context, 'TIMEOUT')
            return {'CANCELLED'}

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
            self._error_message = str(e)
            self._current_step = 'ERROR'
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def _step_download(self, context):
        """Step 1: Download del file model"""
        scene = context.scene

        try:
            # Parse model URLs
            model_urls = self._parse_model_urls()
            if not model_urls:
                self._error_message = "No valid 3D model URLs found"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            scene.openshelf_status_message = f"Downloading model files..."
            scene.openshelf_download_progress = 10

            # Prova download da ogni URL
            archive_path = None
            for i, url in enumerate(model_urls):
                print(f"OpenShelf: Trying download {i+1}/{len(model_urls)}: {url}")

                try:
                    archive_path = self._download_manager.download_file(
                        url,
                        use_cache=True,
                        progress_callback=None  # Semplificato per evitare problemi
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
            self._current_step = 'EXTRACT'

        except Exception as e:
            self._error_message = f"Download error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _step_extract(self, context):
        """Step 2: Estrazione archivio"""
        scene = context.scene

        try:
            scene.openshelf_status_message = "Extracting archive..."
            scene.openshelf_download_progress = 70

            # Estrai archivio
            extract_dir = self._download_manager.extract_archive(self._model_path)
            if not extract_dir or not os.path.exists(extract_dir):
                self._error_message = "Failed to extract archive"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            # Trova file 3D supportati
            supported_extensions = ['.obj', '.gltf', '.glb']
            found_files = self._download_manager.find_files_by_extension(
                extract_dir, supported_extensions
            )

            if not found_files:
                self._error_message = "No supported 3D files found in archive"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            # Successo - usa il primo file trovato
            self._model_path = found_files[0]
            print(f"OpenShelf: Found 3D file: {self._model_path}")
            scene.openshelf_download_progress = 90
            self._current_step = 'IMPORT'

        except Exception as e:
            self._error_message = f"Extract error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _step_import(self, context):
        """Step 3: Import 3D model nel main thread (sicuro)"""
        scene = context.scene

        try:
            scene.openshelf_status_message = "Importing 3D model..."
            scene.openshelf_download_progress = 95

            # Determina tipo file
            file_ext = os.path.splitext(self._model_path)[1].lower()
            print(f"OpenShelf: Importing {file_ext} file: {self._model_path}")

            # Prepara impostazioni import
            import_settings = {
                'import_scale': self.import_scale,
                'auto_center': self.auto_center,
                'apply_materials': self.apply_materials,
                'add_metadata': self.add_metadata
            }

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
                # Applica metadati culturali se richiesto
                if self.add_metadata:
                    self._apply_cultural_metadata(imported_obj)

                # Seleziona oggetto importato
                context.view_layer.objects.active = imported_obj
                imported_obj.select_set(True)

                # Successo!
                self._current_step = 'COMPLETE'
                scene.openshelf_download_progress = 100
                print(f"OpenShelf: Successfully imported {imported_obj.name}")

            else:
                self._error_message = "Failed to import 3D model"
                self._current_step = 'ERROR'

        except Exception as e:
            print(f"OpenShelf: Import error: {e}")
            import traceback
            traceback.print_exc()
            self._error_message = f"Import error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _safe_obj_import(self, context, import_settings):
        """Import OBJ sicuro nel main thread"""
        try:
            # Salva stato selezione corrente
            original_selection = list(context.selected_objects)
            original_active = context.view_layer.objects.active

            # Deseleziona tutto
            bpy.ops.object.select_all(action='DESELECT')

            print(f"OpenShelf: Importing OBJ: {self._model_path}")

            # Parametri import per Blender 4.2+
            import_params = {
                'filepath': self._model_path,

                'use_split_objects': True,
                'use_split_groups': False,
                'forward_axis': 'NEGATIVE_Z',
                'up_axis': 'Y',
            }

            # Esegui import OBJ
            result = bpy.ops.wm.obj_import(**import_params)
            print(f"OpenShelf: OBJ import result: {result}")

            # Trova oggetti importati
            new_objects = [obj for obj in context.selected_objects
                          if obj not in original_selection]

            if new_objects:
                main_object = new_objects[0]
                print(f"OpenShelf: Imported object: {main_object.name}")

                # Applica post-processing
                if import_settings['auto_center']:
                    self._center_object(main_object)

                if import_settings['import_scale'] != 1.0:
                    scale = import_settings['import_scale']
                    main_object.scale = (scale, scale, scale)

                return main_object

            else:
                print("OpenShelf: No objects found after import")
                return None

        except Exception as e:
            print(f"OpenShelf: OBJ import error: {e}")
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
            self.report({'ERROR'}, "Import timed out after 60 seconds")

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

        print(f"OpenShelf: Modal import finished with result: {result_type}")

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
