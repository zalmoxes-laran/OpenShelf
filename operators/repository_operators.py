"""
OpenShelf Repository Operators
Operatori per gestire i repository di asset culturali
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
import threading
from ..repositories.registry import RepositoryRegistry

class OPENSHELF_OT_refresh_repositories(Operator):
    """Aggiorna la lista dei repository"""
    bl_idname = "openshelf.refresh_repositories"
    bl_label = "Refresh Repositories"
    bl_description = "Refresh available repositories list"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            # Aggiorna registry
            RepositoryRegistry.refresh_all_repositories()
            
            # Aggiorna UI
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            self.report({'INFO'}, "Repositories refreshed")
            
        except Exception as e:
            print(f"OpenShelf: Error refreshing repositories: {e}")
            self.report({'ERROR'}, f"Failed to refresh repositories: {str(e)}")
        
        return {'FINISHED'}

class OPENSHELF_OT_test_repository(Operator):
    """Testa la connessione a un repository"""
    bl_idname = "openshelf.test_repository"
    bl_label = "Test Repository"
    bl_description = "Test connection to selected repository"
    bl_options = {'REGISTER'}
    
    repository_name: StringProperty(
        name="Repository Name",
        description="Name of repository to test",
        default=""
    )

    def execute(self, context):
        scene = context.scene
        
        # Usa repository selezionato se non specificato
        repo_name = self.repository_name
        if not repo_name:
            repo_name = scene.openshelf_active_repository
        
        if not repo_name or repo_name == 'all':
            self.report({'ERROR'}, "Please select a specific repository to test")
            return {'CANCELLED'}
        
        # Avvia test in thread separato
        test_thread = threading.Thread(
            target=self._test_repository_thread,
            args=(context, repo_name)
        )
        test_thread.daemon = True
        test_thread.start()
        
        self.report({'INFO'}, f"Testing connection to {repo_name}...")
        
        return {'FINISHED'}
    
    def _test_repository_thread(self, context, repo_name):
        """Thread per testare repository"""
        scene = context.scene
        
        try:
            scene.openshelf_status_message = f"Testing {repo_name}..."
            
            # Testa connessione
            result = RepositoryRegistry.test_repository_connection(repo_name)
            
            # Aggiorna stato
            if result['status'] == 'success':
                scene.openshelf_status_message = f"✓ {repo_name}: {result['message']}"
                print(f"OpenShelf: Repository test successful: {result}")
            elif result['status'] == 'warning':
                scene.openshelf_status_message = f"⚠ {repo_name}: {result['message']}"
                print(f"OpenShelf: Repository test warning: {result}")
            else:
                scene.openshelf_status_message = f"✗ {repo_name}: {result['message']}"
                print(f"OpenShelf: Repository test failed: {result}")
                
        except Exception as e:
            scene.openshelf_status_message = f"✗ {repo_name}: Test error"
            print(f"OpenShelf: Repository test error: {e}")

class OPENSHELF_OT_repository_info(Operator):
    """Mostra informazioni dettagliate su un repository"""
    bl_idname = "openshelf.repository_info"
    bl_label = "Repository Info"
    bl_description = "Show detailed information about repository"
    bl_options = {'REGISTER'}
    
    repository_name: StringProperty(
        name="Repository Name",
        description="Name of repository to show info for",
        default=""
    )

    def execute(self, context):
        scene = context.scene
        
        # Usa repository selezionato se non specificato
        repo_name = self.repository_name
        if not repo_name:
            repo_name = scene.openshelf_active_repository
        
        if not repo_name or repo_name == 'all':
            self.report({'ERROR'}, "Please select a specific repository")
            return {'CANCELLED'}
        
        try:
            # Ottieni informazioni repository
            repo_info = RepositoryRegistry.get_repository_info(repo_name)
            
            if 'error' in repo_info:
                self.report({'ERROR'}, repo_info['error'])
                return {'CANCELLED'}
            
            # Mostra informazioni in popup
            def draw_info_popup(self, context):
                layout = self.layout
                layout.label(text=f"Repository: {repo_info['name']}")
                layout.separator()
                layout.label(text=f"Description: {repo_info['description']}")
                layout.label(text=f"Base URL: {repo_info['base_url']}")
                layout.label(text=f"Language: {repo_info['language']}")
                layout.label(text=f"License: {repo_info['license']}")
                layout.separator()
                layout.label(text="Supported Formats:")
                for fmt in repo_info['supported_formats']:
                    layout.label(text=f"  • {fmt.upper()}")
            
            context.window_manager.popup_menu(
                draw_info_popup, 
                title=f"{repo_name} Information", 
                icon='INFO'
            )
            
        except Exception as e:
            print(f"OpenShelf: Error getting repository info: {e}")
            self.report({'ERROR'}, f"Error getting repository info: {str(e)}")
        
        return {'FINISHED'}

class OPENSHELF_OT_repository_statistics(Operator):
    """Mostra statistiche sui repository"""
    bl_idname = "openshelf.repository_statistics"
    bl_label = "Repository Statistics"
    bl_description = "Show statistics about repositories"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Avvia raccolta statistiche in thread separato
        stats_thread = threading.Thread(
            target=self._collect_statistics_thread,
            args=(context,)
        )
        stats_thread.daemon = True
        stats_thread.start()
        
        self.report({'INFO'}, "Collecting repository statistics...")
        
        return {'FINISHED'}
    
    def _collect_statistics_thread(self, context):
        """Thread per raccogliere statistiche"""
        scene = context.scene
        
        try:
            scene.openshelf_status_message = "Collecting statistics..."
            
            # Ottieni statistiche
            stats = RepositoryRegistry.get_repository_statistics()
            
            # Mostra statistiche (per ora solo stampa)
            print("OpenShelf: Repository Statistics")
            print(f"Total repositories: {stats['total_repositories']}")
            
            for repo_name, repo_stats in stats['repositories'].items():
                print(f"\n{repo_name}:")
                if 'error' in repo_stats:
                    print(f"  Error: {repo_stats['error']}")
                else:
                    print(f"  Total assets: {repo_stats.get('total_assets', 'Unknown')}")
                    print(f"  Assets with 3D: {repo_stats.get('assets_with_3d', 'Unknown')}")
                    
                    # Mostra top 5 tipi oggetto
                    object_types = repo_stats.get('object_types', {})
                    if object_types:
                        print("  Top object types:")
                        sorted_types = sorted(object_types.items(), key=lambda x: x[1], reverse=True)
                        for obj_type, count in sorted_types[:5]:
                            print(f"    {obj_type}: {count}")
            
            scene.openshelf_status_message = "Statistics collected - check console"
            
        except Exception as e:
            scene.openshelf_status_message = f"Statistics error: {str(e)}"
            print(f"OpenShelf: Statistics error: {e}")

class OPENSHELF_OT_clear_repository_cache(Operator):
    """Pulisce la cache di un repository"""
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
        scene = context.scene
        
        if not self.confirm:
            self.report({'ERROR'}, "Cache clearing not confirmed")
            return {'CANCELLED'}
        
        # Usa repository selezionato se non specificato
        repo_name = self.repository_name
        if not repo_name:
            repo_name = scene.openshelf_active_repository
        
        try:
            if repo_name == 'all':
                # Pulisci cache di tutti i repository
                RepositoryRegistry.refresh_all_repositories()
                self.report({'INFO'}, "Cleared cache for all repositories")
            else:
                # Pulisci cache repository specifico
                RepositoryRegistry.refresh_repository(repo_name)
                self.report({'INFO'}, f"Cleared cache for {repo_name}")
                
        except Exception as e:
            print(f"OpenShelf: Error clearing cache: {e}")
            self.report({'ERROR'}, f"Error clearing cache: {str(e)}")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class OPENSHELF_OT_export_repository_config(Operator):
    """Esporta configurazione repository"""
    bl_idname = "openshelf.export_repository_config"
    bl_label = "Export Repository Config"
    bl_description = "Export repository configuration to file"
    bl_options = {'REGISTER'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to save configuration file",
        default="openshelf_repositories.json",
        subtype='FILE_PATH'
    )

    def execute(self, context):
        try:
            # Esporta configurazione
            config = RepositoryRegistry.export_config()
            
            # Salva su file
            import json
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.report({'INFO'}, f"Configuration exported to {self.filepath}")
            
        except Exception as e:
            print(f"OpenShelf: Error exporting config: {e}")
            self.report({'ERROR'}, f"Error exporting config: {str(e)}")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class OPENSHELF_OT_add_custom_repository(Operator):
    """Aggiunge repository personalizzato"""
    bl_idname = "openshelf.add_custom_repository"
    bl_label = "Add Custom Repository"
    bl_description = "Add a custom repository configuration"
    bl_options = {'REGISTER'}
    
    repo_name: StringProperty(
        name="Repository Name",
        description="Name for the custom repository",
        default="My Repository"
    )
    
    repo_url: StringProperty(
        name="Repository URL",
        description="Base URL for the repository",
        default="https://example.com"
    )
    
    repo_description: StringProperty(
        name="Description",
        description="Repository description",
        default="Custom repository"
    )
    
    api_url: StringProperty(
        name="API URL",
        description="API endpoint URL",
        default=""
    )

    def execute(self, context):
        if not self.repo_name or not self.repo_url:
            self.report({'ERROR'}, "Name and URL are required")
            return {'CANCELLED'}
        
        try:
            # Valida configurazione
            config = {
                'name': self.repo_name,
                'base_url': self.repo_url,
                'description': self.repo_description,
                'api_url': self.api_url or self.repo_url
            }
            
            validation = RepositoryRegistry.validate_repository_config(config)
            
            if not validation['valid']:
                error_msg = '; '.join(validation['errors'])
                self.report({'ERROR'}, f"Invalid configuration: {error_msg}")
                return {'CANCELLED'}
            
            # TODO: Implementare registrazione repository custom
            # Per ora solo mostra configurazione
            print(f"OpenShelf: Custom repository config: {config}")
            
            self.report({'INFO'}, f"Custom repository configuration ready: {self.repo_name}")
            
        except Exception as e:
            print(f"OpenShelf: Error adding custom repository: {e}")
            self.report({'ERROR'}, f"Error adding custom repository: {str(e)}")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class OPENSHELF_OT_registry_status(Operator):
    """Mostra stato del registry"""
    bl_idname = "openshelf.registry_status"
    bl_label = "Registry Status"
    bl_description = "Show repository registry status"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            # Ottieni stato registry
            status = RepositoryRegistry.get_status()
            
            # Mostra stato in popup
            def draw_status_popup(self, context):
                layout = self.layout
                layout.label(text="Repository Registry Status")
                layout.separator()
                layout.label(text=f"Initialized: {'Yes' if status['initialized'] else 'No'}")
                layout.label(text=f"Repository count: {status['repository_count']}")
                layout.separator()
                layout.label(text="Available repositories:")
                for repo_name in status['available_repositories']:
                    layout.label(text=f"  • {repo_name}")
            
            context.window_manager.popup_menu(
                draw_status_popup, 
                title="Registry Status", 
                icon='INFO'
            )
            
        except Exception as e:
            print(f"OpenShelf: Error getting registry status: {e}")
            self.report({'ERROR'}, f"Error getting registry status: {str(e)}")
        
        return {'FINISHED'}

# Lista operatori da registrare
operators = [
    OPENSHELF_OT_refresh_repositories,
    OPENSHELF_OT_test_repository,
    OPENSHELF_OT_repository_info,
    OPENSHELF_OT_repository_statistics,
    OPENSHELF_OT_clear_repository_cache,
    OPENSHELF_OT_export_repository_config,
    OPENSHELF_OT_add_custom_repository,
    OPENSHELF_OT_registry_status,
]

def register():
    """Registra gli operatori repository"""
    for op in operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra gli operatori repository"""
    for op in reversed(operators):
        bpy.utils.unregister_class(op)
