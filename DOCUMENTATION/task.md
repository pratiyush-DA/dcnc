# Refactoring Task Breakdown

> **Purpose:** Actionable task list for getting the project back on track  
> **Options:** Incremental Refactor (recommended) or Complete Rebuild  
> **Timeline:** 2-3 weeks (incremental) or 4-6 weeks (rebuild)

---

## Table of Contents

- [Option A: Incremental Refactor](#option-a-incremental-refactor-recommended)
- [Option B: Complete Rebuild](#option-b-complete-rebuild)
- [Testing Strategy](#testing-strategy)
- [Success Criteria](#success-criteria)

---

## Option A: Incremental Refactor (Recommended)

### 📅 Timeline: 2-3 Weeks

---

### Phase 1: Critical Bug Fixes (Week 1, Days 1-2)

#### Task 1.1: Fix LLM Promotion Bug "ABC incident ")

**Priority:** CRITICAL  
**File:** `backend/core/clustering/detector.py` (Lines 1863-1876)

**Current Code:**
```python
for item in bad_data:
    is_valid, confidence = pattern_validator.validate(item)
    if is_valid and confidence > 0.7:
        should_block = run_semantic_checks(item, dt_low, cn_low)
        if not should_block:
            promoted.append({'value': item, 'confidence': confidence})
```

**Required Changes:**
- [ ] Add `can_correct()` validation before promotion
- [ ] Test with corrector to verify value is fixable
- [ ] If uncorrectable, keep in bad_data
- [ ] Update unit test: `test_llm_promotion_rejects_uncorrectable()`

**New Code:**
```python
for item in bad_data:
    is_valid, confidence = pattern_validator.validate(item)
    if is_valid and confidence > 0.7:
        should_block = run_semantic_checks(item, dt_low, cn_low)
        if not should_block:
            # NEW: Verify correctability
            test_corr = self._get_test_corrector(column_name, detected_type)
            can_fix, fix_confidence = test_corr.can_correct(item, column_context)
            
            if can_fix and fix_confidence > 0.5:
                promoted.append({'value': item, 'confidence': confidence})
                print(f"[LLM] Promoted: {item} (correctable)")
            else:
                new_bad.append(item)
                print(f"[LLM] Blocked promotion: {item} (uncorrectable)")
```

**Testing:**
```python
# test_detector.py
def test_llm_promotion_rejects_uncorrectable():
    verifier = LLMVerifier(enabled=True)
    
    good_data = ['john@example.com', 'jane@example.com']
    bad_data = ['invalid@', 'ABC', 'john@gmial.com']  # Only last is correctable
    
    result = verifier.verify_and_reshuffle('email', good_data, bad_data, 'email')
    
    # 'ABC' and 'invalid@' should NOT be promoted
    assert 'ABC' not in [p['value'] for p in result['reshuffled']['promoted']]
    assert 'invalid@' not in [p['value'] for p in result['reshuffled']['promoted']]
    
    # 'john@gmial.com' SHOULD be promoted (typo fix)
    assert 'john@gmial.com' in [p['value'] for p in result['reshuffled']['promoted']]
```

**Estimated Time:** 4 hours

---

#### Task 1.2: Fix Semantic Validation Order

**Priority:** HIGH  
**File:** `backend/core/clustering/detector.py` (Lines 1832-1858)

**Problem:** Semantic checks happen inside LLM verifier, after pattern matching

**Required Changes:**
- [ ] Move semantic validation BEFORE LLM verification
- [ ] Create `run_semantic_validation()` method in clusterer
- [ ] Call it immediately after clustering
- [ ] LLM verifier receives pre-validated data

**New Flow:**
```python
# In DataQualityClusterer.cluster_column()
good_data, bad_data = workflow.cluster(column_data)

# NEW: Semantic validation BEFORE LLM
good_data, bad_data = self.run_semantic_validation(
    good_data, bad_data, column_name, detected_type
)

# THEN LLM verification
if self.llm_verifier:
    result = self.llm_verifier.verify_and_reshuffle(
        column_name, good_data, bad_data, detected_type
    )
```

**Testing:**
```python
def test_semantic_validation_before_llm():
    clusterer = DataQualityClusterer(enable_llm=True)
    
    # Date column with invalid dates
    data = ['2025-01-01', '2025-02-15', '2023-13-45', '2024-99-01']
    
    result = clusterer.cluster_column(data, 'signup_date', 'date')
    
    # Invalid dates should be in bad BEFORE LLM sees them
    assert '2023-13-45' in result['bad_data']
    assert '2024-99-01' in result['bad_data']
    
    # Valid dates in good
    assert '2025-01-01' in result['good_data']
    assert '2025-02-15' in result['good_data']
```

**Estimated Time:** 6 hours

---

#### Task 1.3: Fix Heuristic Priority Order

**Priority:** MEDIUM  
**File:** `backend/core/detection/llm_detector.py` (Lines 112-130)

**Problem:** Generic patterns (like 'address') match before specific ones (like 'city')

**Required Changes:**
- [ ] Update heuristic rules in database
- [ ] Prioritize most specific patterns first
- [ ] Add pattern specificity scoring

**SQL Changes:**
```sql
-- Update priorities in detection_cache.db
UPDATE heuristic_rules SET priority = 10 WHERE pattern LIKE '%city%' OR pattern LIKE '%town%';
UPDATE heuristic_rules SET priority = 15 WHERE pattern LIKE '%state%' OR pattern LIKE '%province%';
UPDATE heuristic_rules SET priority = 20 WHERE pattern LIKE '%zip%' OR pattern LIKE '%postal%';
UPDATE heuristic_rules SET priority = 30 WHERE pattern LIKE '%country%';
UPDATE heuristic_rules SET priority = 40 WHERE pattern LIKE '%address%';

-- Verify
SELECT pattern, workflow, subworkflow, priority 
FROM heuristic_rules 
WHERE pattern LIKE '%city%' OR pattern LIKE '%address%'
ORDER BY priority ASC;
```

**Testing:**
```python
def test_heuristic_priority_specific_before_generic():
    detector = LLMWorkflowDetector()
    
    # Test 'address_city' - should match 'city' not 'address'
    result = detector.detect('address_city', sample_data=['New York', 'Chicago'])
    assert result['workflow'] == 'text'
    assert result['subworkflow'] == 'city'
    
    # Test 'city_address' - should still match 'city'
    result = detector.detect('city_address', sample_data=['New York', 'Chicago'])
    assert result['workflow'] == 'text'
    assert result['subworkflow'] == 'city'
    
    # Test plain 'address' - should match 'address'
    result = detector.detect('address', sample_data=['123 Main St', '456 Oak Ave'])
    assert result['workflow'] == 'contact'
    assert result['subworkflow'] == 'address'
```

**Estimated Time:** 3 hours

---

#### Task 1.4: Fix Timestamp Format Strictness

**Priority:** MEDIUM  
**File:** `backend/core/clustering/detector.py` (DateTimeWorkflow section)

**Problem:** Valid ISO timestamps marked as bad because they don't match majority format

**Required Changes:**
- [ ] Change logic to accept ALL valid datetime formats as good
- [ ] Move format standardization to correction phase
- [ ] Update DatetimeCorrector to handle format conversion

**New Code:**
```python
# In DateTimeWorkflow.cluster()
def cluster(self, data, column_name=None):
    good_data = []
    bad_data = []
    format_counts = Counter()
    
    for item in data:
        parsed, format_detected = self.parse_datetime(item)
        
        if parsed:  # Valid datetime
            good_data.append(item)
            format_counts[format_detected] += 1
        else:  # Invalid
            bad_data.append(item)
    
    # Detect majority format (for correction phase)
    majority_format = format_counts.most_common(1)[0][0] if format_counts else None
    
    return {
        'good_clusters': [good_data],
        'bad_data': bad_data,
        'detected_type': 'datetime',
        'target_format': majority_format  # Pass to corrector
    }
```

**In DatetimeCorrector:**
```python
def correct(self, value, target_format, **kwargs):
    # Parse
    parsed = dateutil.parser.parse(value)
    
    # Current format
    current_format = self.detect_format(value)
    
    # If not majority format, reformat
    if current_format != target_format:
        corrected = parsed.strftime(target_format)
        return corrected, confidence=1.0, changes=['format_standardized']
    
    # Already in target format
    return value, confidence=1.0, changes=[]
```

**Testing:**
```python
def test_all_valid_timestamps_accepted():
    workflow = DateTimeWorkflow()
    
    data = [
        '2025-01-18 10:30:00',     # Standard (80%)
        '2025-01-18 11:00:00',
        '2025-01-18T12:00:00Z',    # ISO format (20% - VALID!)
        '2025-99-99 00:00:00',     # Invalid
    ]
    
    result = workflow.cluster(data, 'timestamp')
    
    # All valid formats in good
    assert '2025-01-18 10:30:00' in result['good_clusters'][0]
    assert '2025-01-18T12:00:00Z' in result['good_clusters'][0]
    
    # Invalid in bad
    assert '2025-99-99 00:00:00' in result['bad_data']
    
    # Majority format detected
    assert result['target_format'] == 'YYYY-MM-DD HH:MM:SS'
```

**Estimated Time:** 5 hours

---

### Phase 2: Code Splitting (Week 1, Days 3-5)

#### Task 2.1: Extract Validation Engines

**Priority:** HIGH  
**Goal:** Split detector.py (3,362 lines) into manageable modules

**Files to Create:**
```
backend/core/engines/
├── __init__.py
├── base_engine.py           # ValidationEngine base class
├── email_engine.py
├── phone_engine.py
├── url_engine.py
├── name_engine.py
├── company_engine.py
├── address_engine.py
├── location_engine.py
├── zipcode_engine.py
├── username_engine.py
├── product_title_engine.py
├── file_path_engine.py
├── ip_address_engine.py
├── state_country_engine.py
└── generic_engine.py
```

**Steps:**
- [ ] Create `backend/core/engines/` directory
- [ ] Create `base_engine.py` with `ValidationEngine` class
- [ ] Extract each engine class to separate file
- [ ] Update imports in `detector.py`
- [ ] Run tests to verify no behavior change

**Example: email_engine.py**
```python
"""Email Validation Engine"""
from .base_engine import ValidationEngine
import re

class EmailEngine(ValidationEngine):
    """Specialized validation for email addresses"""
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        # ... rest of implementation from detector.py lines 129-165
    
    def validate(self, email):
        # ... exact logic from detector.py
```

**Verification:**
```bash
# Run all tests
pytest tests/test_engines.py -v

# Verify import works
python -c "from backend.core.engines import EmailEngine; print(EmailEngine().validate('test@example.com'))"
```

**Estimated Time:** 8 hours

---

#### Task 2.2: Extract Workflows

**Priority:** HIGH

**Files to Create:**
```
backend/core/workflows/
├── __init__.py
├── base_workflow.py         # Abstract base
├── string_workflow.py       # Lines 1990-2178 from detector.py
├── numeric_workflow.py      # Lines 2185-2431 from detector.py
├── datetime_workflow.py     # Lines 2433-2567 from detector.py
└── identifier_workflow.py   # Already exists, refactor
```

**Steps:**
- [ ] Create `backend/core/workflows/` directory
- [ ] Define abstract `BaseWorkflow` class
- [ ] Extract `StringWorkflow` → `string_workflow.py`
- [ ] Extract `NumericWorkflow` → `numeric_workflow.py`
- [ ] Extract `DateTimeWorkflow` → `datetime_workflow.py`
- [ ] Refactor existing `identifier_workflow.py`
- [ ] Update imports in `detector.py`

**Example: base_workflow.py**
```python
"""Abstract Base Workflow"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseWorkflow(ABC):
    """Base class for all data quality workflows"""
    
    @abstractmethod
    def detect_subtype(self, data: List, column_name: str = None) -> str:
        """Detect the specific subtype within this workflow"""
        pass
    
    @abstractmethod
    def cluster(self, data: List, column_name: str = None, **kwargs) -> Dict:
        """
        Cluster data into good and bad groups
        
        Returns:
            {
                'good_clusters': [[good_data]],
                'bad_data': [bad_data],
                'detected_type': 'subtype',
                'metadata': {}
            }
        """
        pass
```

**Example: string_workflow.py**
```python
"""String Data Workflow"""
from .base_workflow import BaseWorkflow
from ..engines import (
    EmailEngine, PhoneEngine, URLEngine, NameEngine,
    CompanyEngine, AddressEngine, LocationEngine, 
    ZipCodeEngine, UsernameEngine, ProductTitleEngine,
    FilePathEngine, IPAddressEngine, StateCountryEngine,
    GenericStringEngine
)

class StringWorkflow(BaseWorkflow):
    """Handles string-based column clustering"""
    
    def __init__(self):
        self.engines = {
            'email': EmailEngine(),
            'phone': PhoneEngine(),
            # ... rest from detector.py lines 1994-2010
        }
    
    def detect_subtype(self, data_sample, column_name=None):
        # ... exact logic from detector.py lines 2014-2081
    
    def cluster(self, data, column_name=None, strictness=0.8):
        # ... exact logic from detector.py lines 2083-2178
```

**Estimated Time:** 12 hours

---

#### Task 2.3: Extract LLM Verifier

**Priority:** MEDIUM

**Files to Create:**
```
backend/core/verification/
├── __init__.py
├── llm_verifier.py          # Lines 1693-1983 from detector.py
├── pattern_validator.py     # Extract from llm_service
└── semantic_checks.py       # Extract semantic validation logic
```

**Steps:**
- [ ] Create `backend/core/verification/` directory
- [ ] Extract `LLMVerifier` class → `llm_verifier.py`
- [ ] Extract semantic check logic → `semantic_checks.py`
- [ ] Update imports in `detector.py`
- [ ] Update imports in `pipeline_service.py`

**Example: semantic_checks.py**
```python
"""Semantic Validation Checks"""
import re
from typing import Tuple, List

def run_semantic_checks(value: str, detected_type: str, column_name: str) -> Tuple[bool, List[str]]:
    """
    Run domain-specific semantic validation
    
    Returns:
        (should_reject, issues)
    """
    value_str = str(value).strip()
    dt_low = detected_type.lower()
    cn_low = column_name.lower()
    
    # DATE check
    if 'date' in dt_low:
        dm = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', value_str)
        if dm:
            month, day = int(dm.group(2)), int(dm.group(3))
            if month < 1 or month > 12 or day < 1 or day > 31:
                return True, ['invalid_date']
    
    # AGE check
    elif 'age' in cn_low:
        try:
            age = float(value_str)
            if age < 0 or age > 120:
                return True, ['age_out_of_range']
        except:
            return True, ['non_numeric_age']
    
    # ... rest of checks from detector.py lines 1769-1827
    
    return False, []  # No issues
```

**Estimated Time:** 6 hours

---

### Phase 3: Add Tests (Week 2, Days 1-3)

#### Task 3.1: Unit Tests for Engines

**Priority:** HIGH

**File:** `tests/test_engines.py`

**Tests to Write:**
```python
import pytest
from backend.core.engines import *

class TestEmailEngine:
    def test_valid_email(self):
        engine = EmailEngine()
        assert engine.validate('test@example.com')
    
    def test_invalid_email(self):
        engine = EmailEngine()
        assert not engine.validate('invalid@')
        assert not engine.validate('no-at-sign.com')
    
    def test_email_with_plus_alias(self):
        engine = EmailEngine()
        assert engine.validate('user+tag@example.com')

class TestPhoneEngine:
    def test_valid_phone_formats(self):
        engine = PhoneEngine()
        assert engine.validate('123-456-7890')
        assert engine.validate('(123) 456-7890')
        assert engine.validate('+1-234-567-8901')
    
    def test_invalid_phone(self):
        engine = PhoneEngine()
        assert not engine.validate('123')  # Too short
        assert not engine.validate('abc-def-ghij')  # Not numeric

# ... 15+ engine test classes
```

**Coverage Goal:** 90%+ for all engines

**Estimated Time:** 8 hours

---

#### Task 3.2: Unit Tests for Workflows

**Priority:** HIGH

**File:** `tests/test_workflows.py`

**Tests to Write:**
```python
import pytest
from backend.core.workflows import *

class TestStringWorkflow:
    def test_detect_email_subtype(self):
        wf = StringWorkflow()
        data = ['john@example.com', 'jane@test.com']
        subtype = wf.detect_subtype(data, 'email')
        assert subtype == 'email'
    
    def test_cluster_email_data(self):
        wf = StringWorkflow()
        data = [
            'john@example.com',     # Good
            'jane@example.com',     # Good
            'invalid@',             # Bad
            'jdoe@gmial.com'        # Bad (typo)
        ]
        result = wf.cluster(data, 'email')
        
        assert len(result['good_clusters'][0]) == 2
        assert len(result['bad_data']) == 2
        assert result['detected_type'] == 'email'

class TestNumericWorkflow:
    def test_detect_age_subtype(self):
        wf = NumericWorkflow()
        data = [25, 30, 45, 67]
        subtype = wf.detect_numeric_type(data, 'age')
        assert subtype == 'age'
    
    def test_reject_age_outliers(self):
        wf = NumericWorkflow()
        data = [25, 30, 999, 45]  # 999 is outlier
        result = wf.cluster(data, 'age')
        
        assert 999 in result['bad_data']
        assert 25 in result['good_clusters'][0]

# ... 4 workflow test classes
```

**Coverage Goal:** 85%+ for all workflows

**Estimated Time:** 10 hours

---

#### Task 3.3: Integration Tests

**Priority:** MEDIUM

**File:** `tests/test_pipeline_integration.py`

**Tests to Write:**
```python
import pytest
import pandas as pd
from backend.services.pipeline_service import PipelineService

class TestFullPipeline:
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create test CSV file"""
        csv_path = tmp_path / "test_data.csv"
        df = pd.DataFrame({
            'email': ['john@example.com', 'jane@gmial.com', 'invalid@'],
            'age': [25, 999, 30],
            'signup_date': ['2025-01-01', '2025/01/02', '2023-13-45']
        })
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    def test_end_to_end_pipeline(self, sample_csv, tmp_path):
        """Test complete pipeline execution"""
        output_dir = tmp_path / "output"
        
        service = PipelineService(enable_llm=False)  # Faster without LLM
        result = service.run(sample_csv, str(output_dir))
        
        # Verify outputs exist
        assert (output_dir / "good_n_bad" / "good_data_email.csv").exists()
        assert (output_dir / "final" / "final_output.csv").exists()
        
        # Verify corrections
        assert result['corrections_made'] >= 1  # At least typo fix
    
    def test_llm_verification_integration(self, sample_csv, tmp_path):
        """Test pipeline with LLM enabled"""
        service = PipelineService(enable_llm=True)
        result = service.run(sample_csv, str(tmp_path))
        
        # Verify LLM was used
        assert result.get('llm_calls_made') > 0
    
    def test_headerless_csv_detection(self, tmp_path):
        """Test detection for headerless CSV"""
        csv_path = tmp_path / "headerless.csv"
        df = pd.DataFrame([
            ['john@example.com', 25, '2025-01-01'],
            ['jane@example.com', 30, '2025-01-02']
        ])
        df.to_csv(csv_path, index=False, header=False)
        
        service = PipelineService()
        result = service.run(str(csv_path), str(tmp_path), no_header=True)
        
        # Verify columns were auto-detected
        assert result['columns_processed'] == 3
```

**Coverage Goal:** 80%+ for pipeline service

**Estimated Time:** 12 hours

---

### Phase 4: Documentation & Cleanup (Week 2, Days 4-5 + Week 3)

#### Task 4.1: Update Code Documentation

**Priority:** MEDIUM

**Files to Update:**
- [ ] Add docstrings to all new modules
- [ ] Update README.md with new structure
- [ ] Create API documentation
- [ ] Add inline comments for complex logic

**Template Docstring:**
```python
"""
Module: email_engine.py
Purpose: Email validation engine for data quality pipeline

This module provides specialized validation for email addresses including:
- RFC 5322 compliant regex validation
- Domain TLD validation
- Common typo detection

Example:
    >>> from backend.core.engines import EmailEngine
    >>> engine = EmailEngine()
    >>> engine.validate('test@example.com')
    True

Author: Data Quality Team
Updated: 2026-01-18
"""
```

**Estimated Time:** 6 hours

---

#### Task 4.2: Performance Profiling

**Priority:** LOW

**Goal:** Identify and fix performance bottlenecks

**Tools:**
```python
# Use cProfile
python -m cProfile -o profile.stats run_pipeline.py data/large_file.csv

# Analyze
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
```

**Optimizations to Consider:**
- [ ] Cache validation regex patterns
- [ ] Batch LLM API calls
- [ ] Use vectorized pandas operations
- [ ] Parallelize column processing

**Estimated Time:** 4 hours

---

#### Task 4.3: Final Regression Testing

**Priority:** CRITICAL

**Goal:** Ensure all previous bugs are fixed

**Test Cases from Conversation History:**
- [ ] ABC promotion bug (should NOT promote)
- [ ] City column classification (should be text/city not contact/address)
- [ ] Timestamp validation (ISO format accepted)
- [ ] Age outliers (999 rejected)
- [ ] Date validation (2023-13-45 rejected)
- [ ] Phone regex backreferences (Python syntax)
- [ ] Department casing (IT stays IT, not It)

**Test File:** `tests/test_regression.py`
```python
import pytest
from backend.core.clustering.detector import DataQualityClusterer, LLMVerifier

class TestRegressionBugs:
    def test_abc_promotion_bug_fixed(self):
        """Regression: ABC should not be promoted to good"""
        verifier = LLMVerifier(enabled=True)
        good = ['john@example.com', 'jane@example.com']
        bad = ['ABC', 'invalid@']
        
        result = verifier.verify_and_reshuffle('email', good, bad, 'email')
        
        # ABC should NOT be promoted
        promoted_values = [p['value'] for p in result['reshuffled']['promoted']]
        assert 'ABC' not in promoted_values
    
    def test_city_heuristic_priority_fixed(self):
        """Regression: address_city should detect as city not address"""
        from backend.core.detection.llm_detector import LLMWorkflowDetector
        
        detector = LLMWorkflowDetector()
        result = detector.detect('address_city', ['New York', 'Chicago'])
        
        assert result['subworkflow'] == 'city'
        assert result['workflow'] == 'text'
    
    # ... 7 more regression tests
```

**Estimated Time:** 6 hours

---

## Option B: Complete Rebuild

### 📅 Timeline: 4-6 Weeks

---

### Phase 1: Architecture Design (Week 1)

#### Task 1.1: Define Core Interfaces

**Priority:** CRITICAL

**Files to Create:**
```
backend/interfaces/
├── __init__.py
├── workflow_interface.py
├── validator_interface.py
├── corrector_interface.py
└── detector_interface.py
```

**Example: workflow_interface.py**
```python
"""Core Workflow Interface"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ClusterResult:
    """Result of clustering operation"""
    good_data: List[Any]
    bad_data: List[Any]
    subtype: str
    confidence: float
    metadata: Dict[str, Any]

class IWorkflow(ABC):
    """Interface for all workflow implementations"""
    
    @abstractmethod
    def detect_subtype(self, data: List[Any], column_name: Optional[str] = None) -> str:
        """Detect the specific subtype of data"""
        pass
    
    @abstractmethod
    def cluster(self, data: List[Any], **kwargs) -> ClusterResult:
        """Cluster data into good and bad groups"""
        pass
    
    @abstractmethod
    def get_validator(self, subtype: str):
        """Get validator for specific subtype"""
        pass
```

**Estimated Time:** 8 hours

---

#### Task 1.2: Design Plugin Architecture

**Priority:** HIGH

**Goal:** Make it easy to add new workflows/validators

**Configuration Format:**
```yaml
# config/workflows.yaml
workflows:
  string:
    class: StringWorkflow
    validators:
      - email: EmailValidator
      - phone: PhoneValidator
      - url: URLValidator
    priority: 10
  
  numeric:
    class: NumericWorkflow
    validators:
      - age: AgeValidator
      - rating: RatingValidator
    priority: 20
```

**Registry System:**
```python
# backend/core/registry.py
class WorkflowRegistry:
    """Registry for all workflow plugins"""
    
    def __init__(self):
        self._workflows = {}
        self._validators = {}
        self._correctors = {}
    
    def register_workflow(self, name: str, workflow_class: type):
        """Register a new workflow"""
        self._workflows[name] = workflow_class
    
    def get_workflow(self, name: str):
        """Get workflow by name"""
        return self._workflows.get(name)
    
    # Decorator for easy registration
    def workflow(self, name: str):
        def decorator(cls):
            self.register_workflow(name, cls)
            return cls
        return decorator

# Usage
registry = WorkflowRegistry()

@registry.workflow('string')
class StringWorkflow(IWorkflow):
    # implementation
```

**Estimated Time:** 12 hours

---

### Phase 2: Core Implementation (Weeks 2-3)

**See separate implementation_plan.md for complete rebuild details**

(This would be another 40-50 hours of work)

---

## Testing Strategy

### Test Pyramid

```
        /\
       /  \      10% - Integration Tests (Full pipeline)
      /____\
     /      \    30% - Component Tests (Workflows, Correctors)
    /        \
   /__________\  60% - Unit Tests (Engines, Validators)
```

### Test Data Sets

**Create:** `tests/fixtures/test_data/`

```
test_data/
├── comprehensive_test.csv     # All data types
├── edge_cases.csv             # Outliers, nulls, extremes
├── large_dataset.csv          # Performance testing (10k+ rows)
├── headerless.csv             # Content-only detection
└── known_bugs.csv             # Regression test cases
```

**Example: comprehensive_test.csv**
```csv
email,phone,age,signup_date,city,rating,amount
john@example.com,123-456-7890,25,2025-01-01,New York,4.5,1250.50
jane@gmial.com,(234) 567-8901,30,2025/01/02,Chicago,5.0,2000.00
invalid@,1234567890,999,2023-13-45,XYZ,99,abc
test+alias@example.com,+1-345-678-9012,45,2025-01-01T10:30:00Z,Los Angeles,3.5,500.75
```

### Continuous Testing

**Setup GitHub Actions / CI:**
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=backend --cov-report=html
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Success Criteria

### Functional Requirements
- [ ] All known bugs fixed (ABC promotion, city heuristics, etc.)
- [ ] All 35+ subworkflows working correctly
- [ ] LLM integration stable with proper error handling
- [ ] Caching working across all 3 layers
- [ ] Output files generated correctly

### Quality Requirements
- [ ] Code coverage ≥ 85%
- [ ] All regression tests passing
- [ ] No file > 500 lines (split detector.py!)
- [ ] All functions documented with docstrings
- [ ] Type hints on all public methods

### Performance Requirements
- [ ] Process 10k rows in < 30 seconds (without LLM)
- [ ] Process 10k rows in < 2 minutes (with LLM, cached)
- [ ] Memory usage < 500MB for 100k rows
- [ ] LLM cache hit rate > 80% on repeat runs

### Maintainability Requirements
- [ ] Clear module separation (workflows, engines, correctors)
- [ ] Easy to add new subworkflow (< 1 hour)
- [ ] Easy to add new correction rule (< 30 minutes)
- [ ] Developer documentation complete
- [ ] Architecture diagram up to date

---

## Deliverables Checklist

### Code
- [ ] Refactored backend/core/clustering/detector.py
- [ ] New backend/core/engines/ module
- [ ] New backend/core/workflows/ module
- [ ] New backend/core/verification/ module
- [ ] Updated backend/services/pipeline_service.py
- [ ] All tests passing (unit + integration)

### Documentation
- [ ] Updated README.md
- [ ] API documentation (Sphinx/pdoc)
- [ ] Architecture diagrams (Mermaid)
- [ ] Developer guide
- [ ] User guide
- [ ] Change log

### Testing
- [ ] Unit tests (60% of test suite)
- [ ] Component tests (30% of test suite)
- [ ] Integration tests (10% of test suite)
- [ ] Regression tests for all known bugs
- [ ] Performance benchmarks

---

## Risk Mitigation

### Risk 1: Breaking Existing Functionality

**Mitigation:**
- Run full test suite after every change
- Keep old code in backup branch
- Use feature flags for new code paths
- Deploy incrementally (1 workflow at a time)

### Risk 2: Timeline Overrun

**Mitigation:**
- Start with critical bugs (Week 1)
- Make incremental progress visible
- Have checkpoint meetings every 2 days
- Be ready to cut scope if needed

### Risk 3: LLM API Dependency

**Mitigation:**
- Always have fallback logic
- Cache aggressively
- Monitor API usage and costs
- Have option to disable LLM entirely

---

**Next Steps:**
1. Choose refactoring approach (A or B)
2. Set up project board (GitHub Projects / Jira)
3. Create branch: `refactor/data-quality-pipeline`
4. Start with Task 1.1 (ABC bug fix)

Ready to begin?
