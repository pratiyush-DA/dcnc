
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import get_db_manager

def clear_cache():
    db = get_db_manager()
    cols = ["sp_postaladdress", "sp_postalcode", "sp_when_created"]
    
    print(f"Clearing cache for columns: {cols}")
    print(f"Database path: {db.db_path}")
    
    with db._get_connection() as conn:
        cursor = conn.cursor()
        
        for col in cols:
            # Clear detection cache
            cursor.execute("DELETE FROM detection_cache WHERE column_name = ?", (col,))
            print(f"Deleted from detection_cache: {col} (rows: {cursor.rowcount})")
            
            # Clear fingerprints
            cursor.execute("DELETE FROM fingerprints WHERE column_name = ?", (col,))
            print(f"Deleted from fingerprints: {col} (rows: {cursor.rowcount})")
            
            # Clear patterns (optional, but good to be safe if we want fresh LLM gen)
            cursor.execute("DELETE FROM pattern_cache WHERE column_name = ?", (col,))
            print(f"Deleted from pattern_cache: {col} (rows: {cursor.rowcount})")

if __name__ == "__main__":
    clear_cache()
