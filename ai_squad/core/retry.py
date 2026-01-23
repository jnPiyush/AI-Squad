"""
Retry Logic and Error Recovery

Implements exponential backoff retry, rate limit handling, and circuit breaker pattern.
"""
import time
import functools
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        retryable_exceptions: tuple = (Exception,)
    ):
        """
        Initialize retry configuration
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Multiplier for exponential backoff
            strategy: Retry strategy to use
            retryable_exceptions: Tuple of exception types to retry
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.strategy = strategy
        self.retryable_exceptions = retryable_exceptions
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.backoff_factor ** attempt)
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * (attempt + 1)
        else:  # FIXED
            delay = self.initial_delay
        
        return min(delay, self.max_delay)


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for retrying functions with exponential backoff
    
    Usage:
        @retry_with_backoff()
        def api_call():
            # code that might fail
            ...
    
    Args:
        config: RetryConfig instance, uses defaults if None
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt, raise the exception
                        logger.error(
                            "%s failed after %s attempts: %s",
                            func.__name__,
                            config.max_attempts,
                            e,
                        )
                        raise
                    
                    # Calculate delay and wait
                    delay = config.get_delay(attempt)
                    logger.warning(
                        "%s attempt %s failed: %s. Retrying in %.2fs...",
                        func.__name__,
                        attempt + 1,
                        e,
                        delay,
                    )
                    time.sleep(delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(
        self,
        calls_per_hour: int = 5000,
        burst_size: int = 100
    ):
        """
        Initialize rate limiter
        
        Args:
            calls_per_hour: Maximum calls per hour
            burst_size: Maximum burst size
        """
        self.calls_per_hour = calls_per_hour
        self.burst_size = burst_size
        self.calls = []
        self.reset_time = None
    
    def can_proceed(self) -> bool:
        """Check if we can make another call"""
        now = datetime.now()
        
        # Remove calls older than 1 hour
        self.calls = [t for t in self.calls if t > now - timedelta(hours=1)]
        
        # Check hourly limit
        if len(self.calls) >= self.calls_per_hour:
            return False
        
        # Check burst limit (last minute)
        recent_calls = [t for t in self.calls if t > now - timedelta(minutes=1)]
        if len(recent_calls) >= self.burst_size:
            return False
        
        return True
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded"""
        while not self.can_proceed():
            logger.warning("Rate limit reached, waiting 60 seconds...")
            time.sleep(60)
    
    def record_call(self) -> None:
        """Record that a call was made"""
        self.calls.append(datetime.now())
    
    def get_remaining(self) -> Dict[str, int]:
        """Get remaining calls in current window"""
        now = datetime.now()
        hour_calls = len([t for t in self.calls if t > now - timedelta(hours=1)])
        minute_calls = len([t for t in self.calls if t > now - timedelta(minutes=1)])
        
        return {
            "hourly_remaining": self.calls_per_hour - hour_calls,
            "burst_remaining": self.burst_size - minute_calls
        }


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes to close circuit (from half-open)
            timeout: Seconds to wait before trying again (open → half-open)
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments for function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._should_attempt_reset():
                logger.info("Circuit breaker entering half-open state")
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open. Retry after "
                    f"{self._time_until_retry():.0f} seconds"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info("Circuit breaker closing (recovered)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            # Reset failure count on success in closed state
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open, go back to open
            logger.warning("Circuit breaker opening (half-open failure)")
            self.state = CircuitState.OPEN
            self.success_count = 0
            
        elif self.failure_count >= self.failure_threshold:
            # Too many failures, open circuit
            logger.warning(
                "Circuit breaker opening (%d failures)",
                self.failure_count,
            )
            self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again"""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout
    
    def _time_until_retry(self) -> float:
        """Calculate seconds until retry is allowed"""
        if self.last_failure_time is None:
            return 0
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return max(0, self.timeout - elapsed)
    
    def reset(self) -> None:
        """Manually reset circuit breaker"""
        logger.info("Circuit breaker manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""


class GitHubRateLimitError(Exception):
    """Raised when GitHub rate limit is exceeded"""


def with_circuit_breaker(breaker: CircuitBreaker):
    """
    Decorator for circuit breaker pattern
    
    Usage:
        breaker = CircuitBreaker()
        
        @with_circuit_breaker(breaker)
        def api_call():
            # code
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


def with_rate_limiting(limiter: RateLimiter):
    """
    Decorator for rate limiting
    
    Usage:
        limiter = RateLimiter(calls_per_hour=5000)
        
        @with_rate_limiting(limiter)
        def api_call():
            # code
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            limiter.wait_if_needed()
            try:
                result = func(*args, **kwargs)
                limiter.record_call()
                return result
            except Exception:
                limiter.record_call()  # Still count failed calls
                raise
        return wrapper
    return decorator


# Pre-configured retry configs for common scenarios
GITHUB_API_RETRY = RetryConfig(
    max_attempts=3,
    initial_delay=2.0,
    max_delay=30.0,
    backoff_factor=2.0,
    strategy=RetryStrategy.EXPONENTIAL,
    retryable_exceptions=(ConnectionError, TimeoutError, GitHubRateLimitError)
)

AGENT_EXECUTION_RETRY = RetryConfig(
    max_attempts=2,
    initial_delay=5.0,
    max_delay=60.0,
    backoff_factor=2.0,
    strategy=RetryStrategy.EXPONENTIAL
)
