#!/usr/bin/env python3
"""
OpenShelf Repository Test Script
Test repository connections without Blender

Usage:
    python test_repository.py --repository ercolano --limit 10
    python test_repository.py --all
"""

import sys
import argparse
import json
import time
from pathlib import Path

# Aggiungi il path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Import delle classi repository
    from repositories.base_repository import CulturalAsset
    from repositories.ercolano_repository import ErcolanoRepository
    from repositories.registry import RepositoryRegistry
except ImportError as e:
    print(f"Error importing OpenShelf modules: {e}")
    print("Make sure you're running this from the OpenShelf root directory")
    sys.exit(1)

def test_ercolano_repository(limit=10):
    """Testa il repository di Ercolano"""
    print("🏛️  Testing Ercolano Repository")
    print("=" * 50)

    repo = ErcolanoRepository()

    print(f"Repository: {repo.name}")
    print(f"Description: {repo.description}")
    print(f"Base URL: {repo.base_url}")
    print(f"API URL: {repo.json_url}")
    print()

    # Test connessione
    print("🔗 Testing connection...")
    start_time = time.time()

    try:
        assets = repo.fetch_assets(limit=limit)
        fetch_time = time.time() - start_time

        print(f"✅ Connection successful!")
        print(f"⏱️  Fetch time: {fetch_time:.2f} seconds")
        print(f"📦 Assets retrieved: {len(assets)}")
        print()

        if assets:
            print("📋 Sample Assets:")
            print("-" * 30)

            for i, asset in enumerate(assets[:5]):  # Mostra primi 5
                print(f"{i+1}. {asset.get_display_name()}")
                print(f"   Type: {asset.object_type}")
                print(f"   Repository: {asset.repository}")
                print(f"   Quality: {asset.quality_score}%")
                print(f"   Has 3D: {'Yes' if asset.has_3d_model() else 'No'}")
                if asset.materials:
                    print(f"   Materials: {', '.join(asset.materials[:3])}")
                if asset.chronology:
                    print(f"   Period: {', '.join(asset.chronology)}")
                print()

        # Test statistiche
        print("📊 Repository Statistics:")
        print("-" * 25)
        stats = repo.get_statistics()

        if 'error' not in stats:
            print(f"Total assets: {stats.get('total_assets', 'Unknown')}")
            print(f"Assets with 3D: {stats.get('assets_with_3d', 'Unknown')}")

            # Top object types
            object_types = stats.get('object_types', {})
            if object_types:
                print("\nTop object types:")
                sorted_types = sorted(object_types.items(), key=lambda x: x[1], reverse=True)
                for obj_type, count in sorted_types[:5]:
                    print(f"  {obj_type}: {count}")

            # Top materials
            materials = stats.get('materials', {})
            if materials:
                print("\nTop materials:")
                sorted_materials = sorted(materials.items(), key=lambda x: x[1], reverse=True)
                for material, count in sorted_materials[:5]:
                    print(f"  {material}: {count}")
        else:
            print(f"❌ Error getting statistics: {stats['error']}")

    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

    return True

def test_search_functionality(repository, query="anello", limit=5):
    """Testa la funzionalità di ricerca"""
    print(f"🔍 Testing Search: '{query}'")
    print("=" * 30)

    try:
        # Test ricerca base
        results = repository.search_assets(query, limit=limit)

        print(f"🎯 Search results: {len(results)}")

        if results:
            print("\n📋 Search Results:")
            print("-" * 20)

            for i, asset in enumerate(results):
                print(f"{i+1}. {asset.get_display_name()}")
                print(f"   Description: {asset.get_short_description(60)}")
                print(f"   Quality: {asset.quality_score}%")
                print()

        # Test ricerca con filtri
        print("🔍 Testing Filtered Search...")
        filtered_results = repository.search_assets(
            query="",
            filters={
                "object_type": "anello",
                "material": "oro"
            },
            limit=3
        )

        print(f"🎯 Filtered results (rings + gold): {len(filtered_results)}")

        if filtered_results:
            for asset in filtered_results:
                print(f"  • {asset.get_display_name()}")

    except Exception as e:
        print(f"❌ Search test failed: {str(e)}")
        return False

    return True

def test_asset_validation(repository, limit=3):
    """Testa la validazione degli asset"""
    print("✅ Testing Asset Validation")
    print("=" * 30)

    try:
        assets = repository.fetch_assets(limit=limit)

        if not assets:
            print("❌ No assets to validate")
            return False

        for asset in assets:
            print(f"Validating: {asset.get_display_name()}")

            # Test model URLs
            model_info = asset.get_model_info()
            if model_info['has_model']:
                print(f"  ✅ Has 3D model ({model_info['model_count']} files)")
                for url in model_info['model_urls'][:2]:  # Check first 2 URLs
                    print(f"    📄 {url}")
            else:
                print(f"  ❌ No 3D model available")

            # Test metadata completeness
            completeness_score = 0
            if asset.description:
                completeness_score += 25
            if asset.materials:
                completeness_score += 25
            if asset.chronology:
                completeness_score += 25
            if asset.has_3d_model():
                completeness_score += 25

            print(f"  📊 Metadata completeness: {completeness_score}%")
            print()

    except Exception as e:
        print(f"❌ Validation test failed: {str(e)}")
        return False

    return True

def test_all_repositories():
    """Testa tutti i repository disponibili"""
    print("🌍 Testing All Available Repositories")
    print("=" * 40)

    # Inizializza registry
    RepositoryRegistry.initialize()

    repositories = RepositoryRegistry.get_all_repositories()

    if not repositories:
        print("❌ No repositories found")
        return False

    success_count = 0

    for repo in repositories:
        print(f"\n🔗 Testing {repo.name}...")
        try:
            # Test base
            test_assets = repo.fetch_assets(limit=3)
            if test_assets:
                print(f"  ✅ {repo.name}: {len(test_assets)} assets retrieved")
                success_count += 1
            else:
                print(f"  ⚠️  {repo.name}: No assets found")
        except Exception as e:
            print(f"  ❌ {repo.name}: {str(e)}")

    print(f"\n📊 Summary: {success_count}/{len(repositories)} repositories working")
    return success_count > 0

def export_sample_data(repository, filename="sample_assets.json", limit=10):
    """Esporta dati di esempio in JSON"""
    print(f"💾 Exporting Sample Data to {filename}")
    print("=" * 40)

    try:
        assets = repository.fetch_assets(limit=limit)

        # Converti in dizionario serializzabile
        export_data = {
            "repository": repository.name,
            "description": repository.description,
            "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_exported": len(assets),
            "assets": [asset.to_dict() for asset in assets]
        }

        # Salva JSON
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Exported {len(assets)} assets to {filename}")
        print(f"📁 File size: {Path(filename).stat().st_size / 1024:.1f} KB")

    except Exception as e:
        print(f"❌ Export failed: {str(e)}")
        return False

    return True

def main():
    """Funzione principale"""
    parser = argparse.ArgumentParser(description="Test OpenShelf repositories")
    parser.add_argument("--repository", "-r", choices=["ercolano", "all"],
                       default="ercolano", help="Repository to test")
    parser.add_argument("--limit", "-l", type=int, default=10,
                       help="Number of assets to fetch")
    parser.add_argument("--search", "-s", type=str,
                       help="Test search with specific query")
    parser.add_argument("--export", "-e", type=str,
                       help="Export sample data to JSON file")
    parser.add_argument("--validate", action="store_true",
                       help="Run asset validation tests")
    parser.add_argument("--stats", action="store_true",
                       help="Show detailed statistics")

    args = parser.parse_args()

    print("🚀 OpenShelf Repository Test")
    print("=" * 50)
    print(f"Python: {sys.version}")
    print(f"Test limit: {args.limit} assets")
    print()

    success = True

    if args.repository == "all":
        success = test_all_repositories()
    else:
        # Test Ercolano
        success = test_ercolano_repository(args.limit)

        if success:
            repo = ErcolanoRepository()

            # Test ricerca se richiesto
            if args.search:
                success &= test_search_functionality(repo, args.search, args.limit)

            # Test validazione se richiesto
            if args.validate:
                success &= test_asset_validation(repo, min(args.limit, 5))

            # Export se richiesto
            if args.export:
                success &= export_sample_data(repo, args.export, args.limit)

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests completed successfully!")
        print("🎉 OpenShelf repositories are working correctly")
    else:
        print("❌ Some tests failed")
        print("🔧 Check your internet connection and repository status")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
