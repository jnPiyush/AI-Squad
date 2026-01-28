"""
Resource Monitoring for Adaptive Concurrency

Monitors system resources (CPU, memory) to dynamically adjust
parallelism in convoy operations.

Key Features:
- CPU and memory utilization tracking
- Adaptive parallelism calculation
- Resource-based throttling
- Process-level monitoring

Dependencies:
- psutil (optional): For detailed system metrics
- Falls back to os module if psutil unavailable
"""
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import psutil for detailed metrics
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning(
        "psutil not available - resource monitoring will use basic metrics. "
        "Install with: pip install psutil"
    )


@dataclass
class ResourceMetrics:
    """System resource usage metrics"""
    cpu_percent: float          # CPU usage (0-100)
    memory_percent: float       # Memory usage (0-100)
    memory_available_mb: float  # Available memory in MB
    process_memory_mb: float    # Current process memory in MB
    process_cpu_percent: float  # Current process CPU usage
    thread_count: int           # Active threads
    timestamp: float            # When measured
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_mb": self.memory_available_mb,
            "process_memory_mb": self.process_memory_mb,
            "process_cpu_percent": self.process_cpu_percent,
            "thread_count": self.thread_count,
            "timestamp": self.timestamp
        }
    
    def is_resource_constrained(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0
    ) -> bool:
        """
        Check if system is resource constrained.
        
        Args:
            cpu_threshold: CPU usage threshold (%)
            memory_threshold: Memory usage threshold (%)
            
        Returns:
            True if either CPU or memory is above threshold
        """
        return (
            self.cpu_percent > cpu_threshold or
            self.memory_percent > memory_threshold
        )


class ResourceMonitor:
    """
    System resource monitor for adaptive concurrency.
    
    Monitors CPU and memory to dynamically adjust parallelism:
    - High resource usage → reduce parallelism
    - Low resource usage → increase parallelism
    
    Usage:
        monitor = ResourceMonitor(
            sample_interval=1.0,  # Sample every second
            history_size=60       # Keep 60 seconds history
        )
        
        # Get current metrics
        metrics = monitor.get_current_metrics()
        print(f"CPU: {metrics.cpu_percent}%, Memory: {metrics.memory_percent}%")
        
        # Get recommended parallelism
        parallelism = monitor.calculate_optimal_parallelism(
            max_parallel=20,
            baseline=5
        )
        
        # Check if throttling needed
        if monitor.should_throttle():
            logger.warning("System under load, reducing parallelism")
    """
    
    def __init__(
        self,
        sample_interval: float = 1.0,
        history_size: int = 60,
        auto_sample: bool = False
    ):
        """
        Initialize resource monitor.
        
        Args:
            sample_interval: Seconds between automatic samples
            history_size: Number of samples to keep in history
            auto_sample: Enable background sampling thread
        """
        self.sample_interval = sample_interval
        self.history_size = history_size
        self.auto_sample = auto_sample
        
        # Metrics history (ring buffer)
        self._history: list[ResourceMetrics] = []
        self._history_lock = threading.Lock()
        
        # Background sampling
        self._sampling_thread: Optional[threading.Thread] = None
        self._stop_sampling = threading.Event()
        
        # Process handle (if psutil available)
        self._process = psutil.Process() if HAS_PSUTIL else None
        
        # Start auto-sampling if enabled
        if auto_sample:
            self.start_sampling()
        
        logger.info(
            "ResourceMonitor initialized: interval=%.1fs, history=%d samples, psutil=%s",
            sample_interval, history_size, HAS_PSUTIL
        )
    
    def get_current_metrics(self) -> ResourceMetrics:
        """
        Get current resource metrics.
        
        Returns:
            ResourceMetrics with current measurements
        """
        if HAS_PSUTIL:
            return self._get_metrics_psutil()
        else:
            return self._get_metrics_basic()
    
    def _get_metrics_psutil(self) -> ResourceMetrics:
        """Get detailed metrics using psutil"""
        # System-wide metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Process-specific metrics
        process_memory = self._process.memory_info().rss / (1024 * 1024)  # MB
        process_cpu = self._process.cpu_percent(interval=0.1)
        thread_count = self._process.num_threads()
        
        return ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_mb=memory.available / (1024 * 1024),
            process_memory_mb=process_memory,
            process_cpu_percent=process_cpu,
            thread_count=thread_count,
            timestamp=time.time()
        )
    
    def _get_metrics_basic(self) -> ResourceMetrics:
        """Get basic metrics without psutil"""
        # Without psutil, we have limited metrics
        # Return conservative estimates
        return ResourceMetrics(
            cpu_percent=50.0,  # Conservative estimate
            memory_percent=50.0,  # Conservative estimate
            memory_available_mb=1024.0,  # 1GB estimate
            process_memory_mb=100.0,  # 100MB estimate
            process_cpu_percent=10.0,  # 10% estimate
            thread_count=threading.active_count(),
            timestamp=time.time()
        )
    
    def sample(self) -> ResourceMetrics:
        """
        Take a sample and add to history.
        
        Returns:
            Sampled metrics
        """
        metrics = self.get_current_metrics()
        
        with self._history_lock:
            self._history.append(metrics)
            # Keep only last N samples
            if len(self._history) > self.history_size:
                self._history.pop(0)
        
        return metrics
    
    def get_average_metrics(self, window_seconds: float = 10.0) -> Optional[ResourceMetrics]:
        """
        Get average metrics over time window.
        
        Args:
            window_seconds: Time window for averaging
            
        Returns:
            Averaged metrics, or None if insufficient history
        """
        with self._history_lock:
            if not self._history:
                return None
            
            # Filter samples within window
            now = time.time()
            cutoff = now - window_seconds
            recent = [m for m in self._history if m.timestamp > cutoff]
            
            if not recent:
                return None
            
            # Calculate averages
            return ResourceMetrics(
                cpu_percent=sum(m.cpu_percent for m in recent) / len(recent),
                memory_percent=sum(m.memory_percent for m in recent) / len(recent),
                memory_available_mb=sum(m.memory_available_mb for m in recent) / len(recent),
                process_memory_mb=sum(m.process_memory_mb for m in recent) / len(recent),
                process_cpu_percent=sum(m.process_cpu_percent for m in recent) / len(recent),
                thread_count=int(sum(m.thread_count for m in recent) / len(recent)),
                timestamp=now
            )
    
    def calculate_optimal_parallelism(
        self,
        max_parallel: int = 20,
        baseline: int = 5,
        cpu_weight: float = 0.6,
        memory_weight: float = 0.4
    ) -> int:
        """
        Calculate optimal parallelism based on available resources.
        
        Algorithm:
        - High resources → use max_parallel
        - Medium resources → scale between baseline and max
        - Low resources → use baseline
        
        Args:
            max_parallel: Maximum parallelism allowed
            baseline: Minimum safe parallelism
            cpu_weight: Weight for CPU in calculation (0-1)
            memory_weight: Weight for memory in calculation (0-1)
            
        Returns:
            Recommended parallelism level
        """
        metrics = self.get_current_metrics()
        
        # Calculate resource availability (inverted utilization)
        cpu_available = 100.0 - metrics.cpu_percent
        memory_available = 100.0 - metrics.memory_percent
        
        # Weighted average of available resources
        available_score = (
            cpu_weight * cpu_available +
            memory_weight * memory_available
        )
        
        # Map to parallelism range
        # available_score: 0-100
        # parallelism: baseline to max_parallel
        if available_score >= 60:
            # High availability - use max parallelism
            return max_parallel
        elif available_score >= 30:
            # Medium availability - scale proportionally
            ratio = (available_score - 30) / 30  # 0-1
            return baseline + int((max_parallel - baseline) * ratio)
        else:
            # Low availability - use baseline
            return baseline
    
    def should_throttle(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0
    ) -> bool:
        """
        Check if throttling recommended.
        
        Args:
            cpu_threshold: CPU usage threshold (%)
            memory_threshold: Memory usage threshold (%)
            
        Returns:
            True if should reduce load
        """
        metrics = self.get_current_metrics()
        return metrics.is_resource_constrained(cpu_threshold, memory_threshold)
    
    def get_throttle_factor(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0
    ) -> float:
        """
        Calculate throttle factor (0.0 = full throttle, 1.0 = no throttle).
        
        Args:
            cpu_threshold: CPU usage threshold (%)
            memory_threshold: Memory usage threshold (%)
            
        Returns:
            Throttle factor between 0.0 and 1.0
        """
        metrics = self.get_current_metrics()
        
        # Calculate how much over threshold
        cpu_over = max(0, metrics.cpu_percent - cpu_threshold) / (100 - cpu_threshold)
        memory_over = max(0, metrics.memory_percent - memory_threshold) / (100 - memory_threshold)
        
        # Use worst case
        max_over = max(cpu_over, memory_over)
        
        # Convert to throttle factor (0 = full throttle, 1 = no throttle)
        return max(0.0, 1.0 - max_over)
    
    def start_sampling(self):
        """Start background sampling thread"""
        if self._sampling_thread and self._sampling_thread.is_alive():
            logger.warning("Sampling already running")
            return
        
        self._stop_sampling.clear()
        self._sampling_thread = threading.Thread(
            target=self._sampling_loop,
            daemon=True,
            name="ResourceMonitor"
        )
        self._sampling_thread.start()
        logger.info("Background sampling started")
    
    def stop_sampling(self):
        """Stop background sampling thread"""
        if not self._sampling_thread:
            return
        
        self._stop_sampling.set()
        self._sampling_thread.join(timeout=5.0)
        logger.info("Background sampling stopped")
    
    def _sampling_loop(self):
        """Background sampling loop"""
        while not self._stop_sampling.is_set():
            try:
                self.sample()
            except Exception as e:
                logger.error("Sampling error: %s", e)
            
            # Wait for next sample (or stop signal)
            self._stop_sampling.wait(self.sample_interval)
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        with self._history_lock:
            history_count = len(self._history)
        
        current = self.get_current_metrics()
        
        return {
            "has_psutil": HAS_PSUTIL,
            "auto_sampling": self.auto_sample,
            "sample_interval": self.sample_interval,
            "history_size": self.history_size,
            "samples_collected": history_count,
            "current_metrics": current.to_dict(),
            "sampling_active": (
                self._sampling_thread is not None and
                self._sampling_thread.is_alive()
            )
        }
    
    def __del__(self):
        """Cleanup on garbage collection"""
        self.stop_sampling()


# Global monitor instance
_global_monitor: Optional[ResourceMonitor] = None
_global_monitor_lock = threading.Lock()


def get_global_monitor(**kwargs) -> ResourceMonitor:
    """
    Get or create global resource monitor.
    
    Args:
        **kwargs: Arguments for ResourceMonitor (only used on first call)
        
    Returns:
        Global ResourceMonitor instance
    """
    global _global_monitor
    
    with _global_monitor_lock:
        if _global_monitor is None:
            _global_monitor = ResourceMonitor(**kwargs)
            logger.info("Global resource monitor created")
        
        return _global_monitor


def reset_global_monitor():
    """Reset global monitor (for testing)"""
    global _global_monitor
    
    with _global_monitor_lock:
        if _global_monitor:
            _global_monitor.stop_sampling()
        _global_monitor = None
