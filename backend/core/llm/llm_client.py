"""
Centralized LLM Client
======================
Single point of contact for ALL LLM calls in the application.
To change LLM provider/model, update ONLY this file.

Supports:
- Groq (default)
- OpenAI (future)
- Anthropic (future)
- Local models (future)
"""

import os
import time
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    raw_response: Optional[Any] = None
    
    def to_json(self) -> Optional[Dict[str, Any]]:
        """Try to parse content as JSON"""
        try:
            return json.loads(self.content)
        except json.JSONDecodeError:
            return None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        pass


class GroqProvider(BaseLLMProvider):
    """Groq LLM Provider"""
    
    def __init__(self, api_key: str, model: str = "llama3-8b-8192"):
        self.api_key = api_key
        self.model = model
        self._client = None
    
    @property
    def name(self) -> str:
        return "groq"
    
    def _get_client(self):
        """Lazy load the Groq client"""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Groq package not installed. Run: pip install groq"
                )
        return self._client
    
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """Make a call to Groq API"""
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        content = response.choices[0].message.content
        tokens = getattr(response.usage, 'total_tokens', 0)
        
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.name,
            tokens_used=tokens,
            latency_ms=latency_ms,
            raw_response=response,
        )


class LLMClient:
    """
    Centralized LLM Client
    ======================
    All LLM calls in the application go through this class.
    
    To change providers:
    1. Add new provider class (e.g., OpenAIProvider)
    2. Update _create_provider() method
    3. Done! All code uses this client.
    
    Usage:
        client = LLMClient()
        response = client.call("What is 2+2?")
        print(response.content)
    """
    
    def __init__(
        self,
        provider: str = "groq",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize LLM Client.
        
        Args:
            provider: LLM provider name ("groq", "openai", etc.)
            model: Model name (uses default if not specified)
            api_key: API key (uses environment variable if not specified)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.provider_name = provider
        self.model = model or self._get_default_model(provider)
        self.api_key = api_key or self._get_api_key(provider)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._provider = self._create_provider()
        
        logger.info(
            f"LLMClient initialized: provider={provider}, model={self.model}"
        )
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider"""
        defaults = {
            "groq": "llama-3.3-70b-versatile",  # Updated from decommissioned llama3-8b-8192
            "openai": "gpt-3.5-turbo",
            "anthropic": "claude-3-haiku-20240307",
        }
        return defaults.get(provider, "llama-3.3-70b-versatile")
    
    def _get_api_key(self, provider: str) -> str:
        """Get API key from environment"""
        env_vars = {
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        var_name = env_vars.get(provider, "GROQ_API_KEY")
        key = os.getenv(var_name, "")
        
        if not key:
            logger.warning(f"API key not found in {var_name}")
        
        return key
    
    def _create_provider(self) -> BaseLLMProvider:
        """Create the appropriate provider instance"""
        if self.provider_name == "groq":
            return GroqProvider(self.api_key, self.model)
        # Add more providers here as needed:
        # elif self.provider_name == "openai":
        #     return OpenAIProvider(self.api_key, self.model)
        else:
            raise ValueError(f"Unknown provider: {self.provider_name}")
    
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        Make an LLM call with retry logic.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            json_mode: If True, respond in JSON format
            **kwargs: Additional provider-specific arguments
            
        Returns:
            LLMResponse with content and metadata
        """
        if json_mode and system_prompt:
            system_prompt = f"{system_prompt}\n\nRespond ONLY with valid JSON."
        elif json_mode:
            system_prompt = "Respond ONLY with valid JSON."
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self._provider.call(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                logger.debug(
                    f"LLM call successful: {response.tokens_used} tokens, "
                    f"{response.latency_ms:.0f}ms"
                )
                
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM call attempt {attempt + 1}/{self.max_retries} "
                    f"failed: {str(e)}"
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        # All retries failed
        logger.error(f"All LLM call attempts failed: {last_error}")
        raise RuntimeError(
            f"LLM call failed after {self.max_retries} attempts: {last_error}"
        )
    
    def generate_patterns(
        self,
        samples: List[str],
        data_type: str
    ) -> List[str]:
        """
        Generate validation patterns from data samples.
        
        Args:
            samples: Sample values from good data
            data_type: Type of data (email, phone, etc.)
            
        Returns:
            List of regex patterns
        """
        from .prompts import PromptTemplates
        
        prompt = PromptTemplates.pattern_generation(samples, data_type)
        response = self.call(prompt, json_mode=True)
        
        result = response.to_json()
        if result and "patterns" in result:
            return result["patterns"]
        
        return []
    
    def assess_quality(
        self,
        value: str,
        good_samples: List[str],
        data_type: str
    ) -> Dict[str, Any]:
        """
        Assess data quality for LLM verification.
        
        Args:
            value: Value to assess
            good_samples: Examples of good data
            data_type: Type of data
            
        Returns:
            Quality assessment result
        """
        from .prompts import PromptTemplates
        
        prompt = PromptTemplates.quality_assessment(
            value, good_samples, data_type
        )
        response = self.call(prompt, json_mode=True, temperature=0.3)
        
        result = response.to_json()
        if result:
            return result
        
        return {"is_valid": False, "confidence": 0.0}
    
    def suggest_correction(
        self,
        bad_value: str,
        good_samples: List[str],
        fingerprint: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Suggest correction for a bad value.
        
        Args:
            bad_value: Value to correct
            good_samples: Examples of good data
            fingerprint: Optional fingerprint data
            
        Returns:
            Suggested correction or None
        """
        from .prompts import PromptTemplates
        
        prompt = PromptTemplates.correction_suggestion(
            bad_value, good_samples, fingerprint
        )
        response = self.call(prompt, json_mode=True, temperature=0.2)
        
        result = response.to_json()
        if result and "corrected_value" in result:
            return result["corrected_value"]
        
        return None


# Global client instance (lazy loaded)
_llm_client: Optional[LLMClient] = None


def get_llm_client(**kwargs) -> LLMClient:
    """
    Get global LLM client instance.
    
    Args:
        **kwargs: Arguments to pass to LLMClient if creating new instance
        
    Returns:
        LLMClient instance
    """
    global _llm_client
    
    if _llm_client is None:
        _llm_client = LLMClient(**kwargs)
    
    return _llm_client


def reset_llm_client():
    """Reset global client (useful for testing)"""
    global _llm_client
    _llm_client = None
