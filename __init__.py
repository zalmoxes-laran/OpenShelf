"""
OpenShelf - Cultural Heritage 3D Assets Browser
Import 3D assets from various cultural heritage repositories

License: GPL-3.0-or-later
Copyright: 2025 Emanuel Demetrescu

VERSIONE ROBUSTA PER SVILUPPO CON VSCODE
"""

import bpy # type: ignore

# Info per compatibilità con versioni precedenti
bl_info = {
    "name": "OpenShelf",
    "author": "Emanuel Demetrescu",
    "version": (1, 0, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > OpenShelf",
    "description": "Browse and import 3D cultural heritage assets",
    "category": "Import-Export",
    "doc_url": "https://github.com/zalmoxes-laran/OpenShelf",
    "support": "extendedmatrix.org",
}

def safe_import_module(module_name, package_path):
    """Import sicuro di un modulo con gestione errori"""
    try:
        if package_path:
            module = __import__(f"{package_path}.{module_name}", fromlist=[module_name])
        else:
            module = __import__(module_name)

        print(f"OpenShelf: Successfully imported {module_name}")
        return module

    except Exception as e:
        print(f"OpenShelf: Failed to import {module_name}: {e}")
        return None

def safe_register_module(module, module_name):
    """Registrazione sicura di un modulo"""
    if module and hasattr(module, 'register'):
        try:
            module.register()
            print(f"OpenShelf: Successfully registered {module_name}")
            return True
        except Exception as e:
            print(f"OpenShelf: Failed to register {module_name}: {e}")
            return False
    else:
        print(f"OpenShelf: Module {module_name} has no register function")
        return False

def safe_unregister_module(module, module_name):
    """Deregistrazione sicura di un modulo"""
    if module and hasattr(module, 'unregister'):
        try:
            module.unregister()
            print(f"OpenShelf: Successfully unregistered {module_name}")
            return True
        except Exception as e:
            print(f"OpenShelf: Failed to unregister {module_name}: {e}")
            return False
    else:
        print(f"OpenShelf: Module {module_name} has no unregister function")
        return False

# Import moduli dell'addon con import sicuro
print("OpenShelf: Starting module imports...")

properties = safe_import_module('properties', __name__)
repositories = safe_import_module('repositories', __name__)
operators = safe_import_module('operators', __name__)
ui = safe_import_module('ui', __name__)

# Lista moduli importati con successo
successfully_imported_modules = []
for module_name, module in [
    ('properties', properties),
    ('repositories', repositories),
    ('operators', operators),
    ('ui', ui)
]:
    if module:
        successfully_imported_modules.append((module_name, module))

print(f"OpenShelf: Successfully imported {len(successfully_imported_modules)} modules")

def register():
    """Registra tutti i moduli dell'addon - VERSIONE ROBUSTA"""
    print("OpenShelf: Starting robust registration...")

    registered_modules = []
    registration_errors = []

    try:
        # Registra moduli nell'ordine corretto con gestione errori individuale
        for module_name, module in successfully_imported_modules:
            try:
                success = safe_register_module(module, module_name)
                if success:
                    registered_modules.append((module_name, module))
                else:
                    registration_errors.append(f"Registration failed for {module_name}")

            except Exception as e:
                error_msg = f"Exception during {module_name} registration: {e}"
                registration_errors.append(error_msg)
                print(f"OpenShelf: {error_msg}")
                continue

        # Report risultati
        if registered_modules:
            print(f"OpenShelf: Successfully registered {len(registered_modules)} modules:")
            for module_name, _ in registered_modules:
                print(f"  ✓ {module_name}")

        if registration_errors:
            print(f"OpenShelf: Registration had {len(registration_errors)} errors:")
            for error in registration_errors:
                print(f"  ✗ {error}")

        # Se almeno un modulo è registrato, considera la registrazione un successo parziale
        if registered_modules:
            print("OpenShelf: Registration completed (with some modules)")
        else:
            print("OpenShelf: Registration failed - no modules registered")
            # Ma non fare raise per evitare di bloccare completamente Blender

    except Exception as e:
        print(f"OpenShelf: Critical registration error: {e}")
        import traceback
        traceback.print_exc()

        # Prova a fare cleanup parziale
        try:
            unregister()
        except:
            pass

def unregister():
    """Deregistra tutti i moduli dell'addon - VERSIONE ROBUSTA"""
    print("OpenShelf: Starting robust unregistration...")

    unregistered_modules = []
    unregistration_errors = []

    try:
        # Deregistra moduli in ordine inverso
        for module_name, module in reversed(successfully_imported_modules):
            try:
                success = safe_unregister_module(module, module_name)
                if success:
                    unregistered_modules.append(module_name)
                else:
                    unregistration_errors.append(f"Unregistration failed for {module_name}")

            except Exception as e:
                error_msg = f"Exception during {module_name} unregistration: {e}"
                unregistration_errors.append(error_msg)
                print(f"OpenShelf: {error_msg}")
                continue

        # Report risultati
        if unregistered_modules:
            print(f"OpenShelf: Successfully unregistered {len(unregistered_modules)} modules:")
            for module_name in unregistered_modules:
                print(f"  ✓ {module_name}")

        if unregistration_errors:
            print(f"OpenShelf: Unregistration had {len(unregistration_errors)} errors:")
            for error in unregistration_errors:
                print(f"  ✗ {error}")

        print("OpenShelf: Unregistration completed")

    except Exception as e:
        print(f"OpenShelf: Critical unregistration error: {e}")
        import traceback
        traceback.print_exc()

# Auto-register se eseguito direttamente (per test)
if __name__ == "__main__":
    register()
