#!/usr/bin/env python3
"""Diagnostic script to check why metadata is empty."""

import asyncio
import sys

# Test 1: Check if the fixed museum_api can be imported
print("=" * 80)
print("TEST 1: Import Check")
print("=" * 80)

try:
    # Try importing from the uploaded files location
    sys.path.insert(0, '/mnt/user-data/uploads')
    from museum_api import fetch_artwork_metadata, RijksCache, extract_core_fields
    print("✓ Successfully imported museum_api from uploads")
    
    # Check if key functions exist
    print(f"✓ fetch_artwork_metadata: {callable(fetch_artwork_metadata)}")
    print(f"✓ extract_core_fields: {callable(extract_core_fields)}")
    print(f"✓ RijksCache: {RijksCache is not None}")
    
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Check if the functions work with sample data
print("\n" + "=" * 80)
print("TEST 2: Sample Data Extraction")
print("=" * 80)

SAMPLE_JSONLD = {
    "@context": "https://linked.art/ns/v1/linked-art.json",
    "@graph": [
        {
            "@id": "https://id.rijksmuseum.nl/test",
            "type": "HumanMadeObject",
            "identified_by": [
                {"type": "Name", "content": "Test Painting"}
            ],
            "made_of": [
                {"@id": "#oil"}
            ],
            "produced_by": {
                "type": "Production",
                "carried_out_by": [{"@id": "#artist"}],
                "timespan": {
                    "type": "TimeSpan",
                    "identified_by": [{"type": "Name", "content": "1650"}]
                }
            }
        },
        {
            "@id": "#oil",
            "type": "Material",
            "_label": "oil paint"
        },
        {
            "@id": "#artist",
            "type": "Person",
            "_label": "Test Artist"
        }
    ]
}

try:
    result = extract_core_fields(SAMPLE_JSONLD)
    print(f"✓ Extraction completed")
    print(f"  - Title: {result.get('title')}")
    print(f"  - Artist: {result.get('artist')}")
    print(f"  - Date: {result.get('date')}")
    print(f"  - Materials: {result.get('materials')}")
    
    if result.get('title') and result.get('artist'):
        print("\n✓ Extraction is WORKING correctly")
    else:
        print("\n✗ Extraction returned empty fields")
        
except Exception as e:
    print(f"✗ Extraction failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Check the helper functions
print("\n" + "=" * 80)
print("TEST 3: Helper Functions Check")
print("=" * 80)

try:
    from museum_api import _has_type, _find_hmo, _build_id_map
    
    sample_node = {
        "@id": "test",
        "@type": "HumanMadeObject"
    }
    
    print(f"✓ _has_type exists: {callable(_has_type)}")
    print(f"✓ _find_hmo exists: {callable(_find_hmo)}")
    print(f"✓ _build_id_map exists: {callable(_build_id_map)}")
    
    # Test type detection
    result = _has_type(sample_node, "HumanMadeObject")
    print(f"\n✓ Type detection test: {result}")
    
    if result:
        print("✓ Type detection is WORKING (handles @type)")
    else:
        print("✗ Type detection FAILED (doesn't handle @type)")
        
except ImportError as e:
    print(f"✗ Helper functions not found: {e}")
    print("  This means you're using the OLD museum_api.py")
    print("  You need to replace it with museum_api_fixed.py")

# Test 4: Try simulating the app startup
print("\n" + "=" * 80)
print("TEST 4: Simulated App Startup")
print("=" * 80)

print("\nChecking if Rijksmuseum API is accessible...")
print("(This will fail in this environment due to network restrictions)")
print("In production, this should fetch real metadata.")

# Test 5: Check config structure
print("\n" + "=" * 80)
print("TEST 5: Config Requirements")
print("=" * 80)

print("""
Your config.yml should have this structure:

rijksmuseum:
  enabled: true  # ← MUST be true!
  objectNumber: "SK-A-2344"  # Vermeer's Milkmaid
  # OR: "SK-A-3262" for Van Gogh self-portrait
  profile: "la"
  mediatype: "application/ld+json"
  cache_ttl_seconds: 86400

If 'enabled: false' or missing, RIJKS_META stays None!
""")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print("""
If extraction works above but /debug/rijks shows empty:

LIKELY CAUSES:
1. Config has 'enabled: false' → startup doesn't fetch metadata
2. Network restrictions → API call fails silently
3. Wrong objectNumber → API returns no results
4. Using old museum_api.py → type detection fails

SOLUTION:
1. Verify config.yml has 'enabled: true'
2. Check app logs for startup errors
3. Try /debug/rijks_raw_keys to see if any data loaded
4. Replace museum_api.py with the fixed version
""")
