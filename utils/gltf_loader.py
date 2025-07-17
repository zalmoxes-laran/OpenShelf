"""
OpenShelf GLTF/GLB Loader
Loader riutilizzabile per file GLTF/GLB con supporto metadati culturali
"""

import bpy
import os
from typing import Optional, Dict, Any, List
from mathutils import Vector

class GLTFLoader:
    """Loader riutilizzabile per file GLTF/GLB"""
    
    @staticmethod
    def import_gltf(filepath: str, **kwargs) -> Optional[bpy.types.Object]:
        """
        Importa un file GLTF/GLB in Blender
        
        Args:
            filepath: Path al file GLTF/GLB
            **kwargs: Parametri aggiuntivi per l'import
            
        Returns:
            Oggetto principale importato o None se errore
        """
        try:
            # Salva selezione e contesto corrente
            original_selection = bpy.context.selected_objects.copy()
            original_active = bpy.context.view_layer.objects.active
            
            # Deseleziona tutto
            bpy.ops.object.select_all(action='DESELECT')
            
            # Parametri import con defaults
            import_params = {
                'filepath': filepath,
                'import_pack_images': kwargs.get('import_pack_images', True),
                'merge_vertices': kwargs.get('merge_vertices', False),
                'import_shading': kwargs.get('import_shading', 'NORMALS'),
                'bone_heuristic': kwargs.get('bone_heuristic', 'TEMPERANCE'),
                'guess_original_bind_pose': kwargs.get('guess_original_bind_pose', True),
                'import_user_extensions': kwargs.get('import_user_extensions', True),
                'import_extras': kwargs.get('import_extras', True),
                'import_cameras': kwargs.get('import_cameras', True),
                'import_lights': kwargs.get('import_lights', True),
                'import_materials': kwargs.get('import_materials', 'IMPORT'),
                'import_colors': kwargs.get('import_colors', True),
                'import_ws_normals': kwargs.get('import_ws_normals', True),
                'import_tangents': kwargs.get('import_tangents', False),
                'loglevel': kwargs.get('loglevel', 0),
                'import_original_specular': kwargs.get('import_original_specular', False),
            }
            
            # Importa GLTF
            bpy.ops.import_scene.gltf(**import_params)
            
            # Trova oggetti importati
            new_objects = [obj for obj in bpy.context.selected_objects if obj not in original_selection]
            
            if new_objects:
                # Trova l'oggetto principale (più grande o con più geometria)
                main_object = GLTFLoader._find_main_object(new_objects)
                
                # Applica post-processing
                GLTFLoader._post_process_objects(new_objects, **kwargs)
                
                return main_object
            
            return None
            
        except Exception as e:
            print(f"OpenShelf: Error importing GLTF {filepath}: {e}")
            return None
    
    @staticmethod
    def _find_main_object(objects: List[bpy.types.Object]) -> bpy.types.Object:
        """Trova l'oggetto principale tra quelli importati"""
        mesh_objects = [obj for obj in objects if obj.type == 'MESH']
        
        if not mesh_objects:
            return objects[0] if objects else None
        
        # Ordina per numero di vertici (oggetto più complesso)
        mesh_objects.sort(key=lambda obj: len(obj.data.vertices) if obj.data else 0, reverse=True)
        
        return mesh_objects[0]
    
    @staticmethod
    def _post_process_objects(objects: List[bpy.types.Object], **kwargs):
        """Applica post-processing agli oggetti importati"""
        
        # Raggruppa oggetti se richiesto
        if kwargs.get('group_objects', True):
            GLTFLoader._group_objects(objects, kwargs.get('group_name', 'GLTF_Import'))
        
        # Centra oggetti se richiesto
        if kwargs.get('auto_center', True):
            GLTFLoader._center_objects(objects)
        
        # Applica scala se richiesta
        scale_factor = kwargs.get('scale_factor', 1.0)
        if scale_factor != 1.0:
            GLTFLoader._scale_objects(objects, scale_factor)
    
    @staticmethod
    def _group_objects(objects: List[bpy.types.Object], group_name: str):
        """Raggruppa oggetti in una collezione"""
        try:
            # Crea collezione se non esiste
            if group_name not in bpy.data.collections:
                collection = bpy.data.collections.new(group_name)
                bpy.context.scene.collection.children.link(collection)
            else:
                collection = bpy.data.collections[group_name]
            
            # Sposta oggetti nella collezione
            for obj in objects:
                # Rimuovi da collezioni esistenti
                for coll in obj.users_collection:
                    coll.objects.unlink(obj)
                
                # Aggiungi alla nuova collezione
                collection.objects.link(obj)
                
        except Exception as e:
            print(f"OpenShelf: Error grouping objects: {e}")
    
    @staticmethod
    def _center_objects(objects: List[bpy.types.Object]):
        """Centra il gruppo di oggetti nell'origine"""
        try:
            if not objects:
                return
            
            # Calcola bounding box combinato
            min_coords = Vector((float('inf'), float('inf'), float('inf')))
            max_coords = Vector((float('-inf'), float('-inf'), float('-inf')))
            
            for obj in objects:
                if obj.type == 'MESH' and obj.data:
                    # Trasforma coordinate locali in globali
                    matrix = obj.matrix_world
                    for vertex in obj.data.vertices:
                        world_coord = matrix @ vertex.co
                        
                        for i in range(3):
                            min_coords[i] = min(min_coords[i], world_coord[i])
                            max_coords[i] = max(max_coords[i], world_coord[i])
            
            # Calcola centro
            center = (min_coords + max_coords) / 2
            
            # Sposta tutti gli oggetti
            for obj in objects:
                obj.location -= center
                
        except Exception as e:
            print(f"OpenShelf: Error centering objects: {e}")
    
    @staticmethod
    def _scale_objects(objects: List[bpy.types.Object], scale_factor: float):
        """Scala tutti gli oggetti"""
        try:
            for obj in objects:
                obj.scale = (scale_factor, scale_factor, scale_factor)
        except Exception as e:
            print(f"OpenShelf: Error scaling objects: {e}")
    
    @staticmethod
    def apply_cultural_metadata(main_object: bpy.types.Object, all_objects: List[bpy.types.Object], asset_data: Dict[str, Any]):
        """Applica metadati culturali agli oggetti importati"""
        if not main_object or not all_objects:
            return
        
        try:
            # Prefisso per le proprietà OpenShelf
            prefix = "openshelf_"
            
            # Applica metadati all'oggetto principale
            basic_metadata = {
                "id": asset_data.get("id", ""),
                "name": asset_data.get("name", ""),
                "description": asset_data.get("description", ""),
                "repository": asset_data.get("repository", ""),
                "object_type": asset_data.get("object_type", ""),
                "inventory_number": asset_data.get("inventory_number", ""),
                "provenance": asset_data.get("provenance", ""),
                "license": asset_data.get("license_info", ""),
                "file_format": "gltf",
                "import_timestamp": str(bpy.context.scene.frame_current),
                "total_objects": len(all_objects)
            }
            
            for key, value in basic_metadata.items():
                if value:
                    main_object[f"{prefix}{key}"] = str(value)
            
            # Applica metadati array
            array_metadata = {
                "materials": asset_data.get("materials", []),
                "chronology": asset_data.get("chronology", []),
                "tags": asset_data.get("tags", []),
                "model_urls": asset_data.get("model_urls", [])
            }
            
            for key, value in array_metadata.items():
                if value:
                    main_object[f"{prefix}{key}"] = ", ".join(str(v) for v in value)
            
            # Applica metadati numerici
            numeric_metadata = {
                "quality_score": asset_data.get("quality_score", 0),
                "file_size": asset_data.get("file_size", 0),
                "has_textures": asset_data.get("has_textures", True)  # GLTF di solito ha texture
            }
            
            for key, value in numeric_metadata.items():
                main_object[f"{prefix}{key}"] = value
            
            # Applica metadati base a tutti gli oggetti correlati
            for obj in all_objects:
                if obj != main_object:
                    obj[f"{prefix}parent_id"] = asset_data.get("id", "")
                    obj[f"{prefix}repository"] = asset_data.get("repository", "")
                    obj[f"{prefix}main_object"] = main_object.name
            
            print(f"OpenShelf: Applied cultural metadata to GLTF import ({len(all_objects)} objects)")
            
        except Exception as e:
            print(f"OpenShelf: Error applying cultural metadata to GLTF: {e}")
    
    @staticmethod
    def get_import_settings_for_repository(repository_name: str) -> Dict[str, Any]:
        """Ottiene impostazioni di import GLTF specifiche per repository"""
        
        repository_settings = {
            "Ercolano": {
                "import_pack_images": True,
                "merge_vertices": False,
                "import_shading": "NORMALS",
                "import_materials": "IMPORT",
                "import_colors": True,
                "auto_center": True,
                "scale_factor": 1.0,
                "group_objects": True,
                "group_name": "Ercolano_Import"
            },
            "default": {
                "import_pack_images": True,
                "merge_vertices": False,
                "import_shading": "NORMALS",
                "import_materials": "IMPORT",
                "import_colors": True,
                "auto_center": True,
                "scale_factor": 1.0,
                "group_objects": True,
                "group_name": "GLTF_Import"
            }
        }
        
        return repository_settings.get(repository_name, repository_settings["default"])
    
    @staticmethod
    def import_with_cultural_metadata(filepath: str, asset_data: Dict[str, Any]) -> Optional[bpy.types.Object]:
        """
        Importa GLTF con metadati culturali
        
        Args:
            filepath: Path al file GLTF/GLB
            asset_data: Dati dell'asset culturale
            
        Returns:
            Oggetto principale importato con metadati applicati
        """
        try:
            # Ottieni impostazioni per repository
            repository = asset_data.get("repository", "default")
            import_settings = GLTFLoader.get_import_settings_for_repository(repository)
            
            # Salva stato prima dell'import
            objects_before = set(bpy.context.scene.objects)
            
            # Importa oggetto
            main_object = GLTFLoader.import_gltf(filepath, **import_settings)
            
            if main_object:
                # Trova tutti gli oggetti importati
                objects_after = set(bpy.context.scene.objects)
                new_objects = list(objects_after - objects_before)
                
                # Applica metadati culturali
                GLTFLoader.apply_cultural_metadata(main_object, new_objects, asset_data)
                
                # Rinomina oggetto principale
                inventory_number = asset_data.get("inventory_number", "")
                object_type = asset_data.get("object_type", "")
                
                if inventory_number and object_type:
                    main_object.name = f"{inventory_number}_{object_type}_GLTF"
                elif inventory_number:
                    main_object.name = f"{inventory_number}_GLTF"
                elif object_type:
                    main_object.name = f"{object_type}_GLTF"
                else:
                    main_object.name = f"Cultural_Asset_{asset_data.get('id', 'unknown')}_GLTF"
                
                # Assicurati che il nome sia valido per Blender
                main_object.name = main_object.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                
                print(f"OpenShelf: Successfully imported GLTF {main_object.name} with cultural metadata")
                
            return main_object
            
        except Exception as e:
            print(f"OpenShelf: Error importing GLTF with cultural metadata: {e}")
            return None
    
    @staticmethod
    def validate_gltf_file(filepath: str) -> Dict[str, Any]:
        """
        Valida un file GLTF/GLB
        
        Args:
            filepath: Path al file GLTF/GLB
            
        Returns:
            Dizionario con risultati validazione
        """
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": {}
        }
        
        try:
            if not os.path.exists(filepath):
                result["errors"].append("File does not exist")
                return result
            
            file_ext = os.path.splitext(filepath)[1].lower()
            if file_ext not in ['.gltf', '.glb']:
                result["errors"].append("File is not a GLTF/GLB file")
                return result
            
            # Controlla dimensione file
            file_size = os.path.getsize(filepath)
            result["info"]["file_size"] = file_size
            result["info"]["file_type"] = file_ext
            
            if file_size == 0:
                result["errors"].append("File is empty")
                return result
            
            if file_size > 500 * 1024 * 1024:  # 500MB
                result["warnings"].append("File is very large (>500MB)")
            
            # Validazione specifica per tipo file
            if file_ext == '.gltf':
                # File GLTF è JSON, controlliamo la struttura base
                try:
                    import json
                    with open(filepath, 'r', encoding='utf-8') as f:
                        gltf_data = json.load(f)
                    
                    # Controlla campi obbligatori
                    if "asset" not in gltf_data:
                        result["errors"].append("Missing required 'asset' field")
                    
                    if "scenes" not in gltf_data:
                        result["warnings"].append("No scenes found in GLTF")
                    
                    if "nodes" not in gltf_data:
                        result["warnings"].append("No nodes found in GLTF")
                    
                    result["info"]["scenes_count"] = len(gltf_data.get("scenes", []))
                    result["info"]["nodes_count"] = len(gltf_data.get("nodes", []))
                    result["info"]["meshes_count"] = len(gltf_data.get("meshes", []))
                    result["info"]["materials_count"] = len(gltf_data.get("materials", []))
                    
                except json.JSONDecodeError as e:
                    result["errors"].append(f"Invalid JSON format: {str(e)}")
                    
            elif file_ext == '.glb':
                # File GLB è binario, controlliamo l'header
                try:
                    with open(filepath, 'rb') as f:
                        # Leggi header GLB (primi 12 bytes)
                        header = f.read(12)
                        
                        if len(header) < 12:
                            result["errors"].append("GLB file too short")
                        else:
                            # Controlla magic number
                            magic = header[:4]
                            if magic != b'glTF':
                                result["errors"].append("Invalid GLB magic number")
                            
                            # Leggi versione
                            version = int.from_bytes(header[4:8], byteorder='little')
                            result["info"]["gltf_version"] = version
                            
                            if version not in [1, 2]:
                                result["warnings"].append(f"Unsupported GLTF version: {version}")
                            
                            # Leggi lunghezza totale
                            total_length = int.from_bytes(header[8:12], byteorder='little')
                            result["info"]["declared_length"] = total_length
                            
                            if total_length != file_size:
                                result["warnings"].append("File size doesn't match declared length")
                                
                except Exception as e:
                    result["errors"].append(f"Error reading GLB header: {str(e)}")
            
            if not result["errors"]:
                result["valid"] = True
            
        except Exception as e:
            result["errors"].append(f"Error validating file: {str(e)}")
        
        return result
    
    @staticmethod
    def get_gltf_info(filepath: str) -> Dict[str, Any]:
        """
        Ottiene informazioni dettagliate su un file GLTF/GLB
        
        Args:
            filepath: Path al file GLTF/GLB
            
        Returns:
            Dizionario con informazioni dettagliate
        """
        validation = GLTFLoader.validate_gltf_file(filepath)
        
        if not validation["valid"]:
            return validation
        
        info = validation["info"].copy()
        info["filepath"] = filepath
        info["filename"] = os.path.basename(filepath)
        
        return info
