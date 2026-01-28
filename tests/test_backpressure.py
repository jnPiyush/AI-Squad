"""
Tests for Backpressure and Rate Limiting

Validates queue-based backpressure and token bucket rate limiting.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from ai_squad.core.backpressure import (
    BackpressureError,
    RateLimitError,
    RateLimiter,
    StorageBackpressure,
    get_global_backpressure,
    get_global_rate_limiter,
    reset_globals,
)


class TestBackpressureBasics:
    """Test basic backpressure operations"""
    
    def test_backpressure_initialization(self):
        """Test backpressure monitor initializes correctly"""
        bp = StorageBackpressure(max_depth=50, threshold=0.7)
        
        assert bp.max_depth == 50
        assert bp.threshold == 0.7
        assert bp.get_utilization() == 0.0
        assert not bp.is_under_pressure()
    
    def test_invalid_threshold_rejected(self):
        """Test invalid threshold values raise error"""
        with pytest.raises(ValueError, match="threshold must be between"):
            StorageBackpressure(threshold=0.0)
        
        with pytest.raises(ValueError, match="threshold must be between"):
            StorageBackpressure(threshold=1.5)
    
    def test_single_acquisition(self):
        """Test single slot acquisition and release"""
        bp = StorageBackpressure(max_depth=10)
        
        with bp.acquire():
            stats = bp.get_stats()
            assert stats["queue_depth"] == 1
            assert stats["total_acquisitions"] == 1
        
        # After release
        final_stats = bp.get_stats()
        assert final_stats["queue_depth"] == 0
        assert final_stats["total_releases"] == 1
    
    def test_multiple_sequential_acquisitions(self):
        """Test multiple sequential acquisitions"""
        bp = StorageBackpressure(max_depth=10)
        
        for i in range(5):
            with bp.acquire():
                assert bp.get_stats()["queue_depth"] == 1
        
        stats = bp.get_stats()
        assert stats["total_acquisitions"] == 5
        assert stats["total_releases"] == 5
        assert stats["queue_depth"] == 0


class TestBackpressureDetection:
    """Test backpressure threshold detection"""
    
    def test_pressure_detection_at_threshold(self):
        """Test pressure detected when threshold reached"""
        bp = StorageBackpressure(max_depth=10, threshold=0.8)  # 8 slots
        
        # Acquire 7 slots - should not be under pressure
        contexts = []
        for i in range(7):
            ctx = bp.acquire()
            ctx.__enter__()
            contexts.append(ctx)
        
        assert not bp.is_under_pressure()
        assert bp.get_utilization() == 70.0
        
        # Acquire 8th slot - now under pressure
        ctx8 = bp.acquire()
        ctx8.__enter__()
        contexts.append(ctx8)
        
        assert bp.is_under_pressure()
        assert bp.get_utilization() == 80.0
        
        # Cleanup
        for ctx in contexts:
            ctx.__exit__(None, None, None)
    
    def test_utilization_calculation(self):
        """Test utilization percentage calculation"""
        bp = StorageBackpressure(max_depth=100)
        
        contexts = []
        for i in range(25):
            ctx = bp.acquire()
            ctx.__enter__()
            contexts.append(ctx)
        
        assert bp.get_utilization() == 25.0
        
        # Cleanup
        for ctx in contexts:
            ctx.__exit__(None, None, None)
    
    def test_metrics_output(self):
        """Test metrics structure"""
        bp = StorageBackpressure(max_depth=10, threshold=0.9)
        
        metrics = bp.get_metrics()
        
        assert metrics.max_queue_depth == 10
        assert metrics.threshold_percent == 90.0
        assert metrics.queue_depth == 0
        assert not metrics.under_pressure
        assert metrics.utilization_percent == 0.0
        
        # Test to_dict
        metrics_dict = metrics.to_dict()
        assert "queue_depth" in metrics_dict
        assert "under_pressure" in metrics_dict


class TestBackpressureExhaustion:
    """Test behavior when queue exhausted"""
    
    def test_queue_full_rejects_request(self):
        """Test rejection when queue full"""
        bp = StorageBackpressure(max_depth=2, timeout=0.5)
        
        # Fill queue
        ctx1 = bp.acquire()
        ctx1.__enter__()
        
        ctx2 = bp.acquire()
        ctx2.__enter__()
        
        # Third request should timeout
        with pytest.raises(BackpressureError) as exc_info:
            with bp.acquire(timeout=0.2):
                pass
        
        assert exc_info.value.queue_depth == 2
        assert exc_info.value.max_depth == 2
        
        # Cleanup
        ctx1.__exit__(None, None, None)
        ctx2.__exit__(None, None, None)
    
    def test_statistics_track_rejections(self):
        """Test rejection statistics"""
        bp = StorageBackpressure(max_depth=1, timeout=0.1)
        
        # Acquire the only slot
        ctx = bp.acquire()
        ctx.__enter__()
        
        # Try to acquire another - should reject
        try:
            with bp.acquire(timeout=0.1):
                pass
        except BackpressureError:
            pass
        
        stats = bp.get_stats()
        assert stats["total_rejections"] == 1
        
        # Cleanup
        ctx.__exit__(None, None, None)
    
    def test_recovery_after_release(self):
        """Test queue recovers after release"""
        bp = StorageBackpressure(max_depth=2)
        
        # Fill queue
        ctx1 = bp.acquire()
        ctx1.__enter__()
        
        ctx2 = bp.acquire()
        ctx2.__enter__()
        
        # Release one slot
        ctx1.__exit__(None, None, None)
        
        # Should be able to acquire now
        with bp.acquire(timeout=0.5):
            assert bp.get_stats()["queue_depth"] == 2
        
        # Cleanup
        ctx2.__exit__(None, None, None)


class TestBackpressureConcurrency:
    """Test concurrent access to backpressure monitor"""
    
    def test_concurrent_acquisitions(self):
        """Test multiple threads acquiring slots"""
        bp = StorageBackpressure(max_depth=20)
        
        def acquire_and_work(thread_id):
            with bp.acquire():
                time.sleep(0.01)  # Simulate work
            return thread_id
        
        # 50 threads with max 20 concurrent
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(acquire_and_work, i) for i in range(50)]
            results = [f.result() for f in as_completed(futures)]
        
        # All should complete
        assert len(results) == 50
        
        # Final state should be empty
        assert bp.get_stats()["queue_depth"] == 0
        
        # Peak should not exceed max
        assert bp.get_stats()["peak_depth"] <= 20
    
    def test_high_contention_handling(self):
        """Test behavior under high contention"""
        bp = StorageBackpressure(max_depth=10, timeout=2.0)
        
        successes = []
        failures = []
        
        def try_acquire(thread_id):
            try:
                with bp.acquire(timeout=0.5):
                    time.sleep(0.1)
                return ("success", thread_id)
            except BackpressureError:
                return ("failure", thread_id)
        
        # 30 threads competing for 10 slots
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(try_acquire, i) for i in range(30)]
            for future in as_completed(futures):
                status, thread_id = future.result()
                if status == "success":
                    successes.append(thread_id)
                else:
                    failures.append(thread_id)
        
        # Some should succeed, some may fail due to contention
        assert len(successes) > 0
        assert len(successes) + len(failures) == 30


class TestRateLimiterBasics:
    """Test basic rate limiter operations"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly"""
        limiter = RateLimiter(rate_per_minute=100, burst=20)
        
        assert limiter.rate == 100
        assert limiter.burst == 20
        assert limiter.window == 60.0
    
    def test_invalid_parameters_rejected(self):
        """Test invalid parameters raise errors"""
        with pytest.raises(ValueError, match="rate_per_minute must be positive"):
            RateLimiter(rate_per_minute=0)
        
        with pytest.raises(ValueError, match="burst cannot be negative"):
            RateLimiter(rate_per_minute=100, burst=-1)
    
    def test_single_request_allowed(self):
        """Test single request is allowed"""
        limiter = RateLimiter(rate_per_minute=10)
        
        assert limiter.allow("agent-1")
        assert limiter.get_current_rate("agent-1") == 1
    
    def test_multiple_requests_within_limit(self):
        """Test multiple requests within limit"""
        limiter = RateLimiter(rate_per_minute=10, burst=5)
        
        # 10 requests should all be allowed
        for i in range(10):
            assert limiter.allow("agent-1")
        
        assert limiter.get_current_rate("agent-1") == 10
    
    def test_requests_beyond_limit_rejected(self):
        """Test requests beyond limit are rejected"""
        limiter = RateLimiter(rate_per_minute=5, burst=2)
        
        # First 7 requests allowed (rate + burst)
        for i in range(7):
            assert limiter.allow("agent-1")
        
        # 8th request should be rejected
        assert not limiter.allow("agent-1")
        
        stats = limiter.get_stats()
        assert stats["total_allowed"] == 7
        assert stats["total_rejected"] == 1


class TestRateLimiterPerAgent:
    """Test per-agent rate limiting"""
    
    def test_different_agents_independent_limits(self):
        """Test agents have independent rate limits"""
        limiter = RateLimiter(rate_per_minute=5, burst=0)
        
        # Agent 1 uses 5 requests
        for i in range(5):
            assert limiter.allow("agent-1")
        
        # Agent 1 is now limited
        assert not limiter.allow("agent-1")
        
        # Agent 2 should still have full quota
        for i in range(5):
            assert limiter.allow("agent-2")
        
        # Agent 2 is now also limited
        assert not limiter.allow("agent-2")
    
    def test_multiple_agents_statistics(self):
        """Test statistics track multiple agents"""
        limiter = RateLimiter(rate_per_minute=10, burst=0)
        
        # Agent 1: 12 requests (2 rejected)
        for i in range(12):
            limiter.allow("agent-1")
        
        # Agent 2: 8 requests (0 rejected)
        for i in range(8):
            limiter.allow("agent-2")
        
        stats = limiter.get_stats()
        assert stats["active_agents"] == 2
        assert stats["rejections_by_agent"]["agent-1"] == 2
        assert "agent-2" not in stats["rejections_by_agent"]


class TestRateLimiterTimeWindow:
    """Test sliding time window behavior"""
    
    def test_tokens_expire_after_window(self):
        """Test tokens expire after time window"""
        limiter = RateLimiter(rate_per_minute=5, burst=0, window_seconds=0.5)
        
        # Use all tokens
        for i in range(5):
            assert limiter.allow("agent-1")
        
        # Should be rate limited
        assert not limiter.allow("agent-1")
        
        # Wait for window to expire
        time.sleep(0.6)
        
        # Should have tokens again
        assert limiter.allow("agent-1")
    
    def test_wait_time_calculation(self):
        """Test wait time calculation"""
        limiter = RateLimiter(rate_per_minute=5, burst=0, window_seconds=1.0)
        
        # Use all tokens
        for i in range(5):
            limiter.allow("agent-1")
        
        # Get wait time
        wait_time = limiter.get_wait_time("agent-1")
        
        # Should be positive (within window)
        assert wait_time > 0
        assert wait_time <= 1.0
        
        # After waiting, should be allowed
        time.sleep(wait_time + 0.1)
        assert limiter.allow("agent-1")
    
    def test_wait_time_zero_when_tokens_available(self):
        """Test wait time is zero when tokens available"""
        limiter = RateLimiter(rate_per_minute=10)
        
        # No tokens used yet
        assert limiter.get_wait_time("agent-1") == 0.0
        
        # Use some tokens
        for i in range(5):
            limiter.allow("agent-1")
        
        # Still have tokens, no wait
        assert limiter.get_wait_time("agent-1") == 0.0


class TestRateLimiterContextManager:
    """Test rate limiter context manager"""
    
    def test_context_manager_success(self):
        """Test context manager allows request"""
        limiter = RateLimiter(rate_per_minute=10)
        
        with limiter.acquire("agent-1"):
            assert limiter.get_current_rate("agent-1") == 1
    
    def test_context_manager_retry_on_limit(self):
        """Test context manager retries when rate limited"""
        limiter = RateLimiter(rate_per_minute=2, burst=0, window_seconds=0.5)
        
        # Use all tokens
        for i in range(2):
            limiter.allow("agent-1")
        
        # Context manager should retry and succeed after window
        with limiter.acquire("agent-1", max_retries=3):
            # Should succeed after wait
            assert limiter.get_current_rate("agent-1") >= 1
    
    def test_context_manager_raises_after_max_retries(self):
        """Test context manager raises after max retries"""
        limiter = RateLimiter(rate_per_minute=2, burst=0, window_seconds=10.0)
        
        # Use all tokens
        for i in range(2):
            limiter.allow("agent-1")
        
        # Should fail quickly with short retries
        with pytest.raises(RateLimitError) as exc_info:
            with limiter.acquire("agent-1", max_retries=1):
                pass
        
        assert exc_info.value.agent == "agent-1"
        assert exc_info.value.rate_limit == 2


class TestRateLimiterConcurrency:
    """Test concurrent rate limiting"""
    
    def test_concurrent_requests_same_agent(self):
        """Test concurrent requests from same agent"""
        limiter = RateLimiter(rate_per_minute=50, burst=10)
        
        def make_request(req_id):
            if limiter.allow("agent-1"):
                return ("allowed", req_id)
            return ("rejected", req_id)
        
        # 100 concurrent requests
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(make_request, i) for i in range(100)]
            results = [f.result() for f in as_completed(futures)]
        
        allowed = [r for r in results if r[0] == "allowed"]
        rejected = [r for r in results if r[0] == "rejected"]
        
        # Should allow rate + burst, reject rest
        assert len(allowed) == 60  # 50 + 10
        assert len(rejected) == 40
    
    def test_concurrent_requests_multiple_agents(self):
        """Test concurrent requests from multiple agents"""
        limiter = RateLimiter(rate_per_minute=10, burst=0)
        
        def make_request(agent_id):
            allowed_count = 0
            for i in range(15):  # Try 15 requests per agent
                if limiter.allow(f"agent-{agent_id}"):
                    allowed_count += 1
            return agent_id, allowed_count
        
        # 5 agents making requests concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [f.result() for f in as_completed(futures)]
        
        # Each agent should get exactly 10 requests
        for agent_id, allowed in results:
            assert allowed == 10


class TestGlobalInstances:
    """Test global instance management"""
    
    def test_global_backpressure_singleton(self):
        """Test global backpressure singleton"""
        reset_globals()
        
        bp1 = get_global_backpressure(max_depth=100)
        bp2 = get_global_backpressure(max_depth=50)  # Should be ignored
        
        assert bp1 is bp2
        assert bp1.max_depth == 100  # First config wins
        
        reset_globals()
    
    def test_global_rate_limiter_singleton(self):
        """Test global rate limiter singleton"""
        reset_globals()
        
        rl1 = get_global_rate_limiter(rate_per_minute=100)
        rl2 = get_global_rate_limiter(rate_per_minute=50)  # Should be ignored
        
        assert rl1 is rl2
        assert rl1.rate == 100  # First config wins
        
        reset_globals()


class TestStatisticsAndReset:
    """Test statistics tracking and reset"""
    
    def test_backpressure_stats_reset(self):
        """Test backpressure statistics reset"""
        bp = StorageBackpressure(max_depth=10)
        
        # Generate some stats
        with bp.acquire():
            pass
        
        assert bp.get_stats()["total_acquisitions"] == 1
        
        # Reset
        bp.reset_stats()
        
        stats = bp.get_stats()
        assert stats["total_acquisitions"] == 0
        assert stats["total_releases"] == 0
        assert stats["peak_depth"] == 0
    
    def test_rate_limiter_stats_reset(self):
        """Test rate limiter statistics reset"""
        limiter = RateLimiter(rate_per_minute=10)
        
        # Generate some stats
        for i in range(15):
            limiter.allow("agent-1")
        
        assert limiter.get_stats()["total_allowed"] > 0
        
        # Reset
        limiter.reset_stats()
        
        stats = limiter.get_stats()
        assert stats["total_allowed"] == 0
        assert stats["total_rejected"] == 0
    
    def test_rate_limiter_clear_agent(self):
        """Test clearing specific agent"""
        limiter = RateLimiter(rate_per_minute=5, burst=0)
        
        # Use tokens for agent-1
        for i in range(5):
            limiter.allow("agent-1")
        
        # Clear agent-1
        limiter.clear_agent("agent-1")
        
        # Agent-1 should have full quota again
        for i in range(5):
            assert limiter.allow("agent-1")
