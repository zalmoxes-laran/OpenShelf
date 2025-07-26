"""
OpenShelf Preferences Panel
Pannello preferenze addon
"""

import bpy
from bpy.types import AddonPreferences
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    EnumProperty,
    FloatProperty
)
import os
import shutil

class OpenShelfPreferences(AddonPreferences):
    """Preferenze addon OpenShelf"""
    bl_idname = __package__.split('.')[0]  # Nome del package principale

    # === IMPOSTAZIONI REPOSITORY ===
    default_repository: EnumProperty(
        name="Default Repository",
        description="Default repository to select on startup",
        items=[
            ('ercolano', 'Ercolano', 'Museo Archeologico Virtuale di Ercolano'),
            ('all', 'All Repositories', 'Search in all available repositories'),
        ],
        default='ercolano'
    )

    auto_refresh_repositories: BoolProperty(
        name="Auto Refresh Repositories",
        description="Automatically refresh repository list on startup",
        default=True
    )

    repository_timeout: IntProperty(
        name="Repository Timeout (seconds)",
        description="Network timeout for repository connections",
        default=30,
        min=5,
        max=120
    )

    # === IMPOSTAZIONI DOWNLOAD ===
    download_cache_enabled: BoolProperty(
        name="Enable Download Cache",
        description="Cache downloaded files for faster access",
        default=True
    )

    cache_max_size: IntProperty(
        name="Max Cache Size (MB)",
        description="Maximum size of download cache in megabytes",
        default=500,
        min=50,
        max=5000
    )

    cache_max_age: IntProperty(
        name="Max Cache Age (days)",
        description="Maximum age of cached files in days",
        default=7,
        min=1,
        max=30
    )

    download_concurrent: IntProperty(
        name="Concurrent Downloads",
        description="Maximum number of concurrent downloads",
        default=3,
        min=1,
        max=10
    )

    # === IMPOSTAZIONI IMPORT ===
    default_import_scale: IntProperty(
        name="Default Import Scale (%)",
        description="Default scale percentage for imported objects",
        default=100,
        min=1,
        max=1000
    )

    auto_center_objects: BoolProperty(
        name="Auto Center Objects",
        description="Automatically center imported objects at origin",
        default=True
    )

    auto_apply_materials: BoolProperty(
        name="Auto Apply Materials",
        description="Automatically apply materials to imported objects",
        default=True
    )

    add_cultural_metadata: BoolProperty(
        name="Add Cultural Metadata",
        description="Add cultural heritage metadata as custom properties",
        default=True
    )

    recalculate_normals: BoolProperty(
        name="Recalculate Normals",
        description="Recalculate normals for imported OBJ files",
        default=False
    )

    # === IMPOSTAZIONI UI ===
    search_results_limit: IntProperty(
        name="Search Results Limit",
        description="Maximum number of search results to display",
        default=50,
        min=10,
        max=500
    )

    auto_search_enabled: BoolProperty(
        name="Enable Auto Search",
        description="Search automatically while typing (may be slower)",
        default=False
    )

    show_quality_scores: BoolProperty(
        name="Show Quality Scores",
        description="Display quality scores in search results",
        default=True
    )

    compact_ui_mode: BoolProperty(
        name="Compact UI Mode",
        description="Use compact UI layout to save space",
        default=False
    )

    # === IMPOSTAZIONI AVANZATE ===
    debug_mode: BoolProperty(
        name="Debug Mode",
        description="Enable debug logging and extended error messages",
        default=False
    )

    log_level: EnumProperty(
        name="Log Level",
        description="Level of logging detail",
        items=[
            ('ERROR', 'Error', 'Only log errors'),
            ('WARNING', 'Warning', 'Log warnings and errors'),
            ('INFO', 'Info', 'Log general information'),
            ('DEBUG', 'Debug', 'Log detailed debug information'),
        ],
        default='INFO'
    )

    custom_cache_directory: StringProperty(
        name="Custom Cache Directory",
        description="Custom directory for cache files (leave empty for default)",
        default="",
        subtype='DIR_PATH'
    )

    # === IMPOSTAZIONI QUALITÀ ===
    minimum_quality_score: IntProperty(
        name="Minimum Quality Score",
        description="Minimum quality score to show in results (0 = show all)",
        default=0,
        min=0,
        max=100
    )

    prefer_high_quality: BoolProperty(
        name="Prefer High Quality",
        description="Sort results by quality score (highest first)",
        default=True
    )

    skip_low_quality_import: BoolProperty(
        name="Warn on Low Quality Import",
        description="Show warning when importing low quality assets",
        default=True
    )

    # === IMPOSTAZIONI SICUREZZA ===
    verify_ssl_certificates: BoolProperty(
        name="Verify SSL Certificates",
        description="Verify SSL certificates for HTTPS connections",
        default=True
    )

    allow_http_downloads: BoolProperty(
        name="Allow HTTP Downloads",
        description="Allow downloads over non-secure HTTP connections",
        default=True
    )

    # Proprietà per tab selector
    prefs_tab: EnumProperty(
        name="Preferences Tab",
        items=[
            ('GENERAL', 'General', 'General settings'),
            ('IMPORT', 'Import', 'Import and download settings'),
            ('CACHE', 'Cache', 'Cache management settings'),
            ('LIBRARY', "Library", "Local library settings"),
            ('ADVANCED', 'Advanced', 'Advanced and debug settings'),
        ],
        default='GENERAL'
    ) # type: ignore

    local_library_path: StringProperty(
        name="Local Library Path",
        description="Path to the local 3D models library directory",
        default="",
        subtype='DIR_PATH'
    )

    auto_save_to_library: BoolProperty(
        name="Auto-save to Library",
        description="Automatically save downloaded models to local library",
        default=True
    )

    show_library_status: BoolProperty(
        name="Show Library Status",
        description="Show if models are already in library in search results",
        default=True
    )



    def draw(self, context):
        """Disegna il pannello preferenze"""
        layout = self.layout

        # Tab selector
        row = layout.row()
        row.prop(self, "prefs_tab", expand=True)

        # Disegna tab appropriato
        if self.prefs_tab == "GENERAL":
            self.draw_general_tab(layout)
        elif self.prefs_tab == "IMPORT":
            self.draw_import_tab(layout)
        elif self.prefs_tab == "CACHE":
            self.draw_cache_tab(layout)
        elif self.prefs_tab == 'LIBRARY':
            self.draw_library_tab(layout)
        elif self.prefs_tab == "ADVANCED":
            self.draw_advanced_tab(layout)

    def draw_library_tab(self, layout):
        """Disegna tab impostazioni libreria locale"""

        # Header informativo
        info_box = layout.box()
        info_box.alert = True
        col = info_box.column(align=True)
        col.scale_y = 0.8
        col.label(text="📚 Local Library stores your 3D models permanently", icon='INFO')
        col.label(text="   Faster access, offline use, and better organization")

        # Impostazioni libreria principale
        box = layout.box()
        box.label(text="Library Settings", icon='OUTLINER_COLLECTION')

        col = box.column()

        # Path della libreria
        library_row = col.row(align=True)
        library_row.prop(self, "local_library_path", text="Library Path")

        # Bottone per aprire cartella
        open_op = library_row.operator("openshelf.open_library_folder", text="", icon='FOLDER_REDIRECT')

        # Bottone per reset al default
        reset_op = library_row.operator("openshelf.reset_library_path", text="", icon='LOOP_BACK')

        # Impostazioni comportamento
        settings_col = col.column()
        settings_col.prop(self, "auto_save_to_library")
        settings_col.prop(self, "show_library_status")

        # Informazioni libreria attuale
        box = layout.box()
        box.label(text="📊 Library Information", icon='GRAPH')

        try:
            from ..utils.local_library_manager import get_library_manager
            library_manager = get_library_manager()
            stats = library_manager.get_library_stats()

            if stats.get("error"):
                error_col = box.column()
                error_col.alert = True
                error_col.label(text=f"❌ Error: {stats['error']}", icon='ERROR')
            else:
                # Statistiche
                stats_col = box.column()
                stats_col.scale_y = 0.9

                asset_count = stats.get("asset_count", 0)
                size_mb = stats.get("total_size_mb", 0)

                stats_col.label(text=f"📦 Assets in library: {asset_count}")

                if size_mb < 1:
                    size_kb = size_mb * 1024
                    stats_col.label(text=f"💾 Total size: {size_kb:.1f} KB")
                else:
                    stats_col.label(text=f"💾 Total size: {size_mb:.1f} MB")

                # Path attuale
                current_path = stats.get("library_path", "Unknown")
                stats_col.label(text=f"📂 Location: {current_path}")

                # Controlli libreria
                controls_row = box.row(align=True)
                controls_row.operator("openshelf.open_library_folder", text="Open Folder", icon='FOLDER_REDIRECT')
                controls_row.operator("openshelf.refresh_library", text="Refresh", icon='FILE_REFRESH')

                # Bottone per cleanup (se ci sono asset)
                if asset_count > 0:
                    cleanup_row = box.row()
                    cleanup_row.alert = True
                    cleanup_row.operator("openshelf.cleanup_library", text="Cleanup Library", icon='TRASH')

        except Exception as e:
            error_box = box.box()
            error_box.alert = True
            error_box.label(text=f"Cannot access library: {str(e)}", icon='ERROR')

        # Informazioni aggiuntive
        help_box = layout.box()
        help_box.label(text="💡 Tips", icon='QUESTION')

        help_col = help_box.column()
        help_col.scale_y = 0.8
        help_col.label(text="• Library organizes models by Asset ID in separate folders")
        help_col.label(text="• Each asset includes metadata.json with cultural information")
        help_col.label(text="• You can backup/sync the library folder across computers")
        help_col.label(text="• Downloaded models work offline once in the library")


    def draw_general_tab(self, layout):
        """Disegna tab impostazioni generali"""

        # Repository settings
        box = layout.box()
        box.label(text="Repository Settings", icon='WORLD_DATA')

        col = box.column()
        col.prop(self, "default_repository")
        col.prop(self, "auto_refresh_repositories")
        col.prop(self, "repository_timeout")

        # UI settings
        box = layout.box()
        box.label(text="User Interface", icon='WINDOW')

        col = box.column()
        col.prop(self, "search_results_limit")
        col.prop(self, "auto_search_enabled")
        col.prop(self, "show_quality_scores")
        col.prop(self, "compact_ui_mode")

        # Quality settings
        box = layout.box()
        box.label(text="Quality Filtering", icon='CHECKMARK')

        col = box.column()
        col.prop(self, "minimum_quality_score")
        col.prop(self, "prefer_high_quality")
        col.prop(self, "skip_low_quality_import")

    def draw_import_tab(self, layout):
        """Disegna tab impostazioni import"""

        # Default import settings
        box = layout.box()
        box.label(text="Default Import Settings", icon='IMPORT')

        col = box.column()
        col.prop(self, "default_import_scale")
        col.prop(self, "auto_center_objects")
        col.prop(self, "auto_apply_materials")
        col.prop(self, "add_cultural_metadata")
        col.prop(self, "recalculate_normals")

        # Download settings
        box = layout.box()
        box.label(text="Download Settings", icon='URL')

        col = box.column()
        col.prop(self, "download_concurrent")
        col.prop(self, "verify_ssl_certificates")
        col.prop(self, "allow_http_downloads")

        # Preview
        box = layout.box()
        box.label(text="Preview", icon='HIDE_OFF')

        col = box.column()
        col.label(text="Default import scale: {:.0f}%".format(self.default_import_scale))
        col.label(text="Auto center: {}".format("Yes" if self.auto_center_objects else "No"))
        col.label(text="Materials: {}".format("Apply" if self.auto_apply_materials else "Skip"))
        col.label(text="Metadata: {}".format("Add" if self.add_cultural_metadata else "Skip"))


    def draw_cache_tab(self, layout):
        """Disegna tab impostazioni cache - VERSIONE MIGLIORATA"""

        # Header con info importante
        info_box = layout.box()
        info_box.alert = True
        col = info_box.column(align=True)
        col.scale_y = 0.8
        col.label(text="📁 Cache stores downloaded 3D models locally", icon='INFO')
        col.label(text="   for faster access and offline use")

        # Cache settings principale
        box = layout.box()
        box.label(text="Cache Settings", icon='FILE_CACHE')

        col = box.column()
        col.prop(self, "download_cache_enabled")

        if self.download_cache_enabled:
            settings_row = col.row(align=True)
            settings_row.prop(self, "cache_max_size", text="Max Size (MB)")
            settings_row.prop(self, "cache_max_age", text="Max Age (days)")

            # Cache Directory con UI migliorata
            cache_box = col.box()
            cache_box.label(text="📂 Cache Directory Location", icon='FOLDER_REDIRECT')

            # Campo input per directory personalizzata
            dir_col = cache_box.column()
            dir_col.prop(self, "custom_cache_directory", text="Custom Path")

            # Info sulla directory corrente con più dettagli
            info_col = cache_box.column()
            info_col.scale_y = 0.8

            if self.custom_cache_directory and self.custom_cache_directory.strip():
                custom_dir = self.custom_cache_directory.strip()

                if os.path.exists(custom_dir):
                    info_col.label(text="✅ Custom directory exists", icon='CHECKMARK')

                    # Mostra dimensione directory se possibile
                    try:
                        from ..utils.file_utils import FileUtils
                        dir_size = FileUtils.get_directory_size(custom_dir)
                        if dir_size > 0:
                            if dir_size < 1024 * 1024:
                                size_text = f"{dir_size / 1024:.0f} KB"
                            else:
                                size_text = f"{dir_size / (1024 * 1024):.1f} MB"
                            info_col.label(text=f"📊 Current size: {size_text}")
                    except:
                        pass

                else:
                    info_col.label(text="⚠️ Directory will be created when needed", icon='ERROR')

                # Mostra path completo se diverso da quello visualizzato
                if len(custom_dir) > 60:
                    info_col.label(text=f"Full path: {custom_dir}")
            else:
                import tempfile
                default_cache = os.path.join(tempfile.gettempdir(), "openshelf_cache")
                info_col.label(text="🔧 Using system default location:")

                # Mostra default path su più righe se necessario
                if len(default_cache) > 50:
                    # Spezza il path in parti più leggibili
                    parts = default_cache.split(os.sep)
                    if len(parts) > 3:
                        short_path = os.sep.join(['..'] + parts[-2:])
                        info_col.label(text=f"   {short_path}")
                    else:
                        info_col.label(text=f"   {default_cache}")
                else:
                    info_col.label(text=f"   {default_cache}")

            # Azioni rapide directory
            actions_row = cache_box.row(align=True)
            actions_row.operator("openshelf.open_cache_directory", text="📁 Open", icon='FILE_FOLDER')

            if self.custom_cache_directory:
                actions_row.operator("openshelf.reset_cache_directory", text="🔄 Reset", icon='LOOP_BACK')

        else:
            warning_box = col.box()
            warning_box.alert = True
            warning_col = warning_box.column()
            warning_col.label(text="⚠️ Cache disabled", icon='ERROR')
            warning_col.label(text="Models will be downloaded every time")
            warning_col.label(text="This will be slower and use more bandwidth")

        # Cache info con statistiche dettagliate
        box = layout.box()
        box.label(text="📊 Cache Information", icon='GRAPH')

        try:
            from ..utils.download_manager import get_download_manager
            dm = get_download_manager()

            # Se custom cache directory è impostata, la usa
            if self.custom_cache_directory and self.custom_cache_directory.strip():
                from ..utils.download_manager import DownloadManager
                dm = DownloadManager(self.custom_cache_directory.strip())

            cache_stats = dm.get_cache_statistics()

            # Statistiche principali
            stats_split = box.split(factor=0.7)

            # Colonna sinistra: numeri
            left_col = stats_split.column()
            left_col.scale_y = 0.9

            cache_size_mb = cache_stats['cache_size'] / (1024*1024)
            file_count = cache_stats['file_count']

            left_col.label(text=f"📦 Files cached: {file_count}")

            if cache_size_mb < 1:
                size_kb = cache_stats['cache_size'] / 1024
                left_col.label(text=f"💾 Total size: {size_kb:.0f} KB")
            else:
                left_col.label(text=f"💾 Total size: {cache_size_mb:.1f} MB")

            # Percentuale utilizzata
            if file_count > 0 and self.download_cache_enabled:
                usage_percent = cache_size_mb / self.cache_max_size * 100
                left_col.label(text=f"📈 Usage: {usage_percent:.1f}% of {self.cache_max_size} MB")

                # Barra di utilizzo visuale
                progress_row = left_col.row()
                progress_row.scale_y = 0.6

                # Semplice barra di progresso usando caratteri
                bar_length = 20
                filled_length = int((usage_percent / 100) * bar_length)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                progress_row.label(text=f"[{bar}]")

            # Colonna destra: directory info
            right_col = stats_split.column()
            right_col.scale_y = 0.8

            cache_dir = cache_stats['cache_dir']
            right_col.label(text="📁 Location:")

            # Mostra directory su più righe se troppo lunga
            if len(cache_dir) > 35:
                # Spezza in parti leggibili
                parts = cache_dir.split(os.sep)
                if len(parts) > 2:
                    right_col.label(text=f"  ...{os.sep}{os.sep.join(parts[-2:])}")
                else:
                    right_col.label(text=f"  {cache_dir}")
            else:
                right_col.label(text=f"  {cache_dir}")

        except Exception as e:
            error_col = box.column()
            error_col.label(text=f"❌ Cache info unavailable: {str(e)}", icon='ERROR')

        # Cache actions con icone e descrizioni
        box = layout.box()
        box.label(text="🛠️ Cache Management", icon='TOOL_SETTINGS')

        actions_col = box.column(align=True)

        # Clear cache con warning
        clear_row = actions_col.row()
        clear_row.scale_y = 1.2
        clear_op = clear_row.operator("openshelf.clear_repository_cache", text="🗑️ Clear All Cache", icon='TRASH')
        clear_op.repository_name = "all"
        clear_op.confirm = True

        # Operazioni aggiuntive
        utils_col = actions_col.column(align=True)
        utils_col.scale_y = 0.9

        utils_col.operator("openshelf.cache_statistics", text="📈 Detailed Statistics", icon='GRAPH')

        if self.custom_cache_directory:
            migrate_op = utils_col.operator("openshelf.migrate_cache", text="📦 Migrate Cache", icon='ARROW_LEFTRIGHT')
            migrate_op.old_directory = ""  # Will be filled by user

        # Tips box
        tips_box = layout.box()
        tips_box.label(text="💡 Cache Tips", icon='LIGHTBULB')

        tips_col = tips_box.column(align=True)
        tips_col.scale_y = 0.8
        tips_col.label(text="• Larger cache = fewer downloads but more disk space")
        tips_col.label(text="• Custom directory = better control over location")
        tips_col.label(text="• Clear cache if you have storage issues")
        tips_col.label(text="• Cache survives Blender restarts")

        if not self.download_cache_enabled:
            tips_col.separator()
            tips_col.label(text="⚡ Enable cache for much faster repeated imports!", icon='INFO')

    def draw_advanced_tab(self, layout):
        """Disegna tab impostazioni avanzate"""

        # Debug settings
        box = layout.box()
        box.label(text="Debug Settings", icon='CONSOLE')

        col = box.column()
        col.prop(self, "debug_mode")
        col.prop(self, "log_level")

        if self.debug_mode:
            col.separator()
            col.label(text="Debug mode enabled - check console for detailed logs")

        # Advanced cache
        box = layout.box()
        box.label(text="Advanced Cache", icon='SETTINGS')

        col = box.column()
        col.prop(self, "custom_cache_directory")

        if self.custom_cache_directory:
            if os.path.exists(self.custom_cache_directory):
                col.label(text="✓ Custom cache directory exists", icon='CHECKMARK')
            else:
                col.label(text="⚠ Custom cache directory not found", icon='ERROR')

        # Performance
        box = layout.box()
        box.label(text="Performance", icon='PREFERENCES')

        col = box.column()
        col.label(text=f"Max concurrent downloads: {self.download_concurrent}")
        col.label(text=f"Repository timeout: {self.repository_timeout}s")
        col.label(text=f"Max cache size: {self.cache_max_size} MB")

        # System info
        box = layout.box()
        box.label(text="System Information", icon='SYSTEM')

        col = box.column()
        col.scale_y = 0.8

        import platform
        import sys

        col.label(text=f"Platform: {platform.system()} {platform.release()}")
        col.label(text=f"Python: {sys.version.split()[0]}")
        col.label(text=f"Blender: {bpy.app.version_string}")

        # Reset to defaults
        box = layout.box()
        box.label(text="Reset Settings", icon='LOOP_BACK')

        row = box.row()
        row.operator("openshelf.reset_preferences", text="Reset to Defaults", icon='FILE_REFRESH')

class OPENSHELF_OT_reset_preferences(bpy.types.Operator):
    """Reset preferenze ai valori di default"""
    bl_idname = "openshelf.reset_preferences"
    bl_label = "Reset Preferences"
    bl_description = "Reset all preferences to default values"
    bl_options = {'REGISTER'}

    confirm: BoolProperty(
        name="Confirm Reset",
        description="Confirm that you want to reset all preferences",
        default=False
    )

    def execute(self, context):
        if not self.confirm:
            self.report({'ERROR'}, "Reset not confirmed")
            return {'CANCELLED'}

        try:
            # Ottieni preferenze addon
            addon_name = __package__.split('.')[0]
            prefs = context.preferences.addons[addon_name].preferences

            # Reset proprietà ai valori default
            prefs.property_unset("default_repository")
            prefs.property_unset("auto_refresh_repositories")
            prefs.property_unset("repository_timeout")
            prefs.property_unset("download_cache_enabled")
            prefs.property_unset("cache_max_size")
            prefs.property_unset("cache_max_age")
            prefs.property_unset("download_concurrent")
            prefs.property_unset("default_import_scale")
            prefs.property_unset("auto_center_objects")
            prefs.property_unset("auto_apply_materials")
            prefs.property_unset("add_cultural_metadata")
            prefs.property_unset("search_results_limit")
            prefs.property_unset("debug_mode")
            prefs.property_unset("custom_cache_directory")

            self.report({'INFO'}, "Preferences reset to defaults")

        except Exception as e:
            print(f"OpenShelf: Error resetting preferences: {e}")
            self.report({'ERROR'}, f"Error resetting preferences: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

def get_addon_preferences(context=None):
    """Utility per ottenere le preferenze addon"""
    if context is None:
        context = bpy.context

    addon_name = __package__.split('.')[0]
    return context.preferences.addons[addon_name].preferences


class OPENSHELF_OT_open_library_folder(Operator):
    """Apre la cartella della libreria locale nel file manager"""
    bl_idname = "openshelf.open_library_folder"
    bl_label = "Open Library Folder"
    bl_description = "Open the local library folder in file manager"

    def execute(self, context):
        try:
            from ..utils.local_library_manager import get_library_manager
            library_manager = get_library_manager()
            library_manager.open_library_folder()
            self.report({'INFO'}, "Library folder opened")
        except Exception as e:
            self.report({'ERROR'}, f"Cannot open library folder: {str(e)}")

        return {'FINISHED'}


class OPENSHELF_OT_reset_library_path(Operator):
    """Reset del path della libreria al default"""
    bl_idname = "openshelf.reset_library_path"
    bl_label = "Reset Library Path"
    bl_description = "Reset library path to default location"

    def execute(self, context):
        # Ottieni preferenze addon
        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        # Reset al path di default
        prefs.local_library_path = ""

        self.report({'INFO'}, "Library path reset to default")
        return {'FINISHED'}


class OPENSHELF_OT_refresh_library(Operator):
    """Aggiorna informazioni libreria"""
    bl_idname = "openshelf.refresh_library"
    bl_label = "Refresh Library"
    bl_description = "Refresh library information and statistics"

    def execute(self, context):
        try:
            # Forza ricreazione del library manager
            from ..utils.local_library_manager import get_library_manager
            global _global_library_manager
            _global_library_manager = None

            # Ricrea manager
            library_manager = get_library_manager()
            stats = library_manager.get_library_stats()

            if stats.get("error"):
                self.report({'ERROR'}, f"Library error: {stats['error']}")
            else:
                asset_count = stats.get("asset_count", 0)
                self.report({'INFO'}, f"Library refreshed: {asset_count} assets found")

        except Exception as e:
            self.report({'ERROR'}, f"Cannot refresh library: {str(e)}")

        return {'FINISHED'}


class OPENSHELF_OT_cleanup_library(Operator):
    """Cleanup della libreria locale"""
    bl_idname = "openshelf.cleanup_library"
    bl_label = "Cleanup Library"
    bl_description = "Remove invalid or corrupted assets from library"

    # Conferma prima della cancellazione
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        try:
            from ..utils.local_library_manager import get_library_manager
            library_manager = get_library_manager()

            # Trova asset corrotti o incompleti
            models_dir = library_manager.models_dir
            cleaned_count = 0

            for asset_dir in models_dir.iterdir():
                if asset_dir.is_dir():
                    # Controlla se ha metadata.json
                    metadata_file = asset_dir / "metadata.json"
                    if not metadata_file.exists():
                        shutil.rmtree(asset_dir)
                        cleaned_count += 1
                        continue

                    # Controlla se ha almeno un file 3D
                    has_3d_file = False
                    for ext in ['.obj', '.gltf', '.glb']:
                        if list(asset_dir.glob(f"*{ext}")):
                            has_3d_file = True
                            break

                    if not has_3d_file:
                        shutil.rmtree(asset_dir)
                        cleaned_count += 1

            if cleaned_count > 0:
                self.report({'INFO'}, f"Cleaned up {cleaned_count} invalid assets")
            else:
                self.report({'INFO'}, "Library is clean, no action needed")

        except Exception as e:
            self.report({'ERROR'}, f"Cleanup error: {str(e)}")

        return {'FINISHED'}

# Lista classi da registrare
classes = [
    OpenShelfPreferences,
    OPENSHELF_OT_reset_preferences,
    OPENSHELF_OT_open_library_folder,
    OPENSHELF_OT_reset_library_path,
    OPENSHELF_OT_refresh_library,
    OPENSHELF_OT_cleanup_library,
]

def register():
    """Registra le preferenze"""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    """Deregistra le preferenze"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
