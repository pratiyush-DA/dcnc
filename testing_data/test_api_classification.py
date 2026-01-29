#!/usr/bin/env python3
"""
Test Classification API
Tests the classification API with comprehensive test data
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from DCNC.api.services.classification_service import ClassificationService


async def test_classification_api():
    """Test the classification API."""
    print("="*80)
    print("TESTING CLASSIFICATION API")
    print("="*80)
    
    # Initialize service
    service = ClassificationService()
    
    # Test file
    test_file = Path(__file__).parent / "comprehensive_workflow_test_data.csv"
    
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return False
    
    print(f"\nTest file: {test_file}")
    print(f"File size: {test_file.stat().st_size / 1024:.2f} KB")
    
    try:
        # Run classification
        print("\nRunning classification...")
        result = await service.classify(
            file_path=str(test_file),
            has_header=True,
            options={
                "enable_validation": True,
                "enable_ml_clustering": True,
                "enable_ensemble_detection": True,
                "enable_llm_verification": False,
                "strict_mode": False,
            }
        )
        
        print("\n" + "="*80)
        print("CLASSIFICATION RESULTS")
        print("="*80)
        
        print(f"\nStatus: {result['status']}")
        print(f"Job ID: {result['job_id']}")
        print(f"Processing Time: {result['metadata']['processing_time']}s")
        
        print("\nFiles Generated:")
        for file_type, file_path in result['files'].items():
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                size = file_path_obj.stat().st_size / 1024
                print(f"  {file_type:20s}: {file_path} ({size:.2f} KB)")
            else:
                print(f"  {file_type:20s}: {file_path} (NOT FOUND)")
        
        print("\nStatistics:")
        stats = result['statistics']
        print(f"  Total Rows: {stats['total_rows']}")
        print(f"  Good Rows: {stats['good_rows']}")
        print(f"  Bad Rows: {stats['bad_rows']}")
        print(f"  Reject Rows: {stats['reject_rows']}")
        print(f"  Columns Processed: {stats['columns_processed']}")
        print(f"  Total Good Values: {stats['total_good_values']}")
        print(f"  Total Bad Values: {stats['total_bad_values']}")
        
        # Validate files
        print("\n" + "="*80)
        print("FILE VALIDATION")
        print("="*80)
        
        import pandas as pd
        
        # Check good_data.csv
        good_data_path = Path(result['files']['good_data'])
        if good_data_path.exists():
            good_df = pd.read_csv(good_data_path)
            print(f"\n✅ good_data.csv: {len(good_df)} rows, {len(good_df.columns)} columns")
        else:
            print(f"\n❌ good_data.csv: NOT FOUND")
        
        # Check bad_data.csv
        bad_data_path = Path(result['files']['bad_data'])
        if bad_data_path.exists():
            bad_df = pd.read_csv(bad_data_path)
            print(f"✅ bad_data.csv: {len(bad_df)} rows, {len(bad_df.columns)} columns")
        else:
            print(f"❌ bad_data.csv: NOT FOUND")
        
        # Check reject_data.csv
        reject_data_path = Path(result['files']['reject_data'])
        if reject_data_path.exists():
            reject_df = pd.read_csv(reject_data_path)
            print(f"✅ reject_data.csv: {len(reject_df)} rows, {len(reject_df.columns)} columns")
        else:
            print(f"❌ reject_data.csv: NOT FOUND")
        
        # Check fingerprint.json
        fingerprint_path = Path(result['files']['fingerprint'])
        if fingerprint_path.exists():
            with open(fingerprint_path, 'r') as f:
                fingerprint_data = json.load(f)
            print(f"✅ fingerprint.json: {len(fingerprint_data)} columns")
            
            # Show sample fingerprint
            if fingerprint_data:
                sample_col = list(fingerprint_data.keys())[0]
                print(f"\nSample fingerprint for '{sample_col}':")
                sample_fp = fingerprint_data[sample_col]
                print(f"  Workflow: {sample_fp.get('workflow')}")
                print(f"  Subtype: {sample_fp.get('subtype')}")
                print(f"  Method: {sample_fp.get('method')}")
                print(f"  Good Count: {sample_fp.get('good_count')}")
                print(f"  Bad Count: {sample_fp.get('bad_count')}")
        else:
            print(f"❌ fingerprint.json: NOT FOUND")
        
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_classification_api())
    sys.exit(0 if success else 1)
