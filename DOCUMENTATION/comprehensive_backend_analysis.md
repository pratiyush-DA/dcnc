# Comprehensive Backend Codebase Analysis

## Table of Contents
1. [System Objective](#system-objective)
2. [Architectural Approach](#architectural-approach)
3. [Core Logic & Philosophy](#core-logic--philosophy)
4. [Detection Flow](#detection-flow)
5. [Workflows](#workflows)
6. [Subworkflows & Methods](#subworkflows--methods)
7. [Column Identification Logic](#column-identification-logic)
8. [Clustering Strategies](#clustering-strategies)
9. [Correction Engine](#correction-engine)
10. [LLM Integration](#llm-integration)
11. [Complete Flow Examples](#complete-flow-examples)

---

## System Objective

### Primary Goal
Build a **production-grade data quality pipeline** that:
1. **Automatically detects** column data types (workflow + subtype)
2. **Clusters data** into "good" (valid) and "bad" (invalid/anomalous) groups
3. **Generates fingerprints** from good data to learn patterns
4. **Corrects bad data** using learned patterns from fingerprints
5. **Provides detailed reports** on data quality and corrections

### Key Requirements
- **No LLM required for detection** - Uses heuristic + pattern analysis
- **Content-first detection** - Analyzes data patterns before column names
- **Fingerprint-based correction** - Correctors learn from good data
- **Generic fallbacks** - Every workflow has a fallback for unknown types
- **Centralized LLM** - Single file for all LLM calls (optional verification)
- **ML-based clustering** - Uses IsolationForest, DBSCAN, IQR for anomaly detection
- **Production-ready** - Caching, error handling, logging, database integration

---

## Architectural Approach

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Service                           │
│  (Orchestrates entire flow: detection → clustering → fix)    │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Detection   │   │  Workflows   │   │  Correction  │
│  Layer       │   │  Layer        │   │  Layer       │
│              │   │              │   │              │
│ - Heuristic  │   │ - Text        │   │ - Text       │
│ - Pattern    │   │ - Numeric     │   │ - Numeric    │
│ - Cache     │   │ - DateTime    │   │ - DateTime   │
│              │   │ - Identifier  │   │ - Generic    │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Clustering │
                    │   Strategies │
                    │              │
                    │ - Validator  │
                    │ - Categorical│
                    │ - FreeText   │
                    │ - Semantic   │
                    │ - Pattern    │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  Fingerprint │
                    │  Generation  │
                    │              │
                    │ - Reference  │
                    │ - Patterns   │
                    │ - Statistics │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  LLM Layer   │
                    │  (Optional)  │
                    │              │
                    │ - Reshuffler │
                    │ - Pattern Gen│
                    │ - Cache      │
                    └──────────────┘
```

### Design Principles

1. **Content-First Detection**: Analyze data patterns BEFORE column names
   - Example: Column named "ip_login" with IP addresses → detected as IP (not username)
   - Example: Column named "last_login" with datetimes → detected as datetime (not text)

2. **Plugin Architecture**: Registry-based system for extensibility
   - Workflows, Validators, Correctors, Fingerprints all registered
   - Easy to add new types without modifying core code

3. **Layered Validation**:
   - **Layer 1**: Pattern/Heuristic Detection (no LLM)
   - **Layer 2**: Workflow-specific clustering (ML-based)
   - **Layer 3**: LLM verification (optional, for edge cases)

4. **Fingerprint-Driven Correction**:
   - Good data → Fingerprint → Correction patterns
   - Correctors learn from fingerprints, not hardcoded rules

---

## Core Logic & Philosophy

### Detection Philosophy

**Priority Order:**
1. **Cache Check** (if enabled)
2. **Content Pattern Analysis** (PRIMARY - checks data patterns)
3. **Heuristic Rules** (SECONDARY - checks column names)
4. **Generic Fallback** (if nothing matches)

**Why Content-First?**
- Column names can be misleading ("ip_login" might contain IPs)
- Data patterns are more reliable than naming conventions
- Ensures robustness across different data sources

### Clustering Philosophy

**Two Modes:**
1. **Strict Validation** (for known types: email, phone, url, etc.)
   - Uses dedicated validator engines
   - Deterministic rule-based validation
   - High confidence, low false positives

2. **Lenient Validation** (for free-text: name, company, address, etc.)
   - Accepts most values by default
   - Only rejects clearly invalid (gibberish, placeholders)
   - Trusts user data unless obviously bad

3. **ML-Based Anomaly Detection** (for generic types)
   - IsolationForest for numeric outliers
   - DBSCAN for string clustering
   - IQR + Z-score ensemble for statistical outliers

### Correction Philosophy

**Fingerprint Learning:**
- Good data → Extract patterns → Build fingerprint
- Fingerprint contains:
  - Reference values (for categorical)
  - Statistical bounds (for numeric)
  - Format patterns (for identifiers)
  - Case/style preferences (for strings)

**Correction Strategy:**
- Fuzzy matching for typos (RapidFuzz)
- Pattern-based correction for formats
- Statistical bounds for numeric outliers
- Reference-based correction for categorical

---

## Detection Flow

### Complete Detection Process

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Cache Check                                          │
│ - Check if column_name exists in detection cache             │
│ - If found → return cached result (workflow, subtype)        │
└─────────────────────────────────────────────────────────────┘
                            │ (cache miss)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Content Pattern Analysis (PRIMARY)                   │
│                                                               │
│ PatternAnalyzer.analyze(sample_data)                         │
│                                                               │
│ Checks patterns in priority order:                           │
│ 1. email (regex: ^[a-zA-Z0-9._%+-]+@...)                     │
│ 2. uuid (regex: ^[0-9a-fA-F]{8}-...)                         │
│ 3. ip_address (regex: ^(?:\d{1,3}\.){3}\d{1,3}$)            │
│ 4. datetime_iso (regex: ^\d{4}-\d{2}-\d{2}[T\s]...)          │
│ 5. date_iso (regex: ^\d{4}-\d{2}-\d{2}$)                     │
│ 6. date_us (regex: ^\d{1,2}/\d{1,2}/\d{2,4}$)                │
│ 7. url (regex: ^(https?://|www\.)[^\s]+$)                     │
│ 8. phone (regex: ^[\d\s\-\(\)\+\.]{7,20}$)                   │
│ 9. zipcode_us (regex: ^\d{5}(-\d{4})?$)                      │
│ 10. boolean (regex: ^(true|false|yes|no|1|0|y|n|t|f)$)      │
│ 11. ssn (regex: ^\d{3}-\d{2}-\d{4}$)                         │
│                                                               │
│ For each pattern:                                            │
│   - Calculate match_ratio = matches / total_samples           │
│   - If match_ratio >= threshold (0.6-0.8) → return result    │
│                                                               │
│ If no strong pattern match → continue to Step 3              │
└─────────────────────────────────────────────────────────────┘
                            │ (no strong match)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Heuristic Rules (SECONDARY)                          │
│                                                               │
│ HeuristicMatcher.match(column_name)                          │
│                                                               │
│ Priority-ordered rules (lower number = higher priority):     │
│                                                               │
│ Priority 1:  id_generic → identifier/pattern_id              │
│ Priority 21: email → text/email                             │
│ Priority 22: phone → text/phone                             │
│ Priority 23: url → text/url                                  │
│ Priority 24: ip_address → text/ip_address                    │
│ Priority 25: ssn → text/ssn                                  │
│ Priority 41: city → text/location                            │
│ Priority 42: state → text/state                              │
│ Priority 43: zipcode → text/zipcode                          │
│ Priority 44: country → text/country                          │
│ Priority 50: address → text/address                           │
│ Priority 61: company → text/company                          │
│ Priority 70: name → text/name                                │
│ Priority 81: age → numeric/age                               │
│ Priority 82: rating → numeric/rating                          │
│ Priority 83: salary → numeric/salary                         │
│ Priority 84: amount → numeric/amount                          │
│ Priority 101: datetime → datetime/datetime                   │
│ Priority 102: date → datetime/date                            │
│ Priority 121: boolean → text/boolean                         │
│ Priority 132: title → text/job_title                          │
│                                                               │
│ Uses fnmatch for glob-style pattern matching                 │
│ Example: "*email*" matches "user_email", "email_address"      │
└─────────────────────────────────────────────────────────────┘
                            │ (no heuristic match)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Generic Fallback                                     │
│                                                               │
│ _detect_generic_type(sample_data)                           │
│                                                               │
│ 1. Check if mostly numeric (>80% parseable as float)        │
│    → numeric/generic_numeric                                  │
│                                                               │
│ 2. Check alpha ratio (letters / total_chars)                 │
│    If < 50% letters in >70% of values                       │
│    → identifier/pattern_id (likely codes/IDs)                │
│                                                               │
│ 3. Default → text/generic                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    Cache result & return
```

### Detection Result Structure

```python
DetectionResult(
    workflow: str,           # "text", "numeric", "datetime", "identifier"
    subtype: str,            # "email", "age", "date", "pattern_id", etc.
    confidence: float,        # 0.0 - 1.0
    source: DetectionSource,  # PATTERN, HEURISTIC, DEFAULT
    matched_rule: str,       # Pattern name or heuristic rule name
    details: Dict            # Additional metadata
)
```

---

## Workflows

### Overview

The system has **4 main workflows**, each handling a category of data types:

1. **Text Workflow** (`StringWorkflow`)
2. **Numeric Workflow** (`NumericWorkflow`)
3. **DateTime Workflow** (`DateTimeWorkflow`)
4. **Identifier Workflow** (`IdentifierWorkflow`)

Each workflow:
- Detects specific subtypes within its domain
- Routes to appropriate clustering strategy
- Generates workflow-specific fingerprints
- Provides subtype-specific correctors

---

### 1. Text Workflow (`StringWorkflow`)

**Purpose**: Handle all text/string data types

**Supported Subtypes** (16+):
- **Structured**: `email`, `phone`, `url`, `ip_address`, `uuid`, `zipcode`, `ssn`, `boolean`
- **Location**: `name`, `company`, `address`, `location`, `state`, `country`
- **Other**: `username`, `file_path`, `product_title`, `job_title`
- **Fallback**: `generic`

**Detection Logic**:
```python
def detect_subtype(data, column_name):
    # Priority order for validation:
    priority_order = [
        "email", "uuid", "ip_address", "url", "phone", 
        "zipcode", "boolean"
    ]
    
    # Try each validator in priority order
    for subtype in priority_order:
        validator = get_validator(subtype)
        if validator:
            ratio = validator.get_pattern_match_ratio(data)
            if ratio >= 0.7:
                return subtype, ratio
    
    # Fallback to generic
    return "generic", 0.5
```

**Clustering Modes**:
- **Strict Mode** (for email, phone, url, etc.):
  - Uses dedicated validator engines
  - Deterministic validation
  - Example: EmailEngine validates email format strictly

- **Lenient Mode** (for name, company, address, etc.):
  - Accepts most values
  - Only rejects: null, empty, gibberish, reserved words
  - Example: "John Doe" → good, "asdf" → bad

**Example Values**:

| Subtype | Good Examples | Bad Examples |
|---------|--------------|--------------|
| email | `user@example.com`, `test.email@domain.co.uk` | `invalid@`, `notanemail`, `user@` |
| phone | `(555) 123-4567`, `+1-555-123-4567`, `5551234567` | `123`, `abc-def-ghij`, `555-123` |
| url | `https://example.com`, `www.site.org/path` | `not a url`, `http://`, `ftp://invalid` |
| name | `John Doe`, `Mary Jane Smith`, `O'Brien` | `null`, `test`, `asdf`, `12345` |
| company | `Acme Corp`, `Microsoft Inc.`, `ABC Industries` | `undefined`, `placeholder`, `xxx` |
| state | `California`, `NY`, `Texas` | `invalid`, `XX`, `test state` |
| country | `United States`, `USA`, `Canada` | `null`, `unknown`, `test` |

---

### 2. Numeric Workflow (`NumericWorkflow`)

**Purpose**: Handle numeric data with semantic constraints

**Supported Subtypes** (14):
- **Semantic**: `age`, `year`, `rating`, `percentage`, `temperature`
- **Geographic**: `latitude`, `longitude`
- **Financial**: `salary`, `amount`
- **Other**: `count`, `phone_numeric`, `zipcode_numeric`, `numeric_id`
- **Fallback**: `generic_numeric`

**Semantic Constraints**:
```python
SEMANTIC_CONSTRAINTS = {
    "age": {"min": 0, "max": 120, "type": "integer"},
    "rating": {"min": 0, "max": 10, "type": "float"},
    "year": {"min": 1900, "max": 2100, "type": "integer"},
    "latitude": {"min": -90, "max": 90, "type": "float"},
    "longitude": {"min": -180, "max": 180, "type": "float"},
    "percentage": {"min": 0, "max": 100, "type": "float"},
    "salary": {"min": 0, "type": "float"},  # No max
    "amount": {"min": 0, "type": "float"},   # No max
}
```

**Detection Logic**:
```python
def detect_subtype(data, column_name):
    # Parse all values as numeric
    parsed_data = [parse_numeric(v) for v in data]
    
    # Analyze statistics
    min_val = min(parsed_data)
    max_val = max(parsed_data)
    is_integer = all(v == int(v) for v in parsed_data)
    
    # Check against semantic constraints
    for subtype, constraints in SEMANTIC_CONSTRAINTS.items():
        if min_val >= constraints["min"] and max_val <= constraints["max"]:
            if constraints["type"] == "integer" and is_integer:
                return subtype, 0.7
            elif constraints["type"] == "float":
                return subtype, 0.6
    
    return "generic_numeric", 0.5
```

**Parsing Logic**:
- Handles currency: `$150,000` → `150000.0`
- Handles European decimals: `4,9` → `4.9`
- Handles thousand separators: `1,000,000` → `1000000.0`
- Handles European thousands: `1.000.000,50` → `1000000.50`

**Clustering**:
- **Semantic Types** (age, rating, year): Uses bounds + IQR
- **Generic Types** (salary, amount): Uses IsolationForest + IQR + Z-score ensemble

**Example Values**:

| Subtype | Good Examples | Bad Examples |
|---------|--------------|--------------|
| age | `25`, `0`, `120` | `-5`, `150`, `abc`, `25.5` |
| rating | `4.5`, `0`, `10`, `7.2` | `-1`, `11`, `abc`, `15` |
| year | `2023`, `1990`, `2050` | `1800`, `2200`, `abc`, `99` |
| salary | `50000`, `150000.50`, `$75,000` | `-1000`, `abc`, `null` |
| amount | `99.99`, `$1,234.56`, `1000000` | `-50`, `invalid`, `NaN` |
| latitude | `40.7128`, `-90.0`, `0.0` | `91`, `-91`, `abc` |
| longitude | `-74.0060`, `180.0`, `-180.0` | `181`, `-181`, `xyz` |

---

### 3. DateTime Workflow (`DateTimeWorkflow`)

**Purpose**: Handle date and datetime data

**Supported Subtypes** (3):
- `date` - Date only (no time component)
- `datetime` - Date + time
- `generic` - Fallback

**Format Patterns Supported**:
```python
FORMAT_PATTERNS = [
    # ISO formats
    (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "%Y-%m-%dT%H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
    
    # US formats
    (r"^\d{1,2}/\d{1,2}/\d{4}$", "%m/%d/%Y"),
    (r"^\d{1,2}/\d{1,2}/\d{2}$", "%m/%d/%y"),
    
    # European formats
    (r"^\d{1,2}-\d{1,2}-\d{4}$", "%d-%m-%Y"),
    (r"^\d{1,2}\.\d{1,2}\.\d{4}$", "%d.%m.%Y"),
    
    # Other
    (r"^\d{8}$", "%Y%m%d"),
    (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),
]
```

**Detection Logic**:
```python
def detect_subtype(data, column_name):
    str_data = [str(v).strip() for v in data if v]
    
    # Check for time component
    has_time = any(":" in s for s in str_data)
    
    if has_time:
        return "datetime", 0.8
    else:
        return "date", 0.8
```

**Clustering**:
- **Key Feature**: ALL valid datetime formats go to `good_data`
- Detects majority format for standardization during correction
- Validates date components (month 1-12, day 1-31, year 1900-2100)

**Example Values**:

| Subtype | Good Examples | Bad Examples |
|---------|--------------|--------------|
| date | `2023-12-25`, `12/25/2023`, `25-12-2023`, `20231225` | `2023-13-45`, `invalid`, `12/32/2023` |
| datetime | `2023-12-25T10:30:00`, `2023-12-25 10:30:00`, `12/25/2023 10:30 AM` | `2023-13-45T25:99:99`, `not a date` |

---

### 4. Identifier Workflow (`IdentifierWorkflow`)

**Purpose**: Handle ID/identifier data with pattern-based clustering

**Supported Subtypes** (3):
- `pattern_id` - Patterned IDs (e.g., `ABC-1234`, `EMP-0001`)
- `numeric_id` - Pure numeric IDs (e.g., `12345`)
- `generic` - Fallback

**Detection Logic**:
```python
def detect_subtype(data, column_name):
    str_data = [str(v).strip() for v in data if v]
    
    # Check if purely numeric
    numeric_count = sum(1 for s in str_data if s.isdigit())
    if numeric_count / len(str_data) > 0.9:
        return "numeric_id", 0.8
    
    # Check for pattern structure
    has_pattern = any(
        re.search(r"[A-Za-z]+[-_][0-9]+|[0-9]+[-_][A-Za-z]+", s)
        for s in str_data
    )
    if has_pattern:
        return "pattern_id", 0.8
    
    return "generic", 0.5
```

**Clustering Logic**:
- **Pattern Fingerprinting**: Converts values to pattern signatures
  - `"ABC-1234"` → `"A-9"`
  - `"EMP_00123"` → `"A_9"`
  - `"12345"` → `"9"`
- **Majority Pattern Detection**: Finds patterns with >10% occurrence
- **Validation**: Values matching majority pattern → good, others → bad

**Example Values**:

| Subtype | Good Examples | Bad Examples |
|---------|--------------|--------------|
| pattern_id | `ABC-1234`, `EMP_00123`, `SKU-98765` | `ABC1234`, `invalid`, `123-ABC-456` |
| numeric_id | `12345`, `00001`, `987654321` | `ABC123`, `12-34-56`, `invalid` |

---

## Subworkflows & Methods

### Clustering Strategy Mapping

The system uses a **strategy selector** to route workflow/subtype combinations to appropriate clusterers:

```python
STRATEGY_MAP = {
    # NUMERIC WORKFLOW
    "age": ("numeric.semantic", {"min": 0, "max": 120, "type": "integer"}),
    "rating": ("numeric.semantic", {"min": 0, "max": 10}),
    "year": ("numeric.semantic", {"min": 1900, "max": 2100, "type": "integer"}),
    "salary": ("numeric.generic", {}),
    "amount": ("numeric.generic", {}),
    "generic_numeric": ("numeric.generic", {}),
    
    # STRING WORKFLOW
    "email": ("string.validator", {"engine": "email"}),
    "phone": ("string.validator", {"engine": "phone"}),
    "url": ("string.validator", {"engine": "url"}),
    "name": ("string.freetext", {}),
    "company": ("string.freetext", {}),
    "state": ("string.categorical", {}),
    "country": ("string.categorical", {}),
    "generic": ("string.freetext", {}),
    
    # DATETIME WORKFLOW
    "date": ("datetime.format", {}),
    "datetime": ("datetime.format", {}),
    
    # IDENTIFIER WORKFLOW
    "pattern_id": ("identifier.pattern", {}),
    "numeric_id": ("identifier.pattern", {}),
}
```

### Clustering Methods

#### 1. Validator-Based Clustering (`ValidatorStringClusterer`)

**Used For**: `email`, `phone`, `url`, `uuid`, `ip_address`, `zipcode`, `boolean`, `ssn`

**Method**: `validator_{engine_name}`

**Logic**:
```python
def cluster(data, indices, column_name):
    engine = get_validator_engine(subtype)  # e.g., EmailEngine
    
    for value, idx in zip(data, indices):
        is_valid, confidence = engine.validate(value)
        
        if is_valid and confidence >= 0.5:
            good_data.append(value)
        else:
            bad_data.append(value)
    
    # Phase 2: Format consistency
    # - Email: Enforce lowercase
    # - Phone: Enforce majority format
    
    return ClusteringResult(good_data, bad_data, fingerprint)
```

**Fingerprint Structure**:
```json
{
    "workflow": "string",
    "method": "validator",
    "engine": "email",
    "sample_size": 100,
    "properties": {
        "avg_length": 25,
        "min_length": 10,
        "max_length": 50,
        "avg_confidence": 0.95
    },
    "correction_hints": {
        "expected_case": "lowercase",
        "expected_format": "XXX-XXX-XXXX"  // for phone
    }
}
```

**Example**:
- Input: `["user@example.com", "USER@EXAMPLE.COM", "invalid@", "test@domain.com"]`
- Good: `["user@example.com", "test@domain.com"]` (lowercase, valid format)
- Bad: `["USER@EXAMPLE.COM", "invalid@"]` (uppercase needs correction, invalid format)

---

#### 2. Categorical Clustering (`CategoricalStringClusterer`)

**Used For**: `state`, `country`, `city` (if cardinality < 0.3)

**Method**: `categorical_frequency_fuzzy`

**Logic**:
```python
def cluster(data, indices, column_name):
    # Step 1: Profile column
    profile = profile_column(data)
    # - Calculate cardinality (unique / total)
    # - Detect case patterns (upper/lower/title)
    # - Analyze length statistics
    
    # Step 2: Build reference set
    reference_set = build_reference_set(data, profile)
    # - Get frequent values (min_frequency threshold)
    # - Filter typos (80-99% similar values)
    
    # Step 3: Classify each value
    for value in data:
        if value in reference_set:
            good_data.append(value)  # Exact match
        else:
            # Fuzzy match
            best_match = rapidfuzz.process.extractOne(
                value, reference_set, scorer=fuzz.ratio
            )
            
            if best_match[1] >= similarity_threshold (85):
                bad_data.append(value)  # Typo - needs correction
            else:
                bad_data.append(value)  # Unknown value
    
    return ClusteringResult(good_data, bad_data, fingerprint)
```

**Fingerprint Structure**:
```json
{
    "workflow": "string",
    "method": "categorical_frequency_fuzzy",
    "reference_values": ["California", "New York", "Texas", "Florida"],
    "reference_frequencies": {
        "California": 150,
        "New York": 120,
        "Texas": 100,
        "Florida": 80
    },
    "similarity_threshold": 85,
    "properties": {
        "is_categorical": true,
        "cardinality": 0.15,
        "case_style": "title",
        "case_consistency": 0.95
    },
    "correction_hints": {
        "expected_case": "title",
        "use_fuzzy_matching": true,
        "similarity_threshold": 85
    }
}
```

**Example**:
- Input: `["California", "california", "Californa", "Texas", "New York", "invalid"]`
- Reference Set: `{"California", "Texas", "New York"}` (from frequency analysis)
- Good: `["California", "Texas", "New York"]` (exact matches)
- Bad: `["california", "Californa", "invalid"]` (case mismatch, typo, unknown)

---

#### 3. FreeText Clustering (`FreeTextStringClusterer`)

**Used For**: `name`, `company`, `address`, `job_title`, `notes`, `description`, `generic`

**Method**: `freetext_lenient`

**Logic**:
```python
def cluster(data, indices, column_name):
    RESERVED_WORDS = {
        "null", "nan", "none", "undefined", "nil",
        "n/a", "na", "tbd", "todo", "placeholder",
        "invalid", "unknown", "test", "testing",
        "asdf", "qwerty", "xxx", "zzz", "abc"
    }
    
    for value, idx in zip(data, indices):
        is_valid, reason = validate_freetext(value)
        
        if is_valid:
            good_data.append(value)
        else:
            bad_data.append(value)  # reason: reserved_word, too_short, etc.
    
    return ClusteringResult(good_data, bad_data, fingerprint)
```

**Validation Rules**:
- ✅ Accept: Non-empty, length >= 2, has some letters
- ❌ Reject: Null, empty, reserved words, too short, low alpha ratio, gibberish patterns

**Fingerprint Structure**:
```json
{
    "workflow": "string",
    "method": "freetext",
    "properties": {
        "avg_length": 15,
        "min_length": 3,
        "max_length": 50,
        "dominant_case": "title",
        "case_distribution": {"title": 80, "mixed": 15, "upper": 5}
    },
    "correction_hints": {
        "mode": "lenient",
        "expected_case": "title",
        "allow_mixed_case": true
    }
}
```

**Example**:
- Input: `["John Doe", "Mary Jane", "null", "test user", "asdf", "ABC Corp"]`
- Good: `["John Doe", "Mary Jane", "ABC Corp"]` (valid text)
- Bad: `["null", "test user", "asdf"]` (reserved word, starts with reserved, gibberish)

---

#### 4. Semantic Numeric Clustering (`SemanticNumericClusterer`)

**Used For**: `age`, `rating`, `year`, `latitude`, `longitude`, `percentage`, `temperature`

**Method**: `semantic_iqr`

**Logic**:
```python
def cluster(data, indices, column_name):
    # Parse all values
    parsed_values = [parse_numeric(v) for v in data]
    
    # Calculate IQR bounds
    q1, q3 = np.percentile(parsed_values, [25, 75])
    iqr = q3 - q1
    iqr_lower = q1 - 1.5 * iqr
    iqr_upper = q3 + 1.5 * iqr
    
    for value, idx in zip(data, indices):
        parsed = parse_numeric(value)
        
        # Check semantic bounds
        if parsed < min_val or parsed > max_val:
            bad_data.append(value)
        # Check IQR outliers (if enabled)
        elif parsed < iqr_lower or parsed > iqr_upper:
            bad_data.append(value)
        else:
            good_data.append(value)
    
    return ClusteringResult(good_data, bad_data, fingerprint)
```

**Fingerprint Structure**:
```json
{
    "workflow": "numeric",
    "method": "semantic",
    "sample_size": 100,
    "properties": {
        "min": 0,
        "max": 120,
        "mean": 45.2,
        "median": 42,
        "std": 15.8,
        "q1": 30,
        "q3": 60,
        "iqr": 30,
        "lower_bound": -15,
        "upper_bound": 105,
        "is_integer": true
    },
    "constraints": {
        "min": 0,
        "max": 120,
        "type": "integer"
    }
}
```

**Example**:
- Input: `[25, 30, 35, 150, -5, 45, 50]` (age column)
- Semantic bounds: 0-120
- IQR bounds: 15-75 (calculated from data)
- Good: `[25, 30, 35, 45, 50]` (within both bounds)
- Bad: `[150, -5]` (outside semantic bounds)

---

#### 5. Generic Numeric Clustering (`GenericNumericClusterer`)

**Used For**: `salary`, `amount`, `count`, `generic_numeric`

**Method**: `isolation_forest_iqr_zscore`

**Logic**:
```python
def cluster(data, indices, column_name):
    # Parse all values
    parsed_values = [parse_numeric(v) for v in data]
    
    # Method 1: IsolationForest
    iso_forest = IsolationForest(contamination=0.1)
    iso_scores = iso_forest.fit_predict(parsed_values.reshape(-1, 1))
    
    # Method 2: IQR
    q1, q3 = np.percentile(parsed_values, [25, 75])
    iqr = q3 - q1
    iqr_lower = q1 - 1.5 * iqr
    iqr_upper = q3 + 1.5 * iqr
    
    # Method 3: Z-score
    mean = np.mean(parsed_values)
    std = np.std(parsed_values)
    z_scores = np.abs((parsed_values - mean) / std)
    
    # Ensemble: Value is bad if flagged by ANY method
    for value, idx, iso, z_score in zip(data, indices, iso_scores, z_scores):
        is_outlier = (
            iso == -1 or  # IsolationForest
            value < iqr_lower or value > iqr_upper or  # IQR
            z_score > 3  # Z-score
        )
        
        if is_outlier:
            bad_data.append(value)
        else:
            good_data.append(value)
    
    return ClusteringResult(good_data, bad_data, fingerprint)
```

**Example**:
- Input: `[50000, 55000, 60000, 65000, 70000, 200000, 75000]` (salary)
- IsolationForest: Flags `200000` as outlier
- IQR: Bounds are `[50000, 70000]`, flags `200000`
- Z-score: `200000` has z-score > 3
- Good: `[50000, 55000, 60000, 65000, 70000, 75000]`
- Bad: `[200000]` (outlier)

---

#### 6. Pattern Identifier Clustering (`PatternIdentifierClusterer`)

**Used For**: `pattern_id`, `numeric_id`

**Method**: `pattern_signature`

**Logic**:
```python
def cluster(data, indices, column_name):
    # Convert values to pattern signatures
    pattern_map = {}
    for value in data:
        pattern = value_to_pattern(value)
        # "ABC-1234" → "A-9"
        # "EMP_00123" → "A_9"
        # "12345" → "9"
        pattern_map[value] = pattern
    
    # Find majority pattern(s)
    pattern_counts = Counter(pattern_map.values())
    valid_patterns = {
        p for p, c in pattern_counts.items()
        if c / len(data) >= 0.1  # At least 10%
    }
    
    # Classify
    for value, idx in zip(data, indices):
        pattern = pattern_map[value]
        if pattern in valid_patterns:
            good_data.append(value)
        else:
            bad_data.append(value)
    
    return ClusteringResult(good_data, bad_data, fingerprint)
```

**Fingerprint Structure**:
```json
{
    "workflow": "identifier",
    "method": "pattern",
    "majority_pattern": "A-9",
    "pattern_counts": {
        "A-9": 150,
        "9": 20,
        "A_9": 10
    }
}
```

**Example**:
- Input: `["ABC-1234", "DEF-5678", "ABC1234", "XYZ-9999", "invalid"]`
- Patterns: `["A-9", "A-9", "A9", "A-9", "mixed"]`
- Majority: `"A-9"` (appears 3 times, >10% threshold)
- Good: `["ABC-1234", "DEF-5678", "XYZ-9999"]` (match pattern)
- Bad: `["ABC1234", "invalid"]` (different pattern)

---

#### 7. Format DateTime Clustering (`FormatDateTimeClusterer`)

**Used For**: `date`, `datetime`

**Method**: `format_parsing`

**Logic**:
```python
def cluster(data, indices, column_name):
    format_counts = Counter()
    
    for value, idx in zip(data, indices):
        # Try to parse with multiple formats
        parsed, format_str = parse_datetime(value)
        
        if parsed:
            good_data.append(value)
            if format_str:
                format_counts[format_str] += 1
        else:
            bad_data.append(value)
    
    # Detect majority format
    majority_format = format_counts.most_common(1)[0][0] if format_counts else None
    
    return ClusteringResult(good_data, bad_data, fingerprint)
```

**Fingerprint Structure**:
```json
{
    "workflow": "datetime",
    "method": "format",
    "majority_format": "%Y-%m-%d",
    "format_counts": {
        "%Y-%m-%d": 80,
        "%m/%d/%Y": 15,
        "%d-%m-%Y": 5
    }
}
```

**Example**:
- Input: `["2023-12-25", "12/25/2023", "25-12-2023", "invalid", "2023-13-45"]`
- Good: `["2023-12-25", "12/25/2023", "25-12-2023"]` (valid formats)
- Bad: `["invalid", "2023-13-45"]` (invalid format, invalid date components)
- Majority format: `"%Y-%m-%d"` (used for standardization)

---

## Column Identification Logic

### Complete Flow: Column → Workflow → Subtype → Method

```
Column: "user_email"
├─ Step 1: Cache Check
│  └─ Not found → continue
│
├─ Step 2: Content Pattern Analysis
│  ├─ Sample: ["user@example.com", "test@domain.org", "invalid"]
│  ├─ Pattern: email (regex match)
│  ├─ Match ratio: 2/3 = 0.67
│  └─ Threshold: 0.7 → Not strong enough, continue
│
├─ Step 3: Heuristic Rules
│  ├─ Pattern: "*email*"
│  ├─ Match: "user_email" matches "*email*"
│  └─ Result: text/email (confidence: 0.9)
│
└─ Step 4: Workflow Routing
   └─ StringWorkflow.cluster_v2()
      ├─ Subtype: email
      ├─ Strategy: string.validator (engine: email)
      ├─ Clusterer: ValidatorStringClusterer
      ├─ Method: validator_email
      └─ Output: good_data, bad_data, fingerprint
```

### Detailed Example: Numeric Column

```
Column: "employee_age"
├─ Step 1: Cache Check
│  └─ Not found → continue
│
├─ Step 2: Content Pattern Analysis
│  ├─ Sample: [25, 30, 35, 150, -5]
│  ├─ Pattern: numeric (80% parseable)
│  ├─ Match ratio: 0.8
│  └─ Result: numeric/generic_numeric (confidence: 0.64)
│     └─ But continue to heuristics for more specific match
│
├─ Step 3: Heuristic Rules
│  ├─ Pattern: "*age*"
│  ├─ Match: "employee_age" matches "*age*"
│  └─ Result: numeric/age (confidence: 0.9) ← SELECTED
│
└─ Step 4: Workflow Routing
   └─ NumericWorkflow.cluster_v2()
      ├─ Subtype: age
      ├─ Strategy: numeric.semantic (min: 0, max: 120, type: integer)
      ├─ Clusterer: SemanticNumericClusterer
      ├─ Method: semantic_iqr
      ├─ Validation:
      │  ├─ 25: ✅ (0 <= 25 <= 120, integer)
      │  ├─ 30: ✅ (0 <= 30 <= 120, integer)
      │  ├─ 35: ✅ (0 <= 35 <= 120, integer)
      │  ├─ 150: ❌ (150 > 120) → bad
      │  └─ -5: ❌ (-5 < 0) → bad
      └─ Output:
         ├─ good_data: [25, 30, 35]
         ├─ bad_data: [150, -5]
         └─ fingerprint: {method: "semantic", constraints: {min: 0, max: 120}}
```

### Decision Tree for Column Identification

```
START: Column "column_name" with sample_data
│
├─ Cache Hit?
│  └─ YES → Return cached (workflow, subtype)
│
└─ NO → Content Pattern Analysis
   │
   ├─ Strong Pattern Match? (confidence >= 0.6, subtype not generic)
   │  └─ YES → Return (workflow, subtype) from pattern
   │
   └─ NO → Heuristic Rules
      │
      ├─ Heuristic Match?
      │  └─ YES → Return (workflow, subtype) from heuristic
      │
      └─ NO → Generic Fallback
         │
         ├─ Mostly Numeric? (>80% parseable)
         │  └─ YES → numeric/generic_numeric
         │
         ├─ Low Alpha Ratio? (<50% letters in >70% values)
         │  └─ YES → identifier/pattern_id
         │
         └─ NO → text/generic
```

### Key Identification Rules

1. **Content Over Name**: Data patterns override column names
   - `"ip_login"` with IP addresses → `text/ip_address` (not `text/username`)
   - `"last_login"` with datetimes → `datetime/datetime` (not `text/generic`)

2. **Priority Order Matters**:
   - Pattern analysis checks email before phone (email has higher priority)
   - Heuristic rules check city before address (city has lower priority number)

3. **Confidence Thresholds**:
   - Pattern match: >= 0.6 confidence
   - Heuristic match: 0.9 confidence (default)
   - Generic fallback: 0.3-0.7 confidence

4. **Generic Fallbacks**:
   - Every workflow has a `generic` subtype
   - Used when no specific match found
   - Still provides clustering and correction capabilities

---

## Clustering Strategies

### Strategy Selection Logic

The `strategy_selector.py` maps workflow/subtype to clusterer:

```python
def get_clusterer(workflow: str, subtype: str) -> BaseClusterer:
    # Look up in STRATEGY_MAP
    if subtype in STRATEGY_MAP:
        strategy_path, config = STRATEGY_MAP[subtype]
    else:
        # Fallback to generic
        fallback_key = f"generic_{workflow}"
        strategy_path, config = STRATEGY_MAP.get(fallback_key, ("string.generic", {}))
    
    # Load clusterer dynamically
    clusterer = _load_clusterer(strategy_path, config)
    return clusterer
```

### Dynamic Routing (Future Enhancement)

Some subtypes can be dynamically routed based on data characteristics:

```python
# Example: city column
if subtype == "city":
    # Check cardinality
    cardinality = unique_count / total_count
    
    if cardinality < 0.3:
        # Low cardinality → categorical
        clusterer = CategoricalStringClusterer()
    else:
        # High cardinality → freetext
        clusterer = FreeTextStringClusterer()
```

---

## Correction Engine

### Correction Flow

```
Bad Data Value
    │
    ├─ Get Corrector for subtype
    │  └─ CorrectorRegistry.get(subtype)
    │
    ├─ Load Fingerprint
    │  └─ Contains: reference_values, patterns, bounds, properties
    │
    ├─ Learn Patterns from Fingerprint
    │  └─ Extract: expected_case, format, bounds, reference_set
    │
    └─ Apply Correction
       ├─ Text Corrector:
       │  ├─ Fuzzy match against reference_values
       │  ├─ Case correction (lowercase for email)
       │  └─ Format standardization
       │
       ├─ Numeric Corrector:
       │  ├─ Bounds clamping (if outside bounds)
       │  ├─ Outlier adjustment (towards mean/median)
       │  └─ Format standardization
       │
       └─ DateTime Corrector:
          ├─ Format conversion (to majority_format)
          └─ Component validation
```

### Correction Result

```python
CorrectionResult(
    original_value: Any,      # "california"
    corrected_value: Any,      # "California"
    status: CorrectionStatus,  # CORRECTED, UNCHANGED, REJECTED, SKIPPED
    confidence: float,        # 0.0 - 1.0
    changes_made: List[str],   # ["case_normalization"]
    details: Dict              # Additional metadata
)
```

### Example Corrections

| Original | Corrected | Method | Reason |
|----------|-----------|--------|--------|
| `california` | `California` | Fuzzy match | Case normalization to title case |
| `USER@EXAMPLE.COM` | `user@example.com` | Format fix | Email lowercase enforcement |
| `(555) 123-4567` | `555-123-4567` | Format standardization | Phone format to majority |
| `150` (age) | `120` | Bounds clamping | Clamp to max age (120) |
| `12/25/2023` | `2023-12-25` | Format conversion | Convert to ISO format |

---

## LLM Integration

### LLM Reshuffler

**Purpose**: Use LLM to generate validation patterns and promote false negatives from bad to good

**Flow**:
```
1. After initial clustering (good/bad split)
2. Get LLM patterns for good data
   ├─ Check cache first
   ├─ If cache miss → Call LLM
   │  ├─ Generate regex patterns
   │  └─ Generate numeric bounds (if generic numeric)
   └─ Save to cache
3. Apply patterns to bad data
   ├─ If matches pattern → promote to good
   └─ If doesn't match → keep in bad
```

**LLM Prompt Template**:
```
You are a data quality expert. Analyze these VALID data samples.

Column: {column_name}
Data Type: {workflow}/{subtype}
Constraints: {constraints}

VALID DATA SAMPLES:
{samples}

TASKS:
1. PATTERNS: Generate 2-5 regex patterns that match all valid data.
2. BOUNDS (only if numeric and subtype is 'generic'):
   - Suggest min/max bounds based on column name and data
   - Return null for pre-defined types (age, percentage, etc.)
```

**Example**:
- Good data: `["user@example.com", "test@domain.org", "admin@site.com"]`
- LLM generates patterns: `["^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"]`
- Bad data: `["user@example", "invalid@", "USER@EXAMPLE.COM"]`
- Apply patterns:
  - `"user@example"` → ❌ (no TLD) → stays bad
  - `"invalid@"` → ❌ (invalid format) → stays bad
  - `"USER@EXAMPLE.COM"` → ✅ (matches pattern) → **promoted to good**

### LLM Caching

- **Unified Cache**: Uses `db_manager` for pattern caching
- **Fingerprint-based**: Cache key includes workflow, subtype, fingerprint hash
- **Column Aliases**: Supports column name aliases (same patterns for similar columns)
- **Cost Tracking**: Logs LLM calls, tokens used, cache hits/misses

---

## Complete Flow Examples

### Example 1: Email Column

```
Input Column: "user_email"
Sample Data: ["user@example.com", "USER@EXAMPLE.COM", "invalid@", "test@domain.org"]

┌─────────────────────────────────────────────────────────────┐
│ DETECTION PHASE                                              │
└─────────────────────────────────────────────────────────────┘
1. Cache Check → Not found
2. Pattern Analysis:
   - email pattern: 2/4 = 0.5 match (below 0.7 threshold)
   - Continue to heuristics
3. Heuristic Rules:
   - "*email*" matches "user_email"
   - Result: text/email (confidence: 0.9)
4. Cache result

┌─────────────────────────────────────────────────────────────┐
│ CLUSTERING PHASE                                             │
└─────────────────────────────────────────────────────────────┘
1. Workflow: StringWorkflow
2. Subtype: email
3. Strategy: string.validator (engine: email)
4. Clusterer: ValidatorStringClusterer
5. Validation:
   - "user@example.com" → ✅ valid, lowercase → good
   - "USER@EXAMPLE.COM" → ✅ valid format, but uppercase → bad (needs correction)
   - "invalid@" → ❌ invalid format → bad
   - "test@domain.org" → ✅ valid, lowercase → good
6. Fingerprint:
   {
     "workflow": "string",
     "method": "validator_email",
     "properties": {
       "avg_length": 20,
       "expected_case": "lowercase"
     },
     "correction_hints": {
       "expected_case": "lowercase"
     }
   }

┌─────────────────────────────────────────────────────────────┐
│ LLM RESHUFFLING (if enabled)                                 │
└─────────────────────────────────────────────────────────────┘
1. Get patterns from cache/LLM:
   - Pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
2. Apply to bad data:
   - "USER@EXAMPLE.COM" → ✅ matches pattern → promoted to good
   - "invalid@" → ❌ doesn't match → stays bad
3. Final good: ["user@example.com", "test@domain.org", "USER@EXAMPLE.COM"]
4. Final bad: ["invalid@"]

┌─────────────────────────────────────────────────────────────┐
│ CORRECTION PHASE                                             │
└─────────────────────────────────────────────────────────────┘
1. Corrector: TextCorrector (for email subtype)
2. Correct "USER@EXAMPLE.COM":
   - Original: "USER@EXAMPLE.COM"
   - Corrected: "user@example.com"
   - Status: CORRECTED
   - Changes: ["case_normalization"]
3. Correct "invalid@":
   - Original: "invalid@"
   - Corrected: "invalid@" (unchanged - uncorrectable)
   - Status: REJECTED
```

### Example 2: Age Column

```
Input Column: "employee_age"
Sample Data: [25, 30, 35, 150, -5, 45]

┌─────────────────────────────────────────────────────────────┐
│ DETECTION PHASE                                              │
└─────────────────────────────────────────────────────────────┘
1. Cache Check → Not found
2. Pattern Analysis:
   - numeric pattern: 6/6 = 1.0 match
   - Result: numeric/generic_numeric (confidence: 0.8)
   - But continue to heuristics for more specific match
3. Heuristic Rules:
   - "*age*" matches "employee_age"
   - Result: numeric/age (confidence: 0.9) ← SELECTED
4. Cache result

┌─────────────────────────────────────────────────────────────┐
│ CLUSTERING PHASE                                             │
└─────────────────────────────────────────────────────────────┘
1. Workflow: NumericWorkflow
2. Subtype: age
3. Strategy: numeric.semantic (min: 0, max: 120, type: integer)
4. Clusterer: SemanticNumericClusterer
5. Validation:
   - 25: ✅ (0 <= 25 <= 120, integer) → good
   - 30: ✅ (0 <= 30 <= 120, integer) → good
   - 35: ✅ (0 <= 35 <= 120, integer) → good
   - 150: ❌ (150 > 120) → bad
   - -5: ❌ (-5 < 0) → bad
   - 45: ✅ (0 <= 45 <= 120, integer) → good
6. IQR Calculation (for additional outlier detection):
   - Q1: 30, Q3: 45, IQR: 15
   - Lower bound: 7.5, Upper bound: 67.5
   - All good values within IQR bounds
7. Fingerprint:
   {
     "workflow": "numeric",
     "method": "semantic",
     "properties": {
       "min": 25,
       "max": 45,
       "mean": 33.75,
       "median": 32.5,
       "std": 8.54,
       "lower_bound": 7.5,
       "upper_bound": 67.5
     },
     "constraints": {
       "min": 0,
       "max": 120,
       "type": "integer"
     }
   }

┌─────────────────────────────────────────────────────────────┐
│ CORRECTION PHASE                                             │
└─────────────────────────────────────────────────────────────┘
1. Corrector: NumericCorrector (for age subtype)
2. Correct 150:
   - Original: 150
   - Corrected: 120 (clamped to max)
   - Status: CORRECTED
   - Changes: ["bounds_clamping"]
3. Correct -5:
   - Original: -5
   - Corrected: 0 (clamped to min)
   - Status: CORRECTED
   - Changes: ["bounds_clamping"]
```

### Example 3: State Column (Categorical)

```
Input Column: "state"
Sample Data: ["California", "california", "Californa", "Texas", "New York", "invalid"]

┌─────────────────────────────────────────────────────────────┐
│ DETECTION PHASE                                              │
└─────────────────────────────────────────────────────────────┘
1. Cache Check → Not found
2. Pattern Analysis:
   - No strong pattern match → continue
3. Heuristic Rules:
   - "*state*" matches "state"
   - Result: text/state (confidence: 0.9)
4. Cache result

┌─────────────────────────────────────────────────────────────┐
│ CLUSTERING PHASE                                             │
└─────────────────────────────────────────────────────────────┘
1. Workflow: StringWorkflow
2. Subtype: state
3. Strategy: string.categorical
4. Clusterer: CategoricalStringClusterer
5. Profile Column:
   - Total: 6
   - Unique: 5
   - Cardinality: 5/6 = 0.83 (high - but still categorical)
6. Build Reference Set:
   - Frequent values: ["California", "Texas", "New York"] (each appears once)
   - Min frequency: 1 (relaxed for high cardinality)
   - Filter typos: "Californa" is 93% similar to "California" → filtered out
   - Reference set: {"California", "Texas", "New York"}
7. Classification:
   - "California" → ✅ exact match → good
   - "california" → ❌ case mismatch → bad (similarity: 95%)
   - "Californa" → ❌ typo → bad (similarity: 93%, but filtered from reference)
   - "Texas" → ✅ exact match → good
   - "New York" → ✅ exact match → good
   - "invalid" → ❌ unknown → bad (similarity: 0%)
8. Fingerprint:
   {
     "workflow": "string",
     "method": "categorical_frequency_fuzzy",
     "reference_values": ["California", "Texas", "New York"],
     "similarity_threshold": 85,
     "properties": {
       "is_categorical": true,
       "cardinality": 0.83,
       "case_style": "title",
       "case_consistency": 0.5
     }
   }

┌─────────────────────────────────────────────────────────────┐
│ CORRECTION PHASE                                             │
└─────────────────────────────────────────────────────────────┘
1. Corrector: TextCorrector (for state subtype)
2. Correct "california":
   - Original: "california"
   - Fuzzy match: "California" (similarity: 95%)
   - Corrected: "California"
   - Status: CORRECTED
   - Changes: ["case_normalization", "fuzzy_match"]
3. Correct "Californa":
   - Original: "Californa"
   - Fuzzy match: "California" (similarity: 93%)
   - Corrected: "California"
   - Status: CORRECTED
   - Changes: ["typo_correction", "fuzzy_match"]
4. Correct "invalid":
   - Original: "invalid"
   - Fuzzy match: None (similarity < 60%)
   - Corrected: "invalid" (unchanged)
   - Status: REJECTED
```

---

## Summary

### Key Takeaways

1. **Content-First Detection**: Data patterns analyzed before column names for robustness
2. **Multi-Layer Validation**: Pattern → Heuristic → Generic fallback
3. **Workflow-Based Architecture**: 4 workflows (text, numeric, datetime, identifier) with 35+ subtypes
4. **ML-Based Clustering**: Uses IsolationForest, DBSCAN, IQR, Z-score for anomaly detection
5. **Fingerprint-Driven Correction**: Correctors learn from good data patterns
6. **Optional LLM Verification**: LLM reshuffler for edge cases, with caching for cost efficiency
7. **Production-Ready**: Caching, error handling, logging, database integration

### Architecture Strengths

- **Extensible**: Plugin architecture via registries
- **Robust**: Multiple fallbacks at every layer
- **Efficient**: Caching at detection, clustering, and LLM levels
- **Maintainable**: Centralized LLM client, clear separation of concerns
- **Scalable**: Can handle large datasets with efficient clustering algorithms

### Areas for Enhancement (For Planning LLM)

1. **Detection Stability**:
   - Add confidence scoring for edge cases
   - Implement ensemble detection (multiple methods vote)
   - Add detection validation/feedback loop

2. **Clustering Robustness**:
   - Improve handling of mixed data types
   - Add adaptive thresholds based on data distribution
   - Implement confidence intervals for clustering results

3. **Security**:
   - Add input validation/sanitization
   - Implement rate limiting for LLM calls
   - Add audit logging for sensitive data

4. **Additional Workflows/Subtypes**:
   - Currency codes (ISO 4217)
   - Credit card numbers (with Luhn validation)
   - MAC addresses
   - ISBN/ISSN
   - Vehicle identification numbers (VIN)

5. **Enhanced Detection Logic**:
   - Context-aware detection (use other columns as hints)
   - Statistical distribution analysis
   - Domain-specific rules (healthcare, finance, etc.)
   - Multi-column relationship detection

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-27  
**Author**: Comprehensive Backend Analysis
