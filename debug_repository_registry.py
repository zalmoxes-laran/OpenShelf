#!/usr/bin/env python3
"""
Debug script for repository registration
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from repositories.registry import RepositoryRegistry
    from repositories.ercolano_repository import ErcolanoRepository
except ImportError as e:
    print(f"Error importing: {e}")
    sys.exit(1)

def debug_registry():
    """Debug repository registry"""
    print("🔍 Debugging Repository Registry")
    print("=" * 40)
    
    # Inizializza registry
    print("1. Initializing registry...")
    RepositoryRegistry.initialize()
    
    # Mostra status
    print("\n2. Registry status:")
    status = RepositoryRegistry.get_status()
    print(f"   Initialized: {status['initialized']}")
    print(f"   Repository count: {status['repository_count']}")
    print(f"   Available repositories: {status['available_repositories']}")
    
    # Mostra tutti i repository registrati
    print("\n3. All registered repositories:")
    all_repos = RepositoryRegistry.get_all_repositories()
    for repo in all_repos:
        print(f"   - Name: '{repo.name}' (Type: {type(repo).__name__})")
    
    # Testa recupero per nome
    print("\n4. Testing repository retrieval:")
    test_names = ["Ercolano", "ercolano", "ERCOLANO"]
    
    for name in test_names:
        repo = RepositoryRegistry.get_repository(name)
        if repo:
            print(f"   ✅ Found repository with name '{name}': {repo.name}")
        else:
            print(f"   ❌ No repository found with name '{name}'")
    
    # Testa connessione
    print("\n5. Testing repository connections:")
    for name in test_names:
        result = RepositoryRegistry.test_repository_connection(name)
        print(f"   '{name}': {result['status']} - {result['message']}")
    
    return True

def test_direct_repository():
    """Test repository directly"""
    print("\n🧪 Testing ErcolanoRepository directly")
    print("=" * 40)
    
    try:
        repo = ErcolanoRepository()
        print(f"✅ Repository created successfully")
        print(f"   Name: '{repo.name}'")
        print(f"   Description: {repo.description}")
        print(f"   Base URL: {repo.base_url}")
        print(f"   JSON URL: {repo.json_url}")
        
        # Test fetch limitato
        print(f"\n📥 Testing fetch (limit 2)...")
        assets = repo.fetch_assets(limit=2)
        print(f"   Retrieved {len(assets)} assets")
        
        if assets:
            asset = assets[0]
            print(f"   Sample asset: {asset.get_display_name()}")
            print(f"   Asset ID: {asset.id}")
            print(f"   Object type: {asset.object_type}")
            print(f"   Has 3D models: {asset.has_3d_model()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing repository directly: {e}")
        return False

def main():
    """Main debug function"""
    print("🔧 OpenShelf Repository Debug")
    print("=" * 50)
    
    success1 = debug_registry()
    success2 = test_direct_repository()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ Debug completed - repositories are working")
    else:
        print("❌ Issues found in repository system")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
