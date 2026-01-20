# DATA_CLUSTERING - Complete Build Specification

> **Purpose:** Complete specification for rebuilding the data quality pipeline from scratch  
> **Version:** 2.0 (Bug-free, refactored)  
> **Created:** 2026-01-18

---

## Project Overview

**Goal:** Build a professional data quality pipeline that automatically:
1. Detects column types (35+ subtypes across 4 workflows)
2. Clusters data into good/bad based on patterns
3. Uses LLM to verify and generate validation patterns
4. Applies intelligent corrections to bad data
5. Generates detailed reports

**Tech Stack:**
- Python 3.9+
- Pandas, NumPy, scikit-learn
- SQLite (caching)
- Groq LLM API
- DBSCAN clustering

---

## Complete Workflow Specification

### Workflow 1: STRING (text)

**Subworkflows (16):**
- `email` - Email addresses (regex + domain validation)
- `phone` - Phone numbers with separators
- `url` - Web URLs (http/https/ftp)
- `ip_address` - IPv4/IPv6 addresses
- `uuid` - Universal unique identifiers
- `name` - Person names (2-4 words, high alpha ratio)
- `company` - Company names (with Inc, LLC, Corp suffixes)
- `address` - Street addresses (numbers + street indicators)
- `location` (city) - City names
- `state` - State/province codes
- `country` - Country names/codes
- `zipcode` - Postal codes (5 or 9 digits)
- `username` - Usernames (alphanumeric + -_.)
- `file_path` - File paths (/ or \ separators)
- `product_title` - Product descriptions
- `generic` - Fallback for unclassified strings

**Validation Rules:**
```yaml
email:
  pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  checks:
    - Must have exactly one @
    - Must have TLD after @
    - No consecutive dots
  
phone:
  digit_count: 7-15
  allowed_separators: ['-', ' ', '(', ')', '.']
  formats:
    - '###-###-####'
    - '(###) ###-####'
    - '+#-###-###-####'

name:
  word_count: 2-4
  alpha_ratio: '>70%'
  reject_if:
    - Contains numbers
    - All uppercase (unless 2 letters like "IT")
    - Excessive special chars (>30%)

city:
  method: 'lookup_or_pattern'
  min_length: 2
  max_length: 50
  alpha_ratio: '>70%'
```

### Workflow 2: NUMERIC (numeric)

**Subworkflows (14):**
- `age` - Age values
- `year` - Year values
- `salary` - Money values (large)
- `amount` - General monetary amounts
- `count` - Count/quantity values
- `rating` - Rating scores
- `percentage` - Percentage values
- `temperature` - Temperature readings
- `latitude` - Latitude coordinates
- `longitude` - Longitude coordinates
- `phone` - Numeric-only phone numbers
- `zipcode` - 5-digit ZIP codes
- `numeric_id` - High-uniqueness numeric IDs
- `generic_numeric` - Fallback

**Semantic Constraints:**
```yaml
age:
  min: 0
  max: 120
  type: integer
  
rating:
  min: 0
  max: 10
  type: float
  normalization: 'if 0-5 scale, multiply by 2'
  
year:
  min: 1900
  max: 2100
  type: integer
  
latitude:
  min: -90
  max: 90
  type: float
  
longitude:
  min: -180
  max: 180
  type: float

percentage:
  ranges:
    - [0, 1]      # Decimal format
    - [0, 100]    # Percent format
```

### Workflow 3: DATETIME (datetime)

**Subworkflows (2):**
- `date` - Date only (YYYY-MM-DD, MM/DD/YYYY, etc.)
- `datetime` - Date + time

**Format Handling:**
```yaml
accepted_formats:
  - 'YYYY-MM-DD'
  - 'MM/DD/YYYY'
  - 'DD-MM-YYYY'
  - 'YYYY-MM-DD HH:MM:SS'
  - 'YYYY-MM-DDTHH:MM:SSZ'  # ISO 8601

validation:
  month: 1-12
  day: 1-31
  year: 1900-2100
  reject_if: 'month=13 or day=45'

clustering_strategy:
  - Parse all dates with dateutil
  - ALL valid formats go to good_data
  - Invalid dates go to bad_data
  - In correction: standardize to majority format
```

### Workflow 4: IDENTIFIER (identifier)

**Subworkflows (3):**
- `pattern_id` - Pattern-based IDs (ABC-123)
- `numeric_id` - Pure numeric IDs
- `generic_id` - Fallback

**Pattern Fingerprinting:**
```yaml
signature_format: 'AAA-9999-BBB'
# A = alpha, 9 = digit, B = alphanumeric

clustering_logic:
  1. Extract signature from each ID
  2. Count signature frequency
  3. If one signature >60%:
     - That signature = good pattern
     - Other signatures = bad (outliers)
  4. Else: All unique patterns = good
```

---

## Critical Bug Fixes (Must implement!)

### Bug 1: LLM Promotion without Correctability Check
**Problem:** LLM promotes uncorrectable values like 'ABC' to good_data  
**Fix:** Test correctability before promotion

```python
# In llm_verifier.py
def _test_correctability(self, value, column_name, detected_type):
    corrector = self._get_corrector(detected_type)
    try:
        corrected, confidence, _ = corrector.correct(value, test_mode=True)
        return confidence > 0.5 and corrected != value
    except:
        return False

# Use in promotion logic
if is_valid and confidence > 0.7:
    can_fix = self._test_correctability(item, column_name, detected_type)
    if can_fix:
        promoted.append(item)
```

### Bug 2: Semantic Validation After LLM
**Problem:** LLM can override semantic checks  
**Fix:** Run semantic validation BEFORE LLM patterns

```python
# Call order in verify_and_reshuffle:
# 1. Semantic validation FIRST
good_data, bad_data = self._semantic_validation(good_data, bad_data, dtype, colname)

# 2. THEN LLM pattern validation
# ... LLM logic
```

### Bug 3: Heuristic Priority Order
**Problem:** Generic patterns match before specific ones (address before city)  
**Fix:** Update SQL priorities - most specific first

```sql
UPDATE heuristic_rules SET priority = 10 WHERE pattern LIKE '%city%';
UPDATE heuristic_rules SET priority = 40 WHERE pattern LIKE '%address%';
```

### Bug 4: Timestamp Format Strictness
**Problem:** Valid ISO timestamps marked as bad  
**Fix:** Accept all valid formats in good_data

```python
# DateTimeWorkflow: Accept ALL valid formats
for item in data:
    if is_valid_datetime(item):  # Not: format == majority
        good_data.append(item)
```

### Bug 5: Phone Regex Backreferences
**Problem:** LLM generates JavaScript syntax `$1`  
**Fix:** Convert to Python syntax `\g<1>`

```python
def fix_backreferences(pattern):
    return re.sub(r'\$(\d+)', r'\\g<\1>', pattern)
```

### Bug 6: Department Casing
**Problem:** "IT" becomes "It"  
**Fix:** Preserve uppercase for known codes

```python
PRESERVE_UPPERCASE = ['IT', 'HR', 'PR', 'QA', 'CEO', 'CFO']

if value.upper() in PRESERVE_UPPERCASE:
    return value.upper()
```

---

## Project Structure

```
DATA_CLUSTERING/
├── run_pipeline.py
├── requirements.txt
├── README.md
├── .env
│
├── backend/
│   ├── services/
│   │   └── pipeline_service.py
│   │
│   ├── core/
│   │   ├── engines/           # 16 validation engines
│   │   ├── workflows/         # 4 workflow classes
│   │   ├── detection/         # Column type detection
│   │   ├── verification/      # LLM verification
│   │   ├── correction/        # Correctors
│   │   ├── llm/              # Groq API wrapper
│   │   └── caching/          # Fingerprint caching
│   │
│   └── output/               # Generated files
│
├── tests/
│   ├── test_engines.py
│   ├── test_workflows.py
│   └── test_regression.py
│
└── data/                     # Input CSVs
```

---

## Database Schema (SQLite)

```sql
-- detection_cache.db

CREATE TABLE workflow_cache (
    column_name TEXT PRIMARY KEY,
    workflow TEXT NOT NULL,
    subworkflow TEXT NOT NULL,
    confidence REAL,
    source TEXT
);

CREATE TABLE heuristic_rules (
    id INTEGER PRIMARY KEY,
    pattern TEXT NOT NULL,
    workflow TEXT NOT NULL,
    subworkflow TEXT NOT NULL,
    priority INTEGER NOT NULL
);
```

---

## Requirements

```
pandas>=1.5.0
numpy>=1.23.0
scikit-learn>=1.2.0
groq>=0.4.0
python-dateutil>=2.8.0
pytest>=7.0.0
```

---

## Implementation Steps

1. **Create project structure**
2. **Implement base classes** (ValidationEngine, BaseWorkflow, BaseCorrector)
3. **Implement 16 validation engines**
4. **Implement 4 workflows**
5. **Implement 3-tier column detector**
6. **Implement LLM verifier** (with all bug fixes!)
7. **Implement 6 correctors**
8. **Implement pipeline orchestrator**
9. **Add comprehensive tests**
10. **Validate with test data**

---

Ready for fresh implementation!
