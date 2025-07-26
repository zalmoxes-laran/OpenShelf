"""
OpenShelf Operators Module - FIX IMPORT CORRETTI
Contiene tutti gli operatori Blender per OpenShelf
FIX: Import corretto usando importlib invece di __import__
"""

import bpy
import importlib
import sys

def safe_import_operator_module(module_name):
    """Import sicuro di un modulo operatori - FIX CON IMPORTLIB"""
    try:
        # Usa importlib.import_module che è più robusto
        full_module_name = f"{__name__}.{module_name}"

        # Se il modulo è già importato, ricaricalo per sviluppo
        if full_module_name in sys.modules:
            module = importlib.reload(sys.modules[full_module_name])
        else:
            module = importlib.import_module(f".{module_name}", package=__name__)

        print(f"OpenShelf: Successfully imported operator module {module_name}")
        return module

    except ImportError as e:
        print(f"OpenShelf: ImportError for operator module {module_name}: {e}")
        return None
    except Exception as e:
        print(f"OpenShelf: Failed to import operator module {module_name}: {e}")
        return None

def safe_register_operator_module(module, module_name):
    """Registrazione sicura di un modulo operatori"""
    if module and hasattr(module, 'register'):
        try:
            module.register()
            print(f"OpenShelf: Successfully registered operator module {module_name}")
            return True
        except Exception as e:
            print(f"OpenShelf: Failed to register operator module {module_name}: {e}")
            # Prova cleanup parziale
            try:
                if hasattr(module, 'unregister'):
                    module.unregister()
            except:
                pass
            return False
    else:
        print(f"OpenShelf: Module {module_name} has no register function")
        return False

def safe_unregister_operator_module(module, module_name):
    """Deregistrazione sicura di un modulo operatori"""
    if module and hasattr(module, 'unregister'):
        try:
            module.unregister()
            print(f"OpenShelf: Successfully unregistered operator module {module_name}")
            return True
        except Exception as e:
            print(f"OpenShelf: Failed to unregister operator module {module_name}: {e}")
            return False
    else:
        print(f"OpenShelf: Module {module_name} has no unregister function or was not imported")
        return False

# Import moduli operatori con gestione errori corretta
print("OpenShelf: Importing operator modules with fixed import...")

# Prova import di ogni modulo individualmente
search_operators = safe_import_operator_module('search_operators')
import_operators = safe_import_operator_module('import_operators')
repository_operators = safe_import_operator_module('repository_operators')
modal_import_operators = safe_import_operator_module('modal_import_operators')
cache_operators = safe_import_operator_module('cache_operators')
library_import_operators = safe_import_operator_module('library_import_operators')

# Moduli opzionali
debug_operators = safe_import_operator_module('debug_operators')

# Lista moduli importati con successo
imported_operator_modules = []

for module_name, module in [
    ('search_operators', search_operators),
    ('import_operators', import_operators),
    ('repository_operators', repository_operators),
    ('modal_import_operators', modal_import_operators),
    ('cache_operators', cache_operators),
    ('library_import_operators', library_import_operators),
    ('debug_operators', debug_operators),  # Opzionale
]:
    if module:
        imported_operator_modules.append((module_name, module))

print(f"OpenShelf: Successfully imported {len(imported_operator_modules)} operator modules:")
for module_name, _ in imported_operator_modules:
    print(f"  ✓ {module_name}")

def register():
    """Registra tutti gli operatori - VERSIONE ROBUSTA"""
    print("OpenShelf: Starting robust operator registration...")

    registered_modules = []
    registration_errors = []

    # Registra ogni modulo individualmente con gestione errori
    for module_name, module in imported_operator_modules:
        try:
            success = safe_register_operator_module(module, module_name)
            if success:
                registered_modules.append((module_name, module))
            else:
                registration_errors.append(f"Failed to register {module_name}")

        except Exception as e:
            error_msg = f"Exception registering {module_name}: {e}"
            registration_errors.append(error_msg)
            print(f"OpenShelf: {error_msg}")
            continue

    # Report risultati
    if registered_modules:
        print(f"OpenShelf: Successfully registered {len(registered_modules)} operator modules:")
        for module_name, _ in registered_modules:
            print(f"  ✓ {module_name}")

    if registration_errors:
        print(f"OpenShelf: Operator registration had {len(registration_errors)} errors:")
        for error in registration_errors:
            print(f"  ✗ {error}")

    # Salva lista moduli registrati per unregister
    global _registered_operator_modules
    _registered_operator_modules = registered_modules

    print("OpenShelf: Operator registration completed")

def unregister():
    """Deregistra tutti gli operatori - VERSIONE ROBUSTA"""
    print("OpenShelf: Starting robust operator unregistration...")

    unregistered_modules = []
    unregistration_errors = []

    # Usa la lista dei moduli effettivamente registrati se disponibile
    modules_to_unregister = getattr(globals(), '_registered_operator_modules', imported_operator_modules)

    # Deregistra in ordine inverso
    for module_name, module in reversed(modules_to_unregister):
        try:
            success = safe_unregister_operator_module(module, module_name)
            if success:
                unregistered_modules.append(module_name)

        except Exception as e:
            error_msg = f"Exception unregistering {module_name}: {e}"
            unregistration_errors.append(error_msg)
            print(f"OpenShelf: {error_msg}")
            continue

    # Report risultati
    if unregistered_modules:
        print(f"OpenShelf: Successfully unregistered {len(unregistered_modules)} operator modules:")
        for module_name in unregistered_modules:
            print(f"  ✓ {module_name}")

    if unregistration_errors:
        print(f"OpenShelf: Operator unregistration had {len(unregistration_errors)} errors:")
        for error in unregistration_errors:
            print(f"  ✗ {error}")

    print("OpenShelf: Operator unregistration completed")

# Variabile globale per tracciare moduli registrati
_registered_operator_modules = []

# Funzioni di utilità per debug
def debug_list_operators():
    """Lista tutti gli operatori OpenShelf attualmente registrati"""
    print("OpenShelf: Currently registered operators:")

    operator_count = 0
    for attr_name in dir(bpy.types):
        if attr_name.startswith('OPENSHELF_OT_'):
            operator_count += 1
            print(f"  ✓ {attr_name}")

    if operator_count == 0:
        print("  (No OpenShelf operators currently registered)")
    else:
        print(f"  Total: {operator_count} operators")

def force_cleanup_operators():
    """Force cleanup di tutti gli operatori OpenShelf registrati"""
    print("OpenShelf: Force cleanup of all registered operators...")

    cleanup_count = 0

    # Cerca e rimuovi tutti gli operatori OpenShelf
    for attr_name in list(dir(bpy.types)):
        if attr_name.startswith('OPENSHELF_OT_'):
            try:
                operator_class = getattr(bpy.types, attr_name)
                bpy.utils.unregister_class(operator_class)
                cleanup_count += 1
                print(f"OpenShelf: Force removed operator {attr_name}")
            except Exception as e:
                print(f"OpenShelf: Could not remove operator {attr_name}: {e}")

    print(f"OpenShelf: Force cleanup completed - removed {cleanup_count} operators")

if __name__ == "__main__":
    # Per test e debug
    print("OpenShelf operators module loaded - debug info:")
    debug_list_operators()
