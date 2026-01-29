"""
Classification Service
=====================
Service for data classification with async support for large files
"""

import json
import logging
import uuid
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from datetime import datetime
import pandas as pd

import sys
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.services.pipeline_service_v2 import PipelineServiceV2
from backend.core.correction.output_writer import OutputWriter
from ..config import OUTPUT_DIR
from ..utils.file_utils import FileHandler

logger = logging.getLogger(__name__)


class ClassificationService:
    """Service for classifying data into good/bad/reject."""
    
    def __init__(self, client_id: Optional[str] = None):
        self.file_handler = FileHandler()
        self.client_id = client_id
    
    async def classify(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[str] = None,
        has_header: bool = True,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify data into good/bad/reject.
        
        Args:
            file_path: Path to input file
            file_content: File content (base64 or raw)
            has_header: Whether file has header
            options: Classification options
            
        Returns:
            Dictionary with file paths and statistics
        """
        start_time = time.time()
        job_id = str(uuid.uuid4())
        
        try:
            # Prepare file
            input_file = await self.file_handler.prepare_file(
                file_path=file_path,
                file_content=file_content,
                job_id=job_id
            )
            
            # Create output directory
            output_dir = OUTPUT_DIR / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Load original dataframe for reject file generation
            original_df = pd.read_csv(input_file, header=0 if has_header else None)
            if not has_header:
                original_df.columns = [f"column_{i}" for i in range(len(original_df.columns))]
            
            # Initialize pipeline with fresh fingerprints (API mode)
            pipeline_options = options or {}
            
            # Try to initialize pipeline, but handle DB errors gracefully
            try:
                pipeline = PipelineServiceV2(
                    client_id=self.client_id,  # Pass client_id for multi-tenancy
                    output_dir=str(output_dir),
                    enable_cache=self.client_id is not None,  # Enable cache if client_id provided
                    enable_llm_verification=pipeline_options.get("enable_llm_verification", False),
                    enable_ml_clustering=pipeline_options.get("enable_ml_clustering", True),
                    enable_ensemble_detection=pipeline_options.get("enable_ensemble_detection", True),
                    enable_validation=pipeline_options.get("enable_validation", True),
                    enable_audit_logging=pipeline_options.get("enable_audit_logging", False),
                    strict_mode=pipeline_options.get("strict_mode", False),
                    fresh_fingerprints_only=True,  # API mode: fresh fingerprints per file
                    skip_cli_outputs=True,  # API mode: skip CLI-specific outputs (API has its own output generation)
                )
            except Exception as db_error:
                # If DB initialization fails, try again with DB disabled
                logger.warning(f"DB initialization failed, retrying without DB: {db_error}")
                # The fresh_fingerprints_only flag should prevent DB usage, but if it still fails,
                # we'll catch it here and continue
                raise
            
            # Run classification
            logger.info(f"Starting classification for job {job_id}")
            summary = pipeline.run(
                input_path=str(input_file),
                has_header=has_header
            )
            
            # Get results from pipeline (stored during run)
            results = getattr(pipeline, '_last_results', {})
            
            # Generate output files
            output_files = await self._generate_output_files(
                original_df=original_df,
                results=results,
                output_dir=output_dir,
                job_id=job_id
            )
            
            # Calculate statistics
            statistics = await self._calculate_statistics(
                original_df=original_df,
                results=results,
                output_dir=output_dir
            )
            
            processing_time = time.time() - start_time
            
            return {
                "status": "success",
                "job_id": job_id,
                "files": output_files,
                "statistics": statistics,
                "metadata": {
                    "processing_time": round(processing_time, 2),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "job_id": job_id
                }
            }
            
        except Exception as e:
            logger.exception(f"Classification failed: {e}")
            raise
    
    async def _generate_output_files(
        self,
        original_df: pd.DataFrame,
        results: Dict[str, Any],
        output_dir: Path,
        job_id: str
    ) -> Dict[str, str]:
        """
        Generate output files: good_data.csv, bad_data.csv, reject_data.csv, fingerprint.json
        
        Args:
            original_df: Original dataframe
            results: Pipeline results dictionary
            output_dir: Output directory
            job_id: Job identifier
            
        Returns:
            Dictionary with file paths
        """
        logger.info("Generating output files...")
        
        # 1. Generate good_data.csv (rows where ALL columns are good)
        good_data_path = output_dir / "good_data.csv"
        good_df = await self._generate_good_data_file(original_df, results)
        good_df.to_csv(good_data_path, index=False)
        logger.info(f"Generated good_data.csv: {len(good_df)} rows")
        
        # 2. Generate bad_data.csv (column-wise bad data)
        bad_data_path = output_dir / "bad_data.csv"
        bad_df = await self._generate_bad_data_file(original_df, results)
        bad_df.to_csv(bad_data_path, index=False)
        logger.info(f"Generated bad_data.csv: {len(bad_df)} rows")
        
        # 3. Generate reject_data.csv (rows where ANY column has bad data)
        reject_data_path = output_dir / "reject_data.csv"
        reject_df = await self._generate_reject_file(original_df, results)
        reject_df.to_csv(reject_data_path, index=False)
        logger.info(f"Generated reject_data.csv: {len(reject_df)} rows")
        
        # 4. Generate fingerprint.json (all column fingerprints)
        fingerprint_path = output_dir / "fingerprint.json"
        fingerprint_data = await self._generate_fingerprint_file(results)
        with open(fingerprint_path, 'w', encoding='utf-8') as f:
            json.dump(fingerprint_data, f, indent=2, default=str)
        logger.info(f"Generated fingerprint.json: {len(fingerprint_data)} columns")
        
        # 5. Generate final_file.csv (good records only, excluding rejects)
        final_file_path = output_dir / "final_file.csv"
        final_df = await self._generate_final_file(original_df, results)
        final_df.to_csv(final_file_path, index=False)
        logger.info(f"Generated final_file.csv: {len(final_df)} rows")
        
        return {
            "good_data": str(good_data_path),
            "bad_data": str(bad_data_path),
            "reject_data": str(reject_data_path),
            "fingerprint": str(fingerprint_path),
            "final_file": str(final_file_path)
        }
    
    async def _generate_good_data_file(
        self,
        original_df: pd.DataFrame,
        results: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Generate good_data.csv containing rows where ALL columns are good.
        
        Rule: A row is "good" only if EVERY column in that row has good data.
        If ANY column has bad data, the row is excluded from good_data.csv.
        
        Args:
            original_df: Original dataframe
            results: Pipeline results dictionary
            
        Returns:
            DataFrame with good rows only (rows where ALL columns are good)
        """
        # Start with all row indices (0-based)
        all_good_indices: Set[int] = set(range(len(original_df)))
        
        # Track all columns that were processed
        processed_columns = 0
        
        for column_name, result in results.items():
            # Skip if result is not a dictionary
            if not isinstance(result, dict):
                continue
            
            # Skip columns with errors (treat as all bad)
            if "error" in result:
                logger.warning(f"Column {column_name} has error, excluding from good data calculation")
                # If column processing failed, exclude all rows for that column
                all_good_indices.clear()
                continue
            
            processed_columns += 1
            
            # Get bad indices for this column
            bad_indices = result.get("bad_indices", [])
            
            # Ensure bad_indices is a list/set of integers
            if not isinstance(bad_indices, (list, set)):
                logger.warning(f"Column {column_name} has invalid bad_indices type: {type(bad_indices)}")
                continue
            
            # Convert to set and ensure all are integers
            bad_indices_set = set()
            for idx in bad_indices:
                try:
                    bad_indices_set.add(int(idx))
                except (ValueError, TypeError):
                    logger.warning(f"Column {column_name} has invalid bad_index: {idx}")
                    continue
            
            # Remove rows with bad data in this column from good_indices
            # This ensures only rows where ALL columns are good remain
            all_good_indices -= bad_indices_set
            
            logger.debug(
                f"Column {column_name}: {len(bad_indices_set)} bad values, "
                f"{len(all_good_indices)} rows still good"
            )
        
        logger.info(
            f"Good data calculation: {processed_columns} columns processed, "
            f"{len(all_good_indices)} rows with all good values"
        )
        
        # Return rows with all good columns
        if all_good_indices:
            good_df = original_df.loc[list(all_good_indices)].copy()
            logger.info(f"Generated good_data.csv with {len(good_df)} rows")
            return good_df
        else:
            # Return empty dataframe with same columns
            logger.info("No rows with all good values, returning empty good_data.csv")
            return pd.DataFrame(columns=original_df.columns)
    
    async def _generate_bad_data_file(
        self,
        original_df: pd.DataFrame,
        results: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Generate bad_data.csv containing column-wise bad data.
        
        Format: column_name, row_index, original_value, workflow, subtype, method
        
        Args:
            original_df: Original dataframe
            results: Pipeline results dictionary
            
        Returns:
            DataFrame with bad data details
        """
        bad_records = []
        
        for column_name, result in results.items():
            # Skip if result is not a dictionary
            if not isinstance(result, dict):
                continue
            if "error" in result:
                continue
            
            bad_data = result.get("bad_data", [])
            bad_indices = result.get("bad_indices", [])
            workflow = result.get("workflow", "unknown")
            subtype = result.get("subtype", "unknown")
            method = result.get("method", "unknown")
            
            for value, idx in zip(bad_data, bad_indices):
                bad_records.append({
                    "column_name": column_name,
                    "row_index": idx,
                    "original_value": value,
                    "workflow": workflow,
                    "subtype": subtype,
                    "method": method
                })
        
        if bad_records:
            return pd.DataFrame(bad_records)
        else:
            return pd.DataFrame(columns=[
                "column_name", "row_index", "original_value",
                "workflow", "subtype", "method"
            ])
    
    async def _generate_reject_file(
        self,
        original_df: pd.DataFrame,
        results: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Generate reject_data.csv containing rows where ANY column has bad data.
        
        Rule: If ANY column in a row has bad data, reject the entire row.
        This is the complement of good_data.csv (all rows except those in good_data).
        
        Args:
            original_df: Original dataframe
            results: Pipeline results dictionary
            
        Returns:
            DataFrame with rejected rows (rows with at least one bad value)
        """
        # Collect all row indices that have at least one bad column
        all_bad_row_indices: Set[int] = set()
        processed_columns = 0
        
        for column_name, result in results.items():
            # Skip if result is not a dictionary
            if not isinstance(result, dict):
                continue
            
            # If column processing failed, reject all rows for that column
            if "error" in result:
                logger.warning(f"Column {column_name} has error, rejecting all rows")
                all_bad_row_indices.update(range(len(original_df)))
                continue
            
            processed_columns += 1
            
            # Get bad indices for this column
            bad_indices = result.get("bad_indices", [])
            
            # Ensure bad_indices is a list/set
            if not isinstance(bad_indices, (list, set)):
                logger.warning(f"Column {column_name} has invalid bad_indices type: {type(bad_indices)}")
                continue
            
            # Convert to integers and add to set
            for idx in bad_indices:
                try:
                    all_bad_row_indices.add(int(idx))
                except (ValueError, TypeError):
                    logger.warning(f"Column {column_name} has invalid bad_index: {idx}")
                    continue
        
        logger.info(
            f"Reject data calculation: {processed_columns} columns processed, "
            f"{len(all_bad_row_indices)} rows with at least one bad value"
        )
        
        # Return rows with any bad data
        if all_bad_row_indices:
            reject_df = original_df.loc[list(all_bad_row_indices)].copy()
            logger.info(f"Generated reject_data.csv with {len(reject_df)} rows")
            return reject_df
        else:
            # Return empty dataframe with same columns
            logger.info("No rows with bad values, returning empty reject_data.csv")
            return pd.DataFrame(columns=original_df.columns)
    
    async def _generate_fingerprint_file(
        self,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate fingerprint.json containing all column fingerprints.
        
        Args:
            results: Pipeline results dictionary
            
        Returns:
            Dictionary with column fingerprints
        """
        fingerprints = {}
        
        for column_name, result in results.items():
            if "error" in result:
                continue
            
            fingerprint = result.get("fingerprint", {})
            if fingerprint:
                fingerprints[column_name] = {
                    "workflow": result.get("workflow", "unknown"),
                    "subtype": result.get("subtype", "unknown"),
                    "method": result.get("method", "unknown"),
                    "detection_confidence": result.get("detection_confidence", 0.0),
                    "clustering_confidence": result.get("clustering_confidence", 0.0),
                    "good_count": result.get("good_count", 0),
                    "bad_count": result.get("bad_count", 0),
                    "fingerprint": fingerprint
                }
        
        return fingerprints
    
    async def _generate_final_file(
        self,
        original_df: pd.DataFrame,
        results: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Generate final_file.csv containing only good records (excluding rejects).
        
        For classification: final_file = good_data (all columns are good)
        This should be identical to good_data.csv - rows where ALL columns are good.
        
        Args:
            original_df: Original dataframe
            results: Pipeline results dictionary
            
        Returns:
            DataFrame with good records only (rows where ALL columns are good)
        """
        # Use the same logic as good_data.csv
        # Find rows where ALL columns are good
        all_good_indices: Set[int] = set(range(len(original_df)))
        
        for column_name, result in results.items():
            # Skip if result is not a dictionary
            if not isinstance(result, dict):
                continue
            
            # Skip columns with errors (treat as all bad)
            if "error" in result:
                all_good_indices.clear()
                continue
            
            # Get bad indices for this column
            bad_indices = result.get("bad_indices", [])
            
            # Ensure bad_indices is a list/set of integers
            if not isinstance(bad_indices, (list, set)):
                continue
            
            # Convert to set and ensure all are integers
            bad_indices_set = set()
            for idx in bad_indices:
                try:
                    bad_indices_set.add(int(idx))
                except (ValueError, TypeError):
                    continue
            
            # Remove rows with bad data in this column
            all_good_indices -= bad_indices_set
        
        # Return rows with all good columns (same as good_data.csv)
        if all_good_indices:
            return original_df.loc[list(all_good_indices)].copy()
        else:
            # Return empty dataframe with same columns
            return pd.DataFrame(columns=original_df.columns)
    
    async def _calculate_statistics(
        self,
        original_df: pd.DataFrame,
        results: Dict[str, Any],
        output_dir: Path
    ) -> Dict[str, int]:
        """
        Calculate classification statistics.
        
        Args:
            original_df: Original dataframe
            results: Pipeline results dictionary
            output_dir: Output directory (for reading generated files)
            
        Returns:
            Dictionary with statistics
        """
        total_rows = len(original_df)
        columns_processed = len([r for r in results.values() if "error" not in r])
        
        # Count good/bad values
        total_good_values = 0
        total_bad_values = 0
        
        for result in results.values():
            # Skip if result is not a dictionary
            if not isinstance(result, dict):
                continue
            if "error" not in result:
                total_good_values += result.get("good_count", 0)
                total_bad_values += result.get("bad_count", 0)
        
        # Count good/reject/final rows (read from generated files)
        good_rows = 0
        reject_rows = 0
        final_rows = 0
        
        good_data_path = output_dir / "good_data.csv"
        if good_data_path.exists():
            try:
                good_df = pd.read_csv(good_data_path)
                good_rows = len(good_df)
            except Exception as e:
                logger.warning(f"Could not read good_data.csv for statistics: {e}")
        
        reject_data_path = output_dir / "reject_data.csv"
        if reject_data_path.exists():
            try:
                reject_df = pd.read_csv(reject_data_path)
                reject_rows = len(reject_df)
            except Exception as e:
                logger.warning(f"Could not read reject_data.csv for statistics: {e}")
        
        final_file_path = output_dir / "final_file.csv"
        if final_file_path.exists():
            try:
                final_df = pd.read_csv(final_file_path)
                final_rows = len(final_df)
            except Exception as e:
                logger.warning(f"Could not read final_file.csv for statistics: {e}")
        
        # Bad rows = rows with at least one bad value
        # This should be: Total Rows - Good Rows
        # (Rows that are NOT completely good)
        bad_rows = total_rows - good_rows
        
        # Reject rows = same as bad rows (rows with any bad value are rejected)
        # But we read it from file to verify, and use it if it makes sense
        # If reject_rows doesn't match bad_rows, log a warning
        if reject_rows != bad_rows:
            logger.warning(
                f"Statistics mismatch: bad_rows={bad_rows} (calculated) vs reject_rows={reject_rows} (from file). "
                f"Using calculated value: bad_rows = total_rows - good_rows = {total_rows} - {good_rows} = {bad_rows}"
            )
            # Use the calculated value for consistency
            reject_rows = bad_rows
        
        logger.info(
            f"Statistics: total={total_rows}, good={good_rows}, bad={bad_rows}, "
            f"reject={reject_rows}, final={final_rows}"
        )
        
        return {
            "total_rows": total_rows,
            "good_rows": good_rows,
            "bad_rows": bad_rows,
            "reject_rows": reject_rows,
            "final_rows": final_rows,
            "columns_processed": columns_processed,
            "total_good_values": total_good_values,
            "total_bad_values": total_bad_values
        }
