"""
OpenShelf Operators Module
Contiene tutti gli operatori Blender per OpenShelf
"""

from . import search_operators
from . import import_operators
from . import repository_operators
from . import modal_import_operators  # <-- Operatore modal sicuro
from . import cache_operators  # <-- NUOVO: Operatori cache

# Debug operators (opzionale - decommentare se necessario)
try:
    from . import debug_operators  # <-- OPZIONALE: Operatori debug
    HAS_DEBUG_OPERATORS = True
except ImportError:
    HAS_DEBUG_OPERATORS = False

def register():
    """Registra tutti gli operatori"""
    search_operators.register()
    import_operators.register()
    repository_operators.register()
    modal_import_operators.register()  # <-- Operatore modal
    cache_operators.register()  # <-- NUOVO: Cache operators

    # Registra debug operators se disponibili
    if HAS_DEBUG_OPERATORS:
        debug_operators.register()
        print("OpenShelf: Debug operators registered")

def unregister():
    """Deregistra tutti gli operatori"""
    # Deregistra debug operators se erano registrati
    if HAS_DEBUG_OPERATORS:
        debug_operators.unregister()

    cache_operators.unregister()  # <-- NUOVO (primo a essere rimosso)
    modal_import_operators.unregister()
    repository_operators.unregister()
    import_operators.unregister()
    search_operators.unregister()
