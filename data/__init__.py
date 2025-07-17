"""
OpenShelf Data Module
Contiene dati statici e configurazioni
"""

import os
import json
from pathlib import Path

# Path alla directory data
DATA_DIR = Path(__file__).parent

def get_data_file_path(filename: str) -> str:
    """Ottiene il path completo a un file nella directory data"""
    return str(DATA_DIR / filename)

def load_repository_configs():
    """Carica le configurazioni repository dal file JSON"""
    config_file = get_data_file_path("repository_configs.json")
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"OpenShelf: Repository config file not found: {config_file}")
            return {}
    except Exception as e:
        print(f"OpenShelf: Error loading repository configs: {e}")
        return {}

def save_repository_configs(configs: dict):
    """Salva le configurazioni repository nel file JSON"""
    config_file = get_data_file_path("repository_configs.json")
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)
        print(f"OpenShelf: Repository configs saved to {config_file}")
    except Exception as e:
        print(f"OpenShelf: Error saving repository configs: {e}")

def get_icon_path(icon_name: str) -> str:
    """Ottiene il path a un'icona"""
    icons_dir = DATA_DIR / "icons"
    icon_path = icons_dir / icon_name
    
    if icon_path.exists():
        return str(icon_path)
    else:
        print(f"OpenShelf: Icon not found: {icon_name}")
        return ""

# Non c'è bisogno di registrazione per i dati
def register():
    """Placeholder per compatibilità"""
    pass

def unregister():
    """Placeholder per compatibilità"""
    pass
