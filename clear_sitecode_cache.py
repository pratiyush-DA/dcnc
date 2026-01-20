
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import get_db_manager

def clear_sitecode_cache():
    print("Clearing cache for sp_fordsitecode...")
    db = get_db_manager()
    
    deleted_detect = 0
    deleted_fp = 0
    
    # 1. Clear detection cache
    with db._get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM detection_cache WHERE column_name = 'sp_fordsitecode'")
        deleted_detect = cursor.rowcount
        
        cursor.execute("DELETE FROM fingerprints WHERE column_name = 'sp_fordsitecode'")
        deleted_fp = cursor.rowcount
    
    # Commit is handled by the context manager
    print(f"Deleted {deleted_detect} detection entries and {deleted_fp} fingerprints.")

if __name__ == "__main__":
    clear_sitecode_cache()
