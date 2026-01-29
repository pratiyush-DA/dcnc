"""
Circuit Breaker Pattern
Prevents cascading failures by opening circuit after repeated failures.

Production-ready circuit breaker with:
- Configurable failure thresholds
- Automatic recovery (half-open state)
- Timeout-based reset
- State monitoring
"""

import time
import logging
from enum import Enum
from typing import Callable, Optional, TypeVar

from ..exceptions import CircuitBreakerOpenError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern for external service calls.
    
    Features:
    - Automatic state transitions
    - Configurable failure thresholds
    - Half-open state for recovery testing
    - Timeout-based reset
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 3,
        name: str = "circuit_breaker"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before trying half-open
            half_open_max_calls: Max calls in half-open state before closing
            name: Name of circuit breaker (for logging)
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.name = name
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
    
    def call(self, func: Callable[[], T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        # Check state and transition if needed
        self._check_and_transition()
        
        # If open, reject immediately
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                service_name=self.name,
                failure_count=self.failure_count
            )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            
            # Success - update state
            self._on_success()
            return result
            
        except Exception as e:
            # Failure - update state
            self._on_failure()
            raise
    
    def _check_and_transition(self):
        """Check state and transition if timeout expired."""
        if self.state == CircuitState.OPEN:
            if self.last_failure_time is not None:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.timeout_seconds:
                    # Transition to half-open
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                    logger.info(
                        f"Circuit breaker '{self.name}': transitioning to half-open"
                    )
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            self.success_count += 1
            
            # If enough successes, close circuit
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
                logger.info(
                    f"Circuit breaker '{self.name}': closed (recovered after "
                    f"{self.success_count} successes)"
                )
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open -> back to open
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            logger.warning(
                f"Circuit breaker '{self.name}': reopened after failure in half-open"
            )
        elif self.state == CircuitState.CLOSED:
            # Check if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(
                    f"Circuit breaker '{self.name}': opened after "
                    f"{self.failure_count} failures"
                )
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "half_open_calls": self.half_open_calls,
        }
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        logger.info(f"Circuit breaker '{self.name}': manually reset")
