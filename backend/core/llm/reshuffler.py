"""
LLM Reshuffler (Production Grade)
=================================
Uses LLM-generated patterns to reshuffle good/bad data.
Cost-efficient: Uses unified cache, combines pattern+bounds in single call.

Integrates with: backend.database.db_manager
"""

import re
import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field

# Use unified database manager
from backend.database import get_db_manager

logger = logging.getLogger(__name__)


class BoundsInfo(BaseModel):
    """Numeric bounds from LLM."""
    min: Optional[float] = Field(default=None, description="Minimum valid value or null")
    max: Optional[float] = Field(default=None, description="Maximum valid value or null")
    reasoning: str = Field(default="", description="Why these bounds apply")


class PatternBoundsResponse(BaseModel):
    """
    Combined LLM response for pattern + bounds (single call).
    
    Saves cost by getting both in one request.
    """
    patterns: List[str] = Field(
        description="List of regex patterns to validate data"
    )
    description: str = Field(
        description="Brief description of what makes data valid"
    )
    bounds: Optional[BoundsInfo] = Field(
        default=None,
        description="For numeric columns: min/max bounds. Null for non-numeric or pre-defined types."
    )


@dataclass
class ReshuffleResult:
    """Result of reshuffling operation."""
    promoted_to_good: List[Tuple[Any, int]]  # (value, original_index)
    demoted_to_bad: List[Tuple[Any, int]]
    patterns_used: List[str]
    bounds_detected: Optional[Dict[str, Any]]
    from_cache: bool
    tokens_used: int


class LLMReshuffler:
    """
    Production-grade LLM reshuffler with unified caching.
    
    Features:
    - Single LLM call for patterns + bounds
    - Unified cache via db_manager
    - Column alias support (smart name matching)
    - Cost tracking and analytics
    
    Flow:
    1. Check alias → get canonical column name
    2. Check cache for patterns matching fingerprint
    3. If cache miss → call LLM with pattern + bounds request
    4. Save to cache + update aliases
    5. Apply patterns to reshuffle good/bad data
    """
    
    COMBINED_PROMPT_TEMPLATE = """You are a data quality expert. Analyze these VALID data samples.

Column: {column_name}
Data Type: {workflow}/{subtype}
Constraints: {constraints}

VALID DATA SAMPLES:
{samples}

TASKS:
1. PATTERNS: Generate 2-5 regex patterns that match all valid data like these samples.
   - Use regex anchors (^ and $) for complete matching
   - Patterns should MATCH valid data, REJECT invalid/garbage data

2. BOUNDS (only if numeric and subtype is 'generic'):
   - For columns like salary, amount, count, any generic numeric data → suggest min/max bounds
   - take in account the column name while deciding the bounds, for example if sales is column name then bounds should be 0-1000000000 (or even no upper limit)
   - Return null if:
     * Non-numeric data (text, email, etc.)
     * Pre-defined numeric types (age: 0-120, percentage: 0-100, etc.)
     * No natural bounds exist

Current subtype: {subtype}
Is numeric generic (needs bounds): {needs_bounds}
"""

    def __init__(self):
        """Initialize reshuffler with unified db_manager."""
        self._db = get_db_manager()
        self._instructor_client = None
        self._groq_client = None
        self._model = "llama-3.3-70b-versatile"
        logger.info("LLMReshuffler initialized with unified db_manager")
    
    def _get_instructor_client(self):
        """Lazy load instructor client."""
        if self._instructor_client is None:
            try:
                from groq import Groq
                import instructor
                from dotenv import load_dotenv
                
                load_dotenv()
                api_key = os.getenv("GROQ_API_KEY")
                
                if not api_key:
                    raise ValueError("GROQ_API_KEY not found in environment")
                
                self._groq_client = Groq(api_key=api_key)
                self._instructor_client = instructor.patch(self._groq_client)
                logger.info("Instructor client initialized with Groq")
                
            except ImportError as e:
                logger.error(f"Import error: {e}. Install: pip install instructor groq")
                raise
        
        return self._instructor_client
    
    def _needs_llm_bounds(self, workflow: str, subtype: str) -> bool:
        """
        Check if this column type needs LLM-detected bounds.
        
        Returns True only for numeric-generic columns.
        Pre-defined types (age, percentage, etc.) return False.
        """
        if workflow != "numeric":
            return False
        
        # Pre-defined numeric types with known bounds
        PREDEFINED_BOUNDS = {
            "age", "rating", "year", "latitude", "longitude",
            "percentage", "temperature", "score"
        }
        
        return subtype not in PREDEFINED_BOUNDS
    
    def get_patterns_and_bounds(
        self,
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any],
        good_data: List[Any],
        column_name: Optional[str] = None,
    ) -> Tuple[List[str], Optional[Dict[str, Any]], bool, int]:
        """
        Get validation patterns and optional bounds (single cache/LLM call).
        
        Returns:
            Tuple of (patterns, bounds, from_cache, tokens_used)
        """
        # Check for column alias first
        if column_name:
            canonical = self._db.get_alias(column_name)
            if canonical:
                logger.debug(f"Using alias: {column_name} → {canonical}")
                # Could use cached patterns for canonical name
        
        # Check cache
        cached = self._db.get_cached_patterns(workflow, subtype, fingerprint)
        
        if cached:
            logger.debug(f"Cache hit for {workflow}/{subtype}")
            self._db.log_llm_call(
                purpose="pattern_bounds",
                column_name=column_name,
                workflow=workflow,
                subtype=subtype,
                from_cache=True,
            )
            return cached.patterns, cached.bounds, True, 0
        
        # Cache miss - call LLM
        logger.info(f"LLM call for patterns+bounds: {workflow}/{subtype}")
        
        patterns, bounds, tokens = self._generate_patterns_and_bounds_llm(
            workflow, subtype, fingerprint, good_data, column_name
        )
        
        if patterns:
            # Save to cache
            self._db.save_patterns(
                workflow=workflow,
                subtype=subtype,
                fingerprint=fingerprint,
                patterns=patterns,
                bounds=bounds,
                description="",
                column_name=column_name,
                llm_model=self._model,
                tokens_used=tokens,
            )
            
            # Save alias for future lookups
            if column_name:
                fp_hash = self._db.compute_fingerprint_hash(workflow, subtype, fingerprint)
                self._db.save_alias(column_name, column_name, fp_hash)
            
            # Save bounds if detected
            if bounds and column_name:
                self._db.save_bounds(
                    column_name=column_name,
                    min_value=bounds.get("min"),
                    max_value=bounds.get("max"),
                    source="llm",
                    workflow=workflow,
                    subtype=subtype,
                    reasoning=bounds.get("reasoning", ""),
                )
        
        # Log LLM call
        self._db.log_llm_call(
            purpose="pattern_bounds",
            column_name=column_name,
            workflow=workflow,
            subtype=subtype,
            tokens_used=tokens,
            from_cache=False,
            model=self._model,
        )
        
        return patterns, bounds, False, tokens
    
    def _generate_patterns_and_bounds_llm(
        self,
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any],
        good_data: List[Any],
        column_name: Optional[str],
    ) -> Tuple[List[str], Optional[Dict[str, Any]], int]:
        """Generate patterns and bounds using LLM (single call)."""
        try:
            client = self._get_instructor_client()
            
            # Prepare samples (limit to 10)
            samples = [str(v) for v in good_data[:10] if v is not None]
            samples_str = "\n".join(f"  - {s}" for s in samples)
            
            # Prepare constraints
            constraints = fingerprint.get("constraints", {})
            if not constraints and fingerprint.get("properties"):
                constraints = fingerprint["properties"]
            constraints_str = ", ".join(
                f"{k}: {v}" for k, v in constraints.items()
            ) if constraints else "none"
            
            # Check if bounds needed
            needs_bounds = self._needs_llm_bounds(workflow, subtype)
            
            # Build prompt
            prompt = self.COMBINED_PROMPT_TEMPLATE.format(
                column_name=column_name or "unknown",
                workflow=workflow,
                subtype=subtype,
                constraints=constraints_str,
                samples=samples_str,
                needs_bounds="YES - please suggest min/max bounds" if needs_bounds else "NO - return null for bounds",
            )
            
            # Call LLM with instructor for structured output
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "You are a data quality expert. Generate regex patterns and optionally numeric bounds."},
                    {"role": "user", "content": prompt},
                ],
                response_model=PatternBoundsResponse,
                max_retries=2,
            )
            
            # Validate patterns are valid regex
            valid_patterns = []
            for p in response.patterns:
                try:
                    re.compile(p)
                    valid_patterns.append(p)
                except re.error:
                    logger.warning(f"Invalid regex from LLM: {p}")
            
            # Extract bounds
            bounds = None
            if response.bounds and needs_bounds:
                bounds = {
                    "min": response.bounds.min,
                    "max": response.bounds.max,
                    "reasoning": response.bounds.reasoning,
                    "source": "llm",
                }
            
            # Estimate tokens
            tokens = len(prompt.split()) + len(str(response.patterns).split()) * 2
            
            logger.info(
                f"Generated {len(valid_patterns)} patterns, "
                f"bounds: {bounds is not None} for {workflow}/{subtype}"
            )
            return valid_patterns, bounds, tokens
            
        except Exception as e:
            logger.error(f"LLM pattern+bounds generation failed: {e}")
            return [], None, 0
    
    def reshuffle(
        self,
        good_data: List[Any],
        bad_data: List[Any],
        good_indices: List[int],
        bad_indices: List[int],
        workflow: str,
        subtype: str,
        fingerprint: Dict[str, Any],
        column_name: Optional[str] = None,
    ) -> ReshuffleResult:
        """
        Reshuffle good/bad data using LLM patterns.
        
        Flow:
        1. Get patterns + bounds (cache or LLM - single call)
        2. Apply patterns to bad data → promote matches to good
        3. Apply patterns to good data → demote non-matches to bad (disabled)
        """
        # Get patterns and bounds (single call)
        patterns, bounds, from_cache, tokens = self.get_patterns_and_bounds(
            workflow, subtype, fingerprint, good_data, column_name
        )
        
        if not patterns:
            logger.warning("No patterns available for reshuffling")
            return ReshuffleResult(
                promoted_to_good=[],
                demoted_to_bad=[],
                patterns_used=[],
                bounds_detected=bounds,
                from_cache=from_cache,
                tokens_used=tokens,
            )
        
        # Compile patterns
        compiled = []
        for p in patterns:
            try:
                compiled.append(re.compile(p, re.IGNORECASE))
            except re.error:
                pass
        
        if not compiled:
            return ReshuffleResult(
                promoted_to_good=[],
                demoted_to_bad=[],
                patterns_used=patterns,
                bounds_detected=bounds,
                from_cache=from_cache,
                tokens_used=tokens,
            )
        
        # Check bad data for promotions
        promoted = []
        for value, idx in zip(bad_data, bad_indices):
            if value is None:
                continue
            str_val = str(value).strip()
            if any(p.fullmatch(str_val) for p in compiled):
                promoted.append((value, idx))
                logger.debug(f"Promoted: {str_val}")
        
        # Demotions disabled - be conservative
        demoted = []
        
        logger.info(
            f"Reshuffle: {len(promoted)} promoted, {len(demoted)} demoted "
            f"(cache: {from_cache}, patterns: {len(patterns)}, bounds: {bounds is not None})"
        )
        
        return ReshuffleResult(
            promoted_to_good=promoted,
            demoted_to_bad=demoted,
            patterns_used=patterns,
            bounds_detected=bounds,
            from_cache=from_cache,
            tokens_used=tokens,
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache and LLM usage statistics."""
        return {
            "cache_stats": self._db.get_stats(),
            "llm_stats": self._db.get_llm_stats(),
        }
