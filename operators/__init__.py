"""
OpenShelf Operators Module
Contiene tutti gli operatori Blender per OpenShelf
"""

from . import search_operators
from . import import_operators
from . import repository_operators
from . import modal_import_operators  # <-- AGGIUNTO: Operatore modal sicuro

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
    modal_import_operators.register()  # <-- AGGIUNTO: Operatore modal
    
    # Registra debug operators se disponibili
    if HAS_DEBUG_OPERATORS:
        debug_operators.register()
        print("OpenShelf: Debug operators registered")

def unregister():
    """Deregistra tutti gli operatori"""
    # Deregistra debug operators se erano registrati
    if HAS_DEBUG_OPERATORS:
        debug_operators.unregister()
    
    modal_import_operators.unregister()  # <-- AGGIUNTO (primo a essere rimosso)
    repository_operators.unregister()
    import_operators.unregister()
    search_operators.unregister()