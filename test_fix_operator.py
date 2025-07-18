"""
Operatore di test per verificare il fix degli URL

Aggiungere temporaneamente agli operators per testare:
"""

import bpy
from bpy.types import Operator
import json

class OPENSHELF_OT_test_url_fix(Operator):
    """Test per verificare correzione URL"""
    bl_idname = "openshelf.test_url_fix"
    bl_label = "Test URL Fix"
    bl_description = "Test the URL parsing fix"
    bl_options = {'REGISTER'}

    def execute(self, context):
        print("\n" + "="*50)
        print("OpenShelf: Testing URL Fix")
        print("="*50)

        # Test 1: Simula URL dal JSON Ercolano
        test_urls = [
            "http://opendata-ercolano.cultura.gov.it/pub/modelli_3d_hr/77445.zip"
        ]
        
        print(f"Test 1: Original URL list: {test_urls}")
        
        # Simula salvataggio con json.dumps (corretto)
        json_string = json.dumps(test_urls)
        print(f"Test 1: JSON serialized: {json_string}")
        
        # Simula parsing con json.loads
        try:
            parsed_urls = json.loads(json_string)
            print(f"Test 1: JSON parsed: {parsed_urls}")
            print(f"Test 1: Type: {type(parsed_urls)}")
            print(f"Test 1: First URL: {parsed_urls[0] if parsed_urls else 'None'}")
            print("Test 1: ✅ SUCCESS")
        except Exception as e:
            print(f"Test 1: ❌ FAILED - {e}")

        print("\n" + "-"*30)

        # Test 2: Simula il vecchio metodo errato con str()
        wrong_string = str(test_urls)
        print(f"Test 2: Wrong str() serialized: {wrong_string}")
        
        # Simula parsing del formato sbagliato
        try:
            parsed_wrong = json.loads(wrong_string)
            print(f"Test 2: Should fail - {parsed_wrong}")
        except json.JSONDecodeError as e:
            print(f"Test 2: Expected JSON error: {e}")
            
            # Test fallback parsing
            try:
                import ast
                fallback_parsed = ast.literal_eval(wrong_string)
                print(f"Test 2: Fallback parsing: {fallback_parsed}")
                print(f"Test 2: Type: {type(fallback_parsed)}")
                print("Test 2: ✅ FALLBACK SUCCESS")
            except Exception as e2:
                print(f"Test 2: ❌ FALLBACK FAILED - {e2}")

        print("\n" + "-"*30)

        # Test 3: Test con asset reale dalla cache se disponibile
        scene = context.scene
        if scene.openshelf_assets_cache:
            asset = scene.openshelf_assets_cache[0]
            print(f"Test 3: Real asset URLs: {repr(asset.model_urls)}")
            
            if asset.model_urls:
                try:
                    real_parsed = json.loads(asset.model_urls)
                    print(f"Test 3: Real parsed: {real_parsed}")
                    print("Test 3: ✅ REAL DATA SUCCESS")
                except Exception as e:
                    print(f"Test 3: ❌ REAL DATA FAILED - {e}")
            else:
                print("Test 3: No URLs in real asset")
        else:
            print("Test 3: No assets in cache to test")

        print("="*50)
        self.report({'INFO'}, "URL fix test completed - check console")
        return {'FINISHED'}

"""
Per aggiungere questo test temporaneamente:

1. Aggiungi la classe sopra a uno dei file operators
2. Aggiungila alla lista operators nel register()
3. Dopo aver fatto una ricerca, usa il nuovo pulsante "Test URL Fix" nel menu operatori (F3)
4. Controlla la console per i risultati
"""