"""
Centralized LLM Client Module
Single point of contact for ALL LLM calls.
Change model/service here to update entire application.

Note: LLMPatternCache is DEPRECATED. Use db_manager for caching.
"""
from .llm_client import LLMClient, get_llm_client
from .prompts import PromptTemplates
from .response_parser import ResponseParser
from .reshuffler import LLMReshuffler, ReshuffleResult

# Deprecated - use backend.database.db_manager instead
try:
    from .pattern_cache import LLMPatternCache
except ImportError:
    LLMPatternCache = None

__all__ = [
    "LLMClient",
    "get_llm_client",
    "PromptTemplates",
    "ResponseParser",
    "LLMReshuffler",
    "ReshuffleResult",
]
