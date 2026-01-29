#!/usr/bin/env python3
"""
Test Correction API
Tests the classification + correction API
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from DCNC.api.services.correction_service import CorrectionService


async def test_correction_api():
    """Test the correction API."""
    print("="*80)
    print("TESTING CORRECTION API")
    print("="*80)
    
    # Initialize service
    service = CorrectionService()
    
    # Test file
    test_file = Path(__file__).parent / "comprehensive_workflow_test_data.csv"
    
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return False
    
    print(f"\nTest file: {test_file}")
    print(f"File size: {test_file.stat().st_size / 1024:.2f} KB")
    
    try:
        # Run classification + correction
        print("\nRunning classification + correction...")
        result = await service.classify_and_correct(
            file_path=str(test_file),
            has_header=True,
            classification_options={
                "enable_validation": True,
                "enable_ml_clustering": True,
                "enable_ensemble_detection": True,
                "enable_llm_verification": False,
                "strict_mode": False,
            },
            correction_options={
                "similarity_threshold": 0.7,
                "max_corrections_per_column": 1000,
            }
        )
        
        print("\n" + "="*80)
        print("CORRECTION RESULTS")
        print("="*80)
        
        print(f"\nStatus: {result['status']}")
        print(f"Job ID: {result['job_id']}")
        print(f"Classification Job ID: {result['classification_job_id']}")
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
        print(f"  Corrected Rows: {stats['corrected_rows']}")
        print(f"  Reject Rows: {stats['reject_rows']}")
        print(f"  Columns Processed: {stats['columns_processed']}")
        print(f"  Corrections Applied: {stats['corrections_applied']}")
        print(f"  Corrections Rejected: {stats['corrections_rejected']}")
        
        # Validate files
        print("\n" + "="*80)
        print("FILE VALIDATION")
        print("="*80)
        
        import pandas as pd
        
        # Check corrected_data.csv
        corrected_data_path = Path(result['files']['corrected_data'])
        if corrected_data_path.exists():
            corrected_df = pd.read_csv(corrected_data_path)
            print(f"\n[OK] corrected_data.csv: {len(corrected_df)} rows, {len(corrected_df.columns)} columns")
        else:
            print(f"\n[ERROR] corrected_data.csv: NOT FOUND")
        
        # Check correction_report.json
        correction_report_path = Path(result['files']['correction_report'])
        if correction_report_path.exists():
            with open(correction_report_path, 'r') as f:
                report = json.load(f)
            print(f"[OK] correction_report.json: {report['summary']['columns_processed']} columns")
            print(f"  Corrections Attempted: {report['summary']['total_corrections_attempted']}")
            print(f"  Corrections Applied: {report['summary']['corrections_applied']}")
            print(f"  Corrections Rejected: {report['summary']['corrections_rejected']}")
        else:
            print(f"[ERROR] correction_report.json: NOT FOUND")
        
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_correction_api())
    sys.exit(0 if success else 1)
