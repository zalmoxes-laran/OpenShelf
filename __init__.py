"""
OpenShelf - Cultural Heritage 3D Assets Browser
Import 3D assets from various cultural heritage repositories

License: GPL-3.0-or-later
Copyright: 2025 Emanuel Demetrescu
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

# Import moduli dell'addon
from . import properties
from . import repositories
from . import operators
from . import ui

# Lista moduli da registrare nell'ordine corretto
modules = [
    properties,
    repositories,
    operators,
    ui,
]

def register():
    """Registra tutti i moduli dell'addon"""
    print("OpenShelf: Registering addon...")

    try:
        for module in modules:
            if hasattr(module, 'register'):
                module.register()
                print(f"OpenShelf: Registered {module.__name__}")

        print("OpenShelf: Registration complete!")

    except Exception as e:
        print(f"OpenShelf: Registration failed: {e}")
        # Cleanup in case of partial registration
        unregister()
        raise

def unregister():
    """Deregistra tutti i moduli dell'addon"""
    print("OpenShelf: Unregistering addon...")

    try:
        for module in reversed(modules):
            if hasattr(module, 'unregister'):
                module.unregister()
                print(f"OpenShelf: Unregistered {module.__name__}")

        print("OpenShelf: Unregistration complete!")

    except Exception as e:
        print(f"OpenShelf: Unregistration failed: {e}")

if __name__ == "__main__":
    register()
