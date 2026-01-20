# Anomaly Detection Pipeline Architecture

## Overview

```mermaid
flowchart TD
    INPUT[/"CSV Data"/] --> DETECT["Column Type Detection"]
    DETECT --> WORKFLOW{"Workflow Router"}
    
    WORKFLOW --> |numeric| NUM[Numeric Workflow]
    WORKFLOW --> |text/string| STR[String Workflow]
    WORKFLOW --> |datetime| DT[DateTime Workflow]
    WORKFLOW --> |identifier| ID[Identifier Workflow]
    
    NUM --> NUM_OUT["Good/Bad Split"]
    STR --> STR_OUT["Good/Bad Split"]
    DT --> DT_OUT["Good/Bad Split"]
    ID --> ID_OUT["Good/Bad Split"]
    
    STR_OUT --> CORRECT["Correction Engine"]
    NUM_OUT --> CORRECT
    DT_OUT --> CORRECT
    ID_OUT --> CORRECT
    
    CORRECT --> REPORT[/"Reports + Corrected CSV"/]
```

---

## Workflows & Subworkflows

| Workflow | Subworkflow | Clusterer | Subtypes |
|----------|-------------|-----------|----------|
| **numeric** | semantic | `SemanticNumericClusterer` | age, rating, year, lat, long, %, temp |
| **numeric** | generic | `GenericNumericClusterer` | salary, amount, count |
| **string** | validator | `ValidatorStringClusterer` | email, phone, url, uuid, ip, zip, ssn, boolean |
| **string** | categorical | `CategoricalStringClusterer` | state, country |
| **string** | freetext | `FreeTextStringClusterer` | name, company, address, city, username |
| **string** | generic | `GenericStringClusterer` | file_path, product_title |
| **datetime** | format | `FormatDateTimeClusterer` | date, datetime |
| **datetime** | generic | `GenericDateTimeClusterer` | unknown date formats |
| **identifier** | pattern | `PatternIdentifierClusterer` | pattern_id, numeric_id |
| **identifier** | generic | `GenericIdentifierClusterer` | unknown ID patterns |

---

## Numeric Workflow

```mermaid
flowchart TD
    N_IN["Numeric Data"] --> N_ROUTE{"Subtype?"}
    
    N_ROUTE --> |"age, rating, lat..."| SEM["Semantic Clusterer"]
    N_ROUTE --> |"salary, amount"| GEN["Generic Clusterer"]
    
    subgraph Semantic["Semantic Detection"]
        SEM --> |"Check bounds"| BOUNDS{"min ≤ value ≤ max?"}
        BOUNDS --> |Yes| S_GOOD["GOOD"]
        BOUNDS --> |No| S_BAD["BAD"]
    end
    
    subgraph Generic["Generic Detection"]
        GEN --> |1| ISO["Isolation Forest"]
        GEN --> |2| IQR["IQR Bounds"]
        GEN --> |3| ZSCORE["Z-Score"]
        ISO & IQR & ZSCORE --> VOTE{"≥2 agree?"}
        VOTE --> |Yes| G_GOOD["GOOD"]
        VOTE --> |No| G_BAD["BAD"]
    end
```

**Semantic Bounds:**
- age: 0-120 | rating: 0-10 | year: 1900-2100
- latitude: -90 to 90 | longitude: -180 to 180

**Generic Ensemble:** IsolationForest + IQR + Z-score (2/3 voting)

---

## String Workflow

```mermaid
flowchart TD
    S_IN["String Data"] --> S_ROUTE{"Subtype?"}
    
    S_ROUTE --> |"email, phone..."| VAL["Validator"]
    S_ROUTE --> |"state, country"| CAT["Categorical"]
    S_ROUTE --> |"name, city..."| FREE["FreeText"]
    S_ROUTE --> |"file_path"| SGEN["Generic"]
    
    subgraph Validator["Validator Detection"]
        VAL --> REGEX{"Matches regex?"}
        REGEX --> |Yes| V_GOOD["GOOD"]
        REGEX --> |No| V_BAD["BAD"]
    end
    
    subgraph Categorical["Categorical Detection"]
        CAT --> FREQ["Build reference set"]
        FREQ --> FUZZY{"Fuzzy match ≥85%?"}
        FUZZY --> |Exact match| C_GOOD["GOOD"]
        FUZZY --> |Similar| C_BAD["BAD (typo)"]
        FUZZY --> |No match| C_BAD2["BAD"]
    end
    
    subgraph FreeText["FreeText Detection"]
        FREE --> RES{"Reserved word?"}
        RES --> |Yes| F_BAD["BAD"]
        RES --> |No| ALPHA{"Alpha ratio ≥30%?"}
        ALPHA --> |Yes| F_GOOD["GOOD"]
        ALPHA --> |No| F_BAD2["BAD (gibberish)"]
    end
```

**Validators:** email, phone, url, uuid, ip_address, zipcode, ssn, boolean

**Categorical:** Frequency-based with typo filtering (80-99% similarity)

**FreeText:** Lenient - rejects only reserved words + gibberish

---

## DateTime Workflow

```mermaid
flowchart TD
    DT_IN["DateTime Data"] --> DT_PARSE["Parse formats"]
    DT_PARSE --> DT_MAJ{"Majority format?"}
    DT_MAJ --> |Matches| DT_GOOD["GOOD"]
    DT_MAJ --> |Different valid| DT_BAD["BAD (correctable)"]
    DT_MAJ --> |Invalid| DT_REJECT["BAD (rejected)"]
```

**Format Detection:** Identifies majority format (e.g., `%Y-%m-%d`)

---

## Identifier Workflow

```mermaid
flowchart TD
    ID_IN["ID Data"] --> ID_PAT["Extract pattern"]
    ID_PAT --> ID_MAJ{"Matches majority?"}
    ID_MAJ --> |Yes| ID_GOOD["GOOD"]
    ID_MAJ --> |No| ID_BAD["BAD"]
```

**Pattern Signature:** e.g., `AN` for alphanumeric like "C001"

---

## File Structure

```
backend/core/clustering/
├── strategy_selector.py      # Routes subtype → clusterer
├── dynamic_selector.py       # Runtime is_categorical() check
├── base_clusterer.py         # Abstract base class
├── numeric/
│   ├── semantic_clusterer.py # Bounds checking
│   └── generic_clusterer.py  # ML ensemble
├── string/
│   ├── validator_clusterer.py # Regex validators
│   ├── categorical_clusterer.py # Frequency+fuzzy
│   ├── freetext_clusterer.py  # Lenient
│   └── generic_clusterer.py   # DBSCAN-based
├── datetime/
│   ├── format_clusterer.py    # Format consistency
│   └── generic_clusterer.py
└── identifier/
    ├── pattern_clusterer.py   # Pattern signature
    └── generic_clusterer.py
```

---

## Detection Logic Summary

| Clusterer | Detection Method | Threshold |
|-----------|------------------|-----------|
| SemanticNumeric | Config bounds (min/max) | Exact |
| GenericNumeric | IQR + Z-score + IsolationForest | 2/3 vote |
| Validator | Regex pattern matching | 100% match |
| Categorical | Frequency + Fuzzy matching | 85% similarity |
| FreeText | Reserved words + Alpha ratio | 30% alpha |
| DateTime | Format consistency | Majority |
| Identifier | Pattern signature | Majority |
