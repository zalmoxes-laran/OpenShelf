# operators/library_import_operators.py
"""
OpenShelf Library Import Operators
Import operators che usano la libreria locale invece della cache temporanea
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, FloatProperty
import threading
import json
import os
import time
from ..utils.local_library_manager import get_library_manager
from ..utils.obj_loader import OBJLoader
from ..utils.gltf_loader import GLTFLoader
from ..repositories.registry import RepositoryRegistry

class LibraryImportState:
    """Stato thread-safe per l'import dalla libreria"""
    def __init__(self):
        self.is_downloading = False
        self.download_progress = 0
        self.status_message = "Ready"
        self.pending_import_data = None
        self.error_message = None
        self.completed = False
        self.lock = threading.Lock()

# Istanza globale per lo stato
_library_import_state = LibraryImportState()

class OPENSHELF_OT_library_import_asset(Operator):
    """Importa un asset usando la libreria locale (NUOVO SISTEMA)"""
    bl_idname = "openshelf.library_import_asset"
    bl_label = "Import from Library"
    bl_description = "Import asset using local library system (recommended)"
    bl_options = {'REGISTER', 'UNDO'}

    asset_id: StringProperty(
        name="Asset ID",
        description="ID of the asset to import",
        default=""
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
        """Esegue l'import dall'asset nella libreria locale"""

        if not self.asset_id:
            self.report({'ERROR'}, "No asset ID specified")
            return {'CANCELLED'}

        print(f"OpenShelf: Starting library import for asset {self.asset_id}")

        # Ottieni asset data dal contesto
        scene = context.scene

        # Cerca l'asset nei risultati della ricerca corrente
        asset_data = None
        if hasattr(scene, 'openshelf_search_results'):
            for result in scene.openshelf_search_results:
                if result.asset_id == self.asset_id:
                    asset_data = result
                    break

        if not asset_data:
            self.report({'ERROR'}, f"Asset {self.asset_id} not found in current search results")
            return {'CANCELLED'}

        # Ottieni library manager
        library_manager = get_library_manager()

        # Controlla se è già nella libreria
        if library_manager.is_asset_downloaded(self.asset_id):
            print(f"OpenShelf: Asset {self.asset_id} found in library, importing directly")
            return self._import_from_library(context, library_manager, asset_data)
        else:
            print(f"OpenShelf: Asset {self.asset_id} not in library, downloading first")
            return self._download_and_import(context, library_manager, asset_data)

    def _import_from_library(self, context, library_manager, asset_data):
        """Importa direttamente dalla libreria locale"""
        try:
            # Ottieni il file del modello
            model_file = library_manager._get_primary_model_file(self.asset_id)

            if not model_file or not os.path.exists(model_file):
                self.report({'ERROR'}, f"Model file not found for asset {self.asset_id}")
                return {'CANCELLED'}

            print(f"OpenShelf: Importing model from library: {model_file}")

            # Ottieni metadati dalla libreria
            metadata = library_manager.get_asset_metadata(self.asset_id)

            # Esegui import
            imported_obj = self._do_import(context, model_file, asset_data, metadata)

            if imported_obj:
                self.report({'INFO'}, f"Successfully imported {asset_data.name} from library")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Import failed")
                return {'CANCELLED'}

        except Exception as e:
            print(f"OpenShelf: Library import error: {e}")
            self.report({'ERROR'}, f"Library import error: {str(e)}")
            return {'CANCELLED'}

    def _download_and_import(self, context, library_manager, asset_data):
        """Scarica nella libreria e poi importa"""

        # Inizia download in thread separato
        scene = context.scene
        scene.openshelf_is_downloading = True
        scene.openshelf_download_progress = 0
        scene.openshelf_status_message = "Starting download..."

        # Prepara parametri thread
        thread_params = {
            'asset_data': asset_data,
            'import_scale': self.import_scale,
            'auto_center': self.auto_center,
            'apply_materials': self.apply_materials,
            'add_metadata': self.add_metadata
        }

        # Avvia thread download
        download_thread = threading.Thread(
            target=self._download_to_library_thread,
            args=(thread_params,),
            daemon=True
        )
        download_thread.start()

        # Avvia timer per aggiornamento UI
        bpy.app.timers.register(self._update_library_ui_state, first_interval=0.1)

        return {'FINISHED'}

    def _download_to_library_thread(self, thread_params):
        """Thread per scaricare asset nella libreria locale"""
        try:
            asset_data = thread_params['asset_data']

            with _library_import_state.lock:
                _library_import_state.is_downloading = True
                _library_import_state.status_message = "Preparing download..."
                _library_import_state.download_progress = 5

            # Ottieni URLs
            try:
                model_urls = json.loads(asset_data.model_urls) if asset_data.model_urls else []
                if isinstance(model_urls, str):
                    model_urls = [model_urls]
            except:
                model_urls = [asset_data.model_urls] if asset_data.model_urls else []

            model_urls = [url.strip() for url in model_urls if url and url.strip()]

            if not model_urls:
                with _library_import_state.lock:
                    _library_import_state.error_message = "No valid model URLs found"
                return

            # Progress callback per il download
            def progress_callback(message):
                with _library_import_state.lock:
                    _library_import_state.status_message = message
                    # Incrementa gradualmente il progresso
                    if "Downloading" in message:
                        _library_import_state.download_progress = min(80, _library_import_state.download_progress + 5)
                    elif "Extracting" in message:
                        _library_import_state.download_progress = 85
                    elif "Organizing" in message:
                        _library_import_state.download_progress = 90
                    elif "complete" in message:
                        _library_import_state.download_progress = 95

            # Scarica nella libreria
            library_manager = get_library_manager()
            model_file = library_manager.download_asset_to_library(
                asset_data, model_urls, progress_callback
            )

            if not model_file:
                with _library_import_state.lock:
                    _library_import_state.error_message = "Failed to download asset to library"
                return

            # Prepara dati per import
            metadata = library_manager.get_asset_metadata(asset_data.asset_id)

            import_data = {
                'model_file': model_file,
                'asset_data': asset_data,
                'metadata': metadata,
                'import_settings': {
                    'import_scale': thread_params['import_scale'],
                    'auto_center': thread_params['auto_center'],
                    'apply_materials': thread_params['apply_materials'],
                    'add_metadata': thread_params['add_metadata']
                }
            }

            with _library_import_state.lock:
                _library_import_state.download_progress = 100
                _library_import_state.status_message = "Download complete, preparing import..."
                _library_import_state.pending_import_data = import_data

        except Exception as e:
            print(f"OpenShelf: Library download error: {e}")
            import traceback
            traceback.print_exc()
            with _library_import_state.lock:
                _library_import_state.error_message = f"Download error: {str(e)}"

    def _update_library_ui_state(self):
        """Aggiorna UI con stato dal thread - per libreria locale"""
        try:
            context = bpy.context
            scene = context.scene

            with _library_import_state.lock:
                # Aggiorna proprietà UI
                scene.openshelf_is_downloading = _library_import_state.is_downloading
                scene.openshelf_download_progress = _library_import_state.download_progress
                scene.openshelf_status_message = _library_import_state.status_message

                # Controlla se c'è un import da eseguire
                if _library_import_state.pending_import_data:
                    import_data = _library_import_state.pending_import_data
                    _library_import_state.pending_import_data = None

                    # Esegui import nel main thread
                    self._do_import_from_library_data(context, import_data)
                    return None

                # Controlla errori
                if _library_import_state.error_message:
                    scene.openshelf_status_message = _library_import_state.error_message
                    scene.openshelf_is_downloading = False
                    scene.openshelf_download_progress = 0
                    _library_import_state.is_downloading = False
                    return None

                # Controlla se completato
                if _library_import_state.completed:
                    scene.openshelf_is_downloading = False
                    _library_import_state.is_downloading = False
                    return None

            # Aggiorna UI
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            # Continua timer se download in corso
            return 0.1 if _library_import_state.is_downloading else None

        except Exception as e:
            print(f"OpenShelf: Library UI update error: {e}")
            return None

    def _do_import_from_library_data(self, context, import_data):
        """Esegue l'import dai dati della libreria"""
        try:
            model_file = import_data['model_file']
            asset_data = import_data['asset_data']
            metadata = import_data['metadata']
            import_settings = import_data['import_settings']

            imported_obj = self._do_import(context, model_file, asset_data, metadata, import_settings)

            if imported_obj:
                context.scene.openshelf_status_message = f"Successfully imported {asset_data.name}"
                with _library_import_state.lock:
                    _library_import_state.completed = True
            else:
                with _library_import_state.lock:
                    _library_import_state.error_message = "Import failed"

        except Exception as e:
            print(f"OpenShelf: Library import execution error: {e}")
            with _library_import_state.lock:
                _library_import_state.error_message = f"Import error: {str(e)}"

    def _do_import(self, context, model_file, asset_data, metadata=None, import_settings=None):
        """Esegue l'import del file 3D"""
        try:
            if import_settings is None:
                import_settings = {
                    'import_scale': self.import_scale,
                    'auto_center': self.auto_center,
                    'apply_materials': self.apply_materials,
                    'add_metadata': self.add_metadata
                }

            print(f"OpenShelf: Importing 3D file: {model_file}")

            file_ext = os.path.splitext(model_file)[1].lower()

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

            # Aggiungi metadati dalla libreria se disponibili
            if metadata:
                asset_dict.update(metadata)

            # Import con loader appropriato
            imported_obj = None

            if file_ext == '.obj':
                # Usa il metodo corretto per i metadati culturali
                if hasattr(OBJLoader, 'import_with_cultural_metadata'):
                    imported_obj = OBJLoader.import_with_cultural_metadata(model_file, asset_dict)
                elif hasattr(OBJLoader, 'import_obj'):
                    # Prova con istanza invece di metodo statico
                    loader = OBJLoader()
                    imported_obj = loader.import_obj(model_file, import_settings)
                elif hasattr(OBJLoader, 'load_obj'):\
                    imported_obj = OBJLoader.load_obj(model_file, import_settings)
                else:
                    # Fallback: import Blender standard
                    bpy.ops.wm.obj_import(filepath=model_file)
                    imported_obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else None

                # Se l'import è andato a buon fine, aggiungi i metadati manualmente
                if imported_obj and import_settings.get('add_metadata', True):
                    for key, value in asset_dict.items():
                        if isinstance(value, (str, int, float)):
                            imported_obj[f"openshelf_{key}"] = value
            elif file_ext in ['.gltf', '.glb']:
                imported_obj = GLTFLoader.import_gltf_with_metadata(
                    model_file, asset_dict, import_settings
                )
            else:
                raise Exception(f"Unsupported file format: {file_ext}")

            if imported_obj:
                print(f"OpenShelf: Successfully imported {asset_data.name}")

                # Seleziona oggetto importato
                try:
                    context.view_layer.objects.active = imported_obj
                    bpy.ops.object.select_all(action='DESELECT')
                    imported_obj.select_set(True)
                except:
                    pass

                return imported_obj
            else:
                raise Exception("Import returned None")

        except Exception as e:
            print(f"OpenShelf: Import error: {e}")
            return None


class OPENSHELF_OT_import_from_library_only(Operator):
    """Importa un asset SOLO se già presente nella libreria locale"""
    bl_idname = "openshelf.import_from_library_only"
    bl_label = "Import from Library Only"
    bl_description = "Import asset only if already present in local library"
    bl_options = {'REGISTER', 'UNDO'}

    asset_id: StringProperty(
        name="Asset ID",
        description="ID of the asset to import",
        default=""
    )

    import_scale: FloatProperty(
        name="Import Scale",
        default=1.0,
        min=0.01,
        max=100.0
    )

    auto_center: BoolProperty(
        name="Auto Center",
        default=True
    )

    apply_materials: BoolProperty(
        name="Apply Materials",
        default=True
    )

    add_metadata: BoolProperty(
        name="Add Metadata",
        default=True
    )

    def execute(self, context):
        """Importa solo se presente nella libreria"""

        library_manager = get_library_manager()

        if not library_manager.is_asset_downloaded(self.asset_id):
            self.report({'WARNING'}, f"Asset {self.asset_id} not found in local library")
            return {'CANCELLED'}

        # Usa l'operatore principale ma in modalità "library only"
        return bpy.ops.openshelf.library_import_asset(
            asset_id=self.asset_id,
            import_scale=self.import_scale,
            auto_center=self.auto_center,
            apply_materials=self.apply_materials,
            add_metadata=self.add_metadata
        )


# Lista classi da registrare
classes = [
    OPENSHELF_OT_library_import_asset,
    OPENSHELF_OT_import_from_library_only,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
