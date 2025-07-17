"""
OpenShelf Operators Module
Contiene tutti gli operatori Blender per OpenShelf
"""

from . import search_operators
from . import import_operators
from . import repository_operators

def register():
    """Registra tutti gli operatori"""
    search_operators.register()
    import_operators.register()
    repository_operators.register()

def unregister():
    """Deregistra tutti gli operatori"""
    repository_operators.unregister()
    import_operators.unregister()
    search_operators.unregister()
