"""
Correction Service
=================
Service for data classification + correction
"""

import json
import logging
import uuid
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd

import sys
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import correction modules to trigger registration
from backend.core import correction  # noqa: F401

from backend.core.registry import get_corrector_registry
from backend.core.interfaces import CorrectionResult, CorrectionStatus
from .classification_service import ClassificationService
from ..config import OUTPUT_DIR

logger = logging.getLogger(__name__)


class CorrectionService:
    """Service for classifying and correcting data."""
    
    def __init__(self, client_id: Optional[str] = None):
        self.client_id = client_id
        self.classification_service = ClassificationService(client_id=client_id)
        self.corrector_registry = get_corrector_registry()
    
    async def classify_and_correct(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[str] = None,
        has_header: bool = True,
        classification_options: Optional[Dict[str, Any]] = None,
        correction_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify data and apply corrections.
        
        Args:
            file_path: Path to input file
            file_content: File content
            has_header: Whether file has header
            classification_options: Classification options
            correction_options: Correction options (similarity_threshold, etc.)
            
        Returns:
            Dictionary with file paths and statistics
        """
        start_time = time.time()
        job_id = str(uuid.uuid4())
        
        try:
            # Step 1: Run classification first
            logger.info(f"Step 1: Running classification for job {job_id}")
            classification_result = await self.classification_service.classify(
                file_path=file_path,
                file_content=file_content,
                has_header=has_header,
                options=classification_options
            )
            
            classification_job_id = classification_result["job_id"]
            output_dir = OUTPUT_DIR / classification_job_id
            
            # Load classification results
            fingerprint_path = Path(classification_result["files"]["fingerprint"])
            with open(fingerprint_path, 'r', encoding='utf-8') as f:
                fingerprints = json.load(f)
            
            # Load original data (use same file that was used for classification)
            if file_path:
                original_df = pd.read_csv(file_path, header=0 if has_header else None)
            else:
                # Get temp file path (classification service saves it)
                from ..config import TEMP_DIR
                temp_file = TEMP_DIR / f"{classification_job_id}_input.csv"
                if temp_file.exists():
                    original_df = pd.read_csv(temp_file, header=0 if has_header else None)
                else:
                    # Fallback: recreate from file_content
                    from ..utils.file_utils import FileHandler
                    file_handler = FileHandler()
                    temp_file = await file_handler.prepare_file(
                        file_path=None,
                        file_content=file_content,
                        job_id=classification_job_id
                    )
                    original_df = pd.read_csv(temp_file, header=0 if has_header else None)
            if not has_header:
                original_df.columns = [f"column_{i}" for i in range(len(original_df.columns))]
            
            bad_data_path = Path(classification_result["files"]["bad_data"])
            bad_df = pd.read_csv(bad_data_path) if bad_data_path.exists() else pd.DataFrame()
            
            # Step 2: Apply corrections
            logger.info(f"Step 2: Applying corrections for job {job_id}")
            correction_options = correction_options or {}
            similarity_threshold = correction_options.get("similarity_threshold", 0.7)
            
            correction_results = await self._apply_corrections(
                original_df=original_df,
                bad_df=bad_df,
                fingerprints=fingerprints,
                similarity_threshold=similarity_threshold,
                output_dir=output_dir
            )
            
            # Step 3: Generate corrected data file
            logger.info(f"Step 3: Generating corrected data file")
            corrected_data_path = output_dir / "corrected_data.csv"
            corrected_df = await self._generate_corrected_data_file(
                original_df=original_df,
                correction_results=correction_results
            )
            corrected_df.to_csv(corrected_data_path, index=False)
            
            # Step 4: Update reject file (uncorrectable data)
            reject_data_path = Path(classification_result["files"]["reject_data"])
            updated_reject_df = await self._update_reject_file(
                original_df=original_df,
                correction_results=correction_results,
                existing_reject_df=pd.read_csv(reject_data_path) if reject_data_path.exists() else pd.DataFrame()
            )
            updated_reject_df.to_csv(reject_data_path, index=False)
            
            # Step 5: Generate correction report
            correction_report_path = output_dir / "correction_report.json"
            correction_report = await self._generate_correction_report(
                correction_results=correction_results,
                fingerprints=fingerprints
            )
            with open(correction_report_path, 'w', encoding='utf-8') as f:
                json.dump(correction_report, f, indent=2, default=str)
            
            # Step 6: Generate final_file.csv (good + corrected records, excluding rejects)
            final_file_path = output_dir / "final_file.csv"
            final_df = await self._generate_final_file(
                original_df=original_df,
                correction_results=correction_results,
                corrected_df=corrected_df,
                updated_reject_df=updated_reject_df
            )
            final_df.to_csv(final_file_path, index=False)
            logger.info(f"Generated final_file.csv: {len(final_df)} rows")
            
            # Calculate statistics
            statistics = await self._calculate_correction_statistics(
                classification_result["statistics"],
                correction_results,
                corrected_df,
                final_df,
                output_dir
            )
            
            processing_time = time.time() - start_time
            
            return {
                "status": "success",
                "job_id": job_id,
                "classification_job_id": classification_job_id,
                "files": {
                    "good_data": classification_result["files"]["good_data"],
                    "bad_data": classification_result["files"]["bad_data"],
                    "reject_data": str(reject_data_path),
                "corrected_data": str(corrected_data_path),
                "fingerprint": classification_result["files"]["fingerprint"],
                "correction_report": str(correction_report_path),
                "final_file": str(final_file_path)
            },
                "statistics": statistics,
                "metadata": {
                    "processing_time": round(processing_time, 2),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "job_id": job_id
                }
            }
            
        except Exception as e:
            logger.exception(f"Classification + correction failed: {e}")
            raise
    
    def _get_temp_file_path(self, job_id: str) -> str:
        """Get temporary file path for a job"""
        from ..config import TEMP_DIR
        temp_file = TEMP_DIR / f"{job_id}_input.csv"
        return str(temp_file)
    
    async def _apply_corrections(
        self,
        original_df: pd.DataFrame,
        bad_df: pd.DataFrame,
        fingerprints: Dict[str, Any],
        similarity_threshold: float,
        output_dir: Path
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Apply corrections to bad data.
        
        Args:
            original_df: Original dataframe
            bad_df: Bad data dataframe
            fingerprints: Column fingerprints
            similarity_threshold: Minimum similarity for correction
            output_dir: Output directory
            
        Returns:
            Dictionary mapping column_name to list of correction results
        """
        correction_results: Dict[str, List[Dict[str, Any]]] = {}
        
        # Group bad data by column
        if bad_df.empty:
            return correction_results
        
        for column_name in fingerprints.keys():
            column_bad_data = bad_df[bad_df["column_name"] == column_name]
            
            if column_bad_data.empty:
                continue
            
            fingerprint_data = fingerprints[column_name]
            workflow = fingerprint_data.get("workflow", "unknown")
            subtype = fingerprint_data.get("subtype", "unknown")
            method = fingerprint_data.get("method", "unknown")
            fingerprint = fingerprint_data.get("fingerprint", {})
            
            # Get corrector for this workflow-subtype
            corrector = self._get_corrector(workflow, subtype)
            
            if not corrector:
                logger.warning(f"No corrector found for {workflow}/{subtype}")
                continue
            
            # Apply corrections to bad values
            column_corrections = []
            for _, row in column_bad_data.iterrows():
                bad_value = row["original_value"]
                row_index = row["row_index"]
                
                try:
                    # Attempt correction
                    correction_result = corrector.correct(
                        value=bad_value,
                        fingerprint=fingerprint,
                        subtype=subtype,
                        column_name=column_name
                    )
                    
                    # Check similarity threshold
                    if correction_result.status == CorrectionStatus.CORRECTED:
                        if correction_result.confidence >= similarity_threshold:
                            # Correction accepted
                            column_corrections.append({
                                "column_name": column_name,
                                "row_index": row_index,
                                "original_value": bad_value,
                                "corrected_value": correction_result.corrected_value,
                                "status": correction_result.status.value,
                                "confidence": correction_result.confidence,
                                "changes_made": correction_result.changes_made,
                                "workflow": workflow,
                                "subtype": subtype,
                                "method": method
                            })
                        else:
                            # Correction rejected (low confidence)
                            column_corrections.append({
                                "column_name": column_name,
                                "row_index": row_index,
                                "original_value": bad_value,
                                "corrected_value": bad_value,
                                "status": CorrectionStatus.REJECTED.value,
                                "confidence": correction_result.confidence,
                                "reason": f"Low confidence: {correction_result.confidence:.2f} < {similarity_threshold}",
                                "workflow": workflow,
                                "subtype": subtype,
                                "method": method
                            })
                    elif correction_result.status == CorrectionStatus.REJECTED:
                        # Correction rejected
                        column_corrections.append({
                            "column_name": column_name,
                            "row_index": row_index,
                            "original_value": bad_value,
                            "corrected_value": bad_value,
                            "status": CorrectionStatus.REJECTED.value,
                            "confidence": correction_result.confidence,
                            "reason": correction_result.details.get("reason", "uncorrectable"),
                            "workflow": workflow,
                            "subtype": subtype,
                            "method": method
                        })
                    
                except Exception as e:
                    logger.warning(f"Correction failed for {column_name}[{row_index}]: {e}")
                    column_corrections.append({
                        "column_name": column_name,
                        "row_index": row_index,
                        "original_value": bad_value,
                        "corrected_value": bad_value,
                        "status": CorrectionStatus.REJECTED.value,
                        "confidence": 0.0,
                        "reason": f"Error: {str(e)}",
                        "workflow": workflow,
                        "subtype": subtype,
                        "method": method
                    })
            
            if column_corrections:
                correction_results[column_name] = column_corrections
        
        return correction_results
    
    def _get_corrector(self, workflow: str, subtype: str):
        """Get corrector for workflow-subtype combination"""
        # Try subtype first
        corrector = self.corrector_registry.get(subtype)
        
        if not corrector:
            # Try workflow-based corrector
            corrector = self.corrector_registry.get(workflow)
        
        if not corrector:
            # Try generic
            generic_name = f"generic_{workflow}" if workflow != "generic" else "generic"
            corrector = self.corrector_registry.get(generic_name)
        
        return corrector
    
    async def _generate_corrected_data_file(
        self,
        original_df: pd.DataFrame,
        correction_results: Dict[str, List[Dict[str, Any]]]
    ) -> pd.DataFrame:
        """
        Generate corrected_data.csv with corrected values applied.
        
        Args:
            original_df: Original dataframe
            correction_results: Correction results dictionary
            
        Returns:
            DataFrame with corrections applied
        """
        corrected_df = original_df.copy()
        
        # Apply corrections
        for column_name, corrections in correction_results.items():
            for correction in corrections:
                if correction["status"] == CorrectionStatus.CORRECTED.value:
                    row_idx = correction["row_index"]
                    if row_idx < len(corrected_df):
                        corrected_df.loc[row_idx, column_name] = correction["corrected_value"]
        
        return corrected_df
    
    async def _update_reject_file(
        self,
        original_df: pd.DataFrame,
        correction_results: Dict[str, List[Dict[str, Any]]],
        existing_reject_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Update reject file with uncorrectable data.
        
        Args:
            original_df: Original dataframe
            correction_results: Correction results
            existing_reject_df: Existing reject dataframe
            
        Returns:
            Updated reject dataframe
        """
        # Collect row indices that were rejected during correction
        rejected_indices = set()
        
        for corrections in correction_results.values():
            for correction in corrections:
                if correction["status"] == CorrectionStatus.REJECTED.value:
                    rejected_indices.add(correction["row_index"])
        
        # Combine with existing rejects
        if not existing_reject_df.empty:
            existing_indices = set(existing_reject_df.index)
            rejected_indices.update(existing_indices)
        
        # Return rejected rows
        if rejected_indices:
            return original_df.loc[list(rejected_indices)].copy()
        else:
            return pd.DataFrame(columns=original_df.columns)
    
    async def _generate_correction_report(
        self,
        correction_results: Dict[str, List[Dict[str, Any]]],
        fingerprints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate correction report JSON.
        
        Args:
            correction_results: Correction results
            fingerprints: Column fingerprints
            
        Returns:
            Correction report dictionary
        """
        report = {
            "summary": {
                "total_corrections_attempted": 0,
                "corrections_applied": 0,
                "corrections_rejected": 0,
                "columns_processed": len(correction_results)
            },
            "by_column": {}
        }
        
        total_attempted = 0
        total_applied = 0
        total_rejected = 0
        
        for column_name, corrections in correction_results.items():
            column_report = {
                "column_name": column_name,
                "workflow": fingerprints.get(column_name, {}).get("workflow", "unknown"),
                "subtype": fingerprints.get(column_name, {}).get("subtype", "unknown"),
                "method": fingerprints.get(column_name, {}).get("method", "unknown"),
                "corrections_attempted": len(corrections),
                "corrections_applied": 0,
                "corrections_rejected": 0,
                "corrections": []
            }
            
            for correction in corrections:
                total_attempted += 1
                if correction["status"] == CorrectionStatus.CORRECTED.value:
                    total_applied += 1
                    column_report["corrections_applied"] += 1
                else:
                    total_rejected += 1
                    column_report["corrections_rejected"] += 1
                
                column_report["corrections"].append(correction)
            
            report["by_column"][column_name] = column_report
        
        report["summary"]["total_corrections_attempted"] = total_attempted
        report["summary"]["corrections_applied"] = total_applied
        report["summary"]["corrections_rejected"] = total_rejected
        
        return report
    
    async def _generate_final_file(
        self,
        original_df: pd.DataFrame,
        correction_results: Dict[str, List[Dict[str, Any]]],
        corrected_df: pd.DataFrame,
        updated_reject_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Generate final_file.csv containing good + corrected records (excluding rejects).
        
        For correction: final_file = good_data + corrected_data - reject_data
        
        Args:
            original_df: Original dataframe
            correction_results: Correction results
            corrected_df: DataFrame with corrections applied
            updated_reject_df: DataFrame with rejected rows
            
        Returns:
            DataFrame with good + corrected records (excluding rejects)
        """
        # Get reject row indices
        reject_indices = set(updated_reject_df.index) if not updated_reject_df.empty else set()
        
        # Start with corrected data (which includes good + corrected)
        final_df = corrected_df.copy()
        
        # Remove reject rows
        if reject_indices:
            # Use original index to match reject indices
            final_df = final_df[~final_df.index.isin(reject_indices)]
        
        # Reset index for clean output
        final_df = final_df.reset_index(drop=True)
        
        return final_df
    
    async def _calculate_correction_statistics(
        self,
        classification_stats: Dict[str, int],
        correction_results: Dict[str, List[Dict[str, Any]]],
        corrected_df: pd.DataFrame,
        final_df: pd.DataFrame,
        output_dir: Path
    ) -> Dict[str, int]:
        """Calculate correction statistics"""
        # Count corrections
        corrections_applied = 0
        corrections_rejected = 0
        
        for corrections in correction_results.values():
            for correction in corrections:
                if correction["status"] == CorrectionStatus.CORRECTED.value:
                    corrections_applied += 1
                else:
                    corrections_rejected += 1
        
        # Count corrected rows
        corrected_rows = len(corrected_df) if not corrected_df.empty else 0
        
        # Count final rows (good + corrected, excluding rejects)
        final_rows = len(final_df) if final_df is not None and not final_df.empty else 0
        
        return {
            "total_rows": classification_stats["total_rows"],
            "good_rows": classification_stats["good_rows"],
            "bad_rows": classification_stats["bad_rows"],
            "corrected_rows": corrected_rows,
            "reject_rows": classification_stats["reject_rows"],
            "final_rows": final_rows,
            "columns_processed": classification_stats["columns_processed"],
            "total_good_values": classification_stats["total_good_values"],
            "total_bad_values": classification_stats["total_bad_values"],
            "corrections_applied": corrections_applied,
            "corrections_rejected": corrections_rejected
        }
