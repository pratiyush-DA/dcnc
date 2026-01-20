"""
Output Writer (Enhanced)
Generates output files (good/bad CSVs, multiple reports)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class OutputWriter:
    """
    Handles output file generation.
    
    Outputs:
    - good_data.csv - Consolidated valid data (wide format)
    - bad_data.csv - Consolidated invalid data (wide format)
    - final_output.csv - All data with status column
    
    Reports:
    - correction_report.json - Detailed per-column report
    - good_report.json - Summary of all good data
    - rejection_report.json - All rejected/uncorrectable data
    - corrections_only.json - Only successful corrections
    - summary.json - Overall pipeline summary
    """
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self._ensure_dirs()
        
        # Buffers for consolidated output
        # Format: { column_name: (data_list, index_list) }
        self._good_buffer: Dict[str, tuple] = {}
        self._bad_buffer: Dict[str, tuple] = {}
    
    def _ensure_dirs(self):
        """Create output directories"""
        (self.output_dir / "good_n_bad").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "final").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "report").mkdir(parents=True, exist_ok=True)
    
    def write_good_bad(
        self,
        column_name: str,
        good_data: List[Any],
        bad_data: List[Any],
        good_indices: Optional[List[int]] = None,
        bad_indices: Optional[List[int]] = None
    ):
        """
        Buffer good and bad data for consolidated writing.
        Does NOT write to disk immediately.
        """
        # Buffer good data
        if good_data:
            indices = good_indices if good_indices else list(range(len(good_data)))
            self._good_buffer[column_name] = (good_data, indices)
        
        # Buffer bad data
        if bad_data:
            indices = bad_indices if bad_indices else list(range(len(bad_data)))
            self._bad_buffer[column_name] = (bad_data, indices)
            
        logger.debug(f"Buffered data for column: {column_name}")

    def write_consolidated_files(self):
        """
        Write buffered data to consolidated wide-format CSV files.
        One file for Good data, one for Bad data.
        """
        base_dir = self.output_dir / "good_n_bad"
        
        # Helper to write buffer to CSV
        def write_buffer(buffer: Dict[str, tuple], filename: str, label: str):
            if not buffer:
                logger.info(f"No {label} data to write.")
                return

            logger.info(f"Consolidating {label} data for {len(buffer)} columns...")
            frames = []
            
            # Sort keys for consistent column ordering
            for col_name in sorted(buffer.keys()):
                data, indices = buffer[col_name]
                
                # Create a mini-dataframe for this column
                # We reset index to ensure concatenation happens side-by-side, ignoring row alignment logic
                # (Since row 1 of Col A serves a different record than row 1 of Col B in this 'bag of values' view)
                col_df = pd.DataFrame({
                    f"{col_name}_val": data,
                    f"{col_name}_idx": indices
                })
                frames.append(col_df)
            
            if frames:
                # Concatenate along columns (axis=1)
                final_df = pd.concat(frames, axis=1)
                
                output_path = base_dir / filename
                final_df.to_csv(output_path, index=False)
                logger.info(f"Wrote consolidated {label} data to {output_path} ({len(final_df)} rows max)")

        # Write Good Data
        write_buffer(self._good_buffer, "good_data.csv", "Good")
        
        # Write Bad Data
        write_buffer(self._bad_buffer, "bad_data.csv", "Bad")
        
        # Clear buffers after writing to free memory
        self._good_buffer.clear()
        self._bad_buffer.clear()
    
    def write_final_output(
        self,
        df: pd.DataFrame,
        filename: str = "final_output.csv"
    ):
        """Write final output DataFrame."""
        path = self.output_dir / "final" / filename
        df.to_csv(path, index=False)
        logger.info(f"Wrote final output to {path}")
    
    def write_correction_report(
        self,
        results: Dict[str, Any],
        filename: str = "correction_report.json"
    ):
        """Write detailed correction report."""
        path = self.output_dir / "report" / filename
        
        # Add metadata
        report = {
            "generated_at": datetime.now().isoformat(),
            "version": "2.0.0",
            **results
        }
        
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Wrote correction report to {path}")
        
        # Generate additional reports
        self._write_good_report(results)
        self._write_rejection_report(results)
        self._write_corrections_only_report(results)
    
    def _write_good_report(self, results: Dict[str, Any]):
        """Write report of all good data by column."""
        path = self.output_dir / "report" / "good_report.json"
        
        good_report = {
            "generated_at": datetime.now().isoformat(),
            "description": "Summary of all valid/good data by column",
            "columns": {}
        }
        
        total_good = 0
        
        for column, result in results.items():
            if not isinstance(result, dict) or "good_count" not in result:
                continue
            
            good_count = result.get("good_count", 0)
            total_good += good_count
            
            good_report["columns"][column] = {
                "workflow": result.get("workflow"),
                "subtype": result.get("subtype"),
                "good_count": good_count,
                "sample_values": result.get("fingerprint", {}).get("common_values", [])[:5] if result.get("fingerprint") else [],
                "confidence": result.get("detection_confidence", 0),
            }
        
        good_report["total_good_values"] = total_good
        good_report["columns_count"] = len(good_report["columns"])
        
        with open(path, "w") as f:
            json.dump(good_report, f, indent=2, default=str)
        
        logger.info(f"Wrote good report to {path}")
    
    def _write_rejection_report(self, results: Dict[str, Any]):
        """Write report of all rejected (uncorrectable) data."""
        path = self.output_dir / "report" / "rejection_report.json"
        
        rejection_report = {
            "generated_at": datetime.now().isoformat(),
            "description": "All rejected/uncorrectable bad data by column",
            "columns": {}
        }
        
        total_rejected = 0
        total_bad = 0
        
        for column, result in results.items():
            if not isinstance(result, dict) or "corrections" not in result:
                continue
            
            bad_count = result.get("bad_count", 0)
            total_bad += bad_count
            
            corrections = result.get("corrections", [])
            rejected = [c for c in corrections if c.get("status") in ("rejected", "unchanged")]
            
            if rejected or bad_count > 0:
                rejection_report["columns"][column] = {
                    "workflow": result.get("workflow"),
                    "subtype": result.get("subtype"),
                    "bad_count": bad_count,
                    "rejected_count": len([c for c in corrections if c.get("status") == "rejected"]),
                    "unchanged_count": len([c for c in corrections if c.get("status") == "unchanged"]),
                    "rejections": [
                        {
                            "value": r.get("original"),
                            "status": r.get("status"),
                            "reason": r.get("changes", ["uncorrectable"])[0] if r.get("changes") else "uncorrectable"
                        }
                        for r in rejected
                    ]
                }
                total_rejected += len(rejected)
        
        rejection_report["total_bad_values"] = total_bad
        rejection_report["total_rejected"] = total_rejected
        rejection_report["columns_with_issues"] = len(rejection_report["columns"])
        
        with open(path, "w") as f:
            json.dump(rejection_report, f, indent=2, default=str)
        
        logger.info(f"Wrote rejection report to {path}")
    
    def _write_corrections_only_report(self, results: Dict[str, Any]):
        """Write report of only successful corrections."""
        path = self.output_dir / "report" / "corrections_only.json"
        
        corrections_report = {
            "generated_at": datetime.now().isoformat(),
            "description": "All successful corrections made by the pipeline",
            "corrections": []
        }
        
        for column, result in results.items():
            if not isinstance(result, dict) or "corrections" not in result:
                continue
            
            corrections = result.get("corrections", [])
            
            for c in corrections:
                if c.get("status") == "corrected":
                    corrections_report["corrections"].append({
                        "column": column,
                        "workflow": result.get("workflow"),
                        "subtype": result.get("subtype"),
                        "original": c.get("original"),
                        "corrected": c.get("corrected"),
                        "changes": c.get("changes", []),
                    })
        
        corrections_report["total_corrections"] = len(corrections_report["corrections"])
        
        with open(path, "w") as f:
            json.dump(corrections_report, f, indent=2, default=str)
        
        logger.info(f"Wrote corrections only report to {path}")
    
    def write_summary_report(self, summary: Dict[str, Any]):
        """Write summary report"""
        path = self.output_dir / "report" / "summary.json"
        
        with open(path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Wrote summary to {path}")
    
    def _safe_filename(self, name: str) -> str:
        """Create safe filename from column name"""
        safe = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        safe = "".join(c for c in safe if c.isalnum() or c in "_-")
        return safe[:50]
