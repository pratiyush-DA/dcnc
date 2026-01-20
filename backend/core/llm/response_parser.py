"""
Response Parser for LLM Outputs
Handles parsing and validation of LLM responses
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Parser for LLM response content.
    Handles various response formats and edge cases.
    """
    
    @staticmethod
    def extract_json(content: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response content.
        Handles markdown code blocks and raw JSON.
        
        Args:
            content: Raw LLM response content
            
        Returns:
            Parsed JSON dict or None
        """
        if not content:
            return None
        
        # Try direct JSON parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*\}',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(json_str)
                except (json.JSONDecodeError, IndexError):
                    continue
        
        logger.warning(f"Could not parse JSON from: {content[:100]}...")
        return None
    
    @staticmethod
    def parse_patterns(response_json: Dict[str, Any]) -> List[str]:
        """
        Parse pattern list from response.
        
        Args:
            response_json: Parsed JSON response
            
        Returns:
            List of patterns
        """
        patterns = response_json.get("patterns", [])
        
        # Fix common backreference issues
        fixed_patterns = []
        for pattern in patterns:
            if isinstance(pattern, str):
                # Convert $1, $2 to \g<1>, \g<2>
                fixed = re.sub(r'\$(\d+)', r'\\g<\1>', pattern)
                fixed_patterns.append(fixed)
        
        return fixed_patterns
    
    @staticmethod
    def parse_validation_result(
        response_json: Dict[str, Any]
    ) -> Tuple[bool, float, List[str]]:
        """
        Parse validation result from response.
        
        Args:
            response_json: Parsed JSON response
            
        Returns:
            Tuple of (is_valid, confidence, issues)
        """
        is_valid = response_json.get("is_valid", False)
        confidence = float(response_json.get("confidence", 0.0))
        issues = response_json.get("issues", [])
        
        # Ensure types
        if not isinstance(is_valid, bool):
            is_valid = str(is_valid).lower() in ("true", "1", "yes")
        
        confidence = max(0.0, min(1.0, confidence))
        
        return is_valid, confidence, issues
    
    @staticmethod
    def parse_correction_result(
        response_json: Dict[str, Any]
    ) -> Tuple[Optional[str], float, List[str], bool]:
        """
        Parse correction suggestion from response.
        
        Args:
            response_json: Parsed JSON response
            
        Returns:
            Tuple of (corrected_value, confidence, changes, correctable)
        """
        corrected = response_json.get("corrected_value")
        confidence = float(response_json.get("confidence", 0.0))
        changes = response_json.get("changes_made", [])
        correctable = response_json.get("correctable", corrected is not None)
        
        # Handle null/None
        if corrected in (None, "null", "None", ""):
            corrected = None
            correctable = False
        
        return corrected, confidence, changes, correctable
    
    @staticmethod
    def parse_batch_results(
        response_json: Dict[str, Any]
    ) -> Dict[int, Tuple[bool, float]]:
        """
        Parse batch validation results.
        
        Args:
            response_json: Parsed JSON response
            
        Returns:
            Dict mapping index to (is_valid, confidence)
        """
        results = {}
        raw_results = response_json.get("results", {})
        
        for idx_str, result in raw_results.items():
            try:
                idx = int(idx_str)
                is_valid = result.get("valid", False)
                confidence = float(result.get("confidence", 0.0))
                results[idx] = (is_valid, confidence)
            except (ValueError, AttributeError):
                continue
        
        return results
    
    @staticmethod
    def safe_parse(
        content: str,
        default: Any = None
    ) -> Any:
        """
        Safely parse LLM response with fallback.
        
        Args:
            content: Response content
            default: Default value if parsing fails
            
        Returns:
            Parsed result or default
        """
        try:
            result = ResponseParser.extract_json(content)
            return result if result is not None else default
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return default
