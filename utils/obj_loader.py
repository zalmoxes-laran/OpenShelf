"""
OpenShelf OBJ Loader - VERSIONE CORRETTA PER BLENDER 4.2+
Loader riutilizzabile per file OBJ con supporto materiali e metadati culturali
FIX: Parametri corretti per bpy.ops.wm.obj_import in Blender 4.2+
"""

import bpy
import os
import bmesh
from mathutils import Vector
from typing import Optional, Dict, Any, List

class OBJLoader:
    """Loader riutilizzabile per file OBJ"""

    @staticmethod
    def import_obj(filepath: str, **kwargs) -> Optional[bpy.types.Object]:
        """
        Importa un file OBJ in Blender - VERSIONE CORRETTA PER BLENDER 4.2+

        Args:
            filepath: Path al file OBJ
            **kwargs: Parametri aggiuntivi per l'import

        Returns:
            Oggetto principale importato o None se errore
        """
        try:
            # Salva selezione e contesto corrente (con gestione errori thread-safe)
            original_selection = []
            original_active = None

            try:
                if hasattr(bpy.context, 'selected_objects'):
                    original_selection = bpy.context.selected_objects.copy()
                if hasattr(bpy.context, 'view_layer') and hasattr(bpy.context.view_layer, 'objects'):
                    original_active = bpy.context.view_layer.objects.active

                # Deseleziona tutto
                bpy.ops.object.select_all(action='DESELECT')
            except (AttributeError, RuntimeError):
                print("OpenShelf: Context not available, proceeding anyway")

            # PARAMETRI CORRETTI PER BLENDER 4.2+ (FIX PRINCIPALE)
            import_params = {
                'filepath': filepath,
                #'use_smooth_groups': kwargs.get('use_smooth_groups', True),
                'use_split_objects': kwargs.get('use_split_objects', True),
                'use_split_groups': kwargs.get('use_split_groups', False),
                # *** FIX CRITICO: Parametri corretti per Blender 4.2+ ***
                'forward_axis': kwargs.get('forward_axis', 'NEGATIVE_Z'),  # Era 'axis_forward'
                'up_axis': kwargs.get('up_axis', 'Y'),                    # Era 'axis_up'
            }

            # Aggiungi parametri opzionali solo se specificati e validi
            if kwargs.get('global_scale', 0.0) > 0:
                import_params['global_scale'] = kwargs.get('global_scale', 1.0)

            print(f"OpenShelf: Importing OBJ with parameters: {list(import_params.keys())}")

            # IMPORT CON GESTIONE ERRORI ROBUSTA
            try:
                # Import OBJ con parametri corretti
                result = bpy.ops.wm.obj_import(**import_params)
                print(f"OpenShelf: OBJ import result: {result}")

            except TypeError as e:
                if "unexpected keyword argument" in str(e) or "unrecognized" in str(e):
                    print(f"OpenShelf: Parameter error, using minimal import: {e}")
                    # Fallback: solo parametri essenziali
                    minimal_params = {
                        'filepath': filepath,

                        'use_split_objects': True,
                        'forward_axis': 'NEGATIVE_Z',
                        'up_axis': 'Y'
                    }
                    result = bpy.ops.wm.obj_import(**minimal_params)
                else:
                    raise

            # Trova oggetti importati (thread-safe)
            new_objects = []
            try:
                if hasattr(bpy.context, 'selected_objects'):
                    new_objects = [obj for obj in bpy.context.selected_objects if obj not in original_selection]
                else:
                    # Fallback: trova oggetti con nomi che contengono il nome del file
                    base_name = os.path.splitext(os.path.basename(filepath))[0]
                    new_objects = [obj for obj in bpy.data.objects if base_name in obj.name]
            except Exception as e:
                print(f"OpenShelf: Error finding imported objects: {e}")
                # Ultimo fallback: prendi l'ultimo oggetto aggiunto
                all_objects = list(bpy.data.objects)
                if all_objects:
                    new_objects = [all_objects[-1]]

            if new_objects:
                # Restituisce il primo oggetto (principale)
                main_object = new_objects[0]

                # Applica post-processing
                OBJLoader._post_process_object(main_object, **kwargs)

                print(f"OpenShelf: Successfully imported OBJ: {main_object.name}")
                return main_object

            print(f"OpenShelf: No objects found after importing {filepath}")
            return None

        except Exception as e:
            print(f"OpenShelf: Error importing OBJ {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def _post_process_object(obj: bpy.types.Object, **kwargs):
        """Applica post-processing all'oggetto importato"""

        # Centra oggetto se richiesto
        if kwargs.get('auto_center', True):
            OBJLoader._center_object(obj)

        # Applica scala se richiesta
        scale_factor = kwargs.get('import_scale', kwargs.get('scale_factor', 1.0))
        if scale_factor != 1.0:
            obj.scale = (scale_factor, scale_factor, scale_factor)

        # Applica materiali se richiesto
        if kwargs.get('auto_materials', kwargs.get('apply_materials', True)):
            OBJLoader._setup_materials(obj)

        # Calcola normali se richiesto
        if kwargs.get('recalculate_normals', False):
            OBJLoader._recalculate_normals(obj)

    @staticmethod
    def _center_object(obj: bpy.types.Object):
        """Centra l'oggetto nell'origine"""
        try:
            # Assicurati che l'oggetto sia selezionato e attivo
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            # Centra geometria
            bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')

            # Sposta all'origine
            obj.location = (0, 0, 0)

        except Exception as e:
            print(f"OpenShelf: Error centering object: {e}")

    @staticmethod
    def _setup_materials(obj: bpy.types.Object):
        """Configura i materiali per l'oggetto"""
        try:
            if not obj.data or not hasattr(obj.data, 'materials'):
                return

            # Cicla attraverso i materiali
            for i, material in enumerate(obj.data.materials):
                if material is None:
                    continue

                # Assicurati che il materiale usi nodes
                if not material.use_nodes:
                    material.use_nodes = True

                # Configura nodi base se necessario
                OBJLoader._setup_material_nodes(material)

        except Exception as e:
            print(f"OpenShelf: Error setting up materials: {e}")

    @staticmethod
    def _setup_material_nodes(material: bpy.types.Material):
        """Configura i nodi del materiale"""
        try:
            nodes = material.node_tree.nodes
            links = material.node_tree.links

            # Trova nodi principali
            principled = None
            output = None

            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled = node
                elif node.type == 'OUTPUT_MATERIAL':
                    output = node

            # Crea nodi se non esistono
            if principled is None:
                principled = nodes.new(type='ShaderNodeBsdfPrincipled')
                principled.location = (0, 0)

            if output is None:
                output = nodes.new(type='ShaderNodeOutputMaterial')
                output.location = (400, 0)

            # Collega nodi
            if not any(link.from_node == principled and link.to_node == output for link in links):
                links.new(principled.outputs['BSDF'], output.inputs['Surface'])

        except Exception as e:
            print(f"OpenShelf: Error setting up material nodes: {e}")

    @staticmethod
    def _recalculate_normals(obj: bpy.types.Object):
        """Ricalcola le normali dell'oggetto"""
        try:
            # Passa in edit mode
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')

            # Seleziona tutto
            bpy.ops.mesh.select_all(action='SELECT')

            # Ricalcola normali
            bpy.ops.mesh.normals_make_consistent(inside=False)

            # Torna in object mode
            bpy.ops.object.mode_set(mode='OBJECT')

        except Exception as e:
            print(f"OpenShelf: Error recalculating normals: {e}")
            # Assicurati di tornare in object mode
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass

    @staticmethod
    def apply_cultural_metadata(obj: bpy.types.Object, asset_data: Dict[str, Any]):
        """Applica metadati culturali all'oggetto importato"""
        if not obj:
            return

        try:
            # Prefisso per le proprietà OpenShelf
            prefix = "openshelf_"

            # Applica metadati base
            basic_metadata = {
                "id": asset_data.get("id", ""),
                "name": asset_data.get("name", ""),
                "description": asset_data.get("description", ""),
                "repository": asset_data.get("repository", ""),
                "object_type": asset_data.get("object_type", ""),
                "inventory_number": asset_data.get("inventory_number", ""),
                "provenance": asset_data.get("provenance", ""),
                "license": asset_data.get("license_info", ""),
                "import_timestamp": str(bpy.context.scene.frame_current)
            }

            for key, value in basic_metadata.items():
                if value:
                    obj[f"{prefix}{key}"] = str(value)

            # Applica metadati array (converti in stringa)
            array_metadata = {
                "materials": asset_data.get("materials", []),
                "chronology": asset_data.get("chronology", []),
                "tags": asset_data.get("tags", []),
                "model_urls": asset_data.get("model_urls", [])
            }

            for key, value in array_metadata.items():
                if value:
                    if isinstance(value, list):
                        obj[f"{prefix}{key}"] = ", ".join(str(v) for v in value)
                    else:
                        obj[f"{prefix}{key}"] = str(value)

            # Applica metadati numerici
            numeric_metadata = {
                "quality_score": asset_data.get("quality_score", 0),
                "file_size": asset_data.get("file_size", 0),
                "has_textures": asset_data.get("has_textures", False)
            }

            for key, value in numeric_metadata.items():
                obj[f"{prefix}{key}"] = value

            # Applica metadati estesi se disponibili
            extended_metadata = asset_data.get("metadata", {})
            for key, value in extended_metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    obj[f"{prefix}meta_{key}"] = value

            print(f"OpenShelf: Applied cultural metadata to {obj.name}")

        except Exception as e:
            print(f"OpenShelf: Error applying cultural metadata: {e}")

    @staticmethod
    def get_import_settings_for_repository(repository_name: str) -> Dict[str, Any]:
        """Ottiene impostazioni di import specifiche per repository"""

        # Impostazioni per repository specifici
        repository_settings = {
            "Ercolano": {
                #"use_smooth_groups": True,
                "use_split_objects": True,
                "use_split_groups": False,
                "auto_center": True,
                "import_scale": 1.0,
                "apply_materials": True,
                "recalculate_normals": False,
                "forward_axis": 'NEGATIVE_Z',
                "up_axis": 'Y'
            },
            # Futuro: aggiungere impostazioni per altri repository
            "default": {
                #"use_smooth_groups": True,
                "use_split_objects": True,
                "use_split_groups": False,
                "auto_center": True,
                "import_scale": 1.0,
                "apply_materials": True,
                "recalculate_normals": False,
                "forward_axis": 'NEGATIVE_Z',
                "up_axis": 'Y'
            }
        }

        return repository_settings.get(repository_name, repository_settings["default"])

    @staticmethod
    def import_with_cultural_metadata(filepath: str, asset_data: Dict[str, Any]) -> Optional[bpy.types.Object]:
        """
        Importa OBJ con metadati culturali

        Args:
            filepath: Path al file OBJ
            asset_data: Dati dell'asset culturale

        Returns:
            Oggetto importato con metadati applicati
        """
        try:
            # Ottieni impostazioni per repository
            repository = asset_data.get("repository", "default")
            import_settings = OBJLoader.get_import_settings_for_repository(repository)

            # Importa oggetto
            obj = OBJLoader.import_obj(filepath, **import_settings)

            if obj:
                # Applica metadati culturali
                OBJLoader.apply_cultural_metadata(obj, asset_data)

                # Rinomina oggetto
                inventory_number = asset_data.get("inventory_number", "")
                object_type = asset_data.get("object_type", "")

                if inventory_number and object_type:
                    obj.name = f"{inventory_number}_{object_type}"
                elif inventory_number:
                    obj.name = inventory_number
                elif object_type:
                    obj.name = object_type
                else:
                    obj.name = f"Cultural_Asset_{asset_data.get('id', 'unknown')}"

                # Assicurati che il nome sia valido per Blender
                obj.name = obj.name.replace(" ", "_").replace("/", "_").replace("\\", "_")

                print(f"OpenShelf: Successfully imported {obj.name} with cultural metadata")

            return obj

        except Exception as e:
            print(f"OpenShelf: Error importing OBJ with cultural metadata: {e}")
            return None

    @staticmethod
    def batch_import_obj(file_list: List[str], asset_data_list: List[Dict[str, Any]]) -> List[bpy.types.Object]:
        """
        Importa multipli file OBJ con metadati

        Args:
            file_list: Lista di path ai file OBJ
            asset_data_list: Lista di dati asset corrispondenti

        Returns:
            Lista di oggetti importati
        """
        imported_objects = []

        for filepath, asset_data in zip(file_list, asset_data_list):
            try:
                obj = OBJLoader.import_with_cultural_metadata(filepath, asset_data)
                if obj:
                    imported_objects.append(obj)
            except Exception as e:
                print(f"OpenShelf: Error in batch import for {filepath}: {e}")
                continue

        return imported_objects

    @staticmethod
    def validate_obj_file(filepath: str) -> Dict[str, Any]:
        """
        Valida un file OBJ

        Args:
            filepath: Path al file OBJ

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

            if not filepath.lower().endswith('.obj'):
                result["warnings"].append("File does not have .obj extension")

            # Controlla dimensione file
            file_size = os.path.getsize(filepath)
            result["info"]["file_size"] = file_size

            if file_size == 0:
                result["errors"].append("File is empty")
                return result

            if file_size > 100 * 1024 * 1024:  # 100MB
                result["warnings"].append("File is very large (>100MB)")

            # Controlla contenuto base
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

                has_vertices = False
                has_faces = False

                for line in lines[:1000]:  # Controlla prime 1000 righe
                    line = line.strip()
                    if line.startswith('v '):
                        has_vertices = True
                    elif line.startswith('f '):
                        has_faces = True

                if not has_vertices:
                    result["errors"].append("No vertices found in file")

                if not has_faces:
                    result["warnings"].append("No faces found in file")

                result["info"]["line_count"] = len(lines)

            if not result["errors"]:
                result["valid"] = True

        except Exception as e:
            result["errors"].append(f"Error validating file: {str(e)}")

        return result

    @staticmethod
    def get_obj_info(filepath: str) -> Dict[str, Any]:
        """
        Ottiene informazioni dettagliate su un file OBJ

        Args:
            filepath: Path al file OBJ

        Returns:
            Dizionario con informazioni dettagliate
        """
        validation = OBJLoader.validate_obj_file(filepath)

        if not validation["valid"]:
            return validation

        info = validation["info"].copy()
        info["filepath"] = filepath
        info["filename"] = os.path.basename(filepath)

        return info
