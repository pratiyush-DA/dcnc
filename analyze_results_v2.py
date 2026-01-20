
import json
import os
import sys
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import get_db_manager

def analyze_results():
    print("Starting Comprehensive Analysis...")
    
    # 1. Load Fingerprints
    fp_path = "output/fingerprints.json"
    if not os.path.exists(fp_path):
        print("Fingerprints file not found!")
        return

    with open(fp_path, "r") as f:
        fp_data = json.load(f)
    
    columns = fp_data.get("columns", {})
    
    # 2. Database Connection
    db = get_db_manager()
    
    analysis_data = []
    
    for col_name, data in columns.items():
        workflow = data.get("workflow", "unknown")
        subtype = data.get("subtype", "unknown")
        good_cnt = data.get("good_count", 0)
        bad_cnt = data.get("bad_count", 0)
        total = good_cnt + bad_cnt
        success_rate = (good_cnt / total * 100) if total > 0 else 0
        
        # Check DB for patterns
        patterns_found = "No Cache"
        if "fingerprint" in data:
            fp_obj = data["fingerprint"]
            cached = db.get_cached_patterns(workflow, subtype, fp_obj)
            if cached:
                patterns = cached.patterns
                patterns_found = f"{len(patterns)} patterns"
                if patterns:
                    patterns_found += f" (Ex: {patterns[0]})"

        analysis_data.append({
            "Column": col_name, 
            "Workflow": workflow, 
            "Subtype": subtype, 
            "SuccessRate": success_rate,
            "Good": good_cnt, 
            "Bad": bad_cnt, 
            "LLMPatterns": patterns_found
        })
    
    # Write to JSON
    with open("final_analysis.json", "w") as f:
        json.dump(analysis_data, f, indent=2)
    print("Analysis saved to final_analysis.json")

if __name__ == "__main__":
    analyze_results()
