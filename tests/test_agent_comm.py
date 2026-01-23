"""
Agent Communication Tests

Tests for agent-to-agent communication and clarification framework.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid

from ai_squad.core.agent_comm import (
    AgentCommunicator,
    AgentMessage,
    MessageType,
    ClarificationMixin
)
from ai_squad.tools.github import GitHubTool
from ai_squad.agents.base import BaseAgent
from ai_squad.core.config import Config


class TestAgentMessage:
    """Test AgentMessage dataclass"""
    
    def test_message_creation(self):
        """Test creating a message"""
        msg = AgentMessage(
            from_agent="architect",
            to_agent="pm",
            message_type=MessageType.QUESTION,
            content="What is the scope?",
            context={"issue": 123},
            issue_number=123
        )
        
        assert msg.from_agent == "architect"
        assert msg.to_agent == "pm"
        assert msg.message_type == MessageType.QUESTION
        assert msg.content == "What is the scope?"
        assert msg.context == {"issue": 123}
        assert msg.issue_number == 123
        assert isinstance(msg.id, str)
        assert isinstance(msg.timestamp, datetime)
    
    def test_message_to_dict(self):
        """Test message serialization"""
        msg = AgentMessage(
            from_agent="architect",
            to_agent="pm",
            message_type=MessageType.QUESTION,
            content="Question",
            context={"key": "value"},
            issue_number=123
        )
        
        data = msg.to_dict()
        
        assert data["from_agent"] == "architect"
        assert data["to_agent"] == "pm"
        assert data["message_type"] == "question"
        assert data["content"] == "Question"
        assert data["context"] == {"key": "value"}
        assert data["issue_number"] == 123
        assert "id" in data
        assert "timestamp" in data


class TestMessageType:
    """Test MessageType enum"""
    
    def test_message_types_defined(self):
        """Test all message types exist"""
        assert MessageType.QUESTION
        assert MessageType.RESPONSE
        assert MessageType.NOTIFICATION
        assert MessageType.CLARIFICATION
    
    def test_message_type_values(self):
        """Test message type string values"""
        assert MessageType.QUESTION.value == "question"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.NOTIFICATION.value == "notification"
        assert MessageType.CLARIFICATION.value == "clarification"


class TestAgentCommunicator:
    """Test AgentCommunicator class"""
    
    @pytest.fixture
    def mock_github(self):
        """Create mock GitHub tool"""
        github = Mock(spec=GitHubTool)
        github.add_comment.return_value = True
        github._is_configured.return_value = True
        return github
    
    @pytest.fixture
    def communicator_automated(self, mock_github):
        """Create communicator in automated mode"""
        return AgentCommunicator(
            execution_mode="automated",
            github_tool=mock_github
        )
    
    @pytest.fixture
    def communicator_manual(self, mock_github):
        """Create communicator in manual mode"""
        return AgentCommunicator(
            execution_mode="manual",
            github_tool=mock_github
        )
    
    def test_communicator_initialization(self, communicator_automated):
        """Test communicator initialization"""
        assert communicator_automated.execution_mode == "automated"
        assert len(communicator_automated.message_queue) == 0
        assert len(communicator_automated.responses) == 0
    
    def test_ask_question_automated(self, communicator_automated, mock_github):
        """Test asking question in automated mode"""
        question_id = communicator_automated.ask(
            from_agent="architect",
            to_agent="pm",
            question="Should we use microservices?",
            context={"issue": 123},
            issue_number=123
        )
        
        assert question_id is not None
        assert len(communicator_automated.message_queue) == 1
        
        message = communicator_automated.message_queue[0]
        assert message.from_agent == "architect"
        assert message.to_agent == "pm"
        assert message.content == "Should we use microservices?"
        
        # Should post to GitHub for visibility
        mock_github.add_comment.assert_called_once()
    
    def test_ask_question_manual(self, communicator_manual, mock_github):
        """Test asking question in manual mode"""
        # In manual mode, should prompt user via Copilot Chat
        with patch('builtins.print') as mock_print:
            question_id = communicator_manual.ask(
                from_agent="architect",
                to_agent="user",
                question="Should we use microservices?",
                context={"issue": 123},
                issue_number=123
            )
        
        assert question_id is not None
        # Should still add to queue
        assert len(communicator_manual.message_queue) == 1
    
    def test_respond_to_message(self, communicator_automated):
        """Test responding to a message"""
        # Ask question
        question_id = communicator_automated.ask(
            "architect", "pm", "Question?", {}, 123
        )
        
        # Respond
        success = communicator_automated.respond(
            question_id,
            "Yes, use microservices",
            "pm"
        )
        
        assert success is True
        assert question_id in communicator_automated.responses
        assert communicator_automated.responses[question_id] == "Yes, use microservices"
        assert len(communicator_automated.message_queue) == 2  # Question + response
    
    def test_respond_to_nonexistent_message(self, communicator_automated):
        """Test responding to non-existent message fails"""
        success = communicator_automated.respond(
            "invalid-id",
            "Response",
            "pm"
        )
        
        assert success is False
    
    def test_get_pending_questions(self, communicator_automated):
        """Test retrieving pending questions"""
        # Ask multiple questions
        q1 = communicator_automated.ask("architect", "pm", "Q1", {}, 123)
        q2 = communicator_automated.ask("engineer", "pm", "Q2", {}, 124)
        q3 = communicator_automated.ask("ux", "architect", "Q3", {}, 125)
        
        # Get PM's pending questions
        pm_questions = communicator_automated.get_pending_questions("pm")
        assert len(pm_questions) == 2
        assert all(q.to_agent == "pm" for q in pm_questions)
        
        # Get Architect's pending questions
        arch_questions = communicator_automated.get_pending_questions("architect")
        assert len(arch_questions) == 1
        assert arch_questions[0].content == "Q3"
        
        # Respond to one
        communicator_automated.respond(q1, "A1", "pm")
        
        # Should now have one fewer pending
        pm_questions = communicator_automated.get_pending_questions("pm")
        assert len(pm_questions) == 1
    
    def test_get_conversation(self, communicator_automated):
        """Test retrieving full conversation for an issue"""
        # Create conversation for issue 123
        q1 = communicator_automated.ask("architect", "pm", "Q1", {}, 123)
        communicator_automated.respond(q1, "A1", "pm")
        
        q2 = communicator_automated.ask("architect", "pm", "Q2", {}, 123)
        communicator_automated.respond(q2, "A2", "pm")
        
        # Add message for different issue
        communicator_automated.ask("engineer", "pm", "Q3", {}, 999)
        
        # Get conversation for issue 123
        conversation = communicator_automated.get_conversation(123)
        
        assert len(conversation) == 4  # 2 questions + 2 responses for issue 123
        assert all(m.issue_number == 123 for m in conversation)
    
    def test_message_threading(self, communicator_automated):
        """Test response_to field links messages"""
        question_id = communicator_automated.ask(
            "architect", "pm", "Question", {}, 123
        )
        
        communicator_automated.respond(question_id, "Answer", "pm")
        
        # Find response
        response = next(
            m for m in communicator_automated.message_queue
            if m.message_type == MessageType.RESPONSE
        )
        
        assert response.response_to == question_id
        assert response.from_agent == "pm"
        assert response.to_agent == "architect"  # Response goes back


class TestClarificationMixin:
    """Test ClarificationMixin functionality"""
    
    class TestAgent(ClarificationMixin, BaseAgent):
        """Test agent with clarification support"""
        
        def get_system_prompt(self):
            return "Test"
        
        def get_output_path(self, issue_number):
            return Path(f"/tmp/test-{issue_number}.md")
        
        def _execute_agent(self, issue, context):
            return {"success": True}
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"test": {"enabled": True}},
            "output": {"prd_dir": "docs/prd"}
        })
    
    @pytest.fixture
    def agent(self, config):
        """Create test agent"""
        agent = self.TestAgent(config, sdk=None)
        agent.github = Mock(spec=GitHubTool)
        agent.github._is_configured.return_value = True
        return agent
    
    def test_agent_has_clarification_methods(self, agent):
        """Test agent has clarification methods"""
        assert hasattr(agent, 'ask_clarification')
        assert hasattr(agent, 'check_pending_questions')
        assert callable(agent.ask_clarification)
        assert callable(agent.check_pending_questions)
    
    def test_ask_clarification_automated(self, agent):
        """Test asking clarification in automated mode"""
        agent.execution_mode = "automated"
        
        question_id = agent.ask_clarification(
            question="Clarify scope?",
            target_agent="pm",
            context={"issue": 123},
            issue_number=123
        )
        
        assert question_id is not None
    
    def test_ask_clarification_manual(self, agent):
        """Test asking clarification in manual mode"""
        agent.execution_mode = "manual"
        
        with patch('builtins.print'):
            question_id = agent.ask_clarification(
                question="Clarify scope?",
                target_agent="user",
                context={"issue": 123},
                issue_number=123
            )
        
        assert question_id is not None
    
    def test_check_pending_questions(self, agent):
        """Test checking pending questions"""
        agent.execution_mode = "automated"
        
        agent.ask_clarification(
            "Question?", "pm", {}, 123
        )
        
        # The agent shouldn't have pending questions - they're sent TO pm
        pending = agent.check_pending_questions()
        assert len(pending) == 0  # No questions directed at this agent


class TestMultiAgentCommunication:
    """Test complex multi-agent communication scenarios"""
    
    @pytest.fixture
    def communicator(self):
        """Create communicator"""
        github = Mock(spec=GitHubTool)
        github._is_configured.return_value = True
        return AgentCommunicator(execution_mode="automated", github_tool=github)
    
    def test_multiple_agents_asking_same_agent(self, communicator):
        """Test multiple agents asking the same agent"""
        # Three agents ask PM
        q1 = communicator.ask("architect", "pm", "Q1", {}, 123)
        q2 = communicator.ask("engineer", "pm", "Q2", {}, 123)
        q3 = communicator.ask("ux", "pm", "Q3", {}, 123)
        
        # PM should have 3 pending questions
        pending = communicator.get_pending_questions("pm")
        assert len(pending) == 3
        
        # PM responds to each
        communicator.respond(q1, "A1", "pm")
        communicator.respond(q2, "A2", "pm")
        communicator.respond(q3, "A3", "pm")
        
        # No more pending
        pending = communicator.get_pending_questions("pm")
        assert len(pending) == 0
    
    def test_circular_communication(self, communicator):
        """Test agents can communicate in a circle"""
        # PM → Architect
        q1 = communicator.ask("pm", "architect", "Design this", {}, 123)
        communicator.respond(q1, "Need clarification", "architect")
        
        # Architect → PM
        q2 = communicator.ask("architect", "pm", "What's the budget?", {}, 123)
        communicator.respond(q2, "$100k", "pm")
        
        # Architect → Engineer
        q3 = communicator.ask("architect", "engineer", "Can we build this?", {}, 123)
        communicator.respond(q3, "Yes", "engineer")
        
        conversation = communicator.get_conversation(123)
        assert len(conversation) == 6  # 3 questions + 3 responses
    
    def test_notification_messages(self, communicator):
        """Test notification-type messages"""
        # Manually create notification
        notification = AgentMessage(
            from_agent="engineer",
            to_agent="pm",
            message_type=MessageType.NOTIFICATION,
            content="PR created",
            issue_number=123
        )
        
        communicator.message_queue.append(notification)
        
        # Notifications don't need responses
        pending = communicator.get_pending_questions("pm")
        assert len(pending) == 0  # Notification not in pending questions


class TestGitHubIntegration:
    """Test GitHub integration for communication"""
    
    def test_clarification_posted_to_github(self):
        """Test clarifications are posted as GitHub comments"""
        github = Mock(spec=GitHubTool)
        github._is_configured.return_value = True
        
        communicator = AgentCommunicator(
            execution_mode="automated",
            github_tool=github
        )
        
        question_id = communicator.ask(
            "architect",
            "pm",
            "Need clarification",
            {"context": "data"},
            123
        )
        
        # Should call add_comment
        github.add_comment.assert_called_once()
        
        call_args = github.add_comment.call_args
        assert call_args[0][0] == 123  # Issue number
        assert "clarification" in call_args[0][1].lower()  # Comment contains "clarification"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
