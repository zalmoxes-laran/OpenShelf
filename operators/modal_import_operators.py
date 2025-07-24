"""
OpenShelf Modal Import Operators - FIX PROGRESS BAR
Operatore modal per import stabile con progress bar più fluida e responsive
FIX: Progress bar che avanza proporzionalmente al tempo e migliore feedback
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
    """Import asset usando operatore modal sicuro - FIX PROGRESS BAR"""
    bl_idname = "openshelf.modal_import_asset"
    bl_label = "Import Asset (Modal)"
    bl_description = "Download and import selected 3D asset with smooth progress feedback"
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

    # Variabili di stato interne
    _timer = None
    _download_manager = None
    _current_step = 'INIT'
    _progress = 0
    _asset_data = None
    _model_path = None
    _error_message = None
    _start_time = 0
    _timeout = 180
    _step_start_time = 0

    # FIX: Nuove variabili per progress fluido
    _last_progress_update = 0
    _smooth_progress_target = 0
    _smooth_progress_current = 0
    _estimated_total_time = 60  # Stima iniziale: 60 secondi

    def invoke(self, context, event):
        """Inizializza e avvia l'operatore modal"""
        scene = context.scene

        # Verifica asset ID
        if not self.asset_id:
            self.report({'ERROR'}, "No asset ID specified")
            return {'CANCELLED'}

        # FIX: Trova asset nella cache usando ID corretto dalla selezione UI
        self._asset_data = None

        # Prima prova a usare l'asset ID dalla selezione corrente
        try:
            selected_index = scene.openshelf_selected_result_index
            if (hasattr(scene, 'openshelf_search_results') and
                len(scene.openshelf_search_results) > selected_index >= 0):

                selected_result = scene.openshelf_search_results[selected_index]
                print(f"OpenShelf: Using selected asset: {selected_result.name} (ID: {selected_result.asset_id})")

                # Trova asset corrispondente nella cache
                for cached_asset in scene.openshelf_assets_cache:
                    if cached_asset.asset_id == selected_result.asset_id:
                        self._asset_data = cached_asset
                        self.asset_id = selected_result.asset_id  # FIX: Aggiorna asset_id
                        break
        except Exception as e:
            print(f"OpenShelf: Error getting selected asset: {e}")

        # Fallback: cerca per asset_id fornito
        if not self._asset_data:
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
        self._current_step = 'INIT'  # FIX: Inizia da INIT invece di DOWNLOAD
        self._progress = 0
        self._start_time = time.time()
        self._step_start_time = time.time()
        self._download_manager = get_download_manager()
        self._error_message = None

        # FIX: Inizializza progress fluido
        self._last_progress_update = time.time()
        self._smooth_progress_target = 0
        self._smooth_progress_current = 0
        self._estimated_total_time = 60  # Stima iniziale

        # Imposta UI state con progress iniziale
        scene.openshelf_is_downloading = True
        scene.openshelf_download_progress = 0
        scene.openshelf_status_message = "Initializing import..."

        # Avvia timer modal più frequente per progress fluido
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.02, window=context.window)  # 20ms = 50 FPS per UI fluida
        wm.modal_handler_add(self)


        # Force UI refresh per mostrare pannello progress
        scene.openshelf_is_downloading = True
        scene.openshelf_download_progress = 0
        scene.openshelf_status_message = "Initializing download..."

        # CRITICAL: Force immediate UI refresh
        self._force_ui_update(context)

        print(f"OpenShelf: Starting modal import for asset {self.asset_id} - {self._asset_data.name}")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Gestisce il loop principale del modal operator - CON DEBUG PROGRESS"""
        scene = context.scene

        # Check timeout globale
        elapsed_time = time.time() - self._start_time
        if elapsed_time > self._timeout:
            print(f"OpenShelf: Global timeout after {elapsed_time:.1f}s")
            self._cleanup_and_finish(context, 'TIMEOUT')
            return {'CANCELLED'}

        # Gestione eventi
        if event.type == 'TIMER':

            # FIX: Aggiorna progress fluido ad ogni timer
            self._update_smooth_progress(context)
            return self._handle_timer_step(context)
        elif event.type in {'ESC'}:
            self._cleanup_and_finish(context, 'CANCELLED')
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def _debug_progress_panel_visibility(self, context):
        """Debug: verifica se il pannello progress è visibile"""
        scene = context.scene

        is_downloading = getattr(scene, 'openshelf_is_downloading', False)
        progress = getattr(scene, 'openshelf_download_progress', 0)
        status = getattr(scene, 'openshelf_status_message', '')

        print(f"OpenShelf: Progress panel debug:")
        print(f"  - is_downloading: {is_downloading}")
        print(f"  - progress: {progress}")
        print(f"  - status: '{status}'")
        print(f"  - panel should be visible: {is_downloading}")

        # Verifica se i pannelli OpenShelf sono registrati
        panel_found = False
        if hasattr(bpy.types, 'OPENSHELF_PT_progress_panel_colored'):
            panel_found = True
            print(f"  - progress panel class found: YES")

            # Try to check panel poll
            try:
                panel_class = bpy.types.OPENSHELF_PT_progress_panel_colored
                poll_result = panel_class.poll(context) if hasattr(panel_class, 'poll') else True
                print(f"  - panel poll result: {poll_result}")
            except Exception as e:
                print(f"  - panel poll error: {e}")
        else:
            print(f"  - progress panel class found: NO")

        return panel_found

    def _update_smooth_progress(self, context):
        """FIX: Aggiorna progress bar MOLTO più aggressivamente"""
        scene = context.scene
        current_time = time.time()
        elapsed = current_time - self._start_time

        # Progress baseline basato sul tempo trascorso
        time_progress = min(85, (elapsed / self._estimated_total_time) * 85)

        # Combina con progress specifico dello step
        step_progress = self._get_step_progress_baseline()

        # Usa il maggiore tra tempo e step progress
        target_progress = max(time_progress, step_progress)

        # Smooth interpolation più rapida
        diff = target_progress - self._smooth_progress_current
        if abs(diff) > 0.1:
            # Movimento più rapido (20% invece di 10%)
            movement = diff * 0.2
            self._smooth_progress_current += movement
        else:
            self._smooth_progress_current = target_progress

        # SEMPRE aggiorna UI se cambiato anche di poco
        new_progress = int(self._smooth_progress_current)
        if new_progress != scene.openshelf_download_progress:
            scene.openshelf_download_progress = new_progress

            # FORCE UI update immediato e aggressivo
            self._force_ui_update(context)

            # EXTRA: Try another way to trigger UI refresh
            try:
                if hasattr(context, 'window'):
                    context.window.cursor_modal_set('WAIT')
                    context.window.cursor_modal_restore()
            except:
                pass

    def _get_step_progress_baseline(self) -> float:
        """Ottiene progress baseline per lo step corrente"""
        if self._current_step == 'INIT':
            return 5  # 5% per inizializzazione
        elif self._current_step == 'DOWNLOAD':
            return 20  # Base 20% per download iniziato
        elif self._current_step == 'EXTRACT':
            return 70  # Base 70% per estrazione
        elif self._current_step == 'IMPORT':
            return 90  # Base 90% per import
        elif self._current_step == 'COMPLETE':
            return 100
        return 0

    def _handle_timer_step(self, context):
        """Gestisce ogni step del processo di import"""
        try:
            if self._current_step == 'INIT':
                return self._step_init(context)
            elif self._current_step == 'DOWNLOAD':
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

    def _step_init(self, context):
        """FIX: Nuovo step di inizializzazione con feedback"""
        scene = context.scene

        try:
            elapsed = time.time() - self._step_start_time

            # FIX: Feedback di inizializzazione con info asset
            asset_name = self._asset_data.name[:30] + "..." if len(self._asset_data.name) > 30 else self._asset_data.name
            scene.openshelf_status_message = f"Preparing {asset_name}..."

            # Simula lavoro di inizializzazione (parsing URL, validazione, etc.)
            if elapsed < 1.0:  # 1 secondo di inizializzazione
                # Progress fluido da 0 a 5%
                init_progress = int(elapsed * 5)
                self._smooth_progress_target = init_progress
                return {'RUNNING_MODAL'}

            # Inizializzazione completata, passa al download
            print(f"OpenShelf: Initialization complete, starting download")
            scene.openshelf_status_message = "Starting download..."
            self._current_step = 'DOWNLOAD'
            self._step_start_time = time.time()
            self._smooth_progress_target = 10

        except Exception as e:
            print(f"OpenShelf: Init step error: {e}")
            self._error_message = f"Initialization error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _step_download(self, context):
        """Step 1: Download con progress callback MOLTO PIÙ AGGRESSIVO"""
        scene = context.scene

        try:
            # Parse model URLs (una sola volta)
            if not hasattr(self, '_parsed_urls'):
                self._parsed_urls = self._parse_model_urls()
                if not self._parsed_urls:
                    self._error_message = "No valid 3D model URLs found"
                    self._current_step = 'ERROR'
                    return {'RUNNING_MODAL'}

            # Stato download iniziale
            if not hasattr(self, '_download_started'):
                scene.openshelf_status_message = "Connecting to server..."
                self._download_started = True
                self._smooth_progress_target = 15
                return {'RUNNING_MODAL'}

            # FIX: Progress callback MOLTO PIÙ AGGRESSIVO
            def progress_callback(downloaded, total):
                current_time = time.time()

                # AGGIORNA UI OGNI VOLTA che viene chiamato il callback
                if total > 0:
                    # Calcola percentuale per la barra di progresso (50% del totale riservato al download)
                    download_percent = (downloaded / total) * 50
                    self._smooth_progress_target = 15 + download_percent

                    # AGGIORNA IMMEDIATAMENTE il progresso nella scene
                    new_progress = int(self._smooth_progress_target)
                    scene.openshelf_download_progress = new_progress

                    # FIX: Visualizzazione AGGIORNATA OGNI VOLTA
                    if total < 1024 * 1024:  # < 1MB: mostra in KB
                        downloaded_kb = downloaded / 1024
                        total_kb = total / 1024

                        if total_kb < 100:  # < 100KB: 1 decimale
                            scene.openshelf_status_message = f"📥 {downloaded_kb:.1f}/{total_kb:.1f} KB ({new_progress}%)"
                        else:  # >= 100KB: numeri interi
                            scene.openshelf_status_message = f"📥 {downloaded_kb:.0f}/{total_kb:.0f} KB ({new_progress}%)"

                    elif total < 10 * 1024 * 1024:  # 1-10MB: mostra MB con 1 decimale
                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        scene.openshelf_status_message = f"📥 {downloaded_mb:.1f}/{total_mb:.1f} MB ({new_progress}%)"

                    else:  # > 10MB: mostra MB con numeri interi
                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        scene.openshelf_status_message = f"📥 {downloaded_mb:.0f}/{total_mb:.0f} MB ({new_progress}%)"

                    # Aggiungi velocità se il download è in corso da più di 1 secondo
                    elapsed = current_time - self._step_start_time
                    if elapsed > 1:
                        speed_bps = downloaded / elapsed
                        if speed_bps > 1024 * 1024:
                            speed_text = f" - {speed_bps / (1024 * 1024):.1f} MB/s"
                        elif speed_bps > 1024:
                            speed_text = f" - {speed_bps / 1024:.0f} KB/s"
                        else:
                            speed_text = f" - {speed_bps:.0f} B/s"

                        scene.openshelf_status_message += speed_text

                    # ETA per file grandi
                    if total > 2 * 1024 * 1024 and elapsed > 2:  # File > 2MB dopo 2 secondi
                        remaining_bytes = total - downloaded
                        eta_seconds = remaining_bytes / (downloaded / elapsed)
                        if eta_seconds < 60:
                            eta_text = f" (ETA: {eta_seconds:.0f}s)"
                        else:
                            eta_minutes = eta_seconds / 60
                            eta_text = f" (ETA: {eta_minutes:.1f}m)"

                        scene.openshelf_status_message += eta_text

                else:
                    # Progress senza dimensione nota - mostra solo scaricato
                    if downloaded < 1024 * 1024:  # < 1MB
                        downloaded_kb = downloaded / 1024
                        scene.openshelf_status_message = f"📥 Downloading {downloaded_kb:.0f} KB..."
                    else:
                        downloaded_mb = downloaded / (1024 * 1024)
                        scene.openshelf_status_message = f"📥 Downloading {downloaded_mb:.1f} MB..."

                    # Progress senza totale noto - incrementa gradualmente
                    self._smooth_progress_target = min(60, self._smooth_progress_target + 0.5)
                    scene.openshelf_download_progress = int(self._smooth_progress_target)

                # CRITICAL: Force UI update AGGRESSIVO ad ogni callback
                self._force_ui_update(context)

                # DEBUG: Stampa ogni 0.5 secondi circa
                if not hasattr(self, '_last_callback_print'):
                    self._last_callback_print = 0
                if current_time - self._last_callback_print > 0.5:
                    print(f"OpenShelf: Download progress - {scene.openshelf_download_progress}% - {scene.openshelf_status_message}")
                    self._last_callback_print = current_time

            # Esegui download con callback migliorato
            if not hasattr(self, '_download_path'):
                print(f"OpenShelf: Starting download from {len(self._parsed_urls)} URLs")
                archive_path = None

                for i, url in enumerate(self._parsed_urls):
                    try:
                        # Mostra quale URL stiamo provando
                        url_display = url.split('/')[-1] if '/' in url else url
                        if len(url_display) > 30:
                            url_display = url_display[:27] + "..."

                        scene.openshelf_status_message = f"📡 Connecting to {url_display}... ({i+1}/{len(self._parsed_urls)})"
                        self._force_ui_update(context)

                        archive_path = self._download_manager.download_file(
                            url,
                            use_cache=True,
                            progress_callback=progress_callback
                        )

                        if archive_path and os.path.exists(archive_path):
                            print(f"OpenShelf: Download successful: {archive_path}")

                            # Mostra dimensione file scaricato
                            file_size = os.path.getsize(archive_path)
                            if file_size < 1024 * 1024:
                                size_text = f"{file_size / 1024:.0f} KB"
                            else:
                                size_text = f"{file_size / (1024 * 1024):.1f} MB"

                            scene.openshelf_status_message = f"✅ Downloaded {size_text} successfully"
                            break

                    except Exception as e:
                        print(f"OpenShelf: Download failed for {url}: {e}")
                        scene.openshelf_status_message = f"❌ Failed from source {i+1}, trying next..."
                        continue

                if not archive_path:
                    self._error_message = "Failed to download asset from any URL"
                    self._current_step = 'ERROR'
                    return {'RUNNING_MODAL'}

                self._download_path = archive_path

            # Download completato
            scene.openshelf_status_message = "✅ Download complete, preparing extraction..."
            self._smooth_progress_target = 70
            self._model_path = self._download_path
            self._current_step = 'EXTRACT'
            self._step_start_time = time.time()
            print(f"OpenShelf: Download step completed")

        except Exception as e:
            print(f"OpenShelf: Download step error: {e}")
            self._error_message = f"Download error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _force_ui_update(self, context):
        """Force immediate UI update - versione CORRETTA senza errori"""
        try:
            # 1. Update del window manager (principale)
            if hasattr(context, 'window_manager'):
                context.window_manager.update_tag()

            # 2. Update di TUTTE le aree 3D in tutti gli screen
            if hasattr(bpy, 'data') and hasattr(bpy.data, 'screens'):
                for screen in bpy.data.screens:
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
                            # Force update anche delle regioni
                            for region in area.regions:
                                if region.type == 'UI':
                                    region.tag_redraw()

            # 3. Fallback: current context areas
            if hasattr(context, 'screen') and hasattr(context.screen, 'areas'):
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                        for region in area.regions:
                            if region.type == 'UI':
                                region.tag_redraw()

            # 4. RIMOSSO: update_tag che causava errori
            # Scene update (solo se il metodo esiste)
            if hasattr(context, 'scene'):
                if hasattr(context.scene, 'update_tag'):
                    context.scene.update_tag()

            # 5. RIMOSSO: ViewLayer.update_tag che non esiste sempre
            # Non chiamare context.view_layer.update_tag() che causava l'errore

        except Exception as e:
            # Fallback molto silenzioso - solo per errori gravi
            pass  # Non stampare più errori "non-critical"

    def _step_extract(self, context):
        """Step 2: Estrazione con progress fluido"""
        scene = context.scene

        try:
            if not hasattr(self, '_extract_started'):
                scene.openshelf_status_message = "Extracting archive..."
                self._extract_started = True
                self._smooth_progress_target = 75
                return {'RUNNING_MODAL'}

            # FIX: Progress callback per estrazione
            def extract_progress_callback(extracted, total):
                if total > 0:
                    extract_percent = (extracted / total) * 15  # 15% del totale per estrazione
                    self._smooth_progress_target = 75 + extract_percent
                    scene.openshelf_status_message = f"Extracting {extracted}/{total} files"

            if not hasattr(self, '_extract_dir'):
                extract_dir = self._download_manager.extract_archive(
                    self._model_path,
                    progress_callback=extract_progress_callback
                )

                if not extract_dir or not os.path.exists(extract_dir):
                    self._error_message = "Failed to extract archive"
                    self._current_step = 'ERROR'
                    return {'RUNNING_MODAL'}

                self._extract_dir = extract_dir

            # Trova file 3D
            if not hasattr(self, '_found_files'):
                supported_extensions = ['.obj', '.gltf', '.glb']
                self._found_files = self._download_manager.find_files_by_extension(
                    self._extract_dir, supported_extensions
                )

                if not self._found_files:
                    self._error_message = "No supported 3D files found in archive"
                    self._current_step = 'ERROR'
                    return {'RUNNING_MODAL'}

            # Estrazione completata
            self._model_path = self._found_files[0]
            scene.openshelf_status_message = "Extraction complete"
            self._smooth_progress_target = 90
            self._current_step = 'IMPORT'
            self._step_start_time = time.time()
            print(f"OpenShelf: Extract step completed")

        except Exception as e:
            print(f"OpenShelf: Extract step error: {e}")
            self._error_message = f"Extract error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}

    def _step_import(self, context):
        """Step 3: Import 3D model"""
        scene = context.scene

        try:
            scene.openshelf_status_message = "Importing 3D model..."
            self._smooth_progress_target = 95

            # Verifica file
            if not os.path.exists(self._model_path):
                self._error_message = f"Model file not found: {self._model_path}"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            file_ext = os.path.splitext(self._model_path)[1].lower()

            # Prepara impostazioni import
            import_settings = {
                'import_scale': self.import_scale,
                'auto_center': self.auto_center,
                'apply_materials': self.apply_materials,
                'add_metadata': self.add_metadata
            }

            # Import
            imported_obj = None
            if file_ext == '.obj':
                imported_obj = self._safe_obj_import(context, import_settings)
            else:
                self._error_message = f"Unsupported file format: {file_ext}"
                self._current_step = 'ERROR'
                return {'RUNNING_MODAL'}

            if imported_obj:
                if self.add_metadata:
                    self._apply_cultural_metadata(imported_obj)

                # Seleziona oggetto
                try:
                    context.view_layer.objects.active = imported_obj
                    imported_obj.select_set(True)
                except:
                    pass

                # Successo!
                self._current_step = 'COMPLETE'
                self._smooth_progress_target = 100
                scene.openshelf_status_message = f"Successfully imported {imported_obj.name}"
            else:
                self._error_message = "Import returned no object"
                self._current_step = 'ERROR'

        except Exception as e:
            print(f"OpenShelf: Import step error: {e}")
            self._error_message = f"Import error: {str(e)}"
            self._current_step = 'ERROR'

        return {'RUNNING_MODAL'}


    def _safe_obj_import(self, context, import_settings):
        """Import OBJ sicuro"""
        try:
            original_selection = list(context.selected_objects) if context.selected_objects else []
            bpy.ops.object.select_all(action='DESELECT')

            import_params = {
                'filepath': self._model_path,
                'use_split_objects': True,
                'use_split_groups': False,
                'forward_axis': 'NEGATIVE_Z',
                'up_axis': 'Y',
            }

            result = bpy.ops.wm.obj_import(**import_params)

            new_objects = [obj for obj in context.selected_objects if obj not in original_selection]

            if new_objects:
                main_object = new_objects[0]

                if import_settings['auto_center']:
                    self._center_object(main_object)

                if import_settings['import_scale'] != 1.0:
                    scale = import_settings['import_scale']
                    main_object.scale = (scale, scale, scale)

                return main_object

            return None

        except Exception as e:
            print(f"OpenShelf: OBJ import error: {e}")
            return None

    def _center_object(self, obj):
        """Centra oggetto"""
        try:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
            obj.location = (0, 0, 0)
        except Exception as e:
            print(f"OpenShelf: Error centering object: {e}")

    def _apply_cultural_metadata(self, obj):
        """Applica metadati culturali"""
        try:
            if not obj or not self._asset_data:
                return

            prefix = "openshelf_"
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

            for key, value in metadata.items():
                if value and str(value).strip():
                    obj[f"{prefix}{key}"] = str(value)

        except Exception as e:
            print(f"OpenShelf: Error applying metadata: {e}")

    def _parse_model_urls(self):
        """Parse URLs dei modelli"""
        if not self._asset_data or not self._asset_data.model_urls:
            return []

        try:
            model_urls = json.loads(self._asset_data.model_urls)
            if isinstance(model_urls, list):
                return [str(url).strip() for url in model_urls if url and str(url).strip()]
            elif isinstance(model_urls, str) and model_urls.strip():
                return [model_urls.strip()]
        except json.JSONDecodeError:
            if self._asset_data.model_urls.strip():
                return [self._asset_data.model_urls.strip()]

        return []

    def _step_complete(self, context):
        """Step finale - successo"""
        self._cleanup_and_finish(context, 'FINISHED')
        return {'FINISHED'}

    def _step_error(self, context):
        """Step finale - errore"""
        error_msg = self._error_message or "Import failed"
        self._cleanup_and_finish(context, 'ERROR', error_msg)
        return {'CANCELLED'}

    def _cleanup_and_finish(self, context, result_type, message=None):
        """Cleanup finale"""
        scene = context.scene

        # Remove timer
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None

        # Update UI state
        scene.openshelf_is_downloading = False

        if result_type == 'FINISHED':
            scene.openshelf_download_progress = 100
            if message:
                scene.openshelf_status_message = message
            self.report({'INFO'}, scene.openshelf_status_message)
        elif result_type == 'TIMEOUT':
            scene.openshelf_download_progress = 0
            scene.openshelf_status_message = "Import timed out"
            self.report({'ERROR'}, "Import timed out")
        elif result_type == 'CANCELLED':
            scene.openshelf_download_progress = 0
            scene.openshelf_status_message = "Import cancelled"
            self.report({'INFO'}, "Import cancelled")
        else:  # ERROR
            scene.openshelf_download_progress = 0
            scene.openshelf_status_message = message or "Import failed"
            self.report({'ERROR'}, scene.openshelf_status_message)

        # Force UI redraw
        self._force_ui_update(context)

        total_time = time.time() - self._start_time
        print(f"OpenShelf: Modal import finished: {result_type} (time: {total_time:.1f}s)")


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
