"""
OpenShelf Utils Module
Utilities riutilizzabili per download, import e gestione file
"""

from . import download_manager
from . import obj_loader
from . import gltf_loader
from . import file_utils

# Non c'è bisogno di registrazione per le utils
def register():
    """Placeholder per compatibilità"""
    pass

def unregister():
    """Placeholder per compatibilità"""
    pass
