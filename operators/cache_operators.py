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

class OPENSHELF_OT_clear_repository_cache(Operator):
    """Pulisce la cache di un repository - VERSIONE CORRETTA"""
    bl_idname = "openshelf.clear_repository_cache"
    bl_label = "Clear Repository Cache"
    bl_description = "Clear cache for selected repository"
    bl_options = {'REGISTER'}

    repository_name: StringProperty(
        name="Repository Name",
        description="Name of repository to clear cache for",
        default=""
    )

    confirm: BoolProperty(
        name="Confirm",
        description="Confirm cache clearing",
        default=False
    )

    def execute(self, context):
        if not self.confirm:
            return self.invoke(context, None)

        try:
            from ..utils.download_manager import get_download_manager

            # FIX: Ottieni download manager con directory custom se impostata
            addon_name = __package__.split('.')[0]
            prefs = context.preferences.addons[addon_name].preferences

            if hasattr(prefs, 'custom_cache_directory') and prefs.custom_cache_directory.strip():
                from ..utils.download_manager import DownloadManager
                dm = DownloadManager(prefs.custom_cache_directory.strip())
            else:
                dm = get_download_manager()

            # Pulisci cache
            if self.repository_name == 'all':
                # Pulisci tutta la cache
                dm.clear_cache()
                self.report({'INFO'}, "Cleared all cache")
                print("OpenShelf: All cache cleared")
            else:
                # Per ora pulisci tutto (in futuro: cache specifica per repository)
                dm.clear_cache()
                self.report({'INFO'}, f"Cleared cache for {self.repository_name}")
                print(f"OpenShelf: Cache cleared for {self.repository_name}")

            # Force UI update
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

        except Exception as e:
            print(f"OpenShelf: Error clearing cache: {e}")
            self.report({'ERROR'}, f"Error clearing cache: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        if self.confirm:
            return self.execute(context)

        # Mostra dialog di conferma
        return context.window_manager.invoke_confirm(self, event)

    def draw(self, context):
        layout = self.layout
        layout.label(text="This will delete all cached files.", icon='ERROR')
        layout.label(text="Files will be re-downloaded when needed.")
        if self.repository_name == 'all':
            layout.label(text="This affects ALL repositories.")

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

# Lista operatori da registrare
operators = [
    OPENSHELF_OT_clear_repository_cache,
    OPENSHELF_OT_open_cache_directory,
    OPENSHELF_OT_reset_cache_directory,
    OPENSHELF_OT_migrate_cache,
    OPENSHELF_OT_cache_statistics,
    OPENSHELF_OT_cache_health_report,
]

def register():
    """Registra gli operatori cache"""
    for op in operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra gli operatori cache"""
    for op in reversed(operators):
        bpy.utils.unregister_class(op)
