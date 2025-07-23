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
            ('ADVANCED', 'Advanced', 'Advanced and debug settings'),
        ],
        default='GENERAL'
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
        elif self.prefs_tab == "ADVANCED":
            self.draw_advanced_tab(layout)

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
        """Disegna tab impostazioni cache - VERSIONE CORRETTA"""

        # Cache settings
        box = layout.box()
        box.label(text="Cache Settings", icon='FILE_CACHE')

        col = box.column()
        col.prop(self, "download_cache_enabled")

        if self.download_cache_enabled:
            col.prop(self, "cache_max_size")
            col.prop(self, "cache_max_age")

            # FIX: Cartella cache personalizzata con migliore UI
            cache_box = col.box()
            cache_box.label(text="Cache Directory", icon='FOLDER_REDIRECT')

            cache_col = cache_box.column()
            cache_col.prop(self, "custom_cache_directory", text="Custom Path")

            # Info sulla directory corrente
            if self.custom_cache_directory and os.path.exists(self.custom_cache_directory):
                cache_col.label(text="✓ Custom directory exists", icon='CHECKMARK')
            elif self.custom_cache_directory:
                cache_col.label(text="⚠ Directory not found - will be created", icon='ERROR')
            else:
                import tempfile
                default_cache = os.path.join(tempfile.gettempdir(), "openshelf_cache")
                cache_col.label(text=f"Using default: {default_cache}", icon='INFO')

        else:
            col.label(text="Cache disabled - files will be downloaded each time")

        # Cache info
        box = layout.box()
        box.label(text="Cache Information", icon='INFO')

        # FIX: Migliore gestione errori per cache stats
        try:
            from ..utils.download_manager import get_download_manager
            dm = get_download_manager()

            # FIX: Se custom cache directory è impostata, la usa
            if self.custom_cache_directory and self.custom_cache_directory.strip():
                # Ricrea download manager con custom directory
                from ..utils.download_manager import DownloadManager
                dm = DownloadManager(self.custom_cache_directory.strip())

            cache_stats = dm.get_cache_statistics()

            col = box.column()
            col.scale_y = 0.8
            col.label(text=f"Current cache size: {cache_stats['cache_size'] / (1024*1024):.1f} MB")
            col.label(text=f"Cached files: {cache_stats['file_count']}")

            # Mostra directory attiva
            cache_dir = cache_stats['cache_dir']
            if len(cache_dir) > 50:
                cache_dir = "..." + cache_dir[-47:]
            col.label(text=f"Directory: {cache_dir}")

            # Percentage utilizzata
            if cache_stats['file_count'] > 0:
                usage_percent = (cache_stats['cache_size'] / (1024*1024)) / self.cache_max_size * 100
                col.label(text=f"Usage: {usage_percent:.1f}% of {self.cache_max_size} MB limit")

        except Exception as e:
            col = box.column()
            col.label(text=f"Cache info unavailable: {str(e)}")

        # Cache actions
        box = layout.box()
        box.label(text="Cache Actions", icon='TOOL_SETTINGS')

        col = box.column(align=True)

        # FIX: Clear cache button corretto
        clear_op = col.operator("openshelf.clear_repository_cache", text="Clear All Cache", icon='TRASH')
        clear_op.repository_name = "all"
        clear_op.confirm = True

        # Operazioni aggiuntive
        col.operator("openshelf.open_cache_directory", text="Open Cache Folder", icon='FILE_FOLDER')

        if self.custom_cache_directory:
            col.operator("openshelf.reset_cache_directory", text="Reset to Default", icon='LOOP_BACK')

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

# Lista classi da registrare
classes = [
    OpenShelfPreferences,
    OPENSHELF_OT_reset_preferences,
]

def register():
    """Registra le preferenze"""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    """Deregistra le preferenze"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
