"""
OpenShelf Properties Module
Gestisce le proprietà scene e addon
"""

from . import scene_properties

def register():
    """Registra tutte le proprietà"""
    scene_properties.register()

def unregister():
    """Deregistra tutte le proprietà"""
    scene_properties.unregister()
