"""
Plugin Registry
================
Central registry for workflows, validators, and correctors.
Enables plugin architecture for easy extensibility.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from .interfaces import (
    IWorkflow,
    IValidator,
    ICorrector,
    IFingerprint,
    IDetector,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Registry:
    """
    Generic registry for plugin classes.
    Supports decorator-based registration.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._registry: Dict[str, Type] = {}
        self._instances: Dict[str, Any] = {}
    
    def register(self, key: str, cls: Type[T]) -> Type[T]:
        """
        Register a class with the given key.
        
        Args:
            key: Registration key
            cls: Class to register
            
        Returns:
            The registered class (for decorator use)
        """
        if key in self._registry:
            logger.warning(
                f"{self.name}: Overwriting existing registration for '{key}'"
            )
        
        self._registry[key] = cls
        logger.debug(f"{self.name}: Registered '{key}' -> {cls.__name__}")
        
        return cls
    
    def get(self, key: str, **kwargs) -> Optional[Any]:
        """
        Get an instance of a registered class.
        Instances are cached by default.
        
        Args:
            key: Registration key
            **kwargs: Arguments to pass to constructor
            
        Returns:
            Instance or None if not found
        """
        if key not in self._registry:
            logger.warning(f"{self.name}: No registration for '{key}'")
            return None
        
        # Check cache if no kwargs
        cache_key = key
        if not kwargs and cache_key in self._instances:
            return self._instances[cache_key]
        
        # Create new instance
        cls = self._registry[key]
        try:
            instance = cls(**kwargs)
            
            # Cache if no kwargs
            if not kwargs:
                self._instances[cache_key] = instance
            
            return instance
        except Exception as e:
            logger.error(f"{self.name}: Failed to create '{key}': {e}")
            return None
    
    def get_class(self, key: str) -> Optional[Type]:
        """Get the registered class (not instance)"""
        return self._registry.get(key)
    
    def list_keys(self) -> List[str]:
        """List all registered keys"""
        return list(self._registry.keys())
    
    def has(self, key: str) -> bool:
        """Check if key is registered"""
        return key in self._registry
    
    def clear(self):
        """Clear registry and instances"""
        self._registry.clear()
        self._instances.clear()
    
    def decorator(self, key: str) -> Callable:
        """
        Decorator for registering classes.
        
        Usage:
            @registry.decorator("my_key")
            class MyClass:
                pass
        """
        def wrapper(cls: Type[T]) -> Type[T]:
            self.register(key, cls)
            return cls
        return wrapper


class WorkflowRegistry(Registry):
    """Registry for workflow classes"""
    
    def __init__(self):
        super().__init__("WorkflowRegistry")
    
    def get_for_type(self, workflow_type: str) -> Optional[IWorkflow]:
        """Get workflow by type (text, numeric, datetime, identifier)"""
        return self.get(workflow_type)


class ValidatorRegistry(Registry):
    """Registry for validator/engine classes"""
    
    def __init__(self):
        super().__init__("ValidatorRegistry")
    
    def get_for_subtype(self, subtype: str) -> Optional[IValidator]:
        """Get validator for a specific subtype"""
        return self.get(subtype)


class CorrectorRegistry(Registry):
    """Registry for corrector classes"""
    
    def __init__(self):
        super().__init__("CorrectorRegistry")
    
    def get_for_subtype(self, subtype: str) -> Optional[ICorrector]:
        """Get corrector for a specific subtype"""
        # Try specific subtype first
        corrector = self.get(subtype)
        if corrector:
            return corrector
        
        # Fall back to generic
        return self.get("generic")


class FingerprintRegistry(Registry):
    """Registry for fingerprint generator classes"""
    
    def __init__(self):
        super().__init__("FingerprintRegistry")
    
    def get_for_workflow(self, workflow_type: str) -> Optional[IFingerprint]:
        """Get fingerprint generator for a workflow type"""
        return self.get(workflow_type)


# Global registry instances
_workflow_registry = WorkflowRegistry()
_validator_registry = ValidatorRegistry()
_corrector_registry = CorrectorRegistry()
_fingerprint_registry = FingerprintRegistry()


def get_workflow_registry() -> WorkflowRegistry:
    """Get the global workflow registry"""
    return _workflow_registry


def get_validator_registry() -> ValidatorRegistry:
    """Get the global validator registry"""
    return _validator_registry


def get_corrector_registry() -> CorrectorRegistry:
    """Get the global corrector registry"""
    return _corrector_registry


def get_fingerprint_registry() -> FingerprintRegistry:
    """Get the global fingerprint registry"""
    return _fingerprint_registry


# Convenient decorator shortcuts
def register_workflow(name: str):
    """Decorator to register a workflow"""
    return _workflow_registry.decorator(name)


def register_validator(name: str):
    """Decorator to register a validator"""
    return _validator_registry.decorator(name)


def register_corrector(name: str):
    """Decorator to register a corrector"""
    return _corrector_registry.decorator(name)


def register_fingerprint(name: str):
    """Decorator to register a fingerprint generator"""
    return _fingerprint_registry.decorator(name)


def get_registered_workflows() -> List[str]:
    """List all registered workflows"""
    return _workflow_registry.list_keys()


def get_registered_validators() -> List[str]:
    """List all registered validators"""
    return _validator_registry.list_keys()


def get_registered_correctors() -> List[str]:
    """List all registered correctors"""
    return _corrector_registry.list_keys()
