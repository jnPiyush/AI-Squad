"""
Backpressure and Rate Limiting

Prevents system overload by monitoring queue depths and limiting request rates.
Implements queue-based backpressure and token bucket rate limiting.

Key Features:
- Queue depth monitoring with configurable thresholds
- Per-agent token bucket rate limiting
- Automatic backpressure detection
- Wait time calculation for rate-limited requests
- Thread-safe operations
"""
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BackpressureError(Exception):
    """Raised when system is under backpressure and cannot accept more requests"""
    
    def __init__(self, queue_depth: int, max_depth: int, wait_time: Optional[float] = None):
        self.queue_depth = queue_depth
        self.max_depth = max_depth
        self.wait_time = wait_time
        
        message = f"System under backpressure: queue depth {queue_depth}/{max_depth}"
        if wait_time:
            message += f", wait {wait_time:.2f}s"
        
        super().__init__(message)


class RateLimitError(Exception):
    """Raised when agent exceeds rate limit"""
    
    def __init__(self, agent: str, wait_time: float, rate_limit: int):
        self.agent = agent
        self.wait_time = wait_time
        self.rate_limit = rate_limit
        
        super().__init__(
            f"Agent '{agent}' rate limited: wait {wait_time:.2f}s "
            f"(limit: {rate_limit}/min)"
        )


@dataclass
class BackpressureMetrics:
    """Backpressure monitoring metrics"""
    queue_depth: int
    max_queue_depth: int
    threshold_percent: float
    under_pressure: bool
    utilization_percent: float
    total_rejections: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "queue_depth": self.queue_depth,
            "max_queue_depth": self.max_queue_depth,
            "threshold_percent": self.threshold_percent,
            "under_pressure": self.under_pressure,
            "utilization_percent": self.utilization_percent,
            "total_rejections": self.total_rejections
        }


class StorageBackpressure:
    """
    Queue-based backpressure monitoring.
    
    Tracks queue depth and prevents overload by rejecting requests
    when queue is near capacity.
    
    Usage:
        backpressure = StorageBackpressure(max_depth=100, threshold=0.8)
        
        # Acquire slot before operation
        with backpressure.acquire():
            # Perform operation
            process_request()
        
        # Check status
        if backpressure.is_under_pressure():
            logger.warning("System under pressure!")
    
    Thread Safety:
        All methods are thread-safe using RLock.
    """
    
    def __init__(
        self,
        max_depth: int = 100,
        threshold: float = 0.8,
        timeout: float = 30.0
    ):
        """
        Initialize backpressure monitor.
        
        Args:
            max_depth: Maximum queue depth before rejecting requests
            threshold: Utilization threshold (0.0-1.0) for pressure detection
            timeout: Max seconds to wait for slot acquisition
        """
        if not 0 < threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        
        self.max_depth = max_depth
        self.threshold = threshold
        self.timeout = timeout
        
        # Current queue depth
        self._queue_depth = 0
        self._lock = threading.RLock()
        
        # Statistics
        self._total_acquisitions = 0
        self._total_releases = 0
        self._total_rejections = 0
        self._peak_depth = 0
        
        logger.info(
            "BackpressureMonitor initialized: max_depth=%d, threshold=%.1f%%",
            max_depth, threshold * 100
        )
    
    def acquire(self, timeout: Optional[float] = None) -> "BackpressureContext":
        """
        Acquire slot in queue (returns context manager).
        
        Args:
            timeout: Override default timeout
            
        Returns:
            Context manager for slot acquisition
            
        Raises:
            BackpressureError: If queue is full or timeout reached
            
        Example:
            with backpressure.acquire():
                process_request()
        """
        return BackpressureContext(self, timeout)
    
    def _try_acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Try to acquire slot in queue.
        
        Args:
            timeout: Max seconds to wait
            
        Returns:
            True if acquired, False if rejected
            
        Raises:
            BackpressureError: If queue full and timeout reached
        """
        effective_timeout = timeout if timeout is not None else self.timeout
        start_time = time.time()
        
        while True:
            with self._lock:
                # Check if slot available
                if self._queue_depth < self.max_depth:
                    self._queue_depth += 1
                    self._total_acquisitions += 1
                    
                    # Update peak
                    if self._queue_depth > self._peak_depth:
                        self._peak_depth = self._queue_depth
                    
                    return True
                
                # Queue full
                elapsed = time.time() - start_time
                if elapsed >= effective_timeout:
                    self._total_rejections += 1
                    raise BackpressureError(
                        queue_depth=self._queue_depth,
                        max_depth=self.max_depth,
                        wait_time=elapsed
                    )
            
            # Wait a bit before retry
            time.sleep(0.01)  # 10ms
    
    def _release(self) -> None:
        """Release slot in queue"""
        with self._lock:
            if self._queue_depth > 0:
                self._queue_depth -= 1
                self._total_releases += 1
    
    def is_under_pressure(self) -> bool:
        """
        Check if system is under backpressure.
        
        Returns:
            True if queue depth exceeds threshold
        """
        with self._lock:
            threshold_depth = int(self.max_depth * self.threshold)
            return self._queue_depth >= threshold_depth
    
    def get_utilization(self) -> float:
        """
        Get current queue utilization percentage.
        
        Returns:
            Utilization as percentage (0-100)
        """
        with self._lock:
            if self.max_depth == 0:
                return 0.0
            return (self._queue_depth / self.max_depth) * 100
    
    def get_metrics(self) -> BackpressureMetrics:
        """
        Get current backpressure metrics.
        
        Returns:
            BackpressureMetrics object
        """
        with self._lock:
            return BackpressureMetrics(
                queue_depth=self._queue_depth,
                max_queue_depth=self.max_depth,
                threshold_percent=self.threshold * 100,
                under_pressure=self.is_under_pressure(),
                utilization_percent=self.get_utilization(),
                total_rejections=self._total_rejections
            )
    
    def get_stats(self) -> Dict:
        """
        Get detailed statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                "queue_depth": self._queue_depth,
                "max_depth": self.max_depth,
                "threshold": self.threshold,
                "utilization_percent": self.get_utilization(),
                "under_pressure": self.is_under_pressure(),
                "total_acquisitions": self._total_acquisitions,
                "total_releases": self._total_releases,
                "total_rejections": self._total_rejections,
                "peak_depth": self._peak_depth
            }
    
    def reset_stats(self) -> None:
        """Reset statistics (for testing)"""
        with self._lock:
            self._total_acquisitions = 0
            self._total_releases = 0
            self._total_rejections = 0
            self._peak_depth = 0


class BackpressureContext:
    """Context manager for backpressure slot acquisition"""
    
    def __init__(self, backpressure: StorageBackpressure, timeout: Optional[float]):
        self.backpressure = backpressure
        self.timeout = timeout
        self.acquired = False
    
    def __enter__(self):
        self.acquired = self.backpressure._try_acquire(self.timeout)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.backpressure._release()
        return False


class RateLimiter:
    """
    Token bucket rate limiter per agent.
    
    Implements sliding window rate limiting with configurable
    rate and burst capacity.
    
    Usage:
        limiter = RateLimiter(rate_per_minute=100, burst=20)
        
        # Check if operation allowed
        if limiter.allow("agent-1"):
            process_request()
        else:
            wait = limiter.get_wait_time("agent-1")
            time.sleep(wait)
        
        # Or use context manager (auto-retry)
        with limiter.acquire("agent-1"):
            process_request()
    
    Thread Safety:
        All methods are thread-safe using Lock.
    """
    
    def __init__(
        self,
        rate_per_minute: int = 100,
        burst: int = 20,
        window_seconds: float = 60.0
    ):
        """
        Initialize rate limiter.
        
        Args:
            rate_per_minute: Maximum requests per minute per agent
            burst: Maximum burst size (tokens above rate)
            window_seconds: Time window for rate calculation (default 60s)
        """
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be positive")
        if burst < 0:
            raise ValueError("burst cannot be negative")
        
        self.rate = rate_per_minute
        self.burst = burst
        self.window = window_seconds
        
        # Token buckets per agent: {agent: [timestamps]}
        self._tokens: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        
        # Statistics
        self._total_allowed = 0
        self._total_rejected = 0
        self._rejections_by_agent: Dict[str, int] = defaultdict(int)
        
        logger.info(
            "RateLimiter initialized: rate=%d/min, burst=%d",
            rate_per_minute, burst
        )
    
    def allow(self, agent: str) -> bool:
        """
        Check if operation is allowed for agent.
        
        Args:
            agent: Agent identifier
            
        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        window_start = now - self.window
        
        with self._lock:
            # Remove expired tokens
            self._tokens[agent] = [
                t for t in self._tokens[agent]
                if t > window_start
            ]
            
            # Check rate limit
            current_count = len(self._tokens[agent])
            max_tokens = self.rate + self.burst
            
            if current_count >= max_tokens:
                self._total_rejected += 1
                self._rejections_by_agent[agent] += 1
                return False
            
            # Allow request - add token
            self._tokens[agent].append(now)
            self._total_allowed += 1
            return True
    
    def get_wait_time(self, agent: str) -> float:
        """
        Calculate wait time until next token available.
        
        Args:
            agent: Agent identifier
            
        Returns:
            Seconds to wait (0 if tokens available)
        """
        now = time.time()
        window_start = now - self.window
        
        with self._lock:
            # Clean expired tokens
            self._tokens[agent] = [
                t for t in self._tokens[agent]
                if t > window_start
            ]
            
            # If under limit, no wait needed
            if len(self._tokens[agent]) < self.rate + self.burst:
                return 0.0
            
            # Calculate when oldest token expires
            if self._tokens[agent]:
                oldest_token = min(self._tokens[agent])
                wait_time = oldest_token + self.window - now
                return max(0.0, wait_time)
            
            return 0.0
    
    def acquire(self, agent: str, max_retries: int = 3) -> "RateLimitContext":
        """
        Acquire rate limit slot (returns context manager).
        
        Args:
            agent: Agent identifier
            max_retries: Maximum retry attempts
            
        Returns:
            Context manager for rate limit acquisition
            
        Raises:
            RateLimitError: If all retries exhausted
            
        Example:
            with limiter.acquire("agent-1"):
                process_request()
        """
        return RateLimitContext(self, agent, max_retries)
    
    def get_current_rate(self, agent: str) -> int:
        """
        Get current request rate for agent.
        
        Args:
            agent: Agent identifier
            
        Returns:
            Requests in current window
        """
        now = time.time()
        window_start = now - self.window
        
        with self._lock:
            # Count tokens in window
            valid_tokens = [
                t for t in self._tokens[agent]
                if t > window_start
            ]
            return len(valid_tokens)
    
    def get_stats(self) -> Dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                "rate_per_minute": self.rate,
                "burst": self.burst,
                "window_seconds": self.window,
                "total_allowed": self._total_allowed,
                "total_rejected": self._total_rejected,
                "rejection_rate": (
                    self._total_rejected / (self._total_allowed + self._total_rejected)
                    if (self._total_allowed + self._total_rejected) > 0
                    else 0.0
                ),
                "active_agents": len(self._tokens),
                "rejections_by_agent": dict(self._rejections_by_agent)
            }
    
    def reset_stats(self) -> None:
        """Reset statistics (for testing)"""
        with self._lock:
            self._total_allowed = 0
            self._total_rejected = 0
            self._rejections_by_agent.clear()
    
    def clear_agent(self, agent: str) -> None:
        """Clear tokens for specific agent (for testing)"""
        with self._lock:
            self._tokens.pop(agent, None)
            self._rejections_by_agent.pop(agent, None)


class RateLimitContext:
    """Context manager for rate limit acquisition with retry"""
    
    def __init__(self, limiter: RateLimiter, agent: str, max_retries: int):
        self.limiter = limiter
        self.agent = agent
        self.max_retries = max_retries
    
    def __enter__(self):
        for attempt in range(self.max_retries):
            if self.limiter.allow(self.agent):
                return self
            
            # Wait and retry
            if attempt < self.max_retries - 1:
                wait_time = self.limiter.get_wait_time(self.agent)
                if wait_time > 0:
                    time.sleep(wait_time)
        
        # All retries failed
        wait_time = self.limiter.get_wait_time(self.agent)
        raise RateLimitError(
            agent=self.agent,
            wait_time=wait_time,
            rate_limit=self.limiter.rate
        )
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


# Global instances (can be configured at startup)
_global_backpressure: Optional[StorageBackpressure] = None
_global_rate_limiter: Optional[RateLimiter] = None
_global_lock = threading.Lock()


def get_global_backpressure(**kwargs) -> StorageBackpressure:
    """
    Get or create global backpressure monitor.
    
    Args:
        **kwargs: Arguments for StorageBackpressure (only used on first call)
        
    Returns:
        Global StorageBackpressure instance
    """
    global _global_backpressure
    
    with _global_lock:
        if _global_backpressure is None:
            _global_backpressure = StorageBackpressure(**kwargs)
            logger.info("Global backpressure monitor created")
        
        return _global_backpressure


def get_global_rate_limiter(**kwargs) -> RateLimiter:
    """
    Get or create global rate limiter.
    
    Args:
        **kwargs: Arguments for RateLimiter (only used on first call)
        
    Returns:
        Global RateLimiter instance
    """
    global _global_rate_limiter
    
    with _global_lock:
        if _global_rate_limiter is None:
            _global_rate_limiter = RateLimiter(**kwargs)
            logger.info("Global rate limiter created")
        
        return _global_rate_limiter


def reset_globals() -> None:
    """Reset global instances (for testing)"""
    global _global_backpressure, _global_rate_limiter
    
    with _global_lock:
        _global_backpressure = None
        _global_rate_limiter = None
