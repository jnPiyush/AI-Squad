"""
Tests for AgentCommunicator retry logic and circuit breaker
"""
import pytest
from unittest.mock import Mock, patch
from ai_squad.core.agent_comm import AgentCommunicator, AgentMessage, MessageType


class TestRetryLogic:
    """Test message routing retry logic"""
    
    @pytest.fixture
    def communicator(self):
        """Create communicator for testing"""
        return AgentCommunicator(execution_mode="automated")
    
    def test_successful_routing(self, communicator):
        """Test successful message routing on first attempt"""
        with patch('ai_squad.core.agent_registry.get_registry') as mock_registry:
            mock_reg = Mock()
            mock_handler = Mock(return_value={"response": "success"})
            mock_reg.get_handler.return_value = mock_handler
            mock_reg.is_circuit_open.return_value = False
            mock_reg.record_success = Mock()
            mock_registry.return_value = mock_reg
            
            message = AgentMessage(
                from_agent="pm",
                to_agent="engineer",
                message_type=MessageType.QUESTION,
                content="Test question",
            )
            
            result = communicator._route_message(message)
            
            assert result == "success"
            assert mock_handler.call_count == 1
            mock_reg.record_success.assert_called_once_with("engineer")
    
    def test_retry_on_failure(self, communicator):
        """Test retry logic on transient failures"""
        with patch('ai_squad.core.agent_registry.get_registry') as mock_registry:
            mock_reg = Mock()
            
            # Fail twice, succeed on third attempt
            mock_handler = Mock(side_effect=[
                Exception("Temporary error"),
                Exception("Temporary error"),
                {"response": "success"},
            ])
            
            mock_reg.get_handler.return_value = mock_handler
            mock_reg.is_circuit_open.return_value = False
            mock_reg.record_success = Mock()
            mock_reg.record_failure = Mock()
            mock_registry.return_value = mock_reg
            
            message = AgentMessage(
                from_agent="pm",
                to_agent="engineer",
                content="Test",
            )
            
            with patch('time.sleep'):  # Speed up test
                result = communicator._route_message(message)
            
            assert result == "success"
            assert mock_handler.call_count == 3
            assert mock_reg.record_failure.call_count == 2
            mock_reg.record_success.assert_called_once()
    
    def test_max_retries_exceeded(self, communicator):
        """Test that failures after max retries return None"""
        with patch('ai_squad.core.agent_registry.get_registry') as mock_registry:
            mock_reg = Mock()
            
            # Always fail
            mock_handler = Mock(side_effect=Exception("Persistent error"))
            
            mock_reg.get_handler.return_value = mock_handler
            mock_reg.is_circuit_open.return_value = False
            mock_reg.record_failure = Mock()
            mock_registry.return_value = mock_reg
            
            message = AgentMessage(
                from_agent="pm",
                to_agent="engineer",
                content="Test",
            )
            
            with patch('time.sleep'):  # Speed up test
                result = communicator._route_message(message)
            
            assert result is None
            assert mock_handler.call_count == 3  # Max retries
            assert mock_reg.record_failure.call_count == 3
    
    def test_circuit_breaker_open(self, communicator):
        """Test that open circuit breaker prevents routing"""
        with patch('ai_squad.core.agent_registry.get_registry') as mock_registry:
            mock_reg = Mock()
            mock_handler = Mock(return_value={"response": "success"})
            
            mock_reg.get_handler.return_value = mock_handler
            mock_reg.is_circuit_open.return_value = True  # Circuit is open
            mock_registry.return_value = mock_reg
            
            message = AgentMessage(
                from_agent="pm",
                to_agent="engineer",
                content="Test",
            )
            
            result = communicator._route_message(message)
            
            assert result is None
            assert mock_handler.call_count == 0  # Should not call handler
    
    def test_exponential_backoff(self, communicator):
        """Test exponential backoff between retries"""
        with patch('ai_squad.core.agent_registry.get_registry') as mock_registry:
            mock_reg = Mock()
            mock_handler = Mock(side_effect=[
                Exception("Error 1"),
                Exception("Error 2"),
                {"response": "success"},
            ])
            
            mock_reg.get_handler.return_value = mock_handler
            mock_reg.is_circuit_open.return_value = False
            mock_reg.record_success = Mock()
            mock_reg.record_failure = Mock()
            mock_registry.return_value = mock_reg
            
            message = AgentMessage(
                from_agent="pm",
                to_agent="engineer",
                content="Test",
            )
            
            with patch('time.sleep') as mock_sleep:
                result = communicator._route_message(message)
            
            # Check backoff delays: 1s, 2s
            assert mock_sleep.call_count == 2
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert delays[0] == 1.0  # First retry: 1 * 2^0
            assert delays[1] == 2.0  # Second retry: 1 * 2^1
    
    def test_routing_without_handler(self, communicator):
        """Test routing when agent has no handler"""
        with patch('ai_squad.core.agent_registry.get_registry') as mock_registry:
            mock_reg = Mock()
            mock_card = Mock()
            
            mock_reg.get_handler.return_value = None
            mock_reg.get.return_value = mock_card  # Agent exists
            mock_registry.return_value = mock_reg
            
            message = AgentMessage(
                from_agent="pm",
                to_agent="engineer",
                content="Test",
            )
            
            result = communicator._route_message(message)
            
            assert result is None  # Queued for async
    
    def test_routing_unknown_agent(self, communicator):
        """Test routing to unknown agent"""
        with patch('ai_squad.core.agent_registry.get_registry') as mock_registry:
            mock_reg = Mock()
            
            mock_reg.get_handler.return_value = None
            mock_reg.get.return_value = None  # Agent doesn't exist
            mock_registry.return_value = mock_reg
            
            message = AgentMessage(
                from_agent="pm",
                to_agent="unknown_agent",
                content="Test",
            )
            
            result = communicator._route_message(message)
            
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
