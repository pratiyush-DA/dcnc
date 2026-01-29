# Comprehensive Improvements & API Implementation Plan
## Based on Test Results Analysis

**Date**: 2026-01-27  
**Status**: Planning Phase

---

## 📊 Phase 1: Classification Engine Improvements

### Critical Issues (P0) - Immediate Fixes

#### 1. Longitude Detection Bug 🔴

**Issue**: `longitude_coord` detected as `latitude` subtype (52% false negative rate)

**Fix Location**: `backend/core/detection/heuristic_matcher.py`

**Implementation**:
```python
# Add to _load_rules() or match() method
if "longitude" in column_name.lower():
    return DetectionResult(
        workflow="numeric",
        subtype="longitude",
        confidence=0.95,
        method="heuristic"
    )
```

**Test**: Verify `longitude_coord` detects as `numeric/longitude` with >90% confidence

---

#### 2. Method Tracking Missing 🟡

**Issue**: All methods show as "unknown" in results

**Fix Locations**: 
- `backend/core/clustering/strategy_selector.py`
- All clusterer files in `backend/core/clustering/`

**Implementation**:
```python
# In each clusterer's cluster() method
return ClusteringResult(
    good_data=good_data,
    bad_data=bad_data,
    good_indices=good_indices,
    bad_indices=bad_indices,
    method="semantic_iqr",  # Set actual method name
    fingerprint=fingerprint,
    confidence=confidence
)
```

**Methods to Track**:
- `validator_email`, `validator_phone`, `validator_url`, etc.
- `categorical_frequency_fuzzy`
- `freetext_lenient`
- `semantic_iqr`
- `isolation_forest_iqr_zscore`
- `format_parsing`
- `pattern_signature`

---

#### 3. Fresh Fingerprint Generation 🟡

**Requirement**: Generate fingerprints fresh for every file (not cached)

**Fix Locations**:
- `backend/services/pipeline_service_v2.py`
- `backend/core/fingerprinting/`

**Implementation**:
```python
# In _process_column_enhanced()
# Disable caching for API calls
fingerprint = workflow.generate_fingerprint(
    data=cluster_result.good_data,
    subtype=detection.subtype,
    column_name=column_name,
    use_cache=False  # Fresh fingerprint
)
```

---

### High Priority (P1) - Short-term Fixes

#### 4. Numeric Subtype Detection 🟡

**Issue**: `phone_numeric`, `zipcode_numeric` detected as text

**Fix**: Improve detection for `*_numeric` columns

**Implementation**:
```python
# In heuristic_matcher.py
if column_name.lower().endswith("_numeric"):
    # Check if values are purely numeric
    numeric_ratio = sum(1 for v in sample if str(v).isdigit()) / len(sample)
    if numeric_ratio > 0.8:
        return DetectionResult(
            workflow="numeric",
            subtype=column_name.replace("_numeric", ""),
            confidence=0.85
        )
```

---

#### 5. Identifier Detection 🟡

**Issue**: `numeric_id` detected as `text/zipcode`

**Fix**: Improve identifier detection logic

**Implementation**:
```python
# In pattern_analyzer.py or workflow_detector.py
if column_name.lower().endswith("_id") or "id" in column_name.lower():
    # Check for identifier patterns
    if has_identifier_pattern(sample):
        return DetectionResult(
            workflow="identifier",
            subtype="pattern_id",
            confidence=0.90
        )
```

---

## 🏗️ Phase 2: API Framework

### API Structure (Created)

```
DCNC/api/
├── app.py                    ✅ Created
├── config.py                 ✅ Created
├── routes/
│   ├── health.py            ✅ Created
│   ├── classification.py    ✅ Created
│   └── correction.py        ✅ Created
├── models/
│   ├── request.py          ✅ Created
│   └── response.py         ✅ Created
├── services/
│   ├── classification_service.py  ✅ Created (skeleton)
│   └── correction_service.py     ✅ Created (skeleton)
└── utils/
    └── file_utils.py       ✅ Created
```

### Next Steps for API Implementation

#### 1. Complete Classification Service

**File**: `DCNC/api/services/classification_service.py`

**Tasks**:
- [ ] Implement `_generate_output_files()`:
  - Combine good data from all columns → `good_data.csv`
  - Combine bad data from all columns → `bad_data.csv`
  - Generate `reject_data.csv` (rows with ANY bad column)
  - Generate `fingerprint.json` (all column fingerprints)
- [ ] Implement `_calculate_statistics()`:
  - Count good/bad/reject rows
  - Calculate total values
  - Column processing stats

#### 2. Implement Reject File Logic

**Rule**: If ANY column in a row has bad data, reject the entire row.

**Implementation**:
```python
def generate_reject_file(
    original_df: pd.DataFrame,
    bad_indices_by_column: Dict[str, List[int]]
) -> pd.DataFrame:
    """
    Generate reject file containing rows where ANY column has bad data.
    
    Args:
        original_df: Original dataframe
        bad_indices_by_column: Dict mapping column_name to list of bad row indices
    
    Returns:
        DataFrame with rejected rows
    """
    # Get all row indices that have at least one bad column
    all_bad_row_indices = set()
    for column, indices in bad_indices_by_column.items():
        all_bad_row_indices.update(indices)
    
    # Return rows with any bad data
    return original_df.loc[list(all_bad_row_indices)].copy()
```

#### 3. Implement File Generation

**Good Data File**:
- Combine all good values column-wise
- Maintain original row structure where possible
- Include all columns with good values

**Bad Data File**:
- Combine all bad values column-wise
- Include column name, row index, original value
- Include detection metadata

**Fingerprint File**:
- JSON structure with all column fingerprints
- Include workflow, subtype, method for each column
- Include fingerprint data (patterns, bounds, etc.)

---

## 🔧 Phase 3: Robust Correction Engine

### Correction Engine Architecture

#### 1. Similarity Calculator

**File**: `backend/core/correction/similarity_calculator.py` (NEW)

**Purpose**: Calculate similarity between bad value and good data fingerprint

**Implementation**:
```python
class SimilarityCalculator:
    """Calculate similarity between bad value and good data."""
    
    def calculate_similarity(
        self,
        bad_value: Any,
        fingerprint: Dict[str, Any],
        workflow: str,
        subtype: str
    ) -> float:
        """
        Calculate similarity score (0.0 to 1.0).
        
        Returns:
            Similarity score. Higher = closer to good data.
        """
        if workflow == "text":
            return self._text_similarity(bad_value, fingerprint, subtype)
        elif workflow == "numeric":
            return self._numeric_similarity(bad_value, fingerprint, subtype)
        elif workflow == "datetime":
            return self._datetime_similarity(bad_value, fingerprint, subtype)
        elif workflow == "identifier":
            return self._identifier_similarity(bad_value, fingerprint, subtype)
        return 0.0
```

#### 2. Correction Router

**File**: `backend/core/correction/correction_router.py` (NEW)

**Purpose**: Route to correct corrector based on workflow-subtype-method

**Implementation**:
```python
CORRECTION_MAP = {
    # Text Workflow
    ("text", "email", "validator_email"): EmailCorrector,
    ("text", "phone", "validator_phone"): PhoneCorrector,
    ("text", "url", "validator_url"): URLCorrector,
    ("text", "name", "freetext_lenient"): TextCorrector,
    ("text", "company", "freetext_lenient"): TextCorrector,
    ("text", "state", "categorical_frequency_fuzzy"): TextCorrector,
    ("text", "country", "categorical_frequency_fuzzy"): TextCorrector,
    
    # Numeric Workflow
    ("numeric", "age", "semantic_iqr"): NumericCorrector,
    ("numeric", "year", "semantic_iqr"): NumericCorrector,
    ("numeric", "salary", "isolation_forest_iqr_zscore"): NumericCorrector,
    ("numeric", "amount", "isolation_forest_iqr_zscore"): NumericCorrector,
    ("numeric", "latitude", "semantic_iqr"): NumericCorrector,
    ("numeric", "longitude", "semantic_iqr"): NumericCorrector,
    
    # DateTime Workflow
    ("datetime", "date", "format_parsing"): DatetimeCorrector,
    ("datetime", "datetime", "format_parsing"): DatetimeCorrector,
    
    # Identifier Workflow
    ("identifier", "pattern_id", "pattern_signature"): IdentifierCorrector,
}

class CorrectionRouter:
    """Route to correct corrector based on workflow-subtype-method."""
    
    def get_corrector(
        self,
        workflow: str,
        subtype: str,
        method: str
    ) -> Optional[ICorrector]:
        """Get corrector for workflow-subtype-method combination."""
        key = (workflow, subtype, method)
        corrector_class = CORRECTION_MAP.get(key)
        if corrector_class:
            return corrector_class()
        return None
```

#### 3. Enhanced Correctors

**Enhancements Needed**:

**Email Corrector**:
- Fix typos: `gmial` → `gmail`, `yahooo` → `yahoo`
- Normalize case: `JOHN@GMAIL.COM` → `john@gmail.com`
- Fix domain extensions: `.con` → `.com`, `.co` → `.com` (context-aware)

**Phone Corrector**:
- Format standardization: `1234567890` → `+1-234-567-8901`
- Remove invalid characters
- Add country code if missing (use fingerprint pattern)

**Numeric Corrector**:
- Clamp to bounds: `150` (age) → `120` (max) or REJECT if too far
- Adjust outliers towards median (if within 2 std dev)
- Format standardization

**DateTime Corrector**:
- Format conversion: `12/25/2023` → `2023-12-25` (use fingerprint format)
- Component validation: `2023-13-45` → REJECT
- Timezone normalization

**Identifier Corrector** (NEW):
- Pattern matching: `EMP-123` → `EMP-00123` (zero-pad using fingerprint)
- Format standardization
- Prefix/suffix correction

#### 4. Correction Validator

**File**: `backend/core/correction/correction_validator.py` (NEW)

**Purpose**: Validate corrections before applying

**Implementation**:
```python
class CorrectionValidator:
    """Validate corrections against fingerprints."""
    
    def validate_correction(
        self,
        original_value: Any,
        corrected_value: Any,
        fingerprint: Dict[str, Any],
        workflow: str,
        subtype: str
    ) -> bool:
        """
        Validate that correction is acceptable.
        
        Returns:
            True if correction is valid, False otherwise
        """
        # Check bounds (for numeric)
        # Check format (for datetime)
        # Check pattern (for identifier)
        # Check similarity to good data
        pass
```

---

## 📋 Implementation Checklist

### Phase 1: Classification Improvements (Week 1)

- [ ] Fix longitude detection bug
- [ ] Implement method tracking in all clusterers
- [ ] Ensure fresh fingerprint generation
- [ ] Improve numeric subtype detection
- [ ] Improve identifier detection
- [ ] Run comprehensive tests
- [ ] Validate improvements

### Phase 2: API Framework (Week 2)

- [ ] Complete classification service
- [ ] Implement reject file generation
- [ ] Implement good/bad file generation
- [ ] Implement fingerprint JSON generation
- [ ] Complete classification API endpoint
- [ ] Add file upload support
- [ ] Add error handling
- [ ] Add API documentation

### Phase 3: Correction Engine (Week 3)

- [ ] Implement similarity calculator
- [ ] Implement correction router
- [ ] Create identifier corrector
- [ ] Enhance existing correctors
- [ ] Implement correction validator
- [ ] Add domain-specific rules
- [ ] Test correction accuracy

### Phase 4: Classification + Correction API (Week 4)

- [ ] Complete correction service
- [ ] Implement classification + correction endpoint
- [ ] Generate correction report
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] API documentation
- [ ] Deployment guide

---

## 🎯 Success Criteria

### Classification API
- ✅ Returns good_data.csv, bad_data.csv, reject_data.csv
- ✅ Returns fingerprint.json for all columns
- ✅ Processes 10K rows in < 30 seconds
- ✅ Handles errors gracefully
- ✅ Fresh fingerprints for every file

### Correction API
- ✅ Corrects data with > 70% similarity
- ✅ Rejects data with < 70% similarity
- ✅ Generates correction report
- ✅ Maintains data integrity
- ✅ Uses workflow-subtype-method mapping

### Correction Engine
- ✅ Maps workflow-subtype-method correctly
- ✅ Uses fresh fingerprints
- ✅ Calculates similarity accurately
- ✅ Applies domain-specific rules
- ✅ Validates corrections

---

**Status**: API framework structure created. Ready to implement services.
