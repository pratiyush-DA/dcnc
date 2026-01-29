"""
Pipeline Service V2
Enhanced pipeline service with all improvements integrated.

Features:
- Input validation & sanitization
- Audit logging
- Graceful degradation
- Confidence scoring
- Ensemble detection
- Circuit breakers
- Comprehensive error handling
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

import pandas as pd

from ..core.detection import WorkflowDetector
from ..core.detection.ensemble_detector import EnsembleDetector
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

# Security components
from ..core.security import InputValidator, DataSanitizer, AuditLogger

# Resilience components
from ..core.resilience import (
    GracefulDegradationHandler,
    CircuitBreaker,
    ConfidenceScorer
)

# Exceptions
from ..core.exceptions import (
    DataQualityError,
    DetectionError,
    ClusteringError,
    ValidationError,
    SecurityError
)

# Import engines and correction to trigger registration
from ..core import engines  # noqa: F401
from ..core import correction  # noqa: F401
from ..core.llm import LLMReshuffler

# Unified database manager
from ..database import get_db_manager

logger = logging.getLogger(__name__)


class PipelineServiceV2:
    """
    Enhanced pipeline orchestrator with all improvements.
    
    New Features:
    - Input validation & sanitization
    - Audit logging for all operations
    - Graceful degradation with fallbacks
    - Confidence scoring for results
    - Ensemble detection for better accuracy
    - Circuit breakers for external services
    - Comprehensive error handling
    """
    
    def __init__(
        self,
        client_id: Optional[str] = None,  # NEW: Client ID for multi-tenancy
        output_dir: str = "output",
        enable_cache: bool = True,
        enable_llm_verification: bool = False,
        enable_ml_clustering: bool = True,
        enable_ensemble_detection: bool = True,
        enable_validation: bool = True,
        enable_audit_logging: bool = True,
        strict_mode: bool = True,
        fresh_fingerprints_only: bool = False,  # For API: generate fresh fingerprints, skip DB cache
        skip_cli_outputs: bool = False,  # For API: skip CLI-specific output generation (correction report CSV, modified final_output)
    ):
        """
        Initialize enhanced pipeline.
        
        Args:
            client_id: Client ID for multi-tenancy (optional)
            output_dir: Output directory path
            enable_cache: Enable detection caching
            enable_llm_verification: Enable LLM verification (optional)
            enable_ml_clustering: Enable ML-based clustering
            enable_ensemble_detection: Enable ensemble detection
            enable_validation: Enable input validation
            enable_audit_logging: Enable audit logging
            strict_mode: Strict validation mode (reject invalid inputs)
            fresh_fingerprints_only: Generate fresh fingerprints, skip DB cache
        """
        # Multi-tenant support
        self.client_id = client_id
        
        # API mode flag (skip CLI-specific outputs)
        self._skip_cli_outputs = skip_cli_outputs
        
        # Client-specific cache service
        if client_id:
            from ..services.cache_service import CacheService
            self._cache_service = CacheService(client_id=client_id)
        else:
            self._cache_service = None
        
        # Core components
        self._detector = WorkflowDetector(enable_cache=enable_cache)
        self._output_writer = OutputWriter(output_dir)
        self._enable_llm = enable_llm_verification
        self._enable_ml_clustering = enable_ml_clustering
        self._enable_ensemble = enable_ensemble_detection
        self._fresh_fingerprints_only = fresh_fingerprints_only  # API mode: fresh fingerprints per file
        
        # Security components
        self._validator = InputValidator(strict_mode=strict_mode) if enable_validation else None
        self._sanitizer = DataSanitizer() if enable_validation else None
        self._audit_logger = AuditLogger() if enable_audit_logging else None
        
        # Resilience components
        self._degradation_handler = GracefulDegradationHandler()
        self._confidence_scorer = ConfidenceScorer()
        self._llm_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout_seconds=60,
            name="llm_service"
        )
        
        # Ensemble detector (if enabled)
        if enable_ensemble_detection:
            self._ensemble_detector = EnsembleDetector(
                enable_statistical=True,
                enable_context=False  # Can be enabled if context available
            )
        else:
            self._ensemble_detector = None
        
        # Initialize unified database manager (skip if fresh_fingerprints_only to avoid DB issues)
        try:
            self._db = get_db_manager() if not fresh_fingerprints_only else None
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}. Continuing without DB.")
            self._db = None
        
        # Initialize LLM reshuffler (lazy - only if enabled)
        self._reshuffler = None
        if enable_llm_verification:
            try:
                self._reshuffler = LLMReshuffler()
                logger.info("LLM Reshuffler initialized")
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
        
        logger.info(
            f"PipelineServiceV2 initialized "
            f"(LLM: {self._enable_llm}, ML: {self._enable_ml_clustering}, "
            f"Ensemble: {enable_ensemble_detection}, Validation: {enable_validation})"
        )
    
    def run(
        self,
        input_path: str,
        has_header: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the complete enhanced pipeline.
        
        Args:
            input_path: Path to input CSV file
            has_header: Whether file has header row
            
        Returns:
            Pipeline results dictionary
        """
        logger.info(f"Starting enhanced pipeline: {input_path}")
        
        # Validate and load data
        df = self._load_and_validate_data(input_path, has_header)
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Process each column with enhanced error handling
        results = {}
        
        for column in df.columns:
            logger.info(f"Processing column: {column}")
            
            try:
                column_result = self._process_column_enhanced(
                    df[column].tolist(),
                    column,
                    list(range(len(df)))
                )
                results[column] = column_result
            except DataQualityError as e:
                logger.error(f"Data quality error processing column {column}: {e}")
                results[column] = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "details": e.details
                }
            except Exception as e:
                logger.exception(f"Unexpected error processing column {column}: {e}")
                results[column] = {"error": str(e), "error_type": "UnexpectedError"}
        
        # Store results for API access
        self._last_results = results
        
        # Generate outputs (skip CLI-specific outputs if in API mode)
        if not self._skip_cli_outputs:
            self._generate_outputs(df, results)
        
        # Write consolidated good/bad files (always needed for both CLI and API)
        self._output_writer.write_consolidated_files()
        
        # Export fingerprints to JSON (only if DB is available)
        fingerprints_path = self._output_dir / "fingerprints.json"
        try:
            if self._db:
                self._db.export_fingerprints_json(str(fingerprints_path))
                logger.info(f"Exported fingerprints to {fingerprints_path}")
            else:
                logger.debug("Skipping fingerprint export (DB not available)")
        except Exception as e:
            logger.warning(f"Failed to export fingerprints: {e}")
        
        # Generate summary (skip CLI-specific reports if in API mode)
        if not self._skip_cli_outputs:
            summary = self._generate_summary(results)
            self._output_writer.write_summary_report(summary)
        else:
            # Still generate summary for return value, just don't write report
            summary = self._generate_summary(results)
        
        logger.info("Enhanced pipeline completed")
        return summary
    
    def _load_and_validate_data(
        self,
        path: str,
        has_header: bool
    ) -> pd.DataFrame:
        """
        Load and validate data with security checks.
        
        Args:
            path: Path to CSV file
            has_header: Whether file has header row
            
        Returns:
            Validated and sanitized DataFrame
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate file
        if self._validator:
            file_validation = self._validator.validate_file(path)
            if not file_validation.is_valid:
                raise ValidationError(
                    f"File validation failed: {file_validation.error_message}",
                    field_name="input_file"
                )
            if file_validation.warnings:
                for warning in file_validation.warnings:
                    logger.warning(f"File validation warning: {warning}")
        
        # Load data
        try:
            if has_header:
                df = pd.read_csv(path)
            else:
                df = pd.read_csv(path, header=None)
                df.columns = [f"col_{i}" for i in range(len(df.columns))]
        except Exception as e:
            raise ValidationError(
                f"Failed to load CSV file: {e}",
                field_name="input_file"
            )
        
        # Validate dataset characteristics
        if self._validator:
            empty_columns = [col for col in df.columns if df[col].isna().all()]
            duplicate_columns = df.columns[df.columns.duplicated()].tolist()
            
            dataset_validation = self._validator.validate_dataset(
                row_count=len(df),
                column_count=len(df.columns),
                empty_columns=empty_columns,
                duplicate_columns=duplicate_columns
            )
            
            if not dataset_validation.is_valid:
                raise ValidationError(
                    f"Dataset validation failed: {dataset_validation.error_message}",
                    field_name="dataset"
                )
            
            if dataset_validation.warnings:
                for warning in dataset_validation.warnings:
                    logger.warning(f"Dataset validation warning: {warning}")
        
        # Sanitize column names
        if self._sanitizer:
            column_mapping = self._sanitizer.sanitize_dataframe_columns(df.columns.tolist())
            if column_mapping:
                df.rename(columns=column_mapping, inplace=True)
                logger.debug(f"Sanitized column names: {column_mapping}")
        
        # Validate and sanitize column names
        if self._validator and self._sanitizer:
            for col in df.columns:
                col_validation = self._validator.validate_column_name(col)
                if not col_validation.is_valid:
                    # Sanitize invalid column name
                    sanitized = self._sanitizer.sanitize_column_name(col)
                    if sanitized != col:
                        df.rename(columns={col: sanitized}, inplace=True)
                        logger.warning(f"Sanitized column name: {col} -> {sanitized}")
        
        return df
    
    def _process_column_enhanced(
        self,
        data: List[Any],
        column_name: str,
        indices: List[int]
    ) -> Dict[str, Any]:
        """
        Process a single column with enhanced error handling and features.
        
        Args:
            data: Column data
            column_name: Column name
            indices: Row indices
            
        Returns:
            Processing result dictionary
        """
        # Validate column name
        if self._validator:
            col_validation = self._validator.validate_column_name(column_name)
            if not col_validation.is_valid:
                raise ValidationError(
                    f"Invalid column name: {col_validation.error_message}",
                    field_name=column_name
                )
        
        # Sanitize data values
        if self._sanitizer:
            data = self._sanitizer.sanitize_batch(data)
        
        # Detect column type with ensemble (if enabled)
        try:
            if self._ensemble_detector:
                detection = self._degradation_handler.safe_detect(
                    self._ensemble_detector,
                    column_name,
                    data[:100]  # Sample for detection
                )
            else:
                detection = self._degradation_handler.safe_detect(
                    self._detector,
                    column_name,
                    data[:100]
                )
            
            # Calculate calibrated confidence
            calibrated_confidence = self._confidence_scorer.calculate_detection_confidence(
                detection,
                data[:100]
            )
            detection.confidence = calibrated_confidence
            
            # Log detection
            if self._audit_logger:
                self._audit_logger.log_detection(
                    column_name=column_name,
                    workflow=detection.workflow,
                    subtype=detection.subtype,
                    confidence=calibrated_confidence,
                    sample_size=min(100, len(data)),
                    source=detection.source.value,
                    metadata={"calibrated": True}
                )
            
        except Exception as e:
            logger.error(f"Detection failed for {column_name}: {e}")
            raise DetectionError(
                f"Detection failed: {e}",
                column_name=column_name,
                details={"error": str(e)}
            )
        
        logger.debug(
            f"Detected: {detection.workflow}/{detection.subtype} "
            f"(confidence: {detection.confidence:.2f})"
        )
        
        # Get workflow
        workflow = self._workflows.get(detection.workflow)
        if not workflow:
            logger.warning(f"No workflow for type: {detection.workflow}")
            workflow = self._workflows["text"]  # Fallback
        
        # Cluster data with graceful degradation
        try:
            if self._enable_ml_clustering and hasattr(workflow, 'cluster_v2'):
                # Use cluster_v2 directly with graceful degradation wrapper
                def try_ml():
                    return workflow.cluster_v2(
                        data=data,
                        indices=indices,
                        column_name=column_name,
                        subtype=detection.subtype,
                        use_ml=True,
                    )
                
                def try_non_ml():
                    return workflow.cluster(
                        data=data,
                        indices=indices,
                        column_name=column_name,
                        subtype=detection.subtype,
                    )
                
                cluster_result = self._degradation_handler.process_with_fallback(
                    primary_method=try_ml,
                    fallback_methods=[try_non_ml],
                    operation_name=f"clustering for {column_name}"
                )
            else:
                cluster_result = workflow.cluster(
                    data=data,
                    indices=indices,
                    column_name=column_name,
                    subtype=detection.subtype,
                )
            
            # Calculate calibrated clustering confidence
            calibrated_clustering_confidence = self._confidence_scorer.calculate_clustering_confidence(
                good_count=len(cluster_result.good_data),
                bad_count=len(cluster_result.bad_data),
                sample_size=len(data)
            )
            cluster_result.confidence = calibrated_clustering_confidence
            
            # Log clustering
            if self._audit_logger:
                # Get method from metadata or fingerprint
                method = cluster_result.metadata.get("method") or (
                    cluster_result.fingerprint.get("method") if cluster_result.fingerprint else None
                ) or "unknown"
                
                self._audit_logger.log_clustering(
                    column_name=column_name,
                    workflow=detection.workflow,
                    subtype=detection.subtype,
                    method=method,
                    good_count=len(cluster_result.good_data),
                    bad_count=len(cluster_result.bad_data),
                    confidence=calibrated_clustering_confidence,
                    metadata={"calibrated": True}
                )
            
        except Exception as e:
            logger.error(f"Clustering failed for {column_name}: {e}")
            raise ClusteringError(
                f"Clustering failed: {e}",
                workflow=detection.workflow,
                subtype=detection.subtype,
                details={"error": str(e)}
            )
        
        # LLM Reshuffling (if enabled) with circuit breaker
        llm_stats = None
        if self._enable_llm and self._reshuffler and cluster_result.fingerprint:
            try:
                # Use circuit breaker for LLM calls
                def llm_reshuffle():
                    return self._reshuffler.reshuffle(
                        good_data=cluster_result.good_data,
                        bad_data=cluster_result.bad_data,
                        good_indices=cluster_result.good_indices,
                        bad_indices=cluster_result.bad_indices,
                        workflow=detection.workflow,
                        subtype=detection.subtype,
                        fingerprint=cluster_result.fingerprint,
                        column_name=column_name,
                    )
                
                reshuffle_result = self._llm_circuit_breaker.call(llm_reshuffle)
                
                # Apply promotions
                if reshuffle_result.promoted_to_good:
                    promoted_indices = {idx for _, idx in reshuffle_result.promoted_to_good}
                    
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
                
                # Log LLM call
                if self._audit_logger:
                    self._audit_logger.log_llm_call(
                        purpose="reshuffle",
                        column_name=column_name,
                        tokens_used=reshuffle_result.tokens_used,
                        cost_usd=0.0,  # Calculate if needed
                        from_cache=reshuffle_result.from_cache
                    )
                
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
        
        # Extract method from metadata or fingerprint (needed for corrections)
        method = cluster_result.metadata.get("method") or (
            cluster_result.fingerprint.get("method") if cluster_result.fingerprint else None
        ) or "unknown"
        
        # Apply corrections with row index tracking
        correction_results = []
        correction_map = {}  # Map row_index -> corrected_value for applying to dataframe
        
        if cluster_result.bad_data and cluster_result.fingerprint:
            corrector = workflow.get_corrector(detection.subtype)
            
            if corrector:
                # Match bad_data with bad_indices to track row positions
                for value, bad_idx in zip(cluster_result.bad_data, cluster_result.bad_indices):
                    try:
                        result = corrector.correct(
                            value=value,
                            fingerprint=cluster_result.fingerprint,
                            subtype=detection.subtype,
                            column_name=column_name,
                        )
                        
                        # Store correction with row index
                        correction_info = {
                            "column_name": column_name,
                            "row_index": bad_idx,
                            "original_value": result.original_value,
                            "corrected_value": result.corrected_value,
                            "status": result.status.value,
                            "confidence": result.confidence,
                            "changes_made": result.changes_made,
                            "workflow": detection.workflow,
                            "subtype": detection.subtype,
                            "method": method,
                        }
                        correction_results.append(correction_info)
                        
                        # Store mapping for applying corrections to dataframe
                        if result.status.value == "corrected":
                            correction_map[bad_idx] = result.corrected_value
                        
                        # Log correction
                        if self._audit_logger:
                            self._audit_logger.log_correction(
                                column_name=column_name,
                                original_value=result.original_value,
                                corrected_value=result.corrected_value,
                                status=result.status.value,
                                confidence=result.confidence,
                                changes_made=result.changes_made
                            )
                    except Exception as e:
                        logger.warning(f"Correction failed for value {value} at index {bad_idx}: {e}")
                        # Track failed corrections as rejected
                        correction_results.append({
                            "column_name": column_name,
                            "row_index": bad_idx,
                            "original_value": value,
                            "corrected_value": value,
                            "status": "rejected",
                            "confidence": 0.0,
                            "changes_made": [],
                            "workflow": detection.workflow,
                            "subtype": detection.subtype,
                            "method": method,
                            "error": str(e)
                        })
        
        result = {
            "column_name": column_name,
            "workflow": detection.workflow,
            "subtype": detection.subtype,
            "detection_confidence": detection.confidence,
            "clustering_confidence": cluster_result.confidence,
            "detection_source": detection.source.value,
            "good_count": len(cluster_result.good_data),
            "bad_count": len(cluster_result.bad_data),
            "good_indices": cluster_result.good_indices,
            "bad_indices": cluster_result.bad_indices,
            "method": method,  # Track method
            "fingerprint": cluster_result.fingerprint,
            "corrections": correction_results,
            "correction_map": correction_map,  # For applying corrections to dataframe
        }
        
        # Save fingerprint to database (only if not in API mode with fresh fingerprints)
        # For API calls, fingerprints are generated fresh per file, so we skip DB save
        # to ensure each file gets its own fingerprint
        if cluster_result.fingerprint and self._db and not getattr(self, '_fresh_fingerprints_only', False):
            try:
                clusterer = cluster_result.fingerprint.get("method", "unknown")
                
                correction_hints = cluster_result.fingerprint.get("correction_hints", {})
                if not correction_hints:
                    correction_hints = {
                        "workflow": detection.workflow,
                        "subtype": detection.subtype,
                    }
                
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
        """Generate final output files with corrections applied"""
        # Create a copy for applying corrections
        corrected_df = df.copy()
        
        # Track which rows have non-correctable data (rejected corrections)
        rows_with_rejected = set()
        
        # Apply corrections to dataframe
        for column, result in results.items():
            if "error" in result or "correction_map" not in result:
                continue
            
            correction_map = result.get("correction_map", {})
            corrections = result.get("corrections", [])
            
            # Apply corrected values to dataframe
            for row_idx, corrected_value in correction_map.items():
                if row_idx < len(corrected_df):
                    corrected_df.loc[row_idx, column] = corrected_value
            
            # Track rows with rejected corrections (non-correctable)
            for correction in corrections:
                if correction.get("status") == "rejected":
                    row_idx = correction.get("row_index")
                    if row_idx is not None:
                        rows_with_rejected.add(row_idx)
        
        # Generate correction report CSV
        self._output_writer.write_correction_report_csv(results)
        
        # Create final output: good data + corrected data, excluding rows with rejected corrections
        # A row is included if:
        # 1. All columns are good (no bad data), OR
        # 2. All bad data in the row was successfully corrected (no rejected corrections)
        
        # Determine which rows to keep
        # Simple rule: Keep all rows that don't have any rejected corrections
        # (i.e., all bad data in the row was either good from start or successfully corrected)
        rows_to_keep = [idx for idx in range(len(corrected_df)) if idx not in rows_with_rejected]
        
        # Create final output dataframe with only kept rows
        final_df = corrected_df.iloc[rows_to_keep].copy()
        
        # Add status columns for tracking
        for column, result in results.items():
            if "error" not in result:
                status_col = f"{column}_status"
                final_df[status_col] = "good"
                
                bad_indices = result.get("bad_indices", [])
                correction_map = result.get("correction_map", {})
                
                # Mark corrected and bad status for rows that had bad data
                for idx in rows_to_keep:
                    if idx in bad_indices:
                        if idx in correction_map:
                            # Find the row in final_df by matching the original index
                            mask = final_df.index == idx
                            if mask.any():
                                final_df.loc[mask, status_col] = "corrected"
                        else:
                            # Bad data that wasn't corrected (shouldn't happen if logic is correct)
                            mask = final_df.index == idx
                            if mask.any():
                                final_df.loc[mask, status_col] = "bad"
        
        # Write final output
        self._output_writer.write_final_output(final_df)
        
        # Write JSON correction report (for backward compatibility)
        self._output_writer.write_correction_report(results)
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pipeline summary"""
        total_columns = len(results)
        total_good = 0
        total_bad = 0
        total_corrected = 0
        error_columns = []
        
        workflow_counts = {}
        confidence_scores = []
        
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
            
            # Collect confidence scores
            detection_conf = result.get("detection_confidence", 0)
            clustering_conf = result.get("clustering_confidence", 0)
            confidence_scores.append({
                "column": column,
                "detection": detection_conf,
                "clustering": clustering_conf
            })
        
        avg_detection_confidence = (
            sum(c["detection"] for c in confidence_scores) / len(confidence_scores)
            if confidence_scores else 0
        )
        avg_clustering_confidence = (
            sum(c["clustering"] for c in confidence_scores) / len(confidence_scores)
            if confidence_scores else 0
        )
        
        return {
            "total_columns": total_columns,
            "total_good_values": total_good,
            "total_bad_values": total_bad,
            "total_corrected": total_corrected,
            "workflow_distribution": workflow_counts,
            "error_columns": error_columns,
            "success_rate": total_good / (total_good + total_bad) if (total_good + total_bad) > 0 else 0,
            "avg_detection_confidence": avg_detection_confidence,
            "avg_clustering_confidence": avg_clustering_confidence,
        }
