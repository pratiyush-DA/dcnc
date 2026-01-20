
import os
import sys
import json

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import get_db_manager

def inspect_patterns():
    print("Inspecting patterns for sp_fordsitecode...")
    db = get_db_manager()
    
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT patterns, description FROM pattern_cache WHERE column_name = 'sp_fordsitecode'")
        rows = cursor.fetchall()
        
        if not rows:
            print("No patterns found in cache!")
            # Try searching by workflow/subtype signature if name missing
            cursor.execute("SELECT patterns, description FROM pattern_cache WHERE workflow='identifier' AND subtype='pattern_id' ORDER BY created_at DESC LIMIT 1")
            rows = cursor.fetchall()
            print(f"Showing most recent identifier pattern ({len(rows)} found)")
            
        for row in rows:
            print(f"Description: {row['description']}")
            print("Patterns:")
            patterns = json.loads(row['patterns'])
            for p in patterns:
                print(f"  - {p}")

if __name__ == "__main__":
    inspect_patterns()
