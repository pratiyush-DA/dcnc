"""
Pipeline Service
Main orchestrator for the data quality pipeline

Integrates with UnifiedDBManager for:
- Fingerprint storage
- LLM caching
- Detection caching
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

import pandas as pd

from ..core.detection import WorkflowDetector
from ..core.workflows import (
    StringWorkflow,
    NumericWorkflow,
    DateTimeWorkflow,
    IdentifierWorkflow,
)
from ..core.correction import OutputWriter
from ..core.interfaces import ClusterResult
from ..core.registry import (
    get_workflow_registry,
    get_corrector_registry,
    get_validator_registry,
)

# Import engines and correction to trigger registration
from ..core import engines  # noqa: F401
from ..core import correction  # noqa: F401
from ..core.llm import LLMReshuffler

# Unified database manager
from ..database import get_db_manager

logger = logging.getLogger(__name__)


class PipelineService:
    """
    Main pipeline orchestrator.
    
    Coordinates:
    1. Data loading
    2. Column type detection (heuristic + pattern, NO LLM)
    3. Workflow-based clustering
    4. Fingerprint generation
    5. Correction (using fingerprints)
    6. Output generation
    """
    
    def __init__(
        self,
        output_dir: str = "output",
        enable_cache: bool = True,
        enable_llm_verification: bool = False,
        enable_ml_clustering: bool = True,
    ):
        """
        Initialize pipeline.
        
        Args:
            output_dir: Output directory path
            enable_cache: Enable detection caching
            enable_llm_verification: Enable LLM verification (optional)
            enable_ml_clustering: Enable ML-based clustering (IsolationForest, DBSCAN, etc.)
        """
        self._detector = WorkflowDetector(enable_cache=enable_cache)
        self._output_writer = OutputWriter(output_dir)
        self._enable_llm = enable_llm_verification
        self._enable_ml_clustering = enable_ml_clustering
        
        # Initialize unified database manager
        self._db = get_db_manager()
        
        # Initialize LLM reshuffler (lazy - only if enabled)
        self._reshuffler = None
        if enable_llm_verification:
            try:
                self._reshuffler = LLMReshuffler()  # Now uses unified db_manager
                logger.info("LLM Reshuffler initialized with unified db_manager")
            except Exception as e:
                logger.warning(f"LLM Reshuffler init failed: {e}")
                self._enable_llm = False
        
        # Initialize workflows
        self._workflows = {
            "text": StringWorkflow(),
            "numeric": NumericWorkflow(),
            "datetime": DateTimeWorkflow(),
            "identifier": IdentifierWorkflow(),
        }
        
        # Output directory for fingerprints JSON
        self._output_dir = Path(output_dir)
        
        logger.info(f"PipelineService initialized (LLM: {self._enable_llm}, ML: {self._enable_ml_clustering})")
    
    def run(
        self,
        input_path: str,
        has_header: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline.
        
        Args:
            input_path: Path to input CSV file
            has_header: Whether file has header row
            
        Returns:
            Pipeline results dictionary
        """
        logger.info(f"Starting pipeline: {input_path}")
        
        # Load data
        df = self._load_data(input_path, has_header)
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Process each column
        results = {}
        
        for column in df.columns:
            logger.info(f"Processing column: {column}")
            
            try:
                column_result = self._process_column(
                    df[column].tolist(),
                    column,
                    list(range(len(df)))
                )
                results[column] = column_result
            except Exception as e:
                logger.error(f"Error processing column {column}: {e}")
                results[column] = {"error": str(e)}
        
        # Generate outputs
        self._generate_outputs(df, results)
        
        # Write consolidated good/bad files (Wide Format)
        self._output_writer.write_consolidated_files()
        
        # Export fingerprints to JSON for correction engine
        fingerprints_path = self._output_dir / "fingerprints.json"
        try:
            self._db.export_fingerprints_json(str(fingerprints_path))
            logger.info(f"Exported fingerprints to {fingerprints_path}")
        except Exception as e:
            logger.warning(f"Failed to export fingerprints: {e}")
        
        # Generate summary
        summary = self._generate_summary(results)
        self._output_writer.write_summary_report(summary)
        
        logger.info("Pipeline completed")
        return summary
    
    def _load_data(self, path: str, has_header: bool) -> pd.DataFrame:
        """Load data from CSV"""
        if has_header:
            df = pd.read_csv(path)
        else:
            df = pd.read_csv(path, header=None)
            # Generate column names
            df.columns = [f"col_{i}" for i in range(len(df.columns))]
        
        return df
    
    def _process_column(
        self,
        data: List[Any],
        column_name: str,
        indices: List[int]
    ) -> Dict[str, Any]:
        """
        Process a single column through the pipeline.
        
        Steps:
        1. Detect column type (heuristic + pattern)
        2. Route to appropriate workflow
        3. Cluster data (good/bad)
        4. Generate fingerprint
        5. Apply corrections
        6. Write outputs
        
        Args:
            data: Column data
            column_name: Column name
            indices: Row indices
            
        Returns:
            Processing result dictionary
        """
        # Detect column type
        detection = self._detector.detect(
            column_name,
            data[:100]  # Sample for detection
        )
        
        logger.debug(
            f"Detected: {detection.workflow}/{detection.subtype} "
            f"(confidence: {detection.confidence:.2f})"
        )
        
        # Get workflow
        workflow = self._workflows.get(detection.workflow)
        if not workflow:
            logger.warning(f"No workflow for type: {detection.workflow}")
            workflow = self._workflows["text"]  # Fallback to text
        
        # Cluster data using ML-based clustering if enabled
        if self._enable_ml_clustering and hasattr(workflow, 'cluster_v2'):
            cluster_result = workflow.cluster_v2(
                data=data,
                indices=indices,
                column_name=column_name,
                subtype=detection.subtype,
                use_ml=True,
            )
            logger.debug(f"Used ML clustering for {column_name}")
        else:
            cluster_result = workflow.cluster(
                data=data,
                indices=indices,
                column_name=column_name,
                subtype=detection.subtype,
            )
        
        # LLM Reshuffling (if enabled and we have good data for fingerprint)
        llm_stats = None
        if self._enable_llm and self._reshuffler and cluster_result.fingerprint:
            try:
                reshuffle_result = self._reshuffler.reshuffle(
                    good_data=cluster_result.good_data,
                    bad_data=cluster_result.bad_data,
                    good_indices=cluster_result.good_indices,
                    bad_indices=cluster_result.bad_indices,
                    workflow=detection.workflow,
                    subtype=detection.subtype,
                    fingerprint=cluster_result.fingerprint,
                    column_name=column_name,
                )
                
                # Apply promotions (bad -> good)
                if reshuffle_result.promoted_to_good:
                    promoted_indices = {idx for _, idx in reshuffle_result.promoted_to_good}
                    
                    # Remove from bad, add to good
                    new_bad_data = []
                    new_bad_indices = []
                    for v, i in zip(cluster_result.bad_data, cluster_result.bad_indices):
                        if i in promoted_indices:
                            cluster_result.good_data.append(v)
                            cluster_result.good_indices.append(i)
                        else:
                            new_bad_data.append(v)
                            new_bad_indices.append(i)
                    
                    cluster_result.bad_data = new_bad_data
                    cluster_result.bad_indices = new_bad_indices
                    
                    logger.info(
                        f"LLM promoted {len(reshuffle_result.promoted_to_good)} "
                        f"values to good for {column_name}"
                    )
                
                llm_stats = {
                    "promoted_count": len(reshuffle_result.promoted_to_good),
                    "patterns_used": len(reshuffle_result.patterns_used),
                    "from_cache": reshuffle_result.from_cache,
                    "tokens_used": reshuffle_result.tokens_used,
                }
                
            except Exception as e:
                logger.warning(f"LLM reshuffling failed for {column_name}: {e}")
        
        # Write good/bad files
        self._output_writer.write_good_bad(
            column_name=column_name,
            good_data=cluster_result.good_data,
            bad_data=cluster_result.bad_data,
            good_indices=cluster_result.good_indices,
            bad_indices=cluster_result.bad_indices,
        )
        
        # Apply corrections to bad data
        correction_results = []
        if cluster_result.bad_data and cluster_result.fingerprint:
            corrector = workflow.get_corrector(detection.subtype)
            
            if corrector:
                for value in cluster_result.bad_data:
                    result = corrector.correct(
                        value=value,
                        fingerprint=cluster_result.fingerprint,
                        subtype=detection.subtype,
                        column_name=column_name,
                    )
                    correction_results.append({
                        "original": result.original_value,
                        "corrected": result.corrected_value,
                        "status": result.status.value,
                        "changes": result.changes_made,
                    })
        
        result = {
            "column_name": column_name,
            "workflow": detection.workflow,
            "subtype": detection.subtype,
            "detection_confidence": detection.confidence,
            "detection_source": detection.source.value,
            "good_count": len(cluster_result.good_data),
            "bad_count": len(cluster_result.bad_data),
            "fingerprint": cluster_result.fingerprint,
            "corrections": correction_results,
        }
        
        # Save fingerprint to database for correction engine
        if cluster_result.fingerprint:
            try:
                # Determine clusterer name from fingerprint
                clusterer = cluster_result.fingerprint.get("method", "unknown")
                
                # Extract correction hints
                correction_hints = cluster_result.fingerprint.get("correction_hints", {})
                if not correction_hints:
                    # Build from fingerprint properties
                    correction_hints = {
                        "workflow": detection.workflow,
                        "subtype": detection.subtype,
                    }
                    if "reference_values" in cluster_result.fingerprint:
                        correction_hints["reference_values"] = cluster_result.fingerprint["reference_values"]
                    if "bounds" in cluster_result.fingerprint:
                        correction_hints["bounds"] = cluster_result.fingerprint["bounds"]
                    if "properties" in cluster_result.fingerprint:
                        props = cluster_result.fingerprint["properties"]
                        if "case_style" in props:
                            correction_hints["expected_case"] = props["case_style"]
                
                # Sample good values
                sample_good = cluster_result.good_data[:10] if cluster_result.good_data else []
                
                self._db.save_fingerprint(
                    column_name=column_name,
                    workflow=detection.workflow,
                    subtype=detection.subtype,
                    clusterer=clusterer,
                    fingerprint=cluster_result.fingerprint,
                    correction_hints=correction_hints,
                    sample_good_values=sample_good,
                    good_count=len(cluster_result.good_data),
                    bad_count=len(cluster_result.bad_data),
                )
                logger.debug(f"Saved fingerprint for {column_name}")
            except Exception as e:
                logger.warning(f"Failed to save fingerprint for {column_name}: {e}")
        
        # Add LLM stats if available
        if llm_stats:
            result["llm_verification"] = llm_stats
        
        return result
    
    def _generate_outputs(
        self,
        df: pd.DataFrame,
        results: Dict[str, Any]
    ):
        """Generate final output files"""
        # Add status columns to dataframe
        status_df = df.copy()
        
        for column, result in results.items():
            if "error" not in result:
                # Create status column
                status_col = f"{column}_status"
                status_df[status_col] = "good"
                
                # Mark bad rows
                bad_indices = []
                if "bad_indices" in result:
                    bad_indices = result["bad_indices"]
                
                for idx in bad_indices:
                    if idx < len(status_df):
                        status_df.loc[idx, status_col] = "bad"
        
        # Write final output
        self._output_writer.write_final_output(status_df)
        
        # Write correction report
        self._output_writer.write_correction_report(results)
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pipeline summary"""
        total_columns = len(results)
        total_good = 0
        total_bad = 0
        total_corrected = 0
        
        workflow_counts = {}
        error_columns = []
        
        for column, result in results.items():
            if "error" in result:
                error_columns.append(column)
                continue
            
            total_good += result.get("good_count", 0)
            total_bad += result.get("bad_count", 0)
            
            corrections = result.get("corrections", [])
            total_corrected += sum(
                1 for c in corrections if c.get("status") == "corrected"
            )
            
            workflow = result.get("workflow", "unknown")
            workflow_counts[workflow] = workflow_counts.get(workflow, 0) + 1
        
        return {
            "total_columns": total_columns,
            "total_good_values": total_good,
            "total_bad_values": total_bad,
            "total_corrected": total_corrected,
            "workflow_distribution": workflow_counts,
            "error_columns": error_columns,
            "success_rate": total_good / (total_good + total_bad) if (total_good + total_bad) > 0 else 0,
        }
