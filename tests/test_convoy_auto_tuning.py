"""
Tests for convoy system with resource-adaptive parallelism.

Tests cover:
- Basic convoy creation and execution
- Auto-tuning based on resource availability
- Dynamic throttling during execution
- Integration with resource monitor
"""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil

from ai_squad.core.convoy import (
    Convoy,
    ConvoyMember,
    ConvoyManager,
    ConvoyStatus
)
from ai_squad.core.workstate import WorkStateManager
from ai_squad.core.resource_monitor import ResourceMetrics, get_global_monitor, reset_global_monitor


@pytest.fixture
def temp_workspace():
    """Create temporary workspace"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def work_state_manager(temp_workspace):
    """Create work state manager"""
    return WorkStateManager(temp_workspace)


@pytest.fixture
def convoy_manager(work_state_manager):
    """Create convoy manager"""
    return ConvoyManager(work_state_manager)


@pytest.fixture(autouse=True)
def reset_resource_monitor():
    """Reset global resource monitor after each test"""
    yield
    reset_global_monitor()


class TestConvoyBasics:
    """Test basic convoy functionality"""
    
    def test_convoy_creation(self):
        """Test creating a convoy"""
        convoy = Convoy(
            id="test-convoy",
            name="Test Convoy",
            description="Test convoy description",
            max_parallel=10
        )
        
        assert convoy.id == "test-convoy"
        assert convoy.name == "Test Convoy"
        assert convoy.max_parallel == 10
        assert convoy.status == ConvoyStatus.PENDING
    
    def test_convoy_auto_tuning_defaults(self):
        """Test auto-tuning default settings"""
        convoy = Convoy(
            id="test-convoy",
            name="Test Convoy"
        )
        
        # Auto-tuning should be enabled by default
        assert convoy.enable_auto_tuning == True
        assert convoy.baseline_parallel == 5
        assert convoy.cpu_threshold == 80.0
        assert convoy.memory_threshold == 85.0
    
    def test_convoy_add_member(self):
        """Test adding members to convoy"""
        convoy = Convoy(id="test", name="Test")
        
        member = convoy.add_member(
            agent_type="pm",
            work_item_id="issue-123"
        )
        
        assert len(convoy.members) == 1
        assert member.agent_type == "pm"
        assert member.work_item_id == "issue-123"
        assert member.status == "pending"
    
    def test_convoy_get_member(self):
        """Test getting member by work item ID"""
        convoy = Convoy(id="test", name="Test")
        convoy.add_member("pm", "issue-123")
        convoy.add_member("engineer", "issue-456")
        
        member = convoy.get_member("issue-123")
        assert member is not None
        assert member.agent_type == "pm"
        
        missing = convoy.get_member("issue-999")
        assert missing is None
    
    def test_convoy_is_complete(self):
        """Test completion checking"""
        convoy = Convoy(id="test", name="Test")
        convoy.add_member("pm", "issue-123")
        convoy.add_member("engineer", "issue-456")
        
        # Not complete initially
        assert not convoy.is_complete()
        
        # Mark members complete
        convoy.members[0].status = "completed"
        convoy.members[1].status = "completed"
        
        assert convoy.is_complete()
    
    def test_convoy_get_progress(self):
        """Test progress reporting"""
        convoy = Convoy(id="test", name="Test")
        convoy.add_member("pm", "issue-1")
        convoy.add_member("engineer", "issue-2")
        convoy.add_member("ux", "issue-3")
        
        # Mark one complete, one failed
        convoy.members[0].status = "completed"
        convoy.members[1].status = "failed"
        convoy.members[2].status = "running"
        
        progress = convoy.get_progress()
        
        assert progress["total"] == 3
        assert progress["completed"] == 1
        assert progress["failed"] == 1
        assert progress["running"] == 1
        assert progress["pending"] == 0
        assert progress["progress_percent"] == 66  # 2/3 done


class TestConvoyManager:
    """Test convoy manager"""
    
    def test_create_convoy(self, convoy_manager):
        """Test creating convoy through manager"""
        work_items = [
            {"agent_type": "pm", "work_item_id": "issue-123"},
            {"agent_type": "engineer", "work_item_id": "issue-456"}
        ]
        
        convoy = convoy_manager.create_convoy(
            name="Test Convoy",
            work_items=work_items,
            max_parallel=10,
            issue_number=100
        )
        
        assert convoy.name == "Test Convoy"
        assert convoy.max_parallel == 10
        assert convoy.issue_number == 100
        assert len(convoy.members) == 2
    
    def test_get_convoy(self, convoy_manager):
        """Test retrieving convoy"""
        work_items = [{"agent_type": "pm", "work_item_id": "issue-1"}]
        
        convoy = convoy_manager.create_convoy("Test", work_items)
        convoy_id = convoy.id
        
        retrieved = convoy_manager.get_convoy(convoy_id)
        assert retrieved is not None
        assert retrieved.id == convoy_id
        
        missing = convoy_manager.get_convoy("nonexistent")
        assert missing is None
    
    def test_list_convoys(self, convoy_manager):
        """Test listing convoys"""
        
        # Create several convoys
        work_items_1 = [{"agent_type": "pm", "work_item_id": "issue-1"}]
        work_items_2 = [{"agent_type": "pm", "work_item_id": "issue-2"}]
        work_items_3 = [{"agent_type": "pm", "work_item_id": "issue-3"}]
        
        c1 = convoy_manager.create_convoy("Convoy 1", work_items_1, issue_number=100)
        c2 = convoy_manager.create_convoy("Convoy 2", work_items_2, issue_number=200)
        c3 = convoy_manager.create_convoy("Convoy 3", work_items_3, issue_number=100)
        
        # List all
        all_convoys = convoy_manager.list_convoys()
        assert len(all_convoys) == 3
        
        # Filter by issue
        issue_100 = convoy_manager.list_convoys(issue_number=100)
        assert len(issue_100) == 2


@pytest.mark.asyncio
class TestConvoyExecution:
    """Test convoy execution with auto-tuning"""
    
    async def test_basic_execution(self, convoy_manager):
        """Test basic convoy execution"""
        # Mock agent executor
        async def mock_executor(agent_type, work_item_id, context):
            await asyncio.sleep(0.1)
            return f"Result for {work_item_id}"
        
        convoy_manager.agent_executor = mock_executor
        
        # Create convoy
        work_items = [
            {"agent_type": "pm", "work_item_id": "issue-1"},
            {"agent_type": "engineer", "work_item_id": "issue-2"}
        ]
        
        convoy = convoy_manager.create_convoy(
            "Test Convoy",
            work_items,
            max_parallel=5,
            enable_auto_tuning=False  # Disable for basic test
        )
        
        # Execute
        await convoy_manager.execute_convoy(convoy.id)
        
        # Check results
        assert convoy.status == ConvoyStatus.COMPLETED
        assert all(m.status == "completed" for m in convoy.members)
    
    async def test_execution_with_auto_tuning(self, convoy_manager):
        """Test execution with resource-based auto-tuning"""
        # Mock agent executor
        async def mock_executor(agent_type, work_item_id, context):
            await asyncio.sleep(0.05)
            return f"Result for {work_item_id}"
        
        convoy_manager.agent_executor = mock_executor
        
        # Mock resource monitor to return high availability
        mock_metrics = ResourceMetrics(
            cpu_percent=20.0,  # 80% available
            memory_percent=30.0,  # 70% available
            memory_available_mb=4096.0,
            process_memory_mb=100.0,
            process_cpu_percent=10.0,
            thread_count=5,
            timestamp=0.0
        )
        
        # Create convoy with auto-tuning
        work_items = [
            {"agent_type": "pm", "work_item_id": f"issue-{i}"}
            for i in range(10)
        ]
        
        convoy = convoy_manager.create_convoy(
            "Auto-tuned Convoy",
            work_items,
            max_parallel=20,
            enable_auto_tuning=True,
            baseline_parallel=5
        )
        
        # Patch resource monitor
        with patch('ai_squad.core.convoy.get_global_monitor') as mock_monitor:
            mock_instance = Mock()
            mock_instance.calculate_optimal_parallelism.return_value = 15
            mock_instance.should_throttle.return_value = False
            mock_instance.get_throttle_factor.return_value = 1.0
            mock_monitor.return_value = mock_instance
            
            # Execute
            await convoy_manager.execute_convoy(convoy.id)
        
        # Verify auto-tuning was called
        mock_instance.calculate_optimal_parallelism.assert_called_once()
        
        # Check results
        assert convoy.status == ConvoyStatus.COMPLETED
        assert all(m.status == "completed" for m in convoy.members)
    
    async def test_execution_with_throttling(self, convoy_manager):
        """Test execution with dynamic throttling"""
        # Mock agent executor
        execution_times = []
        
        async def mock_executor(agent_type, work_item_id, context):
            execution_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.05)
            return f"Result for {work_item_id}"
        
        convoy_manager.agent_executor = mock_executor
        
        # Create convoy
        work_items = [
            {"agent_type": "pm", "work_item_id": f"issue-{i}"}
            for i in range(5)
        ]
        
        convoy = convoy_manager.create_convoy(
            "Throttled Convoy",
            work_items,
            max_parallel=10,
            enable_auto_tuning=True,
            cpu_threshold=70.0  # Lower threshold for testing
        )
        
        # Patch resource monitor to indicate high load
        with patch('ai_squad.core.convoy.get_global_monitor') as mock_monitor:
            mock_instance = Mock()
            mock_instance.calculate_optimal_parallelism.return_value = 5
            mock_instance.should_throttle.return_value = True  # Indicate throttling needed
            mock_instance.get_throttle_factor.return_value = 0.5  # 50% throttle
            mock_monitor.return_value = mock_instance
            
            # Execute
            await convoy_manager.execute_convoy(convoy.id)
        
        # Verify throttling was checked
        assert mock_instance.should_throttle.call_count > 0
        
        # Check results
        assert convoy.status == ConvoyStatus.COMPLETED
    
    async def test_execution_failure_handling(self, convoy_manager):
        """Test handling of execution failures"""
        # Mock agent executor that fails
        async def mock_executor(agent_type, work_item_id, context):
            if work_item_id == "issue-2":
                raise RuntimeError("Simulated failure")
            await asyncio.sleep(0.05)
            return f"Result for {work_item_id}"
        
        convoy_manager.agent_executor = mock_executor
        
        # Create convoy
        work_items = [
            {"agent_type": "pm", "work_item_id": "issue-1"},
            {"agent_type": "engineer", "work_item_id": "issue-2"},
            {"agent_type": "ux", "work_item_id": "issue-3"}
        ]
        
        convoy = convoy_manager.create_convoy(
            "Failing Convoy",
            work_items,
            max_parallel=5,
            enable_auto_tuning=False
        )
        
        # Execute
        await convoy_manager.execute_convoy(convoy.id)
        
        # Check results
        assert convoy.status == ConvoyStatus.PARTIAL
        assert convoy.members[0].status == "completed"
        assert convoy.members[1].status == "failed"
        assert convoy.members[2].status == "completed"
        assert "Simulated failure" in convoy.members[1].error
    
    async def test_stop_on_first_failure(self, convoy_manager):
        """Test stop-on-first-failure mode"""
        # Mock agent executor
        async def mock_executor(agent_type, work_item_id, context):
            if work_item_id == "issue-1":
                raise RuntimeError("First failure")
            await asyncio.sleep(0.1)
            return f"Result for {work_item_id}"
        
        convoy_manager.agent_executor = mock_executor
        
        # Create convoy with stop_on_first_failure
        work_items = [
            {"agent_type": "pm", "work_item_id": f"issue-{i}"}
            for i in range(5)
        ]
        
        convoy = convoy_manager.create_convoy(
            "Stop on Failure",
            work_items,
            max_parallel=5,
            stop_on_first_failure=True,
            enable_auto_tuning=False
        )
        
        # Execute
        await convoy_manager.execute_convoy(convoy.id)
        
        # Should have stopped early
        assert convoy.status == ConvoyStatus.FAILED
        failed_count = len([m for m in convoy.members if m.status == "failed"])
        assert failed_count > 0


@pytest.mark.asyncio
class TestDirectTaskExecution:
    """Test direct task execution mode"""
    
    async def test_direct_task_execution(self, convoy_manager):
        """Test executing tasks directly without convoy object"""
        # Mock agent executor
        async def mock_executor(agent_type, issue_number, context=None):
            await asyncio.sleep(0.05)
            return f"Result for {agent_type}-{issue_number}"
        
        convoy_manager.agent_executor = mock_executor
        
        # Execute directly
        tasks = [
            ("pm", "123"),
            ("engineer", "456")
        ]
        
        result = await convoy_manager.execute_convoy(
            "direct-convoy",
            tasks=tasks,
            max_parallel=5
        )
        
        # Check results
        assert result["completed"] == 2
        assert result["failed"] == 0
        assert len(result["results"]) == 2


class TestConvoyConfiguration:
    """Test convoy configuration options"""
    
    def test_disable_auto_tuning(self):
        """Test disabling auto-tuning"""
        convoy = Convoy(
            id="test",
            name="Test",
            enable_auto_tuning=False
        )
        
        assert convoy.enable_auto_tuning == False
        assert convoy.max_parallel == 5  # Should use fixed value
    
    def test_custom_thresholds(self):
        """Test custom CPU/memory thresholds"""
        convoy = Convoy(
            id="test",
            name="Test",
            cpu_threshold=90.0,
            memory_threshold=95.0
        )
        
        assert convoy.cpu_threshold == 90.0
        assert convoy.memory_threshold == 95.0
    
    def test_custom_baseline(self):
        """Test custom baseline parallelism"""
        convoy = Convoy(
            id="test",
            name="Test",
            baseline_parallel=10
        )
        
        assert convoy.baseline_parallel == 10
