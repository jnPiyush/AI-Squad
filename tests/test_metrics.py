"""
Tests for metrics collection framework.

Tests cover:
- Convoy metrics collection
- Resource metrics recording
- Agent metrics tracking
- Query and aggregation
- Cleanup operations
"""
import tempfile
import time
import shutil
from pathlib import Path
import pytest

from ai_squad.core.metrics import (
    MetricsCollector,
    ConvoyMetrics,
    ResourceMetrics,
    AgentMetrics,
    MetricType,
    get_global_collector,
    reset_global_collector
)


@pytest.fixture
def temp_db():
    """Create temporary database"""
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test_metrics.db"
    yield str(db_path)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def collector(temp_db):
    """Create metrics collector"""
    return MetricsCollector(db_path=temp_db, retention_days=7)


@pytest.fixture(autouse=True)
def reset_collector():
    """Reset global collector after each test"""
    yield
    reset_global_collector()


class TestConvoyMetrics:
    """Test convoy metrics collection"""
    
    def test_convoy_metrics_creation(self):
        """Test creating convoy metrics"""
        metrics = ConvoyMetrics(
            convoy_id="convoy-123",
            convoy_name="Test Convoy",
            started_at=time.time(),
            total_members=10
        )
        
        assert metrics.convoy_id == "convoy-123"
        assert metrics.convoy_name == "Test Convoy"
        assert metrics.total_members == 10
        assert metrics.status == "pending"
    
    def test_convoy_metrics_mark_complete(self):
        """Test marking convoy as complete"""
        start_time = time.time()
        metrics = ConvoyMetrics(
            convoy_id="convoy-123",
            convoy_name="Test",
            started_at=start_time,
            total_members=5
        )
        
        time.sleep(0.1)
        metrics.mark_complete()
        
        assert metrics.completed_at is not None
        assert metrics.duration_seconds is not None
        assert metrics.duration_seconds > 0
        assert metrics.status == "completed"
    
    def test_convoy_metrics_to_dict(self):
        """Test converting metrics to dict"""
        metrics = ConvoyMetrics(
            convoy_id="convoy-123",
            convoy_name="Test",
            started_at=time.time()
        )
        
        d = metrics.to_dict()
        
        assert d["convoy_id"] == "convoy-123"
        assert d["convoy_name"] == "Test"
        assert "started_at" in d


class TestResourceMetrics:
    """Test resource metrics"""
    
    def test_resource_metrics_creation(self):
        """Test creating resource metrics"""
        metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=45.5,
            memory_percent=62.3,
            memory_available_mb=2048.0,
            process_memory_mb=128.5,
            process_cpu_percent=12.3,
            thread_count=8
        )
        
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 62.3
        assert metrics.thread_count == 8
    
    def test_resource_metrics_to_dict(self):
        """Test converting to dict"""
        metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=1024.0,
            process_memory_mb=100.0,
            process_cpu_percent=10.0,
            thread_count=5
        )
        
        d = metrics.to_dict()
        
        assert d["cpu_percent"] == 50.0
        assert d["memory_percent"] == 60.0


class TestAgentMetrics:
    """Test agent metrics"""
    
    def test_agent_metrics_creation(self):
        """Test creating agent metrics"""
        metrics = AgentMetrics(
            agent_id="agent-123",
            agent_type="pm",
            work_item_id="issue-456",
            convoy_id="convoy-789"
        )
        
        assert metrics.agent_id == "agent-123"
        assert metrics.agent_type == "pm"
        assert metrics.status == "pending"
    
    def test_agent_metrics_mark_complete(self):
        """Test marking agent as complete"""
        metrics = AgentMetrics(
            agent_id="agent-123",
            agent_type="engineer",
            work_item_id="issue-456",
            started_at=time.time()
        )
        
        time.sleep(0.05)
        metrics.mark_complete(status="completed")
        
        assert metrics.completed_at is not None
        assert metrics.duration_seconds is not None
        assert metrics.duration_seconds > 0
        assert metrics.status == "completed"
    
    def test_agent_metrics_mark_failed(self):
        """Test marking agent as failed"""
        metrics = AgentMetrics(
            agent_id="agent-123",
            agent_type="engineer",
            work_item_id="issue-456",
            started_at=time.time()
        )
        
        metrics.mark_complete(status="failed", error="Test error")
        
        assert metrics.status == "failed"
        assert metrics.error == "Test error"


class TestMetricsCollector:
    """Test metrics collector"""
    
    def test_collector_initialization(self, temp_db):
        """Test collector initialization"""
        collector = MetricsCollector(
            db_path=temp_db,
            retention_days=30
        )
        
        assert collector.db_path.exists()
        assert collector.retention_days == 30
    
    def test_record_convoy_start(self, collector):
        """Test recording convoy start"""
        metrics = ConvoyMetrics(
            convoy_id="convoy-123",
            convoy_name="Test Convoy",
            started_at=time.time(),
            total_members=5,
            initial_parallelism=3
        )
        
        collector.record_convoy_start(metrics)
        
        # Verify stored
        recent = collector.get_recent_convoy_metrics(limit=1)
        assert len(recent) == 1
        assert recent[0]["convoy_id"] == "convoy-123"
        assert recent[0]["total_members"] == 5
    
    def test_update_convoy_metrics(self, collector):
        """Test updating convoy metrics"""
        # Start convoy
        metrics = ConvoyMetrics(
            convoy_id="convoy-123",
            convoy_name="Test",
            started_at=time.time(),
            total_members=10
        )
        collector.record_convoy_start(metrics)
        
        # Update progress
        metrics.completed_members = 5
        metrics.failed_members = 1
        metrics.peak_cpu_percent = 75.0
        collector.update_convoy_metrics(metrics)
        
        # Verify update
        recent = collector.get_recent_convoy_metrics(limit=1)
        assert recent[0]["completed_members"] == 5
        assert recent[0]["failed_members"] == 1
        assert recent[0]["peak_cpu_percent"] == 75.0
    
    def test_record_convoy_complete(self, collector):
        """Test recording convoy completion"""
        start_time = time.time()
        metrics = ConvoyMetrics(
            convoy_id="convoy-123",
            convoy_name="Test",
            started_at=start_time,
            total_members=5
        )
        collector.record_convoy_start(metrics)
        
        time.sleep(0.1)
        
        # Mark complete
        metrics.completed_members = 5
        metrics.mark_complete()
        collector.record_convoy_complete(metrics)
        
        # Verify completion
        recent = collector.get_recent_convoy_metrics(limit=1)
        assert recent[0]["status"] == "completed"
        assert recent[0]["duration_seconds"] is not None
        assert recent[0]["duration_seconds"] > 0
    
    def test_record_resource_snapshot(self, collector):
        """Test recording resource snapshots"""
        for i in range(5):
            metrics = ResourceMetrics(
                timestamp=time.time() + i,
                cpu_percent=50.0 + i,
                memory_percent=60.0 + i,
                memory_available_mb=2048.0,
                process_memory_mb=100.0,
                process_cpu_percent=10.0,
                thread_count=5 + i
            )
            collector.record_resource_snapshot(metrics)
        
        # Query resources
        resources = collector.get_resource_metrics(hours=1)
        assert len(resources) >= 5
    
    def test_record_agent_execution(self, collector):
        """Test recording agent execution"""
        # Start agent
        metrics = AgentMetrics(
            agent_id="agent-123",
            agent_type="pm",
            work_item_id="issue-456",
            convoy_id="convoy-789",
            started_at=time.time(),
            cpu_percent_start=20.0,
            memory_mb_start=100.0
        )
        collector.record_agent_start(metrics)
        
        time.sleep(0.05)
        
        # Complete agent
        metrics.mark_complete()
        metrics.cpu_percent_end = 30.0
        metrics.memory_mb_end = 150.0
        collector.record_agent_complete(metrics)
        
        # Query via convoy stats (indirect check)
        stats = collector.get_stats()
        assert stats["agent_metrics"] >= 1
    
    def test_get_recent_convoy_metrics(self, collector):
        """Test getting recent convoy metrics"""
        # Create several convoys
        for i in range(5):
            metrics = ConvoyMetrics(
                convoy_id=f"convoy-{i}",
                convoy_name=f"Convoy {i}",
                started_at=time.time() + i,
                total_members=5
            )
            collector.record_convoy_start(metrics)
        
        # Get recent
        recent = collector.get_recent_convoy_metrics(limit=3)
        assert len(recent) == 3
        
        # Should be in reverse chronological order
        assert recent[0]["convoy_id"] == "convoy-4"
    
    def test_get_convoy_stats(self, collector):
        """Test getting convoy statistics"""
        # Create mix of convoys
        for i in range(10):
            metrics = ConvoyMetrics(
                convoy_id=f"convoy-{i}",
                convoy_name=f"Convoy {i}",
                started_at=time.time(),
                total_members=5
            )
            metrics.completed_members = 5
            
            if i % 3 == 0:
                metrics.status = "failed"
            else:
                metrics.mark_complete()
            
            collector.record_convoy_start(metrics)
            collector.record_convoy_complete(metrics)
        
        # Get stats
        stats = collector.get_convoy_stats(hours=1)
        
        assert stats["total_convoys"] == 10
        assert stats["completed"] > 0
        assert stats["failed"] > 0
    
    def test_cleanup_old_metrics(self, collector):
        """Test cleaning up old metrics"""
        # Create old convoy
        old_time = time.time() - (10 * 86400)  # 10 days ago
        metrics = ConvoyMetrics(
            convoy_id="old-convoy",
            convoy_name="Old",
            started_at=old_time,
            total_members=5
        )
        collector.record_convoy_start(metrics)
        
        # Create recent convoy
        metrics = ConvoyMetrics(
            convoy_id="new-convoy",
            convoy_name="New",
            started_at=time.time(),
            total_members=5
        )
        collector.record_convoy_start(metrics)
        
        # Should have 2 convoys
        assert len(collector.get_recent_convoy_metrics(limit=10)) == 2
        
        # Cleanup (7 day retention)
        collector.cleanup_old_metrics(days=7)
        
        # Should have only 1 convoy left
        recent = collector.get_recent_convoy_metrics(limit=10)
        assert len(recent) == 1
        assert recent[0]["convoy_id"] == "new-convoy"
    
    def test_get_stats(self, collector):
        """Test getting collector stats"""
        # Add some metrics
        convoy_metrics = ConvoyMetrics(
            convoy_id="convoy-123",
            convoy_name="Test",
            started_at=time.time()
        )
        collector.record_convoy_start(convoy_metrics)
        
        resource_metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=2048.0,
            process_memory_mb=100.0,
            process_cpu_percent=10.0,
            thread_count=5
        )
        collector.record_resource_snapshot(resource_metrics)
        
        # Get stats
        stats = collector.get_stats()
        
        assert "db_path" in stats
        assert "db_size_mb" in stats
        assert stats["convoy_metrics"] >= 1
        assert stats["resource_metrics"] >= 1


class TestGlobalCollector:
    """Test global collector singleton"""
    
    def test_get_global_collector(self, temp_db):
        """Test getting global collector"""
        collector1 = get_global_collector(db_path=temp_db)
        collector2 = get_global_collector()
        
        # Should be same instance
        assert collector1 is collector2
    
    def test_reset_global_collector(self, temp_db):
        """Test resetting global collector"""
        collector1 = get_global_collector(db_path=temp_db)
        reset_global_collector()
        collector2 = get_global_collector(db_path=temp_db)
        
        # Should be different instances
        assert collector1 is not collector2


class TestMetricsFiltering:
    """Test filtering and querying metrics"""
    
    def test_filter_by_status(self, collector):
        """Test filtering convoys by status"""
        # Create convoys with different statuses
        for i in range(5):
            metrics = ConvoyMetrics(
                convoy_id=f"convoy-{i}",
                convoy_name=f"Convoy {i}",
                started_at=time.time()
            )
            if i % 2 == 0:
                metrics.status = "completed"
            else:
                metrics.status = "failed"
            
            collector.record_convoy_start(metrics)
        
        # Filter by status
        completed = collector.get_recent_convoy_metrics(limit=10, status="completed")
        failed = collector.get_recent_convoy_metrics(limit=10, status="failed")
        
        assert len(completed) == 3
        assert len(failed) == 2
    
    def test_time_range_queries(self, collector):
        """Test querying metrics by time range"""
        # Create metrics at different times
        for i in range(5):
            metrics = ConvoyMetrics(
                convoy_id=f"convoy-{i}",
                convoy_name=f"Convoy {i}",
                started_at=time.time() - (i * 3600)  # i hours ago
            )
            collector.record_convoy_start(metrics)
        
        # Query last 2 hours
        stats_2h = collector.get_convoy_stats(hours=2)
        
        # Query last 10 hours
        stats_10h = collector.get_convoy_stats(hours=10)
        
        # Should have more convoys in wider window
        assert stats_10h["total_convoys"] > stats_2h["total_convoys"]


class TestConcurrency:
    """Test concurrent metrics collection"""
    
    def test_concurrent_convoy_recording(self, collector):
        """Test recording multiple convoys concurrently"""
        import concurrent.futures
        
        def record_convoy(i):
            metrics = ConvoyMetrics(
                convoy_id=f"convoy-{i}",
                convoy_name=f"Convoy {i}",
                started_at=time.time(),
                total_members=5
            )
            collector.record_convoy_start(metrics)
            time.sleep(0.01)
            metrics.completed_members = 5
            collector.update_convoy_metrics(metrics)
            return i
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(record_convoy, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert len(results) == 20
        
        # All convoys should be recorded
        recent = collector.get_recent_convoy_metrics(limit=25)
        assert len(recent) == 20
    
    def test_concurrent_resource_recording(self, collector):
        """Test recording resource metrics concurrently"""
        import concurrent.futures
        
        def record_resource(i):
            metrics = ResourceMetrics(
                timestamp=time.time() + i,
                cpu_percent=50.0,
                memory_percent=60.0,
                memory_available_mb=2048.0,
                process_memory_mb=100.0,
                process_cpu_percent=10.0,
                thread_count=5
            )
            collector.record_resource_snapshot(metrics)
            return i
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(record_resource, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert len(results) == 50
        
        # All snapshots should be recorded
        resources = collector.get_resource_metrics(hours=1)
        assert len(resources) >= 50
