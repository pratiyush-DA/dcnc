# Test Files Purpose & Usage Guide

**Date**: 2026-01-28  
**Purpose**: Explain what test files are for and how they're used

---

## What Are Test Files?

Test files are scripts that **verify your software works correctly** by:
1. Running your code with sample data
2. Checking if results match expected outcomes
3. Finding bugs before they reach production
4. Ensuring changes don't break existing functionality

---

## Types of Test Files in This Project

### 1. **Unit Tests** (`tests/` directory)

**Purpose**: Test individual components in isolation

**Files**:
- `tests/test_ensemble_detector.py` - Tests ensemble detection logic
- `tests/test_performance.py` - Performance benchmarks
- `tests/test_resilience.py` - Tests error handling, circuit breakers
- `tests/test_security.py` - Tests security features (validation, sanitization)

**Example Use Case**:
```python
# test_ensemble_detector.py tests:
# - Does ensemble detector correctly identify age data?
# - Does it return correct confidence scores?
# - Does it handle edge cases?
```

**When to Run**: Before deploying changes, during development

**How to Run**:
```bash
pytest tests/test_ensemble_detector.py
pytest tests/  # Run all tests
```

**Benefits**:
- ✅ Catch bugs early
- ✅ Ensure code quality
- ✅ Document expected behavior
- ✅ Prevent regressions

---

### 2. **Integration Tests** (`testing_data/` directory)

**Purpose**: Test the full pipeline with real data files

#### A. **API Tests** (Test API endpoints)

**Files**:
- `testing_data/test_api_classification.py` - Tests classification API
- `testing_data/test_api_correction.py` - Tests correction API

**What They Do**:
```python
# test_api_classification.py:
# 1. Loads test CSV file
# 2. Calls ClassificationService.classify()
# 3. Verifies results are correct
# 4. Checks response format
```

**Example Use Case**:
- Verify API returns correct workflow/subtype for each column
- Ensure API handles errors gracefully
- Test multi-tenancy (client_id isolation)

**When to Run**: After API changes, before deployment

**How to Run**:
```bash
python testing_data/test_api_classification.py
python testing_data/test_api_correction.py
```

---

#### B. **Pipeline Tests** (Test CLI pipeline)

**Files**:
- `testing_data/run_test_simple.py` - Tests old PipelineService
- `testing_data/run_test_no_db.py` - Tests without database
- `testing_data/test_phase1_simple.py` - Tests Phase 1 features
- `testing_data/test_phase1_fixes.py` - Tests Phase 1 bug fixes
- `testing_data/test_phase1_comprehensive.py` - Comprehensive Phase 1 tests

**What They Do**:
```python
# run_test_simple.py:
# 1. Loads comprehensive_workflow_test_data.csv
# 2. Runs PipelineService.run()
# 3. Analyzes output files
# 4. Generates test report
```

**Example Use Case**:
- Verify pipeline processes all column types correctly
- Check that corrections are applied properly
- Validate output file formats

**When to Run**: After pipeline changes, before production

**How to Run**:
```bash
python testing_data/run_test_simple.py
python testing_data/run_test_no_db.py
```

**Note**: ⚠️ Some of these use **old `PipelineService`** (not `PipelineServiceV2`)

---

### 3. **Test Data Files** (`testing_data/` directory)

**Purpose**: Sample CSV files used by test scripts

**Files**:
- `comprehensive_workflow_test_data.csv` - ✅ **ACTIVE** - Used by tests
- `challenging_realworld_test_data.csv` - ✅ **ACTIVE** - Used by tests
- `test_pipeline.csv` - ⚠️ **REVIEW** - May be outdated
- `with_date.csv` - ⚠️ **REVIEW** - May be outdated

**What They Contain**:
- Sample data with various data types (email, phone, date, numeric, etc.)
- Intentionally bad data to test error handling
- Edge cases (empty values, invalid formats, etc.)

**Example Use Case**:
```python
# Test file contains:
# - Good email: "john@example.com"
# - Bad email: "john@@example.com" (double @)
# - Good phone: "555-123-4567"
# - Bad phone: "INVALID-PHONE"
# 
# Tests verify:
# - Good data is kept as "good"
# - Bad data is flagged as "bad"
# - Correctable bad data is fixed
```

---

## Why Are Test Files Important?

### 1. **Quality Assurance** ✅
- Ensures code works as expected
- Catches bugs before users see them
- Validates edge cases

### 2. **Regression Prevention** ✅
- Prevents new changes from breaking old features
- Ensures fixes stay fixed
- Maintains code stability

### 3. **Documentation** ✅
- Shows how code should be used
- Demonstrates expected behavior
- Provides examples

### 4. **Confidence** ✅
- Allows safe refactoring
- Enables confident deployments
- Reduces production bugs

---

## Current Test File Status

### ✅ **ACTIVE & USEFUL** (Keep These):

1. **Unit Tests** (`tests/`):
   - `test_ensemble_detector.py` ✅
   - `test_performance.py` ✅
   - `test_resilience.py` ✅
   - `test_security.py` ✅

2. **API Tests** (`testing_data/`):
   - `test_api_classification.py` ✅ - Tests current API
   - `test_api_correction.py` ✅ - Tests current API

3. **Test Data**:
   - `comprehensive_workflow_test_data.csv` ✅
   - `challenging_realworld_test_data.csv` ✅

---

### ⚠️ **OUTDATED** (Consider Updating or Removing):

1. **Old Pipeline Tests**:
   - `run_test_simple.py` ⚠️ - Uses old `PipelineService` (not V2)
   - `run_test_no_db.py` ⚠️ - Uses old workflow structure
   - `test_phase1_*.py` ⚠️ - Tests old Phase 1 implementation

2. **Old Test Data**:
   - `test_pipeline.csv` ⚠️ - May be outdated
   - `with_date.csv` ⚠️ - May be outdated

**Recommendation**: 
- **Option 1**: Update to use `PipelineServiceV2`
- **Option 2**: Remove if no longer needed
- **Option 3**: Keep for historical reference

---

## How to Use Test Files

### Running Unit Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_ensemble_detector.py

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=backend
```

### Running Integration Tests

```bash
# Test API
python testing_data/test_api_classification.py
python testing_data/test_api_correction.py

# Test pipeline (old - needs update)
python testing_data/run_test_simple.py
```

### Running Main Pipeline (Not a test, but useful)

```bash
# Test with real data
python run_pipeline.py testing_data/comprehensive_workflow_test_data.csv --enable-llm --enable-ensemble
```

---

## Best Practices

### 1. **Run Tests Before Committing** ✅
```bash
pytest tests/  # Quick check
```

### 2. **Run Tests After Changes** ✅
- After fixing bugs
- After adding features
- After refactoring

### 3. **Write Tests for New Features** ✅
- Test happy path (normal usage)
- Test error cases
- Test edge cases

### 4. **Keep Tests Updated** ✅
- Update tests when code changes
- Remove outdated tests
- Add tests for new bugs

---

## Test File Maintenance

### Current Issues:

1. **Outdated Tests**: Some tests use old `PipelineService` instead of `PipelineServiceV2`
2. **Missing Tests**: Some new features may not have tests yet
3. **Test Data**: Some test data files may be outdated

### Recommendations:

1. ✅ **Update old tests** to use `PipelineServiceV2`
2. ✅ **Add tests** for new features (NaN handling, etc.)
3. ✅ **Remove** truly outdated tests
4. ✅ **Document** test purposes clearly

---

## Summary

**Test Files Are For**:
- ✅ Verifying code works correctly
- ✅ Catching bugs early
- ✅ Preventing regressions
- ✅ Documenting expected behavior
- ✅ Enabling safe refactoring

**Current Status**:
- ✅ Unit tests are active and useful
- ✅ API tests are active and useful
- ⚠️ Some pipeline tests are outdated
- ⚠️ Some test data may be outdated

**Action Items**:
1. Keep active tests (`tests/`, API tests)
2. Update or remove outdated pipeline tests
3. Review and update test data files
4. Add tests for new features

---

**Last Updated**: 2026-01-28
