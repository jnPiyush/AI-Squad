"""
Tests for resource monitoring and adaptive concurrency.

Tests cover:
- Basic metrics collection
- Parallelism calculation
- Throttling logic
- Background sampling
- Global singleton
"""
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import pytest

from ai_squad.core.resource_monitor import (
    ResourceMonitor,
    ResourceMetrics,
    get_global_monitor,
    reset_global_monitor,
    HAS_PSUTIL
)


@pytest.fixture
def monitor():
    """Create monitor for testing"""
    m = ResourceMonitor(sample_interval=0.1, history_size=10)
    yield m
    m.stop_sampling()


@pytest.fixture(autouse=True)
def reset_monitor():
    """Reset global monitor after each test"""
    yield
    reset_global_monitor()


class TestResourceMetrics:
    """Test ResourceMetrics dataclass"""
    
    def test_metrics_creation(self):
        """Test creating metrics object"""
        metrics = ResourceMetrics(
            cpu_percent=45.5,
            memory_percent=62.3,
            memory_available_mb=2048.0,
            process_memory_mb=128.5,
            process_cpu_percent=12.3,
            thread_count=8,
            timestamp=time.time()
        )
        
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 62.3
        assert metrics.thread_count == 8
    
    def test_to_dict(self):
        """Test converting metrics to dictionary"""
        metrics = ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=1024.0,
            process_memory_mb=100.0,
            process_cpu_percent=10.0,
            thread_count=5,
            timestamp=123.456
        )
        
        d = metrics.to_dict()
        
        assert d["cpu_percent"] == 50.0
        assert d["memory_percent"] == 60.0
        assert d["timestamp"] == 123.456
    
    def test_is_resource_constrained(self):
        """Test resource constraint detection"""
        # Not constrained
        metrics = ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=1024.0,
            process_memory_mb=100.0,
            process_cpu_percent=10.0,
            thread_count=5,
            timestamp=time.time()
        )
        
        assert not metrics.is_resource_constrained()
        
        # CPU constrained
        metrics.cpu_percent = 85.0
        assert metrics.is_resource_constrained(cpu_threshold=80.0)
        
        # Memory constrained
        metrics.cpu_percent = 50.0
        metrics.memory_percent = 90.0
        assert metrics.is_resource_constrained(memory_threshold=85.0)


class TestResourceMonitorBasics:
    """Test basic monitor functionality"""
    
    def test_initialization(self):
        """Test monitor initialization"""
        monitor = ResourceMonitor(
            sample_interval=0.5,
            history_size=20,
            auto_sample=False
        )
        
        assert monitor.sample_interval == 0.5
        assert monitor.history_size == 20
        assert not monitor.auto_sample
    
    def test_get_current_metrics(self, monitor):
        """Test getting current metrics"""
        metrics = monitor.get_current_metrics()
        
        assert isinstance(metrics, ResourceMetrics)
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.thread_count > 0
        assert metrics.timestamp > 0
    
    def test_sample_adds_to_history(self, monitor):
        """Test sampling adds to history"""
        # Take a few samples
        for _ in range(3):
            monitor.sample()
            time.sleep(0.05)
        
        stats = monitor.get_stats()
        assert stats["samples_collected"] == 3
    
    def test_history_size_limit(self, monitor):
        """Test history respects size limit"""
        monitor.history_size = 5
        
        # Take more samples than limit
        for _ in range(10):
            monitor.sample()
        
        stats = monitor.get_stats()
        assert stats["samples_collected"] == 5


class TestParallelismCalculation:
    """Test optimal parallelism calculation"""
    
    @patch('ai_squad.core.resource_monitor.HAS_PSUTIL', False)
    def test_basic_calculation(self, monitor):
        """Test parallelism calculation with basic metrics"""
        # Monitor without psutil returns conservative estimates
        parallelism = monitor.calculate_optimal_parallelism(
            max_parallel=20,
            baseline=5
        )
        
        # Should return value between baseline and max
        assert 5 <= parallelism <= 20
    
    def test_high_resources_max_parallelism(self, monitor):
        """Test high resources give max parallelism"""
        # Mock high available resources
        mock_metrics = ResourceMetrics(
            cpu_percent=10.0,  # 90% available
            memory_percent=10.0,  # 90% available
            memory_available_mb=8192.0,
            process_memory_mb=100.0,
            process_cpu_percent=5.0,
            thread_count=5,
            timestamp=time.time()
        )
        
        with patch.object(monitor, 'get_current_metrics', return_value=mock_metrics):
            parallelism = monitor.calculate_optimal_parallelism(
                max_parallel=20,
                baseline=5
            )
            
            # High resources → max parallelism
            assert parallelism == 20
    
    def test_low_resources_baseline_parallelism(self, monitor):
        """Test low resources give baseline parallelism"""
        # Mock low available resources
        mock_metrics = ResourceMetrics(
            cpu_percent=90.0,  # 10% available
            memory_percent=90.0,  # 10% available
            memory_available_mb=128.0,
            process_memory_mb=500.0,
            process_cpu_percent=80.0,
            thread_count=20,
            timestamp=time.time()
        )
        
        with patch.object(monitor, 'get_current_metrics', return_value=mock_metrics):
            parallelism = monitor.calculate_optimal_parallelism(
                max_parallel=20,
                baseline=5
            )
            
            # Low resources → baseline
            assert parallelism == 5
    
    def test_medium_resources_scaled_parallelism(self, monitor):
        """Test medium resources give scaled parallelism"""
        # Mock medium available resources
        mock_metrics = ResourceMetrics(
            cpu_percent=50.0,  # 50% available
            memory_percent=50.0,  # 50% available
            memory_available_mb=2048.0,
            process_memory_mb=200.0,
            process_cpu_percent=25.0,
            thread_count=10,
            timestamp=time.time()
        )
        
        with patch.object(monitor, 'get_current_metrics', return_value=mock_metrics):
            parallelism = monitor.calculate_optimal_parallelism(
                max_parallel=20,
                baseline=5
            )
            
            # Medium resources → between baseline and max
            assert 5 < parallelism < 20


class TestThrottling:
    """Test throttling logic"""
    
    def test_should_throttle_high_cpu(self, monitor):
        """Test throttling with high CPU"""
        mock_metrics = ResourceMetrics(
            cpu_percent=85.0,  # Above threshold
            memory_percent=50.0,
            memory_available_mb=2048.0,
            process_memory_mb=100.0,
            process_cpu_percent=50.0,
            thread_count=10,
            timestamp=time.time()
        )
        
        with patch.object(monitor, 'get_current_metrics', return_value=mock_metrics):
            assert monitor.should_throttle(cpu_threshold=80.0)
    
    def test_should_throttle_high_memory(self, monitor):
        """Test throttling with high memory"""
        mock_metrics = ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=90.0,  # Above threshold
            memory_available_mb=128.0,
            process_memory_mb=500.0,
            process_cpu_percent=25.0,
            thread_count=10,
            timestamp=time.time()
        )
        
        with patch.object(monitor, 'get_current_metrics', return_value=mock_metrics):
            assert monitor.should_throttle(memory_threshold=85.0)
    
    def test_no_throttle_low_usage(self, monitor):
        """Test no throttling with low usage"""
        mock_metrics = ResourceMetrics(
            cpu_percent=30.0,
            memory_percent=40.0,
            memory_available_mb=4096.0,
            process_memory_mb=100.0,
            process_cpu_percent=10.0,
            thread_count=5,
            timestamp=time.time()
        )
        
        with patch.object(monitor, 'get_current_metrics', return_value=mock_metrics):
            assert not monitor.should_throttle()
    
    def test_throttle_factor(self, monitor):
        """Test throttle factor calculation"""
        # No throttling needed
        mock_metrics = ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=50.0,
            memory_available_mb=2048.0,
            process_memory_mb=100.0,
            process_cpu_percent=25.0,
            thread_count=10,
            timestamp=time.time()
        )
        
        with patch.object(monitor, 'get_current_metrics', return_value=mock_metrics):
            factor = monitor.get_throttle_factor()
            assert factor == 1.0  # No throttling
        
        # Heavy throttling needed
        mock_metrics.cpu_percent = 95.0
        
        with patch.object(monitor, 'get_current_metrics', return_value=mock_metrics):
            factor = monitor.get_throttle_factor(cpu_threshold=80.0)
            assert 0.0 <= factor < 0.5  # Heavy throttle


class TestBackgroundSampling:
    """Test background sampling thread"""
    
    def test_start_stop_sampling(self, monitor):
        """Test starting and stopping sampling"""
        monitor.start_sampling()
        time.sleep(0.3)  # Let it sample a few times
        
        stats = monitor.get_stats()
        assert stats["sampling_active"]
        assert stats["samples_collected"] > 0
        
        monitor.stop_sampling()
        
        stats = monitor.get_stats()
        assert not stats["sampling_active"]
    
    def test_auto_sampling_on_init(self):
        """Test auto-sampling starts on initialization"""
        monitor = ResourceMonitor(
            sample_interval=0.1,
            auto_sample=True
        )
        
        time.sleep(0.3)
        
        stats = monitor.get_stats()
        assert stats["sampling_active"]
        assert stats["samples_collected"] > 0
        
        monitor.stop_sampling()
    
    def test_start_sampling_twice_warning(self, monitor, caplog):
        """Test warning when starting sampling twice"""
        monitor.start_sampling()
        monitor.start_sampling()  # Should warn
        
        assert "already running" in caplog.text.lower()
        
        monitor.stop_sampling()


class TestAverageMetrics:
    """Test average metrics calculation"""
    
    def test_get_average_metrics(self, monitor):
        """Test averaging over time window"""
        # Take several samples
        for _ in range(5):
            monitor.sample()
            time.sleep(0.05)
        
        avg = monitor.get_average_metrics(window_seconds=1.0)
        
        assert avg is not None
        assert 0 <= avg.cpu_percent <= 100
        assert 0 <= avg.memory_percent <= 100
    
    def test_get_average_no_history(self, monitor):
        """Test averaging with no history"""
        avg = monitor.get_average_metrics()
        
        assert avg is None
    
    def test_get_average_filters_old_samples(self, monitor):
        """Test averaging filters out old samples"""
        # Take samples
        for _ in range(3):
            monitor.sample()
            time.sleep(0.05)
        
        # Wait for samples to age out
        time.sleep(0.5)
        
        # Ask for very recent window
        avg = monitor.get_average_metrics(window_seconds=0.1)
        
        # Should have no recent samples
        assert avg is None


class TestGlobalMonitor:
    """Test global monitor singleton"""
    
    def test_get_global_monitor(self):
        """Test getting global monitor"""
        monitor1 = get_global_monitor(sample_interval=0.5)
        monitor2 = get_global_monitor()
        
        # Should be same instance
        assert monitor1 is monitor2
    
    def test_reset_global_monitor(self):
        """Test resetting global monitor"""
        monitor1 = get_global_monitor()
        reset_global_monitor()
        monitor2 = get_global_monitor()
        
        # Should be different instances
        assert monitor1 is not monitor2


class TestStats:
    """Test statistics reporting"""
    
    def test_get_stats(self, monitor):
        """Test getting monitor stats"""
        # Take a sample
        monitor.sample()
        
        stats = monitor.get_stats()
        
        assert "has_psutil" in stats
        assert "sample_interval" in stats
        assert "samples_collected" in stats
        assert "current_metrics" in stats
        assert stats["samples_collected"] == 1
    
    def test_stats_with_sampling(self, monitor):
        """Test stats with active sampling"""
        monitor.start_sampling()
        time.sleep(0.3)
        
        stats = monitor.get_stats()
        
        assert stats["sampling_active"]
        assert stats["samples_collected"] > 0
        
        monitor.stop_sampling()


@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil required")
class TestWithPsutil:
    """Tests that require psutil"""
    
    def test_detailed_metrics_with_psutil(self, monitor):
        """Test detailed metrics when psutil available"""
        metrics = monitor.get_current_metrics()
        
        # Should have real values, not estimates
        assert metrics.cpu_percent >= 0
        assert metrics.memory_percent >= 0
        assert metrics.process_memory_mb > 0
        assert metrics.thread_count > 0
    
    def test_process_metrics(self, monitor):
        """Test process-specific metrics"""
        metrics = monitor.get_current_metrics()
        
        # Process should have some CPU and memory usage
        assert metrics.process_cpu_percent >= 0
        assert metrics.process_memory_mb > 0


def test_without_psutil():
    """Test fallback when psutil not available"""
    with patch('ai_squad.core.resource_monitor.HAS_PSUTIL', False):
        monitor = ResourceMonitor()
        metrics = monitor.get_current_metrics()
        
        # Should return conservative estimates
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 50.0
        assert metrics.thread_count > 0  # Uses threading.active_count()
