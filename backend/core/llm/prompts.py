"""
Prompt Templates for LLM Calls
All prompts are centralized here for easy maintenance
"""

from typing import Any, Dict, List, Optional


class PromptTemplates:
    """
    Centralized prompt templates for all LLM operations.
    Modify prompts here to affect entire application.
    """
    
    @staticmethod
    def pattern_generation(samples: List[str], data_type: str) -> str:
        """Generate validation patterns from samples"""
        samples_str = "\n".join(f"  - {s}" for s in samples[:10])
        
        return f"""Analyze these data samples and generate regex validation patterns.

Data Type: {data_type}
Samples:
{samples_str}

Generate regex patterns that would validate this type of data.
Return JSON with:
{{
    "patterns": ["pattern1", "pattern2"],
    "description": "what these patterns validate",
    "strictness": "high/medium/low"
}}

IMPORTANT: Use Python regex syntax (\\g<1> not $1 for backreferences)."""
    
    @staticmethod
    def quality_assessment(
        value: str,
        good_samples: List[str],
        data_type: str
    ) -> str:
        """Assess quality of a single value"""
        samples_str = ", ".join(f'"{s}"' for s in good_samples[:5])
        
        return f"""Assess if this value is valid for the given data type.

Data Type: {data_type}
Value to assess: "{value}"
Examples of GOOD values: {samples_str}

Analyze and return JSON:
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of issues if invalid"],
    "can_correct": true/false
}}"""
    
    @staticmethod
    def correction_suggestion(
        bad_value: str,
        good_samples: List[str],
        fingerprint: Optional[Dict[str, Any]] = None
    ) -> str:
        """Suggest correction for a bad value"""
        samples_str = ", ".join(f'"{s}"' for s in good_samples[:5])
        
        fingerprint_info = ""
        if fingerprint:
            fingerprint_info = f"""
Good data fingerprint:
- Pattern: {fingerprint.get('pattern_signature', 'unknown')}
- Average length: {fingerprint.get('avg_length', 'unknown')}
- Case style: {fingerprint.get('case_style', 'unknown')}
"""
        
        return f"""Suggest a correction for this bad value to match the good data pattern.

Bad value: "{bad_value}"
Examples of GOOD values: {samples_str}
{fingerprint_info}

Return JSON:
{{
    "corrected_value": "the corrected value or null if uncorrectable",
    "confidence": 0.0-1.0,
    "changes_made": ["list of changes"],
    "correctable": true/false
}}

If the value cannot be reasonably corrected, set corrected_value to null and correctable to false."""
    
    @staticmethod
    def semantic_validation(
        value: str,
        data_type: str,
        constraints: Dict[str, Any]
    ) -> str:
        """Validate against semantic constraints"""
        constraints_str = "\n".join(
            f"  - {k}: {v}" for k, v in constraints.items()
        )
        
        return f"""Validate this value against semantic constraints.

Data Type: {data_type}
Value: "{value}"
Constraints:
{constraints_str}

Return JSON:
{{
    "passes": true/false,
    "failed_constraints": ["list of failed constraints"],
    "reason": "explanation if failed"
}}"""
    
    @staticmethod
    def batch_validation(
        values: List[str],
        good_samples: List[str],
        data_type: str
    ) -> str:
        """Validate multiple values at once"""
        values_str = "\n".join(f"  {i}: \"{v}\"" for i, v in enumerate(values[:20]))
        samples_str = ", ".join(f'"{s}"' for s in good_samples[:5])
        
        return f"""Validate these values against the good data pattern.

Data Type: {data_type}
Good examples: {samples_str}

Values to validate:
{values_str}

Return JSON with validation results for each index:
{{
    "results": {{
        "0": {{"valid": true/false, "confidence": 0.0-1.0}},
        "1": {{"valid": true/false, "confidence": 0.0-1.0}},
        ...
    }}
}}"""
