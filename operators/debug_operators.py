"""
OpenShelf Debug Operators - OPZIONALE
Operatori di debug per troubleshooting problemi di import
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
import os

class OPENSHELF_OT_test_direct_import(Operator):
    """Test import diretto di un file OBJ"""
    bl_idname = "openshelf.test_direct_import"
    bl_label = "Test Direct Import"
    bl_description = "Test direct OBJ import for debugging"
    bl_options = {'REGISTER', 'UNDO'}

    test_file_path: StringProperty(
        name="Test File Path",
        description="Path to OBJ file for testing",
        default="",
        subtype='FILE_PATH'
    )

    def execute(self, context):
        if not self.test_file_path or not os.path.exists(self.test_file_path):
            self.report({'ERROR'}, "Invalid test file path")
            return {'CANCELLED'}

        print(f"\n{'='*50}")
        print(f"OpenShelf: DIRECT IMPORT TEST")
        print(f"{'='*50}")
        print(f"File: {self.test_file_path}")

        try:
            # Test import diretto
            print("Step 1: Clearing selection...")
            bpy.ops.object.select_all(action='DESELECT')

            print("Step 2: Importing OBJ...")

            # Import parameters for Blender 4.2+
            import_params = {
                'filepath': self.test_file_path,

                'use_split_objects': True,
                'use_split_groups': False,
                'forward_axis': 'NEGATIVE_Z',
                'up_axis': 'Y',
            }

            print(f"Import params: {import_params}")

            # DO THE IMPORT
            result = bpy.ops.wm.obj_import(**import_params)
            print(f"Import result: {result}")

            # Check imported objects
            imported_objects = context.selected_objects
            print(f"Step 3: Found {len(imported_objects)} imported objects")

            if imported_objects:
                main_obj = imported_objects[0]
                print(f"Main object: {main_obj.name}")
                print(f"Vertices: {len(main_obj.data.vertices) if main_obj.data else 0}")

                # Test centering
                print("Step 4: Testing centering...")
                bpy.context.view_layer.objects.active = main_obj
                bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
                main_obj.location = (0, 0, 0)
                print("Centering completed")

                self.report({'INFO'}, f"✅ SUCCESS: Imported {main_obj.name}")

            else:
                self.report({'ERROR'}, "❌ FAIL: No objects imported")

        except Exception as e:
            print(f"❌ IMPORT ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Import failed: {str(e)}")

        print(f"{'='*50}\n")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class OPENSHELF_OT_debug_context_info(Operator):
    """Debug informazioni su context e stato Blender"""
    bl_idname = "openshelf.debug_context_info"
    bl_label = "Debug Context Info"
    bl_description = "Show debug info about Blender context"
    bl_options = {'REGISTER'}

    def execute(self, context):
        print(f"\n{'='*50}")
        print(f"OpenShelf: CONTEXT DEBUG INFO")
        print(f"{'='*50}")

        try:
            # Context info
            print(f"Context mode: {context.mode}")
            print(f"Active object: {context.active_object}")
            print(f"Selected objects: {len(context.selected_objects)}")
            print(f"Scene: {context.scene.name}")
            print(f"Collection: {context.collection.name if context.collection else 'None'}")

            # View layer info
            print(f"View layer: {context.view_layer.name}")
            print(f"Objects in scene: {len(context.scene.objects)}")

            # Window and area info
            print(f"Window: {context.window}")
            print(f"Screen: {context.screen.name if context.screen else 'None'}")
            print(f"Area: {context.area.type if context.area else 'None'}")

            # Operator context
            print(f"Region: {context.region.type if context.region else 'None'}")

            # Online access
            print(f"Online access: {getattr(bpy.app, 'online_access', 'Unknown')}")
            print(f"Online overridden: {getattr(bpy.app, 'online_access_overridden', 'Unknown')}")

            # Cache info
            scene = context.scene
            if hasattr(scene, 'openshelf_assets_cache'):
                print(f"Assets in cache: {len(scene.openshelf_assets_cache)}")

            if hasattr(scene, 'openshelf_search_results'):
                print(f"Search results: {len(scene.openshelf_search_results)}")

            if hasattr(scene, 'openshelf_is_downloading'):
                print(f"Is downloading: {scene.openshelf_is_downloading}")

            # Download manager info
            try:
                from ..utils.download_manager import get_download_manager
                dm = get_download_manager()
                cache_stats = dm.get_cache_statistics()
                print(f"Cache files: {cache_stats['file_count']}")
                print(f"Cache size: {cache_stats['cache_size'] / (1024*1024):.1f} MB")
            except Exception as e:
                print(f"Download manager error: {e}")

            self.report({'INFO'}, "Debug info printed to console")

        except Exception as e:
            print(f"❌ DEBUG ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Debug failed: {str(e)}")

        print(f"{'='*50}\n")
        return {'FINISHED'}

class OPENSHELF_OT_emergency_reset(Operator):
    """Reset di emergenza per sbloccare situazioni problematiche"""
    bl_idname = "openshelf.emergency_reset"
    bl_label = "Emergency Reset"
    bl_description = "Emergency reset to clear OpenShelf state"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            scene = context.scene

            # Reset stato download
            if hasattr(scene, 'openshelf_is_downloading'):
                scene.openshelf_is_downloading = False

            if hasattr(scene, 'openshelf_download_progress'):
                scene.openshelf_download_progress = 0

            if hasattr(scene, 'openshelf_status_message'):
                scene.openshelf_status_message = "Ready"

            # Reset selezione
            bpy.ops.object.select_all(action='DESELECT')

            # Force UI update
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            print("OpenShelf: Emergency reset completed")
            self.report({'INFO'}, "Emergency reset completed")

        except Exception as e:
            print(f"OpenShelf: Emergency reset error: {e}")
            self.report({'ERROR'}, f"Reset error: {str(e)}")

        return {'FINISHED'}

class OPENSHELF_OT_test_cache_info(Operator):
    """Mostra informazioni dettagliate sulla cache"""
    bl_idname = "openshelf.test_cache_info"
    bl_label = "Test Cache Info"
    bl_description = "Show detailed cache information"
    bl_options = {'REGISTER'}

    def execute(self, context):
        print(f"\n{'='*50}")
        print(f"OpenShelf: CACHE DEBUG INFO")
        print(f"{'='*50}")

        try:
            from ..utils.download_manager import get_download_manager
            dm = get_download_manager()

            cache_stats = dm.get_cache_statistics()
            print(f"Cache directory: {cache_stats['cache_dir']}")
            print(f"Cache files: {cache_stats['file_count']}")
            print(f"Cache size: {cache_stats['cache_size']} bytes ({cache_stats['cache_size'] / (1024*1024):.1f} MB)")
            print(f"Max cache size: {cache_stats['max_cache_size']} bytes ({cache_stats['max_cache_size'] / (1024*1024):.1f} MB)")

            # Lista files in cache
            cache_dir = cache_stats['cache_dir']
            if os.path.exists(cache_dir):
                cache_files = os.listdir(cache_dir)
                print(f"\nCache files ({len(cache_files)}):")
                for i, file in enumerate(cache_files[:10]):  # Primi 10
                    file_path = os.path.join(cache_dir, file)
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    print(f"  {i+1}. {file} ({file_size} bytes)")

                if len(cache_files) > 10:
                    print(f"  ... and {len(cache_files) - 10} more files")

            self.report({'INFO'}, "Cache info printed to console")

        except Exception as e:
            print(f"❌ CACHE ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Cache debug failed: {str(e)}")

        print(f"{'='*50}\n")
        return {'FINISHED'}

class OPENSHELF_OT_debug_selection(Operator):
    """Debug selezione asset corrente"""
    bl_idname = "openshelf.debug_selection"
    bl_label = "Debug Selection"
    bl_description = "Debug current asset selection"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        print("\n" + "="*50)
        print("OpenShelf: DEBUG ASSET SELECTION")
        print("="*50)

        try:
            # Info selezione corrente
            selected_index = getattr(scene, 'openshelf_selected_result_index', -1)
            total_results = len(getattr(scene, 'openshelf_search_results', []))

            print(f"Selected index: {selected_index}")
            print(f"Total results: {total_results}")

            if hasattr(scene, 'openshelf_search_results') and total_results > 0:
                print(f"\nAll results:")
                for i, result in enumerate(scene.openshelf_search_results):
                    marker = ">>> " if i == selected_index else "    "
                    print(f"{marker}{i}: {result.name} (ID: {result.asset_id})")

                # Asset attualmente selezionato
                if 0 <= selected_index < total_results:
                    selected_result = scene.openshelf_search_results[selected_index]
                    print(f"\n🎯 Currently selected:")
                    print(f"   Name: {selected_result.name}")
                    print(f"   ID: {selected_result.asset_id}")
                    print(f"   Repository: {selected_result.repository}")
                    print(f"   Type: {selected_result.object_type}")
                else:
                    print(f"\n❌ Invalid selection index: {selected_index}")
            else:
                print("\n⚠️  No search results available")

            # Cache info
            cache_count = len(getattr(scene, 'openshelf_assets_cache', []))
            print(f"\nCache: {cache_count} assets")

        except Exception as e:
            print(f"❌ Debug error: {e}")
            import traceback
            traceback.print_exc()

        print("="*50)
        self.report({'INFO'}, f"Debug info printed - Index: {selected_index}/{total_results}")
        return {'FINISHED'}


# Registrazione debug operators
debug_operators = [
    OPENSHELF_OT_test_direct_import,
    OPENSHELF_OT_debug_context_info,
    OPENSHELF_OT_emergency_reset,
    OPENSHELF_OT_test_cache_info,
    OPENSHELF_OT_debug_selection
]

def register():
    """Registra operatori debug"""
    for op in debug_operators:
        bpy.utils.register_class(op)

def unregister():
    """Deregistra operatori debug"""
    for op in reversed(debug_operators):
        bpy.utils.unregister_class(op)
