"""
OpenShelf Repositories Module
Sistema modulare per gestire diversi repository di beni culturali
"""

from . import base_repository
from . import ercolano_repository
from . import registry

def register():
    """Registra tutti i repository"""
    # Inizializza il registry con i repository disponibili
    registry.RepositoryRegistry.initialize()
    print("OpenShelf: Repositories registered")

def unregister():
    """Deregistra tutti i repository"""
    # Cleanup del registry
    registry.RepositoryRegistry.cleanup()
    print("OpenShelf: Repositories unregistered")
