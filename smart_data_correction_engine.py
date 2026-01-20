"""
Smart Data Correction Engine
A production-ready class for data quality validation and correction

Author: AI Assistant
Version: 1.0.0
License: MIT

Features:
- Frequency-based fuzzy matching
- Anomaly detection validation
- Auto-parameter configuration
- Column type detection
- Bad data detection
"""

import pandas as pd
import numpy as np
from rapidfuzz import process, fuzz
from typing import Dict, List, Tuple, Optional, Union
import re
from collections import Counter
import warnings


class SmartDataCorrectionEngine:
    """
    Intelligent data correction engine for data quality improvement.
    
    Main Features:
    1. Validate anomaly detection results
    2. Auto-correct typos using fuzzy matching
    3. Detect bad data using frequency analysis
    4. Auto-configure parameters based on column type
    
    Example Usage:
        >>> engine = SmartDataCorrectionEngine()
        >>> validation = engine.validate_anomaly_detection(good_data, bad_data)
        >>> corrected_df = engine.correct_column(df, 'country', good_data)
        >>> bad_data = engine.detect_anomalies(df['product_name'])
    """
    
    def __init__(self, default_threshold: int = 85, verbose: bool = True):
        """
        Initialize the correction engine.
        
        Args:
            default_threshold: Default similarity threshold (0-100)
            verbose: Print detailed logs during processing
        """
        self.default_threshold = default_threshold
        self.verbose = verbose
        self.column_profiles = {}
        self.correction_history = []
        self.validation_history = []
        
    # ==================== PUBLIC METHODS ====================
    
    def validate_anomaly_detection(self, 
                                   good_data: List[str], 
                                   bad_data: List[str],
                                   threshold: Optional[int] = None) -> Dict:
        """
        Validate anomaly detection results by checking if bad data
        can be corrected to good data using fuzzy matching.
        
        Use this to verify your anomaly detector is working correctly.
        
        Args:
            good_data: List of values considered correct/normal
            bad_data: List of values flagged as anomalies
            threshold: Similarity threshold (uses default if None)
            
        Returns:
            Dictionary containing:
                - total_bad_data: Number of anomalies
                - correctable: List of anomalies that can be corrected
                - uncorrectable: List of anomalies that cannot be corrected
                - false_positive_candidates: Likely false positives
                - validation_accuracy: Percentage of correctable anomalies
                - avg_similarity: Average similarity score
                
        Example:
            >>> validation = engine.validate_anomaly_detection(
            ...     good_data=['USA', 'Canada'],
            ...     bad_data=['US', 'Canda']
            ... )
            >>> print(f"Accuracy: {validation['validation_accuracy']:.1f}%")
        """
        threshold = threshold or self.default_threshold
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"VALIDATING ANOMALY DETECTION")
            print(f"{'='*60}")
            print(f"Good data references: {len(good_data)}")
            print(f"Bad data to validate: {len(bad_data)}")
            print(f"Threshold: {threshold}%")
        
        report = {
            'total_bad_data': len(bad_data),
            'correctable': [],
            'uncorrectable': [],
            'false_positive_candidates': [],
            'validation_accuracy': 0.0,
            'avg_similarity': 0.0
        }
        
        if not bad_data:
            if self.verbose:
                print("⚠️  No bad data to validate")
            return report
        
        similarities = []
        
        for bad_value in bad_data:
            match = process.extractOne(bad_value, good_data, scorer=fuzz.ratio)
            
            if match and match[1] >= threshold:
                # Can be corrected - likely true positive
                report['correctable'].append({
                    'original': bad_value,
                    'suggested_correction': match[0],
                    'similarity': match[1]
                })
                similarities.append(match[1])
            else:
                # Cannot be corrected
                report['uncorrectable'].append(bad_value)
                
                # If similarity is very low, might be false positive
                if not match or match[1] < 60:
                    report['false_positive_candidates'].append({
                        'value': bad_value,
                        'best_match': match[0] if match else None,
                        'similarity': match[1] if match else 0,
                        'reason': 'Very low similarity to any good value'
                    })
                similarities.append(match[1] if match else 0)
        
        report['validation_accuracy'] = (len(report['correctable']) / len(bad_data)) * 100
        report['avg_similarity'] = np.mean(similarities) if similarities else 0
        
        if self.verbose:
            print(f"\n📊 VALIDATION RESULTS:")
            print(f"✓ Correctable: {len(report['correctable'])}/{len(bad_data)}")
            print(f"✗ Uncorrectable: {len(report['uncorrectable'])}")
            print(f"⚠️  Possible false positives: {len(report['false_positive_candidates'])}")
            print(f"📈 Validation accuracy: {report['validation_accuracy']:.1f}%")
            print(f"📊 Average similarity: {report['avg_similarity']:.1f}%")
            
            if report['correctable'] and self.verbose:
                print(f"\n🔧 Sample corrections:")
                for i, corr in enumerate(report['correctable'][:5], 1):
                    print(f"   {i}. '{corr['original']}' → '{corr['suggested_correction']}' ({corr['similarity']:.1f}%)")
        
        self.validation_history.append(report)
        return report
    
    def correct_column(self,
                      df: pd.DataFrame,
                      column_name: str,
                      reference_values: Optional[List[str]] = None,
                      threshold: Optional[int] = None,
                      min_frequency: int = 2,
                      inplace: bool = False) -> pd.DataFrame:
        """
        Correct typos in a DataFrame column using fuzzy matching.
        
        Args:
            df: Input DataFrame
            column_name: Name of column to correct
            reference_values: List of correct values to match against.
                            If None, uses most frequent values from the column
            threshold: Similarity threshold (uses default if None)
            min_frequency: Minimum frequency for auto-detected reference values
            inplace: Modify DataFrame in place (default: False)
            
        Returns:
            DataFrame with new column '{column_name}_corrected'
            
        Example:
            >>> # Using provided reference
            >>> corrected_df = engine.correct_column(
            ...     df, 'country', 
            ...     reference_values=['USA', 'Canada', 'Mexico']
            ... )
            
            >>> # Auto-detect reference from data
            >>> corrected_df = engine.correct_column(df, 'country')
        """
        threshold = threshold or self.default_threshold
        
        if column_name not in df.columns:
            raise ValueError(f"Column '{column_name}' not found in DataFrame")
        
        result_df = df if inplace else df.copy()
        
        # Extract and clean values
        values = df[column_name].astype(str).str.strip()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"CORRECTING COLUMN: '{column_name}'")
            print(f"{'='*60}")
            print(f"Total rows: {len(values)}")
        
        # Build reference set
        if reference_values is None:
            # Auto-detect from frequency
            value_counts = values.value_counts()
            frequent_values = value_counts[value_counts >= min_frequency]
            reference_values = frequent_values.index.tolist()
            
            if self.verbose:
                print(f"📚 Auto-detected reference (appearing ≥{min_frequency} times): {len(reference_values)} values")
        else:
            if self.verbose:
                print(f"📚 Using provided reference: {len(reference_values)} values")
        
        if not reference_values:
            warnings.warn(f"No reference values found for column '{column_name}'. Returning original data.")
            return result_df
        
        # Perform corrections
        corrected_values = []
        corrections = []
        
        for idx, val in enumerate(values):
            # Exact match - no correction needed
            if val in reference_values:
                corrected_values.append(val)
                continue
            
            # Find best fuzzy match
            match = process.extractOne(val, reference_values, scorer=fuzz.ratio)
            
            if match and match[1] >= threshold:
                corrected_values.append(match[0])
                corrections.append({
                    'row_index': idx,
                    'column': column_name,
                    'original': val,
                    'corrected': match[0],
                    'similarity': match[1]
                })
            else:
                # No good match - keep original
                corrected_values.append(val)
        
        # Add corrected column
        result_df[f'{column_name}_corrected'] = corrected_values
        
        if self.verbose:
            print(f"✅ Corrections applied: {len(corrections)}/{len(values)}")
            if corrections:
                print(f"\n🔧 Sample corrections:")
                for i, corr in enumerate(corrections[:5], 1):
                    print(f"   {i}. '{corr['original']}' → '{corr['corrected']}' ({corr['similarity']:.1f}%)")
        
        # Store history
        self.correction_history.extend(corrections)
        
        return result_df
    
    def detect_anomalies(self,
                        series: pd.Series,
                        min_frequency: int = 2,
                        z_score_threshold: float = 2.0) -> Dict:
        """
        Detect anomalies/bad data in a series using frequency analysis.
        
        Use this when you don't have pre-labeled good/bad data.
        
        Args:
            series: Pandas Series to analyze
            min_frequency: Values appearing less than this are suspicious
            z_score_threshold: Standard deviations for length outliers
            
        Returns:
            Dictionary containing:
                - likely_good: List of values likely to be correct
                - likely_bad: List of values likely to be anomalies
                - total_values: Total number of values
                - unique_values: Number of unique values
                - confidence: Confidence score (0-100)
                - detection_methods: Breakdown by detection method
                
        Example:
            >>> result = engine.detect_anomalies(df['product_name'])
            >>> print(f"Found {len(result['likely_bad'])} anomalies")
            >>> print(f"Confidence: {result['confidence']:.1f}%")
        """
        clean_series = series.dropna().astype(str).str.strip()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"DETECTING ANOMALIES")
            print(f"{'='*60}")
            print(f"Total values: {len(clean_series)}")
            print(f"Unique values: {clean_series.nunique()}")
        
        # Strategy 1: Frequency-based detection
        value_counts = clean_series.value_counts()
        rare_values = value_counts[value_counts < min_frequency].index.tolist()
        
        # Strategy 2: Length outliers
        lengths = clean_series.str.len()
        mean_len = lengths.mean()
        std_len = lengths.std()
        
        length_outliers = []
        if std_len > 0:
            z_scores = np.abs((lengths - mean_len) / std_len)
            outlier_mask = z_scores > z_score_threshold
            length_outliers = clean_series[outlier_mask].unique().tolist()
        
        # Strategy 3: Pattern violations
        pattern_violations = self._detect_pattern_violations(clean_series)
        
        # Combine strategies
        bad_candidates = set(rare_values + length_outliers + pattern_violations)
        frequent_values = value_counts[value_counts >= min_frequency].index.tolist()
        
        # Calculate confidence
        confidence = self._calculate_confidence(value_counts, bad_candidates)
        
        result = {
            'likely_good': frequent_values,
            'likely_bad': list(bad_candidates),
            'total_values': len(clean_series),
            'unique_values': clean_series.nunique(),
            'confidence': confidence,
            'detection_methods': {
                'rare_values': len(rare_values),
                'length_outliers': len(length_outliers),
                'pattern_violations': len(pattern_violations)
            }
        }
        
        if self.verbose:
            print(f"\n📊 DETECTION RESULTS:")
            print(f"✓ Likely good: {len(result['likely_good'])} values")
            print(f"⚠️  Likely bad: {len(result['likely_bad'])} values")
            print(f"📈 Confidence: {result['confidence']:.1f}%")
            print(f"\nDetection breakdown:")
            print(f"   - Rare values: {result['detection_methods']['rare_values']}")
            print(f"   - Length outliers: {result['detection_methods']['length_outliers']}")
            print(f"   - Pattern violations: {result['detection_methods']['pattern_violations']}")
        
        return result
    
    def profile_column(self, series: pd.Series) -> Dict:
        """
        Analyze column characteristics and recommend correction strategy.
        
        Args:
            series: Pandas Series to profile
            
        Returns:
            Dictionary with column profile including:
                - data_type: Detected type (categorical, text, email, etc.)
                - should_correct: Whether fuzzy correction is recommended
                - recommended_threshold: Suggested similarity threshold
                - cardinality: Ratio of unique values to total
                - statistics: Basic stats
                
        Example:
            >>> profile = engine.profile_column(df['country'])
            >>> if profile['should_correct']:
            ...     corrected = engine.correct_column(df, 'country')
        """
        profile = {
            'name': series.name,
            'total_rows': len(series),
            'unique_values': series.nunique(),
            'null_count': series.isna().sum(),
            'null_percentage': (series.isna().sum() / len(series)) * 100,
            'cardinality': series.nunique() / len(series),
            'data_type': 'unknown',
            'should_correct': False,
            'recommended_threshold': self.default_threshold,
            'recommended_min_frequency': 2,
            'pattern': None
        }
        
        # Clean series for analysis
        clean_series = series.dropna().astype(str).str.strip()
        
        if len(clean_series) == 0:
            return profile
        
        # Detect data type
        if self._is_email(clean_series):
            profile['data_type'] = 'email'
            profile['should_correct'] = True
            profile['recommended_threshold'] = 90
            profile['pattern'] = 'email'
            
        elif self._is_phone(clean_series):
            profile['data_type'] = 'phone'
            profile['should_correct'] = False
            profile['pattern'] = 'phone'
            
        elif self._is_numeric_string(clean_series):
            profile['data_type'] = 'numeric_string'
            profile['should_correct'] = False
            
        elif self._is_categorical(clean_series):
            profile['data_type'] = 'categorical'
            profile['should_correct'] = True
            profile['recommended_threshold'] = 85
            profile['recommended_min_frequency'] = max(2, int(len(clean_series) * 0.01))
            
        elif self._is_text(clean_series):
            profile['data_type'] = 'text'
            profile['should_correct'] = True
            profile['recommended_threshold'] = 80
            
        # Add statistics
        profile['statistics'] = {
            'avg_length': clean_series.str.len().mean(),
            'std_length': clean_series.str.len().std(),
            'min_length': clean_series.str.len().min(),
            'max_length': clean_series.str.len().max()
        }
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"COLUMN PROFILE: '{series.name}'")
            print(f"{'='*60}")
            print(f"Type: {profile['data_type']}")
            print(f"Total rows: {profile['total_rows']}")
            print(f"Unique values: {profile['unique_values']}")
            print(f"Cardinality: {profile['cardinality']:.2%}")
            print(f"Nulls: {profile['null_count']} ({profile['null_percentage']:.1f}%)")
            print(f"Should correct: {profile['should_correct']}")
            if profile['should_correct']:
                print(f"Recommended threshold: {profile['recommended_threshold']}%")
                print(f"Recommended min frequency: {profile['recommended_min_frequency']}")
        
        self.column_profiles[series.name] = profile
        return profile
    
    def get_correction_suggestions(self,
                                  value: str,
                                  reference_values: List[str],
                                  top_n: int = 3,
                                  threshold: Optional[int] = None) -> List[Dict]:
        """
        Get top N correction suggestions for a single value.
        
        Useful for interactive correction or manual review.
        
        Args:
            value: Value to find corrections for
            reference_values: List of correct values
            top_n: Number of suggestions to return
            threshold: Minimum similarity (returns all if None)
            
        Returns:
            List of suggestion dictionaries with 'value' and 'similarity'
            
        Example:
            >>> suggestions = engine.get_correction_suggestions(
            ...     'Untied States',
            ...     ['United States', 'Canada', 'Mexico']
            ... )
            >>> for s in suggestions:
            ...     print(f"{s['value']}: {s['similarity']:.1f}%")
        """
        threshold = threshold or 0  # Return all if not specified
        
        matches = process.extract(
            value,
            reference_values,
            scorer=fuzz.ratio,
            limit=top_n
        )
        
        suggestions = [
            {'value': match[0], 'similarity': match[1]}
            for match in matches
            if match[1] >= threshold
        ]
        
        return suggestions
    
    def batch_correct_columns(self,
                            df: pd.DataFrame,
                            columns: List[str],
                            auto_detect: bool = True,
                            threshold: Optional[int] = None) -> pd.DataFrame:
        """
        Correct multiple columns in batch.
        
        Args:
            df: Input DataFrame
            columns: List of column names to correct
            auto_detect: Auto-detect which columns should be corrected
            threshold: Similarity threshold for all columns
            
        Returns:
            DataFrame with corrected columns
            
        Example:
            >>> corrected_df = engine.batch_correct_columns(
            ...     df,
            ...     columns=['country', 'state', 'city']
            ... )
        """
        result_df = df.copy()
        
        for col in columns:
            if col not in df.columns:
                warnings.warn(f"Column '{col}' not found, skipping")
                continue
            
            if auto_detect:
                profile = self.profile_column(df[col])
                if not profile['should_correct']:
                    if self.verbose:
                        print(f"\n⚠️  Skipping '{col}' - type '{profile['data_type']}' not suitable for correction")
                    continue
            
            result_df = self.correct_column(
                result_df,
                col,
                threshold=threshold,
                inplace=True
            )
        
        return result_df
    
    def get_correction_report(self) -> pd.DataFrame:
        """
        Get detailed report of all corrections made in this session.
        
        Returns:
            DataFrame with correction history
            
        Example:
            >>> report = engine.get_correction_report()
            >>> report.to_csv('corrections_audit.csv')
        """
        if not self.correction_history:
            if self.verbose:
                print("No corrections have been made yet")
            return pd.DataFrame()
        
        return pd.DataFrame(self.correction_history)
    
    def export_validation_report(self, filepath: str):
        """
        Export validation history to CSV.
        
        Args:
            filepath: Path to save the report
            
        Example:
            >>> engine.export_validation_report('validation_report.csv')
        """
        if not self.validation_history:
            warnings.warn("No validation history to export")
            return
        
        # Flatten validation results
        records = []
        for val in self.validation_history:
            for corr in val.get('correctable', []):
                records.append({
                    'original': corr['original'],
                    'suggested': corr['suggested_correction'],
                    'similarity': corr['similarity'],
                    'status': 'correctable'
                })
        
        df = pd.DataFrame(records)
        df.to_csv(filepath, index=False)
        
        if self.verbose:
            print(f"✓ Validation report exported to: {filepath}")
    
    # ==================== PRIVATE HELPER METHODS ====================
    
    def _is_email(self, series: pd.Series) -> bool:
        """Check if column contains emails"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        sample = series.head(100)
        matches = sample.str.match(email_pattern, na=False).sum()
        return matches / len(sample) > 0.7
    
    def _is_phone(self, series: pd.Series) -> bool:
        """Check if column contains phone numbers"""
        phone_pattern = r'^\+?[\d\s\-\(\)]{10,}$'
        sample = series.head(100)
        matches = sample.str.match(phone_pattern, na=False).sum()
        return matches / len(sample) > 0.7
    
    def _is_categorical(self, series: pd.Series) -> bool:
        """Check if column is categorical"""
        cardinality = series.nunique() / len(series)
        return cardinality < 0.3 and series.nunique() < 1000
    
    def _is_text(self, series: pd.Series) -> bool:
        """Check if column contains text"""
        avg_len = series.str.len().mean()
        has_letters = series.str.contains(r'[a-zA-Z]', na=False).sum()
        return avg_len > 3 and has_letters / len(series) > 0.8
    
    def _is_numeric_string(self, series: pd.Series) -> bool:
        """Check if column contains numeric strings"""
        sample = series.head(100)
        numeric = pd.to_numeric(sample, errors='coerce').notna().sum()
        return numeric / len(sample) > 0.8
    
    def _detect_pattern_violations(self, series: pd.Series) -> List[str]:
        """Detect values that violate common patterns"""
        value_counts = series.value_counts()
        if len(value_counts) < 10:
            return []
        
        # Use top 10 values to establish pattern
        top_values = value_counts.head(10).index.tolist()
        avg_len = np.mean([len(v) for v in top_values])
        std_len = np.std([len(v) for v in top_values])
        
        violations = []
        for value in series.unique():
            # Check if length is unusual
            if abs(len(value) - avg_len) > 3 * std_len:
                violations.append(value)
        
        return violations
    
    def _calculate_confidence(self, value_counts, bad_candidates) -> float:
        """Calculate confidence score for anomaly detection"""
        if len(value_counts) == 0:
            return 0.0
        
        freq_values = list(value_counts.values)
        if len(freq_values) < 2:
            return 50.0
        
        sorted_freqs = sorted(freq_values, reverse=True)
        gap_ratio = sorted_freqs[0] / (sorted_freqs[-1] + 1)
        
        confidence = min(100, gap_ratio * 10)
        return round(confidence, 2)


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    print("Smart Data Correction Engine - Usage Examples\n")
    print("="*70)
    
    # Example 1: Basic correction
    print("\n1. BASIC COLUMN CORRECTION")
    print("-" * 70)
    
    df = pd.DataFrame({
        'country': ['USA', 'USA', 'Canada', 'Canda', 'Mexco', 'Mexico']
    })
    
    engine = SmartDataCorrectionEngine(verbose=True)
    corrected_df = engine.correct_column(df, 'country', min_frequency=2)
    print(corrected_df[['country', 'country_corrected']])
    
    # Example 2: Validation
    print("\n\n2. VALIDATE ANOMALY DETECTION")
    print("-" * 70)
    
    good_data = ['United States', 'Canada', 'Mexico']
    bad_data = ['USA', 'Canda', 'Mexco']
    
    validation = engine.validate_anomaly_detection(good_data, bad_data)
    
    # Example 3: Anomaly detection
    print("\n\n3. AUTO-DETECT ANOMALIES")
    print("-" * 70)
    
    df2 = pd.DataFrame({
        'product': ['iPhone', 'iPhone', 'iPhone', 'iPhoen', 'Samsung', 'Samsung', 'Samsng']
    })
    
    anomalies = engine.detect_anomalies(df2['product'])
    
    print("\n" + "="*70)
    print("For more examples, see the documentation or integration guide")
    print("="*70)