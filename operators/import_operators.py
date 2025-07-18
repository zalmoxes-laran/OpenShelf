"""
OpenShelf Import Operators
Operatori per importare asset 3D dai repository
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty
import threading
import json
import os
from ..utils.download_manager import get_download_manager
from ..utils.obj_loader import OBJLoader
from ..utils.gltf_loader import GLTFLoader
from ..repositories.registry import RepositoryRegistry

class OPENSHELF_OT_import_asset(Operator):
    """Importa un asset 3D specifico"""
    bl_idname = "openshelf.import_asset"
    bl_label = "Import Asset"
    bl_description = "Download and import selected 3D asset"
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

        # Impedisci download multipli simultanei
        if scene.openshelf_is_downloading:
            self.report({'INFO'}, "Download already in progress")
            return {'CANCELLED'}

        # Avvia import in thread separato
        import_thread = threading.Thread(
            target=self._import_thread,
            args=(context, asset_data)
        )
        import_thread.daemon = True
        import_thread.start()

        # Avvia timer per controllare progresso
        bpy.app.timers.register(
            lambda: self._check_import_progress(context),
            first_interval=0.1
        )

        return {'FINISHED'}

    def _import_thread(self, context, asset_data):
        """Thread per eseguire import senza bloccare UI"""
        scene = context.scene

        try:
            # Imposta stato download
            scene.openshelf_is_downloading = True
            scene.openshelf_download_progress = 0
            scene.openshelf_status_message = "Downloading asset..."

            # Ottieni repository per informazioni download
            repository = RepositoryRegistry.get_repository(asset_data.repository)
            if not repository:
                scene.openshelf_status_message = f"Repository '{asset_data.repository}' not available"
                return

            # Parsa URLs modelli
            try:
                model_urls = json.loads(asset_data.model_urls) if asset_data.model_urls else []
            except:
                model_urls = [asset_data.model_urls] if asset_data.model_urls else []

            if not model_urls:
                scene.openshelf_status_message = "No 3D model URLs available"
                return

            # Scarica primo modello disponibile
            download_manager = get_download_manager()
            archive_path = None

            for model_url in model_urls:
                scene.openshelf_status_message = f"Downloading from {model_url}..."

                # Callback per progresso download
                def progress_callback(downloaded, total):
                    if total > 0:
                        progress = int((downloaded / total) * 50)  # 50% per download
                        scene.openshelf_download_progress = progress

                archive_path = download_manager.download_file(
                    model_url,
                    use_cache=self.use_cache,
                    progress_callback=progress_callback
                )

                if archive_path:
                    break

            if not archive_path:
                scene.openshelf_status_message = "Failed to download asset"
                return

            # Estrai archivio
            scene.openshelf_status_message = "Extracting archive..."
            scene.openshelf_download_progress = 60

            def extract_progress_callback(extracted, total):
                if total > 0:
                    progress = 60 + int((extracted / total) * 20)  # 20% per estrazione
                    scene.openshelf_download_progress = progress

            extract_dir = download_manager.extract_archive(
                archive_path,
                progress_callback=extract_progress_callback
            )

            if not extract_dir:
                scene.openshelf_status_message = "Failed to extract archive"
                return

            # Trova file 3D supportati
            scene.openshelf_status_message = "Finding 3D files..."
            scene.openshelf_download_progress = 85

            supported_extensions = ['.obj', '.gltf', '.glb']
            found_files = download_manager.find_files_by_extension(extract_dir, supported_extensions)

            if not found_files:
                scene.openshelf_status_message = "No supported 3D files found"
                return

            # Importa primo file trovato
            model_path = found_files[0]
            file_ext = os.path.splitext(model_path)[1].lower()

            scene.openshelf_status_message = f"Importing {file_ext.upper()} model..."
            scene.openshelf_download_progress = 90

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
                'model_urls': model_urls,
                'thumbnail_url': asset_data.thumbnail_url,
                'metadata': {
                    'import_scale': self.import_scale,
                    'auto_center': self.auto_center,
                    'apply_materials': self.apply_materials,
                    'add_metadata': self.add_metadata
                }
            }

            # Importa con loader appropriato
            imported_obj = None

            if file_ext == '.obj':
                # Usa OBJLoader con parametri personalizzati
                import_settings = {
                    'scale_factor': self.import_scale,
                    'auto_center': self.auto_center,
                    'auto_materials': self.apply_materials,
                    'recalculate_normals': True
                }

                imported_obj = OBJLoader.import_obj(model_path, **import_settings)

                if imported_obj and self.add_metadata:
                    OBJLoader.apply_cultural_metadata(imported_obj, asset_dict)

            elif file_ext in ['.gltf', '.glb']:
                # Usa GLTFLoader con parametri personalizzati
                import_settings = {
                    'scale_factor': self.import_scale,
                    'auto_center': self.auto_center,
                    'group_objects': True,
                    'group_name': f"{asset_data.repository}_Import"
                }

                imported_obj = GLTFLoader.import_gltf(model_path, **import_settings)

                if imported_obj and self.add_metadata:
                    # Per GLTF, ottieni tutti gli oggetti importati
                    all_objects = [obj for obj in bpy.context.scene.objects if obj.get('openshelf_import_batch')]
                    GLTFLoader.apply_cultural_metadata(imported_obj, all_objects, asset_dict)

            # Finalizza import
            if imported_obj:
                scene.openshelf_download_progress = 100
                scene.openshelf_status_message = f"Successfully imported {asset_data.name}"

                # Seleziona oggetto importato
                bpy.context.view_layer.objects.active = imported_obj
                imported_obj.select_set(True)

                print(f"OpenShelf: Successfully imported {asset_data.name}")

            else:
                scene.openshelf_status_message = "Failed to import 3D model"

        except Exception as e:
            print(f"OpenShelf: Import error: {e}")
            scene.openshelf_status_message = f"Import error: {str(e)}"

        finally:
            scene.openshelf_is_downloading = False
            scene.openshelf_download_progress = 0

    def _check_import_progress(self, context):
        """Controlla progresso import (chiamato da timer)"""
        scene = context.scene

        # Forza aggiornamento UI
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        # Continua timer solo se download in corso
        return 0.1 if scene.openshelf_is_downloading else None

    def invoke(self, context, event):
        # Popola proprietà con valori dalle preferenze scene
        scene = context.scene
        self.import_scale = scene.openshelf_import_scale / 100.0
        self.auto_center = scene.openshelf_auto_center
        self.apply_materials = scene.openshelf_apply_materials
        self.add_metadata = scene.openshelf_add_metadata

        return self.execute(context)

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

        # Avvia batch import
        batch_thread = threading.Thread(
            target=self._batch_import_thread,
            args=(context, selected_assets)
        )
        batch_thread.daemon = True
        batch_thread.start()

        self.report({'INFO'}, f"Starting batch import of {len(selected_assets)} assets")

        return {'FINISHED'}

    def _batch_import_thread(self, context, asset_ids):
        """Thread per batch import"""
        scene = context.scene

        try:
            scene.openshelf_is_downloading = True
            scene.openshelf_status_message = "Batch importing assets..."

            imported_objects = []

            for i, asset_id in enumerate(asset_ids):
                try:
                    # Aggiorna progresso
                    progress = int((i / len(asset_ids)) * 100)
                    scene.openshelf_download_progress = progress
                    scene.openshelf_status_message = f"Importing asset {i+1}/{len(asset_ids)}"

                    # Simula import (qui chiameresti l'import vero)
                    # Per ora solo una pausa
                    import time
                    time.sleep(1)

                    # Calcola posizione per spaziatura
                    x_offset = (i % 5) * self.import_spacing
                    y_offset = (i // 5) * self.import_spacing

                    # TODO: Implementare import vero con posizionamento

                except Exception as e:
                    print(f"OpenShelf: Error importing asset {asset_id}: {e}")
                    continue

            scene.openshelf_download_progress = 100
            scene.openshelf_status_message = f"Batch import completed ({len(imported_objects)} objects)"

        except Exception as e:
            print(f"OpenShelf: Batch import error: {e}")
            scene.openshelf_status_message = f"Batch import error: {str(e)}"

        finally:
            scene.openshelf_is_downloading = False
            scene.openshelf_download_progress = 0

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

        # Mostra informazioni asset
        info_text = f"""
Asset: {asset_data.name}
Type: {asset_data.object_type}
Repository: {asset_data.repository}
Inventory: {asset_data.inventory_number}
Materials: {asset_data.materials}
Chronology: {asset_data.chronology}
Quality Score: {asset_data.quality_score}
Description: {asset_data.description}
        """

        # Mostra popup con informazioni
        def draw_popup(self, context):
            lines = info_text.strip().split('\n')
            for line in lines:
                self.layout.label(text=line)

        context.window_manager.popup_menu(draw_popup, title="Asset Preview", icon='INFO')

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

            # Valida presenza URL modelli
            try:
                model_urls = json.loads(asset_data.model_urls) if asset_data.model_urls else []
            except:
                model_urls = [asset_data.model_urls] if asset_data.model_urls else []

            if not model_urls:
                validation_results.append("❌ No model URLs available")
            else:
                # Controlla formato degli URL/path
                from ..utils.file_utils import URLUtils
                valid_count = 0

                for i, url in enumerate(model_urls):
                    if not url or not url.strip():
                        validation_results.append(f"❌ Model URL {i+1}: Empty")
                        continue

                    url = url.strip()

                    # Accetta sia URL completi che path/ID relativi
                    if URLUtils.is_valid_url(url):
                        validation_results.append(f"✅ Model URL {i+1}: Valid HTTP URL")
                        valid_count += 1
                    elif url.startswith('/') or '.' in url or len(url) > 10:
                        # Potrebbe essere un path relativo o ID lungo
                        validation_results.append(f"⚠️ Model URL {i+1}: Relative path or ID")
                        valid_count += 1
                    else:
                        validation_results.append(f"❓ Model URL {i+1}: Unknown format: {url[:50]}")

                if valid_count == 0:
                    validation_results.append("❌ No usable model URLs found")

            # Valida metadati
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

            # Valuta qualità generale
            quality_percentage = (metadata_score / total_checks) * 100

            if asset_data.quality_score > 0:
                validation_results.append(f"📊 Quality score: {asset_data.quality_score}%")

            validation_results.append(f"📈 Metadata completeness: {quality_percentage:.0f}%")

            # Mostra risultati in popup
            validation_text = "\n".join(validation_results)

            def draw_validation_popup(self, context):
                layout = self.layout
                layout.label(text=f"Validation: {asset_data.name}")
                layout.separator()

                # Mostra risultati linea per linea
                for line in validation_results:
                    if line.startswith("✅"):
                        layout.label(text=line, icon='CHECKMARK')
                    elif line.startswith("❌"):
                        layout.label(text=line, icon='CANCEL')
                    elif line.startswith("⚠️"):
                        layout.label(text=line, icon='ERROR')
                    elif line.startswith("📊") or line.startswith("📈"):
                        layout.label(text=line, icon='INFO')
                    else:
                        layout.label(text=line)

            context.window_manager.popup_menu(
                draw_validation_popup,
                title="Asset Validation Results",
                icon='CHECKMARK'
            )

            # Determina risultato finale
            has_models = len([r for r in validation_results if "✅" in r and "URL" in r]) > 0
            has_basic_metadata = metadata_score >= 3

            if has_models and has_basic_metadata:
                self.report({'INFO'}, f"Asset validation passed ({quality_percentage:.0f}% complete)")
            elif has_models:
                self.report({'WARNING'}, f"Asset has models but incomplete metadata ({quality_percentage:.0f}%)")
            else:
                self.report({'ERROR'}, "Asset validation failed - no usable models found")

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

        if not scene.openshelf_is_downloading:
            self.report({'INFO'}, "No import in progress")
            return {'CANCELLED'}

        # Ferma download
        scene.openshelf_is_downloading = False
        scene.openshelf_download_progress = 0
        scene.openshelf_status_message = "Import cancelled"

        self.report({'INFO'}, "Import cancelled")

        return {'FINISHED'}

# Lista operatori da registrare
operators = [
    OPENSHELF_OT_import_asset,
    OPENSHELF_OT_batch_import,
    OPENSHELF_OT_preview_asset,
    OPENSHELF_OT_validate_asset,
    OPENSHELF_OT_cancel_import,
]

def register():
    """Registra gli operatori di import"""
    for op in operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra gli operatori di import"""
    for op in reversed(operators):
        bpy.utils.unregister_class(op)
