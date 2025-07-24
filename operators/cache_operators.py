"""
OpenShelf Cache Operators
Operatori per gestione cache e cartelle personalizzate
"""

import bpy # type: ignore
from bpy.types import Operator # type: ignore
from bpy.props import StringProperty, BoolProperty # type: ignore
import os
import subprocess
import platform
import tempfile
import shutil
from pathlib import Path
from ..utils.chunked_download_manager import get_chunked_download_manager


class OPENSHELF_OT_clear_repository_cache(Operator):
    """Operatore per pulizia cache repository MIGLIORATO"""
    bl_idname = "openshelf.clear_repository_cache"
    bl_label = "Clear Repository Cache"
    bl_description = "Clear cached data for selected repository"
    bl_options = {'REGISTER', 'UNDO'}

    repository_name: StringProperty(
        name="Repository Name",
        description="Name of repository to clear (use 'all' for all repositories)",
        default="all"
    )

    confirm: BoolProperty(
        name="Confirm",
        description="Confirm cache clearing operation",
        default=False
    )

    clear_type: EnumProperty(
        name="Clear Type",
        description="Type of cache data to clear",
        items=[
            ('metadata', 'Metadata Only', 'Clear only metadata cache (search results, asset info)'),
            ('downloads', 'Downloads Only', 'Clear only downloaded 3D model files'),
            ('all', 'Everything', 'Clear all cached data')
        ],
        default='all'
    )

    def invoke(self, context, event):
        """Mostra dialog di conferma"""
        if not self.confirm:
            return context.window_manager.invoke_props_dialog(self, width=400)
        else:
            return self.execute(context)

    def draw(self, context):
        """Draw del dialog di conferma"""
        layout = self.layout

        # Warning
        layout.label(text="⚠️  Clear Repository Cache", icon='ERROR')
        layout.separator()

        # Info su cosa verrà cancellato
        col = layout.column(align=True)
        if self.repository_name == "all":
            col.label(text="This will clear cache for ALL repositories:")
        else:
            col.label(text=f"This will clear cache for repository: {self.repository_name}")

        col.separator()

        if self.clear_type == 'metadata':
            col.label(text="• Search results and asset metadata")
            col.label(text="• Repository configurations")
        elif self.clear_type == 'downloads':
            col.label(text="• Downloaded 3D model files")
            col.label(text="• Temporary extraction files")
        else:  # all
            col.label(text="• All search results and metadata")
            col.label(text="• All downloaded 3D model files")
            col.label(text="• All temporary files")

        layout.separator()

        # Opzioni
        layout.prop(self, "clear_type")
        layout.prop(self, "confirm")

    def execute(self, context):
        """Esegue pulizia cache con feedback dettagliato"""

        if not self.confirm:
            self.report({'ERROR'}, "Cache clearing cancelled - confirmation required")
            return {'CANCELLED'}

        try:
            cache_dir = bpy.utils.user_resource('DATAFILES', path="openshelf/cache", create=False)

            if not cache_dir or not os.path.exists(cache_dir):
                self.report({'INFO'}, "No cache directory found - nothing to clear")
                return {'FINISHED'}

            total_size_before = self._get_directory_size(cache_dir)
            files_removed = 0
            errors = []

            print(f"OpenShelf: Starting cache cleanup - Type: {self.clear_type}, Repository: {self.repository_name}")

            # Cancella download attivi se presenti
            try:
                chunked_manager = get_chunked_download_manager()
                active_downloads = chunked_manager.get_active_download_count()
                if active_downloads > 0:
                    chunked_manager.cancel_all_downloads()
                    print(f"OpenShelf: Cancelled {active_downloads} active downloads")
            except Exception as e:
                print(f"OpenShelf: Warning - could not cancel active downloads: {e}")

            # Pulizia basata sul tipo
            if self.clear_type in ['downloads', 'all']:
                files_removed += self._clear_download_cache(cache_dir, errors)

            if self.clear_type in ['metadata', 'all']:
                files_removed += self._clear_metadata_cache(cache_dir, errors)

            # Pulizia repository-specifica
            if self.repository_name != "all":
                files_removed += self._clear_repository_specific_cache(cache_dir, self.repository_name, errors)

            # Calcola spazio liberato
            total_size_after = self._get_directory_size(cache_dir) if os.path.exists(cache_dir) else 0
            space_freed = total_size_before - total_size_after
            space_freed_mb = space_freed / (1024 * 1024)

            # Risultato
            if errors:
                error_summary = f"Cleared {files_removed} files but encountered {len(errors)} errors"
                self.report({'WARNING'}, error_summary)
                for error in errors[:3]:  # Mostra solo primi 3 errori
                    print(f"OpenShelf: Cache clear error: {error}")
            else:
                success_msg = f"Cache cleared successfully: {files_removed} files removed, {space_freed_mb:.1f} MB freed"
                self.report({'INFO'}, success_msg)
                print(f"OpenShelf: {success_msg}")

            # Force UI refresh per aggiornare statistiche
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            return {'FINISHED'}

        except Exception as e:
            error_msg = f"Cache clearing failed: {str(e)}"
            self.report({'ERROR'}, error_msg)
            print(f"OpenShelf: {error_msg}")
            return {'CANCELLED'}

    def _clear_download_cache(self, cache_dir: str, errors: list) -> int:
        """Pulisce cache dei download"""
        files_removed = 0

        try:
            # File patterns per download
            download_patterns = ['*.zip', '*.obj', '*.mtl', '*.ply', '*.stl', '*.3ds', '*.dae', '*.fbx']
            temp_patterns = ['*.tmp', '.*.tmp']

            cache_path = Path(cache_dir)

            # Rimuovi file di download
            for pattern in download_patterns:
                for file_path in cache_path.glob(pattern):
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                            files_removed += 1
                    except Exception as e:
                        errors.append(f"Failed to remove {file_path}: {e}")

            # Rimuovi file temporanei
            for pattern in temp_patterns:
                for file_path in cache_path.glob(pattern):
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                            files_removed += 1
                    except Exception as e:
                        errors.append(f"Failed to remove temp file {file_path}: {e}")

            # Rimuovi directory di estrazione
            extract_dirs = ['extracts', 'temp_extracts']
            for dir_name in extract_dirs:
                extract_path = cache_path / dir_name
                if extract_path.exists() and extract_path.is_dir():
                    try:
                        shutil.rmtree(extract_path)
                        files_removed += 1
                    except Exception as e:
                        errors.append(f"Failed to remove extract directory {extract_path}: {e}")

        except Exception as e:
            errors.append(f"Download cache clearing error: {e}")

        return files_removed

    def _clear_metadata_cache(self, cache_dir: str, errors: list) -> int:
        """Pulisce cache dei metadata"""
        files_removed = 0

        try:
            cache_path = Path(cache_dir)

            # File patterns per metadata
            metadata_patterns = ['*.json', '*.cache', '*.db']

            for pattern in metadata_patterns:
                for file_path in cache_path.glob(pattern):
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                            files_removed += 1
                    except Exception as e:
                        errors.append(f"Failed to remove metadata {file_path}: {e}")

            # Directory metadata
            metadata_dirs = ['metadata', 'search_cache', 'repository_cache']
            for dir_name in metadata_dirs:
                metadata_path = cache_path / dir_name
                if metadata_path.exists() and metadata_path.is_dir():
                    try:
                        shutil.rmtree(metadata_path)
                        files_removed += 1
                    except Exception as e:
                        errors.append(f"Failed to remove metadata directory {metadata_path}: {e}")

        except Exception as e:
            errors.append(f"Metadata cache clearing error: {e}")

        return files_removed

    def _clear_repository_specific_cache(self, cache_dir: str, repository_name: str, errors: list) -> int:
        """Pulisce cache specifica per un repository"""
        files_removed = 0

        try:
            cache_path = Path(cache_dir)

            # Cerca file che contengono il nome del repository
            for file_path in cache_path.rglob(f"*{repository_name}*"):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        files_removed += 1
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        files_removed += 1
                except Exception as e:
                    errors.append(f"Failed to remove repository file {file_path}: {e}")

        except Exception as e:
            errors.append(f"Repository-specific cache clearing error: {e}")

        return files_removed

    def _get_directory_size(self, directory: str) -> int:
        """Calcola dimensione totale directory"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
            return total_size
        except Exception:
            return 0

class OPENSHELF_OT_reset_ui_state(Operator):
    """Reset dello stato UI in caso di problemi"""
    bl_idname = "openshelf.reset_ui_state"
    bl_label = "Reset UI State"
    bl_description = "Reset OpenShelf UI state if stuck or corrupted"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Reset completo dello stato UI"""
        try:
            scene = context.scene

            # Reset stati di download/ricerca
            scene.openshelf_is_downloading = False
            scene.openshelf_is_searching = False
            scene.openshelf_download_progress = 0
            scene.openshelf_status_message = "UI state reset"

            # Reset filtri e query
            scene.openshelf_search_query = ""
            scene.openshelf_object_type_filter = ""
            scene.openshelf_material_filter = ""
            scene.openshelf_chronology_filter = ""

            # Cancella operazioni attive
            try:
                chunked_manager = get_chunked_download_manager()
                chunked_manager.cancel_all_downloads()
            except Exception as e:
                print(f"OpenShelf: Warning during download cancellation: {e}")

            # Force UI refresh completo
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    for region in area.regions:
                        region.tag_redraw()

            self.report({'INFO'}, "OpenShelf UI state reset successfully")
            print("OpenShelf: UI state reset completed")

            return {'FINISHED'}

        except Exception as e:
            error_msg = f"UI reset failed: {str(e)}"
            self.report({'ERROR'}, error_msg)
            print(f"OpenShelf: {error_msg}")
            return {'CANCELLED'}


class OPENSHELF_OT_test_chunked_download(Operator):
    """Operatore di test per il sistema chunked download"""
    bl_idname = "openshelf.test_chunked_download"
    bl_label = "Test Chunked Download"
    bl_description = "Test the chunked download system with a sample file"
    bl_options = {'REGISTER'}

    test_url: StringProperty(
        name="Test URL",
        description="URL to test chunked download with",
        default="https://httpbin.org/drip?duration=5&numbytes=1048576"  # 1MB file over 5 seconds
    )

    def execute(self, context):
        """Test del sistema chunked download"""
        try:
            scene = context.scene

            # Inizializza manager
            chunked_manager = get_chunked_download_manager()

            # Progress callback di test
            def test_progress_callback(downloaded, total):
                if total > 0:
                    progress = (downloaded / total) * 100
                    print(f"Test download: {progress:.1f}% ({downloaded}/{total} bytes)")
                else:
                    print(f"Test download: {downloaded} bytes (size unknown)")

            # Avvia download di test
            session_id = chunked_manager.start_chunked_download(
                self.test_url,
                progress_callback=test_progress_callback,
                use_cache=False
            )

            if session_id:
                self.report({'INFO'}, f"Test download started: {session_id}")
                print(f"OpenShelf: Test chunked download started - Session: {session_id}")

                # Nota: il download continuerà in background attraverso i timer degli operatori modal attivi
                scene.openshelf_status_message = f"Test download in progress: {session_id}"
            else:
                self.report({'ERROR'}, "Failed to start test download")

            return {'FINISHED'}

        except Exception as e:
            error_msg = f"Test download failed: {str(e)}"
            self.report({'ERROR'}, error_msg)
            print(f"OpenShelf: {error_msg}")
            return {'CANCELLED'}

class OPENSHELF_OT_open_cache_directory(Operator):
    """Apre la cartella cache nel file manager"""
    bl_idname = "openshelf.open_cache_directory"
    bl_label = "Open Cache Directory"
    bl_description = "Open cache directory in file manager"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            # Ottieni directory cache
            addon_name = __package__.split('.')[0]
            prefs = context.preferences.addons[addon_name].preferences

            cache_dir = None
            if hasattr(prefs, 'custom_cache_directory') and prefs.custom_cache_directory.strip():
                cache_dir = prefs.custom_cache_directory.strip()
            else:
                cache_dir = os.path.join(tempfile.gettempdir(), "openshelf_cache")

            # Crea directory se non existe
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
                self.report({'INFO'}, f"Created cache directory: {cache_dir}")

            # Apri nel file manager per OS
            if platform.system() == "Windows":
                os.startfile(cache_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", cache_dir])
            else:  # Linux
                subprocess.run(["xdg-open", cache_dir])

            self.report({'INFO'}, f"Opened cache directory: {cache_dir}")

        except Exception as e:
            print(f"OpenShelf: Error opening cache directory: {e}")
            self.report({'ERROR'}, f"Error opening cache directory: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_reset_cache_directory(Operator):
    """Reset cache directory al default"""
    bl_idname = "openshelf.reset_cache_directory"
    bl_label = "Reset Cache Directory"
    bl_description = "Reset cache directory to default location"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            addon_name = __package__.split('.')[0]
            prefs = context.preferences.addons[addon_name].preferences

            # Reset custom directory
            prefs.custom_cache_directory = ""

            # Ottieni default directory
            default_cache = os.path.join(tempfile.gettempdir(), "openshelf_cache")

            self.report({'INFO'}, f"Reset to default cache directory: {default_cache}")

        except Exception as e:
            print(f"OpenShelf: Error resetting cache directory: {e}")
            self.report({'ERROR'}, f"Error resetting cache directory: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_migrate_cache(Operator):
    """Migra cache da una directory all'altra"""
    bl_idname = "openshelf.migrate_cache"
    bl_label = "Migrate Cache"
    bl_description = "Migrate cache files to new directory"
    bl_options = {'REGISTER'}

    old_directory: StringProperty(
        name="Old Directory",
        description="Old cache directory path",
        default=""
    )

    new_directory: StringProperty(
        name="New Directory",
        description="New cache directory path",
        default=""
    )

    def execute(self, context):
        if not self.old_directory or not self.new_directory:
            self.report({'ERROR'}, "Both directories must be specified")
            return {'CANCELLED'}

        try:
            if not os.path.exists(self.old_directory):
                self.report({'ERROR'}, f"Old directory does not exist: {self.old_directory}")
                return {'CANCELLED'}

            # Crea nuova directory
            os.makedirs(self.new_directory, exist_ok=True)

            # Conta file da migrare
            files_to_migrate = []
            for root, dirs, files in os.walk(self.old_directory):
                for file in files:
                    old_path = os.path.join(root, file)
                    rel_path = os.path.relpath(old_path, self.old_directory)
                    new_path = os.path.join(self.new_directory, rel_path)
                    files_to_migrate.append((old_path, new_path))

            if not files_to_migrate:
                self.report({'INFO'}, "No files to migrate")
                return {'FINISHED'}

            # Migra file
            migrated_count = 0
            for old_path, new_path in files_to_migrate:
                try:
                    # Crea directory di destinazione se necessario
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)

                    # Copia file
                    shutil.copy2(old_path, new_path)
                    migrated_count += 1
                except Exception as e:
                    print(f"OpenShelf: Error migrating {old_path}: {e}")

            self.report({'INFO'}, f"Migrated {migrated_count}/{len(files_to_migrate)} cache files")

        except Exception as e:
            print(f"OpenShelf: Error migrating cache: {e}")
            self.report({'ERROR'}, f"Error migrating cache: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_cache_statistics(Operator):
    """Mostra statistiche dettagliate cache"""
    bl_idname = "openshelf.cache_statistics"
    bl_label = "Cache Statistics"
    bl_description = "Show detailed cache statistics"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            from ..utils.download_manager import get_download_manager

            # Ottieni download manager con directory corretta
            addon_name = __package__.split('.')[0]
            prefs = context.preferences.addons[addon_name].preferences

            if hasattr(prefs, 'custom_cache_directory') and prefs.custom_cache_directory.strip():
                from ..utils.download_manager import DownloadManager
                dm = DownloadManager(prefs.custom_cache_directory.strip())
            else:
                dm = get_download_manager()

            stats = dm.get_cache_statistics()

            # Mostra popup con statistiche
            def draw_stats_popup(self, context):
                layout = self.layout
                layout.label(text="Cache Statistics", icon='GRAPH')
                layout.separator()

                box = layout.box()
                box.label(text="Current Cache", icon='FILE_CACHE')

                col = box.column(align=True)
                col.scale_y = 0.8
                col.label(text=f"Files: {stats['file_count']}")
                col.label(text=f"Size: {stats['cache_size'] / (1024*1024):.1f} MB")
                col.label(text=f"Max Size: {stats['max_cache_size'] / (1024*1024):.1f} MB")

                usage = (stats['cache_size'] / stats['max_cache_size']) * 100
                col.label(text=f"Usage: {usage:.1f}%")

                # Directory info
                box = layout.box()
                box.label(text="Directory", icon='FOLDER_REDIRECT')

                cache_dir = stats['cache_dir']
                # Tronca path se troppo lungo per popup
                if len(cache_dir) > 40:
                    cache_dir = "..." + cache_dir[-37:]
                box.label(text=cache_dir)

            context.window_manager.popup_menu(
                draw_stats_popup,
                title="Cache Statistics",
                icon='GRAPH'
            )

        except Exception as e:
            print(f"OpenShelf: Error getting cache statistics: {e}")
            self.report({'ERROR'}, f"Error getting cache statistics: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_cache_health_report(bpy.types.Operator):
    """Mostra report salute cache"""
    bl_idname = "openshelf.cache_health_report"
    bl_label = "Cache Health Report"
    bl_description = "Show detailed cache health analysis"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            from ..utils.download_manager import get_download_manager
            dm = get_download_manager()
            report = dm.get_cache_health_report()

            # Mostra popup con report
            def draw_health_popup(self, context):
                layout = self.layout

                if "error" in report:
                    layout.label(text=report["error"], icon='ERROR')
                    return

                # Header con punteggio
                header_box = layout.box()
                health_score = report["health_score"]

                if health_score >= 80:
                    icon = 'CHECKMARK'
                    status = "Excellent"
                elif health_score >= 60:
                    icon = 'INFO'
                    status = "Good"
                elif health_score >= 40:
                    icon = 'ERROR'
                    status = "Fair"
                else:
                    icon = 'CANCEL'
                    status = "Poor"

                header_box.label(text=f"Health Score: {health_score}/100 ({status})", icon=icon)

                # Stats
                stats_box = layout.box()
                stats_box.label(text="Statistics", icon='GRAPH')
                col = stats_box.column(align=True)
                col.scale_y = 0.8
                col.label(text=f"Files: {report['total_files']}")
                col.label(text=f"Size: {report['total_size_mb']:.1f} MB")
                col.label(text=f"Usage: {report['usage_percent']:.1f}%")

                # Issues
                if report['issues']:
                    issues_box = layout.box()
                    issues_box.label(text="Issues Found", icon='ERROR')
                    for issue in report['issues']:
                        issues_box.label(text=f"• {issue}")

                # Recommendations
                rec_box = layout.box()
                rec_box.label(text="Recommendations", icon='LIGHTBULB')
                for rec in report['recommendations']:
                    rec_box.label(text=f"• {rec}")

            context.window_manager.popup_menu(
                draw_health_popup,
                title="Cache Health Report",
                icon='GRAPH'
            )

        except Exception as e:
            self.report({'ERROR'}, f"Error generating health report: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_quick_search(Operator):
    """Operatore per ricerche rapide predefinite"""
    bl_idname = "openshelf.quick_search"
    bl_label = "Quick Search"
    bl_description = "Perform predefined quick search"
    bl_options = {'REGISTER'}

    search_term: StringProperty(
        name="Search Term",
        description="Term to search for",
        default=""
    )

    search_field: StringProperty(
        name="Search Field",
        description="Field to search in",
        default="search"
    )

    def execute(self, context):
        """Esegue ricerca rapida con feedback migliorato"""
        scene = context.scene

        if not self.search_term:
            self.report({'ERROR'}, "No search term specified")
            return {'CANCELLED'}

        try:
            # Imposta parametri di ricerca
            if self.search_field == "object_type":
                scene.openshelf_object_type_filter = self.search_term
                scene.openshelf_search_query = ""  # Reset query generica
                search_description = f"object type '{self.search_term}'"
            elif self.search_field == "material":
                scene.openshelf_material_filter = self.search_term
                scene.openshelf_search_query = ""
                search_description = f"material '{self.search_term}'"
            elif self.search_field == "chronology":
                scene.openshelf_chronology_filter = self.search_term
                scene.openshelf_search_query = ""
                search_description = f"chronology '{self.search_term}'"
            else:  # search_field == "search" o altro
                scene.openshelf_search_query = self.search_term
                # Reset filtri specifici
                scene.openshelf_object_type_filter = ""
                scene.openshelf_material_filter = ""
                scene.openshelf_chronology_filter = ""
                search_description = f"general term '{self.search_term}'"

            # Esegui ricerca automaticamente
            result = bpy.ops.openshelf.search_assets()

            if result == {'FINISHED'}:
                self.report({'INFO'}, f"Quick search performed for {search_description}")
                print(f"OpenShelf: Quick search executed - {search_description}")
            else:
                self.report({'WARNING'}, f"Quick search may have encountered issues")

            return {'FINISHED'}

        except Exception as e:
            error_msg = f"Quick search failed: {str(e)}"
            self.report({'ERROR'}, error_msg)
            print(f"OpenShelf: {error_msg}")
            return {'CANCELLED'}

# Lista operatori da registrare
operators = [
    OPENSHELF_OT_clear_repository_cache,
    OPENSHELF_OT_open_cache_directory,
    OPENSHELF_OT_reset_cache_directory,
    OPENSHELF_OT_migrate_cache,
    OPENSHELF_OT_cache_statistics,
    OPENSHELF_OT_cache_health_report,
    OPENSHELF_OT_reset_ui_state,
    OPENSHELF_OT_test_chunked_download,

]

def register():
    """Registra gli operatori cache"""
    for op in operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra gli operatori cache"""
    for op in reversed(operators):
        bpy.utils.unregister_class(op)
