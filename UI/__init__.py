"""
OpenShelf UI Module
Contiene tutti i pannelli dell'interfaccia utente
"""

from . import search_panel
from . import viewport_panels
from . import preferences_panel

def register():
    """Registra tutti i pannelli UI"""
    search_panel.register()
    viewport_panels.register()
    preferences_panel.register()

def unregister():
    """Deregistra tutti i pannelli UI"""
    preferences_panel.unregister()
    viewport_panels.unregister()
    search_panel.unregister()
