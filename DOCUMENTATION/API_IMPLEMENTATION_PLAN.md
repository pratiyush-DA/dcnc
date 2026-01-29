# API Implementation Plan
## Comprehensive Development Roadmap

**Date**: 2026-01-27  
**Objective**: Build production-ready API framework for Data Quality Pipeline

---

## 📋 Executive Summary

This plan outlines the development of a robust API framework that exposes our data quality pipeline as a service, enabling:
1. **Classification API**: Separate good/bad data and generate fingerprints
2. **Classification + Correction API**: Full pipeline with intelligent corrections
3. **Robust Correction Engine**: Domain-aware corrections using fingerprints

---

## 🎯 Phase 1: Classification Engine Improvements

### Based on Test Results Analysis

#### Critical Issues (P0)

1. **Longitude Detection Bug** 🔴
   - **Issue**: `longitude_coord` detected as `latitude` subtype
   - **Impact**: 52% false negative rate
   - **Fix**: Add longitude keyword detection in `heuristic_matcher.py`
   - **Location**: `backend/core/detection/heuristic_matcher.py`
   - **Implementation**:
     ```python
     # Add to heuristic rules
     if "longitude" in column_name.lower():
         return DetectionResult(workflow="numeric", subtype="longitude", confidence=0.95)
     ```

#### High Priority (P1)

2. **Method Tracking Missing** 🟡
   - **Issue**: All methods show as "unknown"
   - **Impact**: Cannot analyze method performance
   - **Fix**: Ensure `ClusterResult.method` is set in all clusterers
   - **Location**: `backend/core/clustering/` (all clusterer files)
   - **Implementation**:
     ```python
     # In each clusterer's cluster() method
     return ClusteringResult(
         good_data=good_data,
         bad_data=bad_data,
         method="semantic_iqr",  # Set actual method name
         fingerprint=fingerprint
     )
     ```

3. **Fresh Fingerprint Generation** 🟡
   - **Issue**: Fingerprints may be cached/reused
   - **Requirement**: Generate fresh fingerprints for every file
   - **Fix**: Ensure fingerprint generation is per-file, not cached
   - **Location**: `backend/core/fingerprinting/` and `backend/services/pipeline_service*.py`

#### Medium Priority (P2)

4. **Numeric Subtype Detection** 🟡
   - **Issue**: `phone_numeric`, `zipcode_numeric` detected as text
   - **Fix**: Improve detection for `*_numeric` columns
   - **Location**: `backend/core/detection/heuristic_matcher.py`

5. **Identifier Detection** 🟡
   - **Issue**: `numeric_id` detected as `text/zipcode`
   - **Fix**: Improve identifier detection logic
   - **Location**: `backend/core/detection/pattern_analyzer.py`

---

## 🏗️ Phase 2: API Framework Architecture

### API Structure

```
/DCNC/api/
├── __init__.py
├── app.py                    # FastAPI application
├── config.py                 # API configuration
├── dependencies.py           # Shared dependencies
├── models/
│   ├── __init__.py
│   ├── request.py           # Request models
│   ├── response.py          # Response models
│   └── schemas.py           # Pydantic schemas
├── routes/
│   ├── __init__.py
│   ├── classification.py    # Classification endpoints
│   ├── correction.py        # Correction endpoints
│   └── health.py            # Health check endpoints
├── services/
│   ├── __init__.py
│   ├── classification_service.py
│   ├── correction_service.py
│   └── file_handler.py
└── utils/
    ├── __init__.py
    ├── file_utils.py
    └── response_formatter.py
```

### API Endpoints

#### 1. Classification API

**POST** `/api/v1/classify`

**Request**:
```json
{
  "file_path": "path/to/file.csv",
  "file_content": "base64_encoded_content",  // Optional
  "has_header": true,
  "options": {
    "enable_ml_clustering": true,
    "enable_ensemble_detection": true,
    "strict_mode": false
  }
}
```

**Response**:
```json
{
  "status": "success",
  "job_id": "uuid",
  "files": {
    "good_data": "path/to/good_data.csv",
    "bad_data": "path/to/bad_data.csv",
    "reject_data": "path/to/reject_data.csv",
    "fingerprint": "path/to/fingerprint.json"
  },
  "statistics": {
    "total_rows": 1000,
    "good_rows": 950,
    "bad_rows": 30,
    "reject_rows": 20,
    "columns_processed": 36
  },
  "metadata": {
    "processing_time": 12.5,
    "timestamp": "2026-01-27T10:00:00Z"
  }
}
```

#### 2. Classification + Correction API

**POST** `/api/v1/classify-and-correct`

**Request**:
```json
{
  "file_path": "path/to/file.csv",
  "file_content": "base64_encoded_content",
  "has_header": true,
  "correction_options": {
    "confidence_threshold": 0.7,
    "max_corrections_per_column": 100,
    "enable_llm_verification": false
  },
  "options": {
    "enable_ml_clustering": true,
    "enable_ensemble_detection": true
  }
}
```

**Response**:
```json
{
  "status": "success",
  "job_id": "uuid",
  "files": {
    "good_data": "path/to/good_data.csv",
    "corrected_data": "path/to/corrected_data.csv",
    "reject_data": "path/to/reject_data.csv",
    "fingerprint": "path/to/fingerprint.json",
    "correction_report": "path/to/correction_report.json"
  },
  "statistics": {
    "total_rows": 1000,
    "good_rows": 950,
    "corrected_rows": 25,
    "reject_rows": 25,
    "corrections_applied": 45
  },
  "metadata": {
    "processing_time": 18.3,
    "timestamp": "2026-01-27T10:00:00Z"
  }
}
```

#### 3. Health Check

**GET** `/api/v1/health`

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "classification": "operational",
    "correction": "operational",
    "database": "operational"
  }
}
```

---

## 🔧 Phase 3: Robust Correction Engine

### Correction Engine Architecture

```
backend/core/correction/
├── base_corrector.py          # Base class (exists)
├── text_corrector.py          # Text corrections (exists)
├── numeric_corrector.py      # Numeric corrections (exists)
├── datetime_corrector.py     # DateTime corrections (exists)
├── identifier_corrector.py   # Identifier corrections (NEW)
├── correction_router.py      # Route to correct corrector (NEW)
├── similarity_calculator.py  # Calculate closeness to good data (NEW)
└── correction_validator.py   # Validate corrections (NEW)
```

### Correction Strategy

#### 1. Similarity-Based Correction

For each bad value:
1. **Calculate Similarity** to good data fingerprint
2. **If similarity > threshold** (e.g., 0.7):
   - Attempt correction
   - Apply domain-specific rules
   - Validate against fingerprint
3. **If similarity < threshold**:
   - Mark as REJECT (too far from good data)

#### 2. Workflow-Subtype-Method Mapping

```python
CORRECTION_MAP = {
    # Text Workflow
    ("text", "email", "validator_email"): EmailCorrector,
    ("text", "phone", "validator_phone"): PhoneCorrector,
    ("text", "url", "validator_url"): URLCorrector,
    ("text", "name", "freetext_lenient"): TextCorrector,
    ("text", "company", "freetext_lenient"): TextCorrector,
    ("text", "state", "categorical_frequency_fuzzy"): TextCorrector,
    
    # Numeric Workflow
    ("numeric", "age", "semantic_iqr"): NumericCorrector,
    ("numeric", "salary", "isolation_forest_iqr_zscore"): NumericCorrector,
    ("numeric", "latitude", "semantic_iqr"): NumericCorrector,
    ("numeric", "longitude", "semantic_iqr"): NumericCorrector,
    
    # DateTime Workflow
    ("datetime", "date", "format_parsing"): DatetimeCorrector,
    ("datetime", "datetime", "format_parsing"): DatetimeCorrector,
    
    # Identifier Workflow
    ("identifier", "pattern_id", "pattern_signature"): IdentifierCorrector,
}
```

#### 3. Correction Rules by Subtype

**Email**:
- Fix common typos: `gmial` → `gmail`
- Normalize case: `JOHN@GMAIL.COM` → `john@gmail.com`
- Fix domain extensions: `.con` → `.com`

**Phone**:
- Format standardization: `1234567890` → `+1-234-567-8901`
- Remove invalid characters
- Add country code if missing

**Numeric (Age, Year, etc.)**:
- Clamp to bounds: `150` (age) → `120` (max) or REJECT
- Adjust outliers towards median
- Format standardization

**DateTime**:
- Format conversion: `12/25/2023` → `2023-12-25`
- Component validation: `2023-13-45` → REJECT
- Timezone normalization

**Identifier**:
- Pattern matching: `EMP-123` → `EMP-00123` (zero-pad)
- Format standardization
- Prefix/suffix correction

---

## 📊 Implementation Roadmap

### Week 1: Classification Engine Improvements

**Day 1-2**: Fix Critical Issues
- [ ] Fix longitude detection bug
- [ ] Implement method tracking
- [ ] Ensure fresh fingerprint generation

**Day 3-4**: Fix High Priority Issues
- [ ] Improve numeric subtype detection
- [ ] Improve identifier detection
- [ ] Add comprehensive tests

**Day 5**: Testing & Validation
- [ ] Run comprehensive tests
- [ ] Validate improvements
- [ ] Update documentation

### Week 2: API Framework Foundation

**Day 1-2**: API Structure
- [ ] Create API folder structure
- [ ] Set up FastAPI application
- [ ] Implement health check endpoint

**Day 3-4**: Classification Service
- [ ] Implement classification service
- [ ] File handling utilities
- [ ] Response formatting

**Day 5**: Classification API Endpoint
- [ ] Implement POST `/api/v1/classify`
- [ ] Good/bad/reject file generation
- [ ] Fingerprint generation
- [ ] Testing

### Week 3: Correction Engine Enhancement

**Day 1-2**: Similarity Calculator
- [ ] Implement similarity calculation
- [ ] Fingerprint-based distance metrics
- [ ] Threshold-based routing

**Day 3-4**: Correction Router & Validator
- [ ] Implement correction router
- [ ] Workflow-subtype-method mapping
- [ ] Correction validator

**Day 5**: Enhanced Correctors
- [ ] Enhance existing correctors
- [ ] Add identifier corrector
- [ ] Domain-specific rules

### Week 4: Classification + Correction API

**Day 1-2**: Correction Service
- [ ] Implement correction service
- [ ] Integration with classification
- [ ] Correction report generation

**Day 3-4**: Combined API Endpoint
- [ ] Implement POST `/api/v1/classify-and-correct`
- [ ] End-to-end testing
- [ ] Performance optimization

**Day 5**: Documentation & Deployment
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Deployment guide
- [ ] Final testing

---

## 🔑 Key Design Decisions

### 1. Reject File Logic

**Rule**: If ANY column in a row has bad data, reject the entire row.

**Implementation**:
```python
def generate_reject_file(df, bad_indices_by_column):
    """
    Generate reject file containing rows where ANY column has bad data.
    
    Args:
        df: Original dataframe
        bad_indices_by_column: Dict[column_name, List[indices]]
    
    Returns:
        DataFrame with rejected rows
    """
    # Get all row indices that have at least one bad column
    all_bad_row_indices = set()
    for column, indices in bad_indices_by_column.items():
        all_bad_row_indices.update(indices)
    
    # Return rows with any bad data
    return df.loc[list(all_bad_row_indices)]
```

### 2. Fresh Fingerprint Generation

**Requirement**: Generate fingerprints fresh for every file, not cached.

**Implementation**:
- Disable fingerprint caching for API calls
- Generate fingerprints from good_data only
- Store fingerprints per-file, not globally

### 3. Correction Confidence Threshold

**Default**: 0.7 (70% similarity to good data)

**Logic**:
- If correction confidence > threshold: Apply correction
- If correction confidence < threshold: Reject (too far from good data)

### 4. File Output Structure

```
output/
├── {job_id}/
│   ├── good_data.csv          # All good data (column-wise)
│   ├── bad_data.csv           # All bad data (column-wise)
│   ├── reject_data.csv        # Rejected rows (any bad column)
│   ├── fingerprint.json        # All column fingerprints
│   ├── correction_report.json # Correction details (if correction enabled)
│   └── metadata.json          # Processing metadata
```

---

## 🧪 Testing Strategy

### Unit Tests
- Individual corrector tests
- Similarity calculator tests
- File handler tests
- API endpoint tests

### Integration Tests
- End-to-end classification flow
- End-to-end correction flow
- File generation validation
- Fingerprint generation validation

### Performance Tests
- Large file processing (10K+ rows)
- Concurrent API requests
- Memory usage monitoring
- Processing time benchmarks

---

## 📝 API Documentation

### OpenAPI/Swagger
- Auto-generated from FastAPI
- Interactive API explorer
- Request/response examples
- Error code documentation

### User Guide
- API usage examples
- File format requirements
- Response interpretation
- Error handling

---

## 🚀 Deployment Considerations

### Environment Variables
```bash
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
LOG_LEVEL=INFO
OUTPUT_DIR=/data/output
MAX_FILE_SIZE=100MB
ENABLE_LLM=false
```

### Docker Support
- Dockerfile for API service
- docker-compose.yml for full stack
- Health check endpoints

### Monitoring
- Request logging
- Performance metrics
- Error tracking
- Resource usage

---

## ✅ Success Criteria

1. **Classification API**:
   - ✅ Returns good_data.csv, bad_data.csv, reject_data.csv
   - ✅ Returns fingerprint.json for all columns
   - ✅ Processes files in < 30 seconds (10K rows)
   - ✅ Handles errors gracefully

2. **Correction API**:
   - ✅ Corrects data with > 70% confidence
   - ✅ Rejects data with < 70% confidence
   - ✅ Generates correction report
   - ✅ Maintains data integrity

3. **Correction Engine**:
   - ✅ Maps workflow-subtype-method correctly
   - ✅ Uses fresh fingerprints
   - ✅ Calculates similarity accurately
   - ✅ Applies domain-specific rules

---

**Next Steps**: Start implementing Phase 1 improvements, then build API framework.
