#!/usr/bin/env python3
"""
Test script for the new Ercolano URL
"""

import json
import urllib.request
import ssl
import sys
from pathlib import Path

def test_new_ercolano_url():
    """Test the new Ercolano dataset URL"""

    print("🏛️  Testing New Ercolano URL")
    print("=" * 50)

    # URL corretto trovato
    url = "https://opendata-ercolano.cultura.gov.it/dataset/55608c19-2406-419f-84db-fa3d0b9cd033/resource/64324e26-a659-4c96-8958-98dbc5ecd3a9/download/modelli_3d_hig_res.json"

    print(f"Testing URL: {url}")
    print()

    try:
        # Crea contesto SSL che non verifica certificati (per test)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Crea richiesta
        headers = {
            'User-Agent': 'OpenShelf/1.0 (Blender Addon) Test Script',
            'Accept': 'application/json',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
        }

        req = urllib.request.Request(url, headers=headers)

        print("🔗 Making request...")

        # Esegui richiesta
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
            print(f"✅ Response Status: {response.status}")
            print(f"📄 Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            print(f"📏 Content-Length: {response.headers.get('Content-Length', 'unknown')}")
            print(f"🖥️  Server: {response.headers.get('Server', 'unknown')}")
            print()

            # Leggi contenuto
            content = response.read()
            print(f"📦 Downloaded: {len(content):,} bytes")

            # Prova a parsare JSON
            print("🔍 Parsing JSON...")
            try:
                data = json.loads(content.decode('utf-8'))
                print("✅ JSON parsing successful!")

                # Analizza struttura
                print("\n📊 JSON Structure Analysis:")
                print("-" * 30)

                if isinstance(data, dict):
                    print("📋 Root is a dictionary")
                    print(f"🔑 Root keys: {list(data.keys())}")

                    # Esamina ogni chiave
                    for key, value in data.items():
                        print(f"\n🔍 Key '{key}':")
                        print(f"   Type: {type(value).__name__}")

                        if isinstance(value, list):
                            print(f"   Length: {len(value)}")
                            if len(value) > 0:
                                print(f"   First item type: {type(value[0]).__name__}")
                                if isinstance(value[0], dict):
                                    print(f"   First item keys: {list(value[0].keys())}")

                        elif isinstance(value, dict):
                            print(f"   Sub-keys: {list(value.keys())}")

                        elif isinstance(value, str):
                            preview = value[:100] + ("..." if len(value) > 100 else "")
                            print(f"   Preview: {preview}")

                        else:
                            print(f"   Value: {value}")

                elif isinstance(data, list):
                    print("📋 Root is a list")
                    print(f"📏 Length: {len(data)}")

                    if len(data) > 0:
                        print(f"🔍 First item type: {type(data[0]).__name__}")

                        if isinstance(data[0], dict):
                            print(f"🔑 First item keys: {list(data[0].keys())}")

                            # Mostra primi 3 record come esempio
                            print("\n📄 Sample Records:")
                            for i, record in enumerate(data[:3]):
                                print(f"\n--- Record {i+1} ---")
                                for key, value in record.items():
                                    if isinstance(value, str) and len(value) > 50:
                                        value = value[:50] + "..."
                                    print(f"  {key}: {value}")

                else:
                    print(f"📋 Root is: {type(data).__name__}")
                    print(f"📄 Value: {data}")

                # Cerca campi che potrebbero contenere URLs di modelli 3D
                print("\n🎯 Looking for 3D model URLs...")
                model_url_candidates = []

                def find_urls_recursive(obj, path=""):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            new_path = f"{path}.{key}" if path else key
                            if isinstance(value, str) and ('.obj' in value.lower() or '.zip' in value.lower() or 'model' in key.lower() or '3d' in key.lower() or 'file' in key.lower() or 'download' in key.lower() or 'url' in key.lower()):
                                model_url_candidates.append((new_path, value))
                            elif isinstance(value, (dict, list)):
                                find_urls_recursive(value, new_path)
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            new_path = f"{path}[{i}]"
                            find_urls_recursive(item, new_path)

                find_urls_recursive(data)

                if model_url_candidates:
                    print("🎯 Found potential 3D model URLs:")
                    for path, url in model_url_candidates[:10]:  # Show first 10
                        print(f"   {path}: {url}")
                else:
                    print("⚠️  No obvious 3D model URLs found in field names")

                # Cerca specificamente nei records se disponibili
                if isinstance(data, dict) and 'jsonData' in data and 'records' in data['jsonData']:
                    records = data['jsonData']['records']
                    print(f"\n🔍 Analyzing {len(records)} records for 3D content...")

                    # Analizza tutti i campi unici nei record
                    all_fields = set()
                    sample_values = {}

                    for record in records[:10]:  # Analizza primi 10 record
                        for key, value in record.items():
                            all_fields.add(key)
                            if key not in sample_values:
                                sample_values[key] = str(value)[:100] if value else ""

                    print(f"\n📋 All unique fields in records ({len(all_fields)} total):")
                    for field in sorted(all_fields):
                        sample = sample_values.get(field, "")
                        if len(sample) > 50:
                            sample = sample[:50] + "..."
                        print(f"   📄 {field}: {sample}")

                        # Cerca campi che potrebbero contenere URL
                        if any(keyword in field.lower() for keyword in ['url', 'link', 'file', 'model', '3d', 'download', 'href']):
                            print(f"      🎯 Potential URL field!")

                # Statistiche finali
                if isinstance(data, dict) and 'jsonData' in data:
                    json_data = data['jsonData']
                    if 'totRecord' in json_data:
                        print(f"\n📊 Summary: {json_data['totRecord']} total records available")
                    if 'records' in json_data:
                        print(f"📦 Downloaded: {len(json_data['records'])} records in this response")
                elif isinstance(data, list):
                    print(f"\n📊 Summary: Found {len(data)} records")
                elif isinstance(data, dict):
                    total_records = 0
                    for value in data.values():
                        if isinstance(value, list):
                            total_records += len(value)
                    print(f"\n📊 Summary: Found ~{total_records} total items")

                return True

            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"📄 Content preview: {content[:500]}")
                return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Test principale"""
    print("🚀 Ercolano URL Test")
    print("=" * 50)

    success = test_new_ercolano_url()

    print("\n" + "=" * 50)
    if success:
        print("✅ Test completed successfully!")
        print("🎉 The new Ercolano URL is working!")
    else:
        print("❌ Test failed")
        print("🔧 Check the URL and network connection")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
