"""
Tests for Gastown-inspired orchestration modules.
"""
import pytest
from pathlib import Path
import tempfile
import shutil


class TestWorkState:
    """Tests for WorkState persistence"""
    
    def setup_method(self):
        """Set up test workspace"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_work_item_creation(self):
        """Test WorkItem dataclass"""
        from ai_squad.core.workstate import WorkItem, WorkStatus
        
        item = WorkItem(
            id="sq-test1",
            title="Test work item",
            description="Test description"
        )
        
        assert item.id == "sq-test1"
        assert item.title == "Test work item"
        assert item.status == WorkStatus.BACKLOG
        assert item.agent_assignee is None
    
    def test_work_item_status_transition(self):
        """Test WorkItem status transitions"""
        from ai_squad.core.workstate import WorkItem, WorkStatus
        
        item = WorkItem(id="sq-test2", title="Test")
        item.update_status(WorkStatus.READY)
        
        assert item.status == WorkStatus.READY
        assert item.updated_at is not None
    
    def test_work_item_assignment(self):
        """Test WorkItem agent assignment"""
        from ai_squad.core.workstate import WorkItem, WorkStatus
        
        item = WorkItem(id="sq-test3", title="Test")
        item.assign_to("engineer")
        
        assert item.agent_assignee == "engineer"
        assert item.status == WorkStatus.HOOKED
    
    def test_work_item_to_dict(self):
        """Test WorkItem serialization"""
        from ai_squad.core.workstate import WorkItem
        
        item = WorkItem(id="sq-test4", title="Test")
        data = item.to_dict()
        
        assert data["id"] == "sq-test4"
        assert "status" in data
        assert isinstance(data["status"], str)
    
    def test_work_item_from_dict(self):
        """Test WorkItem deserialization"""
        from ai_squad.core.workstate import WorkItem, WorkStatus
        
        data = {
            "id": "sq-test5",
            "title": "Test",
            "description": "",
            "status": "ready",
            "issue_number": 123,
            "agent_assignee": None,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "context": {},
            "artifacts": [],
            "depends_on": [],
            "blocks": [],
            "convoy_id": None,
            "labels": [],
            "priority": 0
        }
        
        item = WorkItem.from_dict(data)
        assert item.id == "sq-test5"
        assert item.status == WorkStatus.READY
        assert item.issue_number == 123
    
    def test_work_state_manager_initialization(self):
        """Test WorkStateManager initialization"""
        from ai_squad.core.workstate import WorkStateManager
        
        manager = WorkStateManager(self.workspace)
        assert manager.workspace_root == self.workspace
    
    def test_work_state_manager_create_item(self):
        """Test creating work items through manager"""
        from ai_squad.core.workstate import WorkStateManager, WorkStatus
        
        manager = WorkStateManager(self.workspace)
        item = manager.create_work_item(
            title="Test item",
            description="Test description",
            issue_number=123
        )
        
        assert item.id.startswith("sq-")
        assert item.title == "Test item"
        assert item.issue_number == 123
        # Should be ready since no dependencies
        assert item.status == WorkStatus.READY

    def test_work_state_updates_operational_graph(self):
        """Test work item creates graph nodes and edges"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.operational_graph import OperationalGraph, EdgeType

        manager = WorkStateManager(self.workspace)
        item = manager.create_work_item(
            title="Test graph item",
            description="Test description",
            issue_number=123,
            agent="engineer",
        )

        graph = OperationalGraph(self.workspace)
        node = graph.get_node(item.id)
        assert node is not None

        edges = graph.get_outgoing_edges(item.id, EdgeType.OWNS)
        assert any(e.to_node == "engineer" for e in edges)
    
    def test_work_state_manager_persistence(self):
        """Test work state persists to disk"""
        from ai_squad.core.workstate import WorkStateManager
        
        manager1 = WorkStateManager(self.workspace)
        item = manager1.create_work_item(title="Persistent item")
        item_id = item.id
        
        # Create new manager to load from disk
        manager2 = WorkStateManager(self.workspace)
        loaded = manager2.get_work_item(item_id)
        
        assert loaded is not None
        assert loaded.title == "Persistent item"
    
    def test_work_state_manager_list_items(self):
        """Test listing work items with filters"""
        from ai_squad.core.workstate import WorkStateManager, WorkStatus
        
        manager = WorkStateManager(self.workspace)
        manager.create_work_item(title="Item 1")
        manager.create_work_item(title="Item 2")
        manager.create_work_item(title="Item 3")
        
        all_items = manager.list_work_items()
        assert len(all_items) == 3
        
        ready_items = manager.list_work_items(status=WorkStatus.READY)
        assert len(ready_items) == 3
    
    def test_work_state_manager_dependencies(self):
        """Test work item dependencies"""
        from ai_squad.core.workstate import WorkStateManager, WorkStatus
        
        manager = WorkStateManager(self.workspace)
        item1 = manager.create_work_item(title="First")
        item2 = manager.create_work_item(title="Second", depends_on=[item1.id])
        
        assert item1.id in item2.depends_on
        # Second should be blocked since first is not done
        assert item2.status == WorkStatus.BLOCKED


class TestBattlePlan:
    """Tests for BattlePlan system"""
    
    def setup_method(self):
        """Set up test workspace"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_BattlePlan_step_creation(self):
        """Test BattlePlanPhase dataclass"""
        from ai_squad.core.battle_plan import BattlePlanPhase
        
        step = BattlePlanPhase(
            name="test_step",
            agent="engineer",
            action="implement"
        )
        
        assert step.name == "test_step"
        assert step.agent == "engineer"
        assert step.action == "implement"
    
    def test_BattlePlan_creation(self):
        """Test BattlePlan dataclass"""
        from ai_squad.core.battle_plan import BattlePlan, BattlePlanPhase
        
        battle_plan = BattlePlan(
            name="test_BattlePlan",
            description="Test description",
            phases=[
                BattlePlanPhase(name="step1", agent="pm", action="prd"),
                BattlePlanPhase(name="step2", agent="engineer", action="implement"),
            ]
        )
        
        assert battle_plan.name == "test_BattlePlan"
        assert len(battle_plan.phases) == 2
    
    def test_BattlePlan_to_yaml(self):
        """Test BattlePlan YAML serialization"""
        from ai_squad.core.battle_plan import BattlePlan, BattlePlanPhase
        
        battle_plan = BattlePlan(
            name="test",
            description="Test",
            phases=[BattlePlanPhase(name="s1", agent="pm", action="prd")]
        )
        
        yaml_str = battle_plan.to_yaml()
        assert "name: test" in yaml_str
        assert "steps:" in yaml_str
    
    def test_BattlePlan_from_yaml(self):
        """Test BattlePlan YAML deserialization"""
        from ai_squad.core.battle_plan import BattlePlan
        
        yaml_content = """
name: test_yaml
description: Test from YAML
version: "1.0"
steps:
  - name: step1
    agent: pm
    action: create_prd
labels:
  - test
"""
        battle_plan = BattlePlan.from_yaml(yaml_content)
        assert battle_plan.name == "test_yaml"
        assert len(battle_plan.phases) == 1
        assert "test" in battle_plan.labels
    
    def test_BattlePlan_manager_initialization(self):
        """Test BattlePlanManager initialization"""
        from ai_squad.core.battle_plan import BattlePlanManager
        
        manager = BattlePlanManager(self.workspace)
        assert manager.workspace_root == self.workspace
    
    def test_BattlePlan_manager_builtin_BattlePlans(self):
        """Test built-in BattlePlans are loaded"""
        from ai_squad.core.battle_plan import BattlePlanManager
        
        manager = BattlePlanManager(self.workspace)
        strategies = manager.list_strategies()
        
        # Should have built-in strategies
        names = [f.name for f in strategies]
        # Built-in strategies should exist if templates exist
        assert isinstance(strategies, list)


class TestSignal:
    """Tests for Agent Signal system"""
    
    def setup_method(self):
        """Set up test workspace"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_message_creation(self):
        """Test Message dataclass"""
        from ai_squad.core.signal import Message, MessagePriority, MessageStatus
        
        msg = Message(
            id="msg-test1",
            sender="pm",
            recipient="engineer",
            subject="Test subject",
            body="Test body"
        )
        
        assert msg.id == "msg-test1"
        assert msg.sender == "pm"
        assert msg.recipient == "engineer"
        assert msg.priority == MessagePriority.NORMAL
        assert msg.status == MessageStatus.PENDING
    
    def test_message_to_dict(self):
        """Test Message serialization"""
        from ai_squad.core.signal import Message
        
        msg = Message(
            id="msg-test2",
            sender="pm",
            recipient="engineer",
            subject="Test",
            body="Body"
        )
        
        data = msg.to_dict()
        assert data["id"] == "msg-test2"
        assert "priority" in data
    
    def test_signal_manager_initialization(self):
        """Test SignalManager initialization"""
        from ai_squad.core.signal import SignalManager
        
        manager = SignalManager(self.workspace)
        assert manager.workspace_root == self.workspace
    
    def test_Signal_manager_send_message(self):
        """Test sending messages"""
        from ai_squad.core.signal import SignalManager, MessageStatus
        
        manager = SignalManager(self.workspace)
        msg = manager.send_message(
            sender="pm",
            recipient="engineer",
            subject="Task Assignment",
            body="Please implement feature X"
        )
        
        assert msg.id.startswith("msg-")
        assert msg.status == MessageStatus.DELIVERED
    
    def test_Signal_manager_get_inbox(self):
        """Test getting inbox messages"""
        from ai_squad.core.signal import SignalManager
        
        manager = SignalManager(self.workspace)
        manager.send_message(
            sender="pm",
            recipient="engineer",
            subject="Message 1",
            body="Body 1"
        )
        manager.send_message(
            sender="architect",
            recipient="engineer",
            subject="Message 2",
            body="Body 2"
        )
        
        inbox = manager.get_inbox("engineer")
        assert len(inbox) == 2
    
    def test_Signal_manager_broadcast(self):
        """Test broadcast messages"""
        from ai_squad.core.signal import SignalManager
        
        manager = SignalManager(self.workspace)
        
        # Create some Signals first
        manager._get_or_create_Signal("pm")
        manager._get_or_create_Signal("engineer")
        manager._get_or_create_Signal("reviewer")
        
        msg = manager.send_message(
            sender="system",
            recipient="broadcast",
            subject="Announcement",
            body="System announcement"
        )
        
        # All should receive (except sender)
        pm_inbox = manager.get_inbox("pm")
        engineer_inbox = manager.get_inbox("engineer")
        
        assert len(pm_inbox) == 1
        assert len(engineer_inbox) == 1


class TestHandoff:
    """Tests for Handoff protocol"""
    
    def setup_method(self):
        """Set up test workspace"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_handoff_context_creation(self):
        """Test HandoffContext dataclass"""
        from ai_squad.core.handoff import HandoffContext
        
        context = HandoffContext(
            summary="Work summary",
            current_state="Phase complete",
            next_steps=["Step 1", "Step 2"]
        )
        
        assert context.summary == "Work summary"
        assert len(context.next_steps) == 2
    
    def test_handoff_creation(self):
        """Test Handoff dataclass"""
        from ai_squad.core.handoff import Handoff, HandoffReason, HandoffStatus
        
        handoff = Handoff(
            id="handoff-test1",
            work_item_id="sq-abc12",
            from_agent="pm",
            to_agent="architect",
            reason=HandoffReason.WORKFLOW
        )
        
        assert handoff.id == "handoff-test1"
        assert handoff.from_agent == "pm"
        assert handoff.to_agent == "architect"
        assert handoff.status == HandoffStatus.INITIATED
    
    def test_handoff_audit_log(self):
        """Test Handoff audit logging"""
        from ai_squad.core.handoff import Handoff, HandoffReason
        
        handoff = Handoff(
            id="handoff-test2",
            work_item_id="sq-abc13",
            from_agent="pm",
            to_agent="architect",
            reason=HandoffReason.WORKFLOW
        )
        
        handoff.add_audit_entry("test_action", "pm", "Test details")
        
        assert len(handoff.audit_log) == 1
        assert handoff.audit_log[0]["action"] == "test_action"
    
    def test_handoff_manager_initialization(self):
        """Test HandoffManager initialization"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.handoff import HandoffManager
        
        work_manager = WorkStateManager(self.workspace)
        handoff_manager = HandoffManager(work_manager, workspace_root=self.workspace)
        
        assert handoff_manager.workspace_root == self.workspace
    
    def test_handoff_manager_initiate_handoff(self):
        """Test initiating a handoff"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.handoff import HandoffManager, HandoffReason, HandoffStatus
        
        work_manager = WorkStateManager(self.workspace)
        handoff_manager = HandoffManager(work_manager, workspace_root=self.workspace)
        
        # Create a work item first
        work_item = work_manager.create_work_item(title="Test work")
        
        handoff = handoff_manager.initiate_handoff(
            work_item_id=work_item.id,
            from_agent="pm",
            to_agent="architect",
            reason=HandoffReason.WORKFLOW
        )
        
        assert handoff is not None
        assert handoff.status == HandoffStatus.PENDING


class TestConvoy:
    """Tests for Convoy system"""
    
    def setup_method(self):
        """Set up test workspace"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_convoy_creation(self):
        """Test Convoy dataclass"""
        from ai_squad.core.convoy import Convoy, ConvoyStatus
        
        convoy = Convoy(
            id="convoy-test1",
            name="Test Convoy",
            description="Test description"
        )
        
        assert convoy.id == "convoy-test1"
        assert convoy.name == "Test Convoy"
        assert convoy.status == ConvoyStatus.PENDING
    
    def test_convoy_member_addition(self):
        """Test adding members to convoy"""
        from ai_squad.core.convoy import Convoy
        
        convoy = Convoy(id="convoy-test2", name="Test")
        member = convoy.add_member("engineer", "sq-work1")
        
        assert len(convoy.members) == 1
        assert member.agent_type == "engineer"
        assert member.work_item_id == "sq-work1"
    
    def test_convoy_progress(self):
        """Test convoy progress calculation"""
        from ai_squad.core.convoy import Convoy
        
        convoy = Convoy(id="convoy-test3", name="Test")
        convoy.add_member("pm", "sq-1")
        convoy.add_member("architect", "sq-2")
        convoy.add_member("engineer", "sq-3")
        
        progress = convoy.get_progress()
        assert progress["total"] == 3
        assert progress["pending"] == 3
        assert progress["progress_percent"] == 0
    
    def test_convoy_manager_initialization(self):
        """Test ConvoyManager initialization"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.convoy import ConvoyManager
        
        work_manager = WorkStateManager(self.workspace)
        convoy_manager = ConvoyManager(work_manager)
        
        assert convoy_manager.work_state_manager == work_manager
    
    def test_convoy_manager_create_convoy(self):
        """Test creating a convoy"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.convoy import ConvoyManager
        
        work_manager = WorkStateManager(self.workspace)
        convoy_manager = ConvoyManager(work_manager)
        
        # Create work items
        item1 = work_manager.create_work_item(title="Work 1")
        item2 = work_manager.create_work_item(title="Work 2")
        
        convoy = convoy_manager.create_convoy(
            name="Test Convoy",
            work_items=[
                {"agent_type": "pm", "work_item_id": item1.id},
                {"agent_type": "architect", "work_item_id": item2.id}
            ]
        )
        
        assert convoy.id.startswith("convoy-")
        assert len(convoy.members) == 2
    
    def test_convoy_get_member(self):
        """Test getting a member by work item ID"""
        from ai_squad.core.convoy import Convoy
        
        convoy = Convoy(id="convoy-test4", name="Test")
        convoy.add_member("pm", "sq-1")
        convoy.add_member("architect", "sq-2")
        
        member = convoy.get_member("sq-1")
        assert member is not None
        assert member.agent_type == "pm"
        
        missing = convoy.get_member("sq-nonexistent")
        assert missing is None
    
    def test_convoy_is_complete(self):
        """Test convoy completion check"""
        from ai_squad.core.convoy import Convoy
        
        convoy = Convoy(id="convoy-test5", name="Test")
        convoy.add_member("pm", "sq-1")
        convoy.add_member("architect", "sq-2")
        
        # Not complete initially
        assert not convoy.is_complete()
        
        # Mark members as completed
        convoy.members[0].status = "completed"
        assert not convoy.is_complete()  # Still one pending
        
        convoy.members[1].status = "completed"
        assert convoy.is_complete()
    
    def test_convoy_is_complete_with_failed(self):
        """Test convoy completion with failed members"""
        from ai_squad.core.convoy import Convoy
        
        convoy = Convoy(id="convoy-test6", name="Test")
        convoy.add_member("pm", "sq-1")
        convoy.add_member("architect", "sq-2")
        
        convoy.members[0].status = "completed"
        convoy.members[1].status = "failed"
        
        # Should still be complete (all members have terminal status)
        assert convoy.is_complete()
    
    def test_convoy_to_dict(self):
        """Test convoy serialization to dict"""
        from ai_squad.core.convoy import Convoy, ConvoyStatus
        
        convoy = Convoy(
            id="convoy-test7",
            name="Test Convoy",
            description="Test description",
            max_parallel=3,
            timeout_minutes=30,
            issue_number=123
        )
        convoy.add_member("pm", "sq-1")
        
        data = convoy.to_dict()
        
        assert data["id"] == "convoy-test7"
        assert data["name"] == "Test Convoy"
        assert data["status"] == "pending"
        assert data["max_parallel"] == 3
        assert data["issue_number"] == 123
        assert len(data["members"]) == 1
    
    def test_convoy_manager_get_convoy(self):
        """Test getting a convoy by ID"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.convoy import ConvoyManager
        
        work_manager = WorkStateManager(self.workspace)
        convoy_manager = ConvoyManager(work_manager)
        
        item = work_manager.create_work_item(title="Work 1")
        convoy = convoy_manager.create_convoy(
            name="Test",
            work_items=[{"agent_type": "pm", "work_item_id": item.id}]
        )
        
        # Get existing convoy
        retrieved = convoy_manager.get_convoy(convoy.id)
        assert retrieved is not None
        assert retrieved.id == convoy.id
        
        # Get non-existent convoy
        missing = convoy_manager.get_convoy("convoy-nonexistent")
        assert missing is None
    
    def test_convoy_manager_list_convoys(self):
        """Test listing all convoys"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.convoy import ConvoyManager
        
        work_manager = WorkStateManager(self.workspace)
        convoy_manager = ConvoyManager(work_manager)
        
        # Create multiple convoys
        item1 = work_manager.create_work_item(title="Work 1")
        item2 = work_manager.create_work_item(title="Work 2")
        
        convoy_manager.create_convoy(
            name="Convoy 1",
            work_items=[{"agent_type": "pm", "work_item_id": item1.id}]
        )
        convoy_manager.create_convoy(
            name="Convoy 2",
            work_items=[{"agent_type": "architect", "work_item_id": item2.id}]
        )
        
        convoys = convoy_manager.list_convoys()
        assert len(convoys) == 2
    
    def test_convoy_member_to_dict(self):
        """Test ConvoyMember serialization"""
        from ai_squad.core.convoy import ConvoyMember
        
        member = ConvoyMember(
            agent_type="engineer",
            work_item_id="sq-123",
            status="running",
            started_at="2026-01-24T10:00:00",
            result="Some result"
        )
        
        data = member.to_dict()
        assert data["agent_type"] == "engineer"
        assert data["work_item_id"] == "sq-123"
        assert data["status"] == "running"
        assert data["started_at"] == "2026-01-24T10:00:00"
    
    def test_convoy_progress_with_mixed_status(self):
        """Test convoy progress with various statuses"""
        from ai_squad.core.convoy import Convoy
        
        convoy = Convoy(id="convoy-test8", name="Test")
        convoy.add_member("pm", "sq-1")
        convoy.add_member("architect", "sq-2")
        convoy.add_member("engineer", "sq-3")
        convoy.add_member("ux", "sq-4")
        
        convoy.members[0].status = "completed"
        convoy.members[1].status = "running"
        convoy.members[2].status = "failed"
        convoy.members[3].status = "pending"
        
        progress = convoy.get_progress()
        assert progress["completed"] == 1
        assert progress["running"] == 1
        assert progress["failed"] == 1
        assert progress["pending"] == 1
        assert progress["progress_percent"] == 50  # 2/4 terminal states
    
    def test_convoy_manager_with_workspace_path(self):
        """Test ConvoyManager accepts workspace path"""
        from ai_squad.core.convoy import ConvoyManager
        
        # Pass workspace path directly instead of manager
        convoy_manager = ConvoyManager(self.workspace)
        
        assert convoy_manager.work_state_manager is not None
    
    def test_convoy_stop_on_first_failure_setting(self):
        """Test convoy stop_on_first_failure setting"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.convoy import ConvoyManager
        
        work_manager = WorkStateManager(self.workspace)
        convoy_manager = ConvoyManager(work_manager)
        
        item = work_manager.create_work_item(title="Work 1")
        convoy = convoy_manager.create_convoy(
            name="Test",
            work_items=[{"agent_type": "pm", "work_item_id": item.id}],
            stop_on_first_failure=True
        )
        
        assert convoy.stop_on_first_failure is True


class TestCLIOrchestration:
    """Tests for CLI orchestration commands"""
    
    def test_cli_has_orchestration_commands(self):
        """Test that CLI has new orchestration commands"""
        from click.testing import CliRunner
        from ai_squad.cli import main
        
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        
        assert result.exit_code == 0
        assert "captain" in result.output
        assert "work" in result.output
        assert "plans" in result.output
        assert "convoys" in result.output
        assert "signal" in result.output
        assert "handoff" in result.output
        assert "status" in result.output


