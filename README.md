# Data Anomaly Detector & Correction Tool

A production-grade data quality pipeline for detecting column types, clustering data into good/bad groups, and applying intelligent corrections.

## Features

- **Smart Column Detection**: Heuristic + pattern-based detection (no LLM required)
- **4 Workflows**: Text, Numeric, DateTime, Identifier
- **35+ Subtypes**: Email, phone, URL, age, date, ID patterns, etc.
- **Fingerprint-Based Correction**: Correctors learn from good data patterns
- **Generic Fallbacks**: Every workflow has a fallback for unknown types
- **Centralized LLM**: Single file for all LLM calls (easy to swap providers)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run pipeline
python run_pipeline.py data/sample.csv

# With options
python run_pipeline.py data/sample.csv --no-header --verbose
python run_pipeline.py data/sample.csv --output-dir ./results
```

## Project Structure

```
├── run_pipeline.py          # CLI entry point
├── requirements.txt
├── backend/
│   ├── config/              # Configuration files
│   ├── services/            # Pipeline orchestration
│   └── core/
│       ├── interfaces/      # Abstract base classes
│       ├── detection/       # Column type detection
│       ├── fingerprinting/  # Good data fingerprinting
│       ├── engines/         # Validation engines
│       ├── workflows/       # Data type workflows
│       ├── correction/      # Correction engines
│       └── llm/             # Centralized LLM client
├── data/                    # Sample data & cache
├── output/                  # Generated outputs
└── tests/                   # Test suite
```

## Output Files

- `output/good_n_bad/good_data_{column}.csv` - Valid data
- `output/good_n_bad/bad_data_{column}.csv` - Invalid data
- `output/final/final_output.csv` - Complete data with status
- `output/report/correction_report.json` - Correction details

## Configuration

Copy `.env.example` to `.env` and configure:

```env
GROQ_API_KEY=your_key_here
ENABLE_LLM_VERIFICATION=false
```

## Architecture

1. **Detection Layer**: Heuristics → Pattern Analysis → Cache
2. **Workflow Layer**: Type-specific clustering with fingerprint generation
3. **Correction Layer**: Fingerprint-driven corrections
4. **LLM Layer**: Optional verification (centralized client)

## Bug Fixes Implemented

1. ✅ Correctability check before LLM promotion
2. ✅ Semantic validation before LLM patterns
3. ✅ Priority-ordered heuristics (city before address)
4. ✅ Accept all valid datetime formats
5. ✅ Python regex backreferences (\g<1>)
6. ✅ Preserve IT/HR uppercase abbreviations

## License

MIT
