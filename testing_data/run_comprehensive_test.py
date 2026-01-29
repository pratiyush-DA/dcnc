#!/usr/bin/env python3
"""
Comprehensive Test Runner
Tests the pipeline with comprehensive test data covering all workflows, subworkflows, and methods.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.pipeline_service_v2 import PipelineServiceV2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_results(output_dir: str = "output"):
    """
    Analyze pipeline results and generate comprehensive report.
    
    Args:
        output_dir: Output directory path
    """
    output_path = Path(output_dir)
    
    # Load fingerprints
    fingerprints_file = output_path / "fingerprints.json"
    fingerprints = {}
    if fingerprints_file.exists():
        with open(fingerprints_file) as f:
            fingerprints = json.load(f)
    
    # Load summary report
    summary_file = output_path / "report" / "summary_report.json"
    summary = {}
    if summary_file.exists():
        with open(summary_file) as f:
            summary = json.load(f)
    
    # Load correction report
    correction_file = output_path / "report" / "correction_report.json"
    corrections = {}
    if correction_file.exists():
        with open(correction_file) as f:
            corrections = json.load(f)
    
    # Analyze good/bad files
    good_bad_dir = output_path / "good_n_bad"
    column_stats = {}
    
    if good_bad_dir.exists():
        for file in good_bad_dir.glob("good_data_*.csv"):
            column_name = file.stem.replace("good_data_", "")
            try:
                good_df = pd.read_csv(file)
                bad_file = good_bad_dir / f"bad_data_{column_name}.csv"
                bad_df = pd.read_csv(bad_file) if bad_file.exists() else pd.DataFrame()
                
                column_stats[column_name] = {
                    "good_count": len(good_df),
                    "bad_count": len(bad_df),
                    "total_count": len(good_df) + len(bad_df),
                    "success_rate": len(good_df) / (len(good_df) + len(bad_df)) if (len(good_df) + len(bad_df)) > 0 else 0
                }
            except Exception as e:
                logger.warning(f"Error analyzing {file}: {e}")
    
    # Generate analysis report
    analysis = {
        "test_timestamp": datetime.now().isoformat(),
        "test_data_file": "comprehensive_workflow_test_data.csv",
        "total_columns": len(column_stats),
        "summary_statistics": summary,
        "column_analysis": {},
        "workflow_distribution": {},
        "subtype_distribution": {},
        "method_distribution": {},
        "performance_metrics": {}
    }
    
    # Analyze each column
    for column_name, stats in column_stats.items():
        fingerprint = fingerprints.get("columns", {}).get(column_name, {})
        
        workflow = fingerprint.get("workflow", "unknown")
        subtype = fingerprint.get("subtype", "unknown")
        method = fingerprint.get("method", "unknown")
        
        analysis["column_analysis"][column_name] = {
            "workflow": workflow,
            "subtype": subtype,
            "method": method,
            "good_count": stats["good_count"],
            "bad_count": stats["bad_count"],
            "success_rate": stats["success_rate"],
            "fingerprint_available": bool(fingerprint)
        }
        
        # Update distributions
        analysis["workflow_distribution"][workflow] = analysis["workflow_distribution"].get(workflow, 0) + 1
        analysis["subtype_distribution"][subtype] = analysis["subtype_distribution"].get(subtype, 0) + 1
        analysis["method_distribution"][method] = analysis["method_distribution"].get(method, 0) + 1
    
    # Calculate overall metrics
    total_good = sum(s["good_count"] for s in column_stats.values())
    total_bad = sum(s["bad_count"] for s in column_stats.values())
    total_records = total_good + total_bad
    
    analysis["performance_metrics"] = {
        "overall_success_rate": total_good / total_records if total_records > 0 else 0,
        "total_good_values": total_good,
        "total_bad_values": total_bad,
        "total_records_processed": total_records,
        "columns_processed": len(column_stats),
        "average_column_success_rate": sum(s["success_rate"] for s in column_stats.values()) / len(column_stats) if column_stats else 0
    }
    
    # Save analysis report
    analysis_file = output_path / "comprehensive_test_analysis.json"
    with open(analysis_file, "w") as f:
        json.dump(analysis, f, indent=2)
    
    logger.info(f"Analysis report saved to {analysis_file}")
    
    return analysis


def print_analysis_report(analysis: dict):
    """Print formatted analysis report."""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST ANALYSIS REPORT")
    print("="*80)
    
    print(f"\nTest Timestamp: {analysis['test_timestamp']}")
    print(f"Test Data File: {analysis['test_data_file']}")
    print(f"Total Columns Processed: {analysis['total_columns']}")
    
    print("\n" + "-"*80)
    print("OVERALL PERFORMANCE METRICS")
    print("-"*80)
    metrics = analysis["performance_metrics"]
    print(f"Overall Success Rate: {metrics['overall_success_rate']:.2%}")
    print(f"Total Good Values: {metrics['total_good_values']:,}")
    print(f"Total Bad Values: {metrics['total_bad_values']:,}")
    print(f"Total Records Processed: {metrics['total_records_processed']:,}")
    print(f"Average Column Success Rate: {metrics['average_column_success_rate']:.2%}")
    
    print("\n" + "-"*80)
    print("WORKFLOW DISTRIBUTION")
    print("-"*80)
    for workflow, count in sorted(analysis["workflow_distribution"].items()):
        print(f"  {workflow:20s}: {count:3d} columns")
    
    print("\n" + "-"*80)
    print("SUBTYPE DISTRIBUTION")
    print("-"*80)
    for subtype, count in sorted(analysis["subtype_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {subtype:20s}: {count:3d} columns")
    
    print("\n" + "-"*80)
    print("METHOD DISTRIBUTION")
    print("-"*80)
    for method, count in sorted(analysis["method_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {method:30s}: {count:3d} columns")
    
    print("\n" + "-"*80)
    print("COLUMN-BY-COLUMN ANALYSIS")
    print("-"*80)
    print(f"{'Column Name':<30s} {'Workflow':<12s} {'Subtype':<20s} {'Method':<25s} {'Good':<8s} {'Bad':<8s} {'Success':<10s}")
    print("-"*80)
    
    for column_name, col_analysis in sorted(analysis["column_analysis"].items()):
        print(
            f"{column_name:<30s} "
            f"{col_analysis['workflow']:<12s} "
            f"{col_analysis['subtype']:<20s} "
            f"{col_analysis['method']:<25s} "
            f"{col_analysis['good_count']:<8d} "
            f"{col_analysis['bad_count']:<8d} "
            f"{col_analysis['success_rate']:<10.2%}"
        )
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


def main():
    """Main test runner."""
    test_data_file = Path(__file__).parent / "comprehensive_workflow_test_data.csv"
    output_dir = "output"
    
    if not test_data_file.exists():
        logger.error(f"Test data file not found: {test_data_file}")
        return
    
    logger.info("="*80)
    logger.info("COMPREHENSIVE WORKFLOW TEST")
    logger.info("="*80)
    logger.info(f"Test Data: {test_data_file}")
    logger.info(f"Output Directory: {output_dir}")
    logger.info("="*80)
    
    try:
        # Try V2 first, fallback to V1 if database issues
        try:
            # Initialize enhanced pipeline with all features
            pipeline = PipelineServiceV2(
                output_dir=output_dir,
                enable_validation=True,
                enable_audit_logging=False,  # Disable to avoid file I/O issues
                enable_ensemble_detection=True,
                enable_ml_clustering=True,
                strict_mode=False  # Allow warnings for test data
            )
            logger.info("Using PipelineServiceV2")
        except Exception as e:
            logger.error(f"PipelineServiceV2 init failed: {e}")
            raise RuntimeError(f"Failed to initialize PipelineServiceV2: {e}")
            # Old PipelineService removed - use PipelineServiceV2 only
                output_dir=output_dir,
                enable_cache=False,  # Disable cache to avoid DB issues
                enable_llm_verification=False,
                enable_ml_clustering=True
            )
        
        # Run pipeline
        logger.info("Starting pipeline execution...")
        results = pipeline.run(
            input_path=str(test_data_file),
            has_header=True
        )
        
        logger.info("Pipeline execution completed successfully!")
        
        # Analyze results
        logger.info("Analyzing results...")
        analysis = analyze_results(output_dir)
        
        # Print report
        print_analysis_report(analysis)
        
        logger.info(f"\nDetailed analysis saved to: {Path(output_dir) / 'comprehensive_test_analysis.json'}")
        
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
