#!/usr/bin/env python3
"""
Data Anomaly Detector & Correction Tool
========================================
CLI entry point for running the data quality pipeline.

Usage:
    python run_pipeline.py input.csv
    python run_pipeline.py input.csv --no-header
    python run_pipeline.py input.csv --output-dir ./results
    python run_pipeline.py input.csv --enable-llm

Author: Data Quality Team
Version: 2.0.0
"""

import sys
import argparse
import logging
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.pipeline_service import PipelineService
from backend.config.settings import Settings, get_settings


def setup_logging(level: str = "INFO", log_file: str = None):
    """Configure logging"""
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


def clear_output_folder(output_dir: str):
    """
    Clear all files and subdirectories in the output folder.
    Preserves the output folder itself.
    """
    output_path = Path(output_dir)
    
    if not output_path.exists():
        return
    
    for item in output_path.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(str(item), ignore_errors=True)
            else:
                item.unlink()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not remove {item}: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Data Anomaly Detector & Correction Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_pipeline.py data/sample.csv
    python run_pipeline.py data/sample.csv --no-header
    python run_pipeline.py data/sample.csv --output-dir ./results
    python run_pipeline.py data/sample.csv --enable-llm --verbose
        """
    )
    
    parser.add_argument(
        "input",
        help="Input CSV file path"
    )
    
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="CSV file has no header row"
    )
    
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable detection caching"
    )
    
    parser.add_argument(
        "--enable-llm",
        action="store_true",
        help="Enable LLM verification (requires GROQ_API_KEY)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--log-file",
        help="Write logs to file"
    )
    
    parser.add_argument(
        "--no-ml",
        action="store_true",
        help="Disable ML-based clustering (use legacy rule-based)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level, args.log_file)
    
    logger = logging.getLogger(__name__)
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Data Anomaly Detector & Correction Tool v2.0.0")
    logger.info("=" * 60)
    logger.info(f"Input: {input_path}")
    logger.info(f"Output: {args.output_dir}")
    logger.info(f"Has Header: {not args.no_header}")
    logger.info(f"LLM Enabled: {args.enable_llm}")
    logger.info(f"ML Clustering: {not args.no_ml}")
    logger.info("=" * 60)
    
    # Clear output folder before running
    clear_output_folder(args.output_dir)
    logger.info(f"Cleared output folder: {args.output_dir}")
    
    try:
        # Create pipeline
        pipeline = PipelineService(
            output_dir=args.output_dir,
            enable_cache=not args.no_cache,
            enable_llm_verification=args.enable_llm,
            enable_ml_clustering=not args.no_ml,
        )
        
        # Run pipeline
        results = pipeline.run(
            input_path=str(input_path),
            has_header=not args.no_header,
        )
        
        # Print summary
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Columns processed: {results.get('total_columns', 0)}")
        logger.info(f"Good values: {results.get('total_good_values', 0)}")
        logger.info(f"Bad values: {results.get('total_bad_values', 0)}")
        logger.info(f"Corrected: {results.get('total_corrected', 0)}")
        logger.info(f"Success rate: {results.get('success_rate', 0):.1%}")
        logger.info("=" * 60)
        logger.info(f"Output files written to: {args.output_dir}/")
        
        if results.get("error_columns"):
            logger.warning(f"Columns with errors: {results['error_columns']}")
        
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
