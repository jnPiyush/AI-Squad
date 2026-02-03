"""
Tests for WorkItem A2A Task Schema Alignment
"""
import pytest
from datetime import datetime
from ai_squad.core.workstate import WorkItem, WorkStatus


class TestWorkItemA2A:
    """Test WorkItem A2A Protocol alignment"""
    
    def test_workitem_creation(self):
        """Test creating a work item"""
        item = WorkItem(
            id="test-1",
            title="Test Task",
            description="Test description",
            status=WorkStatus.BACKLOG,
        )
        
        assert item.id == "test-1"
        assert item.title == "Test Task"
        assert item.status == WorkStatus.BACKLOG
        assert len(item.history) == 0
    
    def test_add_history_entry(self):
        """Test adding history entries"""
        item = WorkItem(id="test-1", title="Test", description="Desc")
        
        item.add_history_entry("created", "pm", "Task created")
        item.add_history_entry("assigned", "engineer", "Assigned to engineer")
        
        assert len(item.history) == 2
        assert item.history[0]["action"] == "created"
        assert item.history[0]["agent"] == "pm"
        assert item.history[1]["action"] == "assigned"
    
    def test_to_a2a_task(self):
        """Test converting WorkItem to A2A Task format"""
        item = WorkItem(
            id="test-1",
            title="Test Task",
            description="Description",
            status=WorkStatus.IN_PROGRESS,
            issue_number=123,
            agent_assignee="engineer",
            priority=5,
            labels=["feature", "backend"],
            artifacts=["src/main.py", "tests/test_main.py"],
        )
        item.add_history_entry("created", "pm")
        
        a2a_task = item.to_a2a_task()
        
        # Check A2A structure
        assert a2a_task["id"] == "test-1"
        assert a2a_task["status"]["state"] == "working"
        assert "message" in a2a_task
        assert a2a_task["message"]["role"] == "user"
        assert "Test Task" in a2a_task["message"]["parts"][0]["text"]
        assert len(a2a_task["artifacts"]) == 2
        assert a2a_task["artifacts"][0]["uri"] == "src/main.py"
        assert len(a2a_task["history"]) == 1
        assert a2a_task["metadata"]["issue_number"] == 123
        assert a2a_task["metadata"]["agent_assignee"] == "engineer"
        assert a2a_task["metadata"]["priority"] == 5
    
    def test_a2a_status_mapping(self):
        """Test WorkStatus to A2A status mapping"""
        test_cases = [
            (WorkStatus.BACKLOG, "submitted"),
            (WorkStatus.READY, "submitted"),
            (WorkStatus.IN_PROGRESS, "working"),
            (WorkStatus.HOOKED, "working"),
            (WorkStatus.BLOCKED, "input-required"),
            (WorkStatus.IN_REVIEW, "working"),
            (WorkStatus.DONE, "completed"),
            (WorkStatus.FAILED, "failed"),
        ]
        
        for status, expected_a2a in test_cases:
            item = WorkItem(id="test", title="Test", description="", status=status)
            a2a_task = item.to_a2a_task()
            assert a2a_task["status"]["state"] == expected_a2a
    
    def test_from_a2a_task(self):
        """Test creating WorkItem from A2A Task format"""
        a2a_task = {
            "id": "task-123",
            "sessionId": "session-456",
            "status": {
                "state": "working",
                "timestamp": "2026-02-03T12:00:00",
            },
            "message": {
                "role": "user",
                "parts": [{"text": "Create REST API\n\nImplement CRUD endpoints"}],
            },
            "artifacts": [
                {"name": "api.py", "uri": "src/api.py"},
            ],
            "history": [
                {"action": "created", "agent": "pm", "timestamp": "2026-02-03T11:00:00"},
            ],
            "metadata": {
                "issue_number": 789,
                "agent_assignee": "engineer",
                "priority": 3,
                "labels": ["api", "backend"],
                "custom_field": "custom_value",
            },
        }
        
        item = WorkItem.from_a2a_task(a2a_task)
        
        assert item.id == "task-123"
        assert item.session_id == "session-456"
        assert item.title == "Create REST API"
        assert item.description == "Implement CRUD endpoints"
        assert item.status == WorkStatus.IN_PROGRESS
        assert item.issue_number == 789
        assert item.agent_assignee == "engineer"
        assert item.priority == 3
        assert item.labels == ["api", "backend"]
        assert len(item.artifacts) == 1
        assert item.artifacts[0] == "src/api.py"
        assert len(item.history) == 1
        assert item.metadata["custom_field"] == "custom_value"
    
    def test_a2a_roundtrip(self):
        """Test A2A conversion roundtrip"""
        original = WorkItem(
            id="test-roundtrip",
            title="Roundtrip Test",
            description="Test A2A conversion",
            status=WorkStatus.IN_PROGRESS,
            issue_number=999,
            agent_assignee="test_agent",
            priority=7,
            labels=["test"],
            artifacts=["test.py"],
        )
        original.add_history_entry("created", "pm", "Created task")
        
        # Convert to A2A
        a2a_task = original.to_a2a_task()
        
        # Convert back
        restored = WorkItem.from_a2a_task(a2a_task)
        
        # Verify key fields preserved
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.issue_number == original.issue_number
        assert restored.agent_assignee == original.agent_assignee
        assert restored.priority == original.priority
        assert restored.labels == original.labels
        assert restored.artifacts == original.artifacts
        assert len(restored.history) == len(original.history)
    
    def test_a2a_minimal_task(self):
        """Test A2A conversion with minimal fields"""
        a2a_task = {
            "id": "minimal",
            "message": {
                "parts": [{"text": "Minimal task"}],
            },
        }
        
        item = WorkItem.from_a2a_task(a2a_task)
        
        assert item.id == "minimal"
        assert item.title == "Minimal task"
        assert item.description == ""
        assert item.status == WorkStatus.BACKLOG
    
    def test_session_id_handling(self):
        """Test session_id field (A2A-specific)"""
        item = WorkItem(
            id="test-session",
            title="Test",
            description="Desc",
            session_id="custom-session-123",
        )
        
        a2a_task = item.to_a2a_task()
        assert a2a_task["sessionId"] == "custom-session-123"
        
        # Without session_id, should use id
        item2 = WorkItem(id="test-no-session", title="Test", description="")
        a2a_task2 = item2.to_a2a_task()
        assert a2a_task2["sessionId"] == "test-no-session"
    
    def test_parent_task_id(self):
        """Test parent_task_id field (A2A subtasks)"""
        parent = WorkItem(id="parent-1", title="Parent", description="")
        child = WorkItem(
            id="child-1",
            title="Child",
            description="",
            parent_task_id="parent-1",
        )
        
        assert child.parent_task_id == "parent-1"
    
    def test_artifacts_handling(self):
        """Test artifact list in A2A format"""
        item = WorkItem(
            id="test-artifacts",
            title="Test",
            description="",
            artifacts=["file1.py", "file2.py", "docs/README.md"],
        )
        
        a2a_task = item.to_a2a_task()
        
        assert len(a2a_task["artifacts"]) == 3
        assert a2a_task["artifacts"][0] == {"name": "file1.py", "uri": "file1.py"}
        assert a2a_task["artifacts"][2] == {"name": "docs/README.md", "uri": "docs/README.md"}


class TestWorkItemLegacy:
    """Test WorkItem backward compatibility"""
    
    def test_to_dict_includes_new_fields(self):
        """Test that to_dict includes A2A fields"""
        item = WorkItem(
            id="test",
            title="Test",
            description="",
            session_id="session-1",
            parent_task_id="parent-1",
        )
        
        data = item.to_dict()
        
        assert "session_id" in data
        assert "parent_task_id" in data
        assert "history" in data
    
    def test_from_dict_handles_new_fields(self):
        """Test that from_dict handles A2A fields"""
        data = {
            "id": "test",
            "title": "Test",
            "description": "",
            "status": "backlog",
            "session_id": "session-1",
            "parent_task_id": "parent-1",
            "history": [{"action": "created", "agent": "pm"}],
        }
        
        item = WorkItem.from_dict(data)
        
        assert item.session_id == "session-1"
        assert item.parent_task_id == "parent-1"
        assert len(item.history) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
