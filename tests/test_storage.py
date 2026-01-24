"""
Tests for Persistent Storage

Tests cover:
- Database initialization and schema
- Message operations (save, retrieve, query)
- Status transition tracking
- Agent execution audit trail
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

from ai_squad.core.storage import PersistentStorage
from ai_squad.core.agent_comm import AgentMessage, MessageType
from ai_squad.core.status import StatusTransition, IssueStatus


class TestPersistentStorageInitialization:
    """Test storage initialization"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)
    
    def test_storage_creates_database(self, temp_dir):
        """Test storage creates database file"""
        db_path = temp_dir / ".ai_squad" / "history.db"
        storage = PersistentStorage(str(db_path))
        
        assert db_path.exists()
    
    def test_storage_creates_parent_directory(self, temp_dir):
        """Test storage creates parent directory if needed"""
        db_path = temp_dir / "nested" / "dir" / "history.db"
        storage = PersistentStorage(str(db_path))
        
        assert db_path.parent.exists()
    
    def test_storage_initializes_schema(self, temp_dir):
        """Test storage creates all required tables"""
        import sqlite3
        
        db_path = temp_dir / "test.db"
        storage = PersistentStorage(str(db_path))
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert "messages" in tables
        assert "status_transitions" in tables
        assert "agent_executions" in tables
        
        conn.close()


class TestMessageOperations:
    """Test message storage operations"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create storage instance"""
        return PersistentStorage(str(temp_dir / "test.db"))
    
    def test_save_message(self, storage):
        """Test saving a message"""
        message = AgentMessage(
            id="msg-test-001",
            from_agent="pm",
            to_agent="architect",
            message_type=MessageType.NOTIFICATION,
            content="PRD complete, ready for architecture",
            context={"issue": 123},
            timestamp=datetime.now(),
            issue_number=123
        )
        
        result = storage.save_message(message)
        assert result is True
    
    def test_save_and_retrieve_message(self, storage):
        """Test saving and retrieving messages"""
        message = AgentMessage(
            id="msg-test-002",
            from_agent="engineer",
            to_agent="reviewer",
            message_type=MessageType.NOTIFICATION,
            content="Implementation complete",
            context={"pr": 456},
            timestamp=datetime.now(),
            issue_number=789
        )
        
        storage.save_message(message)
        
        messages = storage.get_messages_for_issue(789)
        assert len(messages) == 1
        assert messages[0].id == "msg-test-002"
        assert messages[0].from_agent == "engineer"
        assert messages[0].to_agent == "reviewer"
    
    def test_get_messages_for_nonexistent_issue(self, storage):
        """Test getting messages for issue with no messages"""
        messages = storage.get_messages_for_issue(99999)
        assert messages == []
    
    def test_get_pending_questions(self, storage):
        """Test getting unanswered questions"""
        # Create a question
        question = AgentMessage(
            id="msg-question-001",
            from_agent="pm",
            to_agent="architect",
            message_type=MessageType.QUESTION,
            content="What API design pattern should we use?",
            context={},
            timestamp=datetime.now(),
            issue_number=123
        )
        storage.save_message(question)
        
        # Get pending questions for architect
        pending = storage.get_pending_questions("architect")
        assert len(pending) == 1
        assert pending[0].id == "msg-question-001"
    
    def test_answered_question_not_in_pending(self, storage):
        """Test that answered questions are not pending"""
        # Create a question
        question = AgentMessage(
            id="msg-question-002",
            from_agent="pm",
            to_agent="architect",
            message_type=MessageType.QUESTION,
            content="What framework?",
            context={},
            timestamp=datetime.now(),
            issue_number=123
        )
        storage.save_message(question)
        
        # Create a response
        answer = AgentMessage(
            id="msg-answer-001",
            from_agent="architect",
            to_agent="pm",
            message_type=MessageType.RESPONSE,
            content="Use FastAPI",
            context={},
            timestamp=datetime.now(),
            response_to="msg-question-002",
            issue_number=123
        )
        storage.save_message(answer)
        
        # Question should no longer be pending
        pending = storage.get_pending_questions("architect")
        assert len(pending) == 0
    
    def test_save_message_with_response_to(self, storage):
        """Test saving a message that responds to another"""
        original = AgentMessage(
            id="msg-original",
            from_agent="pm",
            to_agent="engineer",
            message_type=MessageType.QUESTION,
            content="Can you estimate effort?",
            context={},
            timestamp=datetime.now(),
            issue_number=100
        )
        storage.save_message(original)
        
        response = AgentMessage(
            id="msg-response",
            from_agent="engineer",
            to_agent="pm",
            message_type=MessageType.RESPONSE,
            content="About 3 days",
            context={},
            timestamp=datetime.now(),
            response_to="msg-original",
            issue_number=100
        )
        result = storage.save_message(response)
        
        assert result is True


class TestStatusTransitionOperations:
    """Test status transition tracking"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create storage instance"""
        return PersistentStorage(str(temp_dir / "test.db"))
    
    def test_save_transition(self, storage):
        """Test saving a status transition"""
        transition = StatusTransition(
            issue_number=123,
            from_status=IssueStatus.BACKLOG,
            to_status=IssueStatus.IN_PROGRESS,
            agent="pm",
            timestamp=datetime.now(),
            reason="Started PRD creation"
        )
        
        result = storage.save_transition(transition)
        assert result is True
    
    def test_save_and_retrieve_transitions(self, storage):
        """Test saving and retrieving transitions"""
        # Create multiple transitions
        t1 = StatusTransition(
            issue_number=456,
            from_status=IssueStatus.BACKLOG,
            to_status=IssueStatus.IN_PROGRESS,
            agent="pm",
            timestamp=datetime.now(),
            reason="Started work"
        )
        t2 = StatusTransition(
            issue_number=456,
            from_status=IssueStatus.IN_PROGRESS,
            to_status=IssueStatus.IN_REVIEW,
            agent="pm",
            timestamp=datetime.now() + timedelta(hours=1),
            reason="PRD complete"
        )
        
        storage.save_transition(t1)
        storage.save_transition(t2)
        
        transitions = storage.get_transitions_for_issue(456)
        assert len(transitions) == 2
        assert transitions[0].from_status == IssueStatus.BACKLOG
        assert transitions[1].to_status == IssueStatus.IN_REVIEW
    
    def test_get_transitions_for_nonexistent_issue(self, storage):
        """Test getting transitions for issue with no transitions"""
        transitions = storage.get_transitions_for_issue(99999)
        assert transitions == []


class TestAgentExecutionOperations:
    """Test agent execution audit trail"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create storage instance"""
        return PersistentStorage(str(temp_dir / "test.db"))
    
    def test_start_execution(self, storage):
        """Test recording execution start"""
        exec_id = storage.start_execution(
            issue_number=123,
            agent="pm",
            execution_mode="manual"
        )
        
        assert exec_id is not None
        assert exec_id > 0
    
    def test_complete_execution_success(self, storage):
        """Test recording successful execution completion"""
        exec_id = storage.start_execution(
            issue_number=123,
            agent="engineer",
            execution_mode="automated"
        )
        
        result = storage.complete_execution(
            execution_id=exec_id,
            success=True,
            output_file="docs/prd/PRD-123.md"
        )
        
        assert result is True
    
    def test_complete_execution_failure(self, storage):
        """Test recording failed execution"""
        exec_id = storage.start_execution(
            issue_number=456,
            agent="architect",
            execution_mode="manual"
        )
        
        result = storage.complete_execution(
            execution_id=exec_id,
            success=False,
            error="GitHub API rate limit exceeded"
        )
        
        assert result is True
    
    def test_get_executions_for_issue(self, storage):
        """Test getting execution history for an issue"""
        # Create multiple executions
        exec1 = storage.start_execution(789, "pm", "manual")
        storage.complete_execution(exec1, True, output_file="docs/prd/PRD-789.md")
        
        exec2 = storage.start_execution(789, "architect", "manual")
        storage.complete_execution(exec2, True, output_file="docs/adr/ADR-789.md")
        
        executions = storage.get_executions_for_issue(789)
        assert len(executions) == 2
    
    def test_get_executions_for_nonexistent_issue(self, storage):
        """Test getting executions for issue with no executions"""
        executions = storage.get_executions_for_issue(99999)
        assert executions == []


class TestStorageEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create storage instance"""
        return PersistentStorage(str(temp_dir / "test.db"))
    
    def test_save_message_with_empty_context(self, storage):
        """Test saving message with empty context"""
        message = AgentMessage(
            id="msg-empty-context",
            from_agent="pm",
            to_agent="engineer",
            message_type=MessageType.NOTIFICATION,
            content="Ready",
            context={},
            timestamp=datetime.now(),
            issue_number=100
        )
        
        result = storage.save_message(message)
        assert result is True
        
        messages = storage.get_messages_for_issue(100)
        assert messages[0].context == {}
    
    def test_save_message_with_complex_context(self, storage):
        """Test saving message with complex nested context"""
        message = AgentMessage(
            id="msg-complex-context",
            from_agent="captain",
            to_agent="pm",
            message_type=MessageType.NOTIFICATION,
            content="Task breakdown complete",
            context={
                "work_items": ["wi-1", "wi-2"],
                "nested": {"a": 1, "b": [1, 2, 3]},
                "metadata": {"priority": "high"}
            },
            timestamp=datetime.now(),
            issue_number=200
        )
        
        result = storage.save_message(message)
        assert result is True
        
        messages = storage.get_messages_for_issue(200)
        assert messages[0].context["work_items"] == ["wi-1", "wi-2"]
    
    def test_duplicate_message_id_fails(self, storage):
        """Test that duplicate message ID fails gracefully"""
        message1 = AgentMessage(
            id="msg-duplicate",
            from_agent="pm",
            to_agent="engineer",
            message_type=MessageType.NOTIFICATION,
            content="First",
            context={},
            timestamp=datetime.now(),
            issue_number=100
        )
        storage.save_message(message1)
        
        # Try to save another message with same ID
        message2 = AgentMessage(
            id="msg-duplicate",
            from_agent="engineer",
            to_agent="reviewer",
            message_type=MessageType.NOTIFICATION,
            content="Second",
            context={},
            timestamp=datetime.now(),
            issue_number=100
        )
        result = storage.save_message(message2)
        
        # Should fail due to primary key constraint
        assert result is False
    
    def test_multiple_pending_questions(self, storage):
        """Test getting multiple pending questions"""
        # Create several questions
        for i in range(5):
            question = AgentMessage(
                id=f"msg-q-{i}",
                from_agent="pm",
                to_agent="architect",
                message_type=MessageType.QUESTION,
                content=f"Question {i}",
                context={},
                timestamp=datetime.now() + timedelta(minutes=i),
                issue_number=100 + i
            )
            storage.save_message(question)
        
        pending = storage.get_pending_questions("architect")
        assert len(pending) == 5
        
        # Answer one question
        answer = AgentMessage(
            id="msg-a-0",
            from_agent="architect",
            to_agent="pm",
            message_type=MessageType.RESPONSE,
            content="Answer 0",
            context={},
            timestamp=datetime.now(),
            response_to="msg-q-0",
            issue_number=100
        )
        storage.save_message(answer)
        
        pending = storage.get_pending_questions("architect")
        assert len(pending) == 4


class TestStorageConnection:
    """Test database connection handling"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)
    
    def test_multiple_storage_instances(self, temp_dir):
        """Test multiple storage instances can access same DB"""
        db_path = temp_dir / "shared.db"
        
        storage1 = PersistentStorage(str(db_path))
        storage2 = PersistentStorage(str(db_path))
        
        # Write with storage1
        message = AgentMessage(
            id="msg-shared",
            from_agent="pm",
            to_agent="engineer",
            message_type=MessageType.NOTIFICATION,
            content="Shared message",
            context={},
            timestamp=datetime.now(),
            issue_number=100
        )
        storage1.save_message(message)
        
        # Read with storage2
        messages = storage2.get_messages_for_issue(100)
        assert len(messages) == 1
        assert messages[0].id == "msg-shared"
