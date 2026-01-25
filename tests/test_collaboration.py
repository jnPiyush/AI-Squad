"""
Tests for iterative collaboration with dialogue flow
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from pathlib import Path

from ai_squad.core.collaboration import (
    run_collaboration,
    CollaborationMode,
    _run_sequential_collaboration,
    _run_iterative_collaboration,
    _parse_feedback
)


class TestCollaborationModes:
    """Test collaboration mode selection"""
    
    def test_collaboration_mode_enum(self):
        """Test CollaborationMode enum values"""
        assert CollaborationMode.SEQUENTIAL == "sequential"
        assert CollaborationMode.ITERATIVE == "iterative"
    
    def test_run_collaboration_defaults_to_iterative(self):
        """Test run_collaboration uses iterative mode by default"""
        with patch('ai_squad.core.collaboration._run_iterative_collaboration') as mock_iter:
            mock_iter.return_value = {"success": True, "mode": "iterative"}
            result = run_collaboration(123, ["pm", "architect"])
            
            assert result["success"]
            assert result["mode"] == "iterative"
            mock_iter.assert_called_once()
    
    def test_run_collaboration_sequential_mode(self):
        """Test run_collaboration uses sequential mode when specified"""
        with patch('ai_squad.core.collaboration._run_sequential_collaboration') as mock_seq:
            mock_seq.return_value = {"success": True, "mode": "sequential"}
            result = run_collaboration(123, ["pm", "architect", "engineer"], mode=CollaborationMode.SEQUENTIAL)
            
            assert result["success"]
            assert result["mode"] == "sequential"
            mock_seq.assert_called_once()


class TestSequentialCollaboration:
    """Test sequential collaboration (legacy mode)"""
    
    @pytest.fixture
    def mock_executor(self):
        """Mock AgentExecutor"""
        with patch('ai_squad.core.collaboration.AgentExecutor') as mock:
            executor = Mock()
            mock.return_value = executor
            yield executor
    
    def test_sequential_collaboration_success(self, mock_executor):
        """Test sequential collaboration executes agents in order"""
        mock_executor.execute.side_effect = [
            {"success": True, "output": "PRD created", "file_path": "docs/prd/PRD-123.md"},
            {"success": True, "output": "ADR created", "file_path": "docs/adr/ADR-123.md"}
        ]
        
        result = _run_sequential_collaboration(123, ["pm", "architect"])
        
        assert result["success"]
        assert result["mode"] == "sequential"
        assert len(result["results"]) == 2
        assert len(result["files"]) == 2
        assert "docs/prd/PRD-123.md" in result["files"]
        assert "docs/adr/ADR-123.md" in result["files"]
    
    def test_sequential_collaboration_agent_failure(self, mock_executor):
        """Test sequential collaboration stops on agent failure"""
        mock_executor.execute.side_effect = [
            {"success": True, "output": "PRD created", "file_path": "docs/prd/PRD-123.md"},
            {"success": False, "error": "Architect failed"}
        ]
        
        result = _run_sequential_collaboration(123, ["pm", "architect"])
        
        assert not result["success"]
        assert "Architect failed" in result["error"]
        assert len(result["partial_results"]) == 2


class TestIterativeCollaboration:
    """Test iterative collaboration with dialogue"""
    
    @pytest.fixture
    def mock_executor(self):
        """Mock AgentExecutor"""
        with patch('ai_squad.core.collaboration.AgentExecutor') as mock:
            executor = Mock()
            mock.return_value = executor
            yield executor
    
    @pytest.fixture
    def mock_signal_manager(self):
        """Mock SignalManager"""
        with patch('ai_squad.core.collaboration.SignalManager') as mock:
            manager = Mock()
            mock.return_value = manager
            yield manager
    
    def test_iterative_requires_exactly_two_agents(self):
        """Test iterative mode validates exactly 2 agents"""
        result = _run_iterative_collaboration(123, ["pm"])
        assert not result["success"]
        assert "exactly 2 agents" in result["error"]
        
        result = _run_iterative_collaboration(123, ["pm", "architect", "engineer"])
        assert not result["success"]
        assert "exactly 2 agents" in result["error"]
    
    def test_iterative_collaboration_immediate_approval(self, mock_executor, mock_signal_manager):
        """Test iterative collaboration with immediate approval"""
        mock_executor.execute.side_effect = [
            # PM initial output
            {"success": True, "output": "PRD v1", "file_path": "docs/prd/PRD-123.md"},
            # Architect review - approves
            {"success": True, "output": "Looks good! APPROVED. This is excellent."}
        ]
        
        result = _run_iterative_collaboration(123, ["pm", "architect"], max_iterations=3)
        
        assert result["success"]
        assert result["mode"] == "iterative"
        assert result["approved"]
        assert result["iterations"] == 1
        assert len(result["conversation"]) == 2  # Initial + review
        assert result["participants"]["primary"] == "pm"
        assert result["participants"]["reviewer"] == "architect"
    
    def test_iterative_collaboration_with_iterations(self, mock_executor, mock_signal_manager):
        """Test iterative collaboration with multiple iterations"""
        mock_executor.execute.side_effect = [
            # PM initial output
            {"success": True, "output": "PRD v1", "file_path": "docs/prd/PRD-123.md"},
            # Architect review 1 - needs work
            {"success": True, "output": "Needs work on security requirements"},
            # PM iteration 1
            {"success": True, "output": "PRD v2", "file_path": "docs/prd/PRD-123.md"},
            # Architect review 2 - approves
            {"success": True, "output": "Perfect! APPROVED."}
        ]
        
        result = _run_iterative_collaboration(123, ["pm", "architect"], max_iterations=3)
        
        assert result["success"]
        assert result["mode"] == "iterative"
        assert result["approved"]
        assert result["iterations"] == 2
        assert len(result["conversation"]) == 4  # Initial + review + iteration + review
    
    def test_iterative_collaboration_max_iterations_reached(self, mock_executor, mock_signal_manager):
        """Test iterative collaboration stops at max iterations"""
        # All reviews say "needs work"
        mock_executor.execute.side_effect = [
            {"success": True, "output": "PRD v1", "file_path": "docs/prd/PRD-123.md"},
            {"success": True, "output": "Needs work on X"},
            {"success": True, "output": "PRD v2", "file_path": "docs/prd/PRD-123.md"},
            {"success": True, "output": "Needs work on Y"},
            {"success": True, "output": "PRD v3", "file_path": "docs/prd/PRD-123.md"},
            {"success": True, "output": "Still needs work on Z"}
        ]
        
        result = _run_iterative_collaboration(123, ["pm", "architect"], max_iterations=3)
        
        assert result["success"]  # Completes successfully
        assert result["mode"] == "iterative"
        assert not result["approved"]  # Not approved
        assert result["iterations"] == 3  # Reached max
    
    def test_iterative_collaboration_primary_failure(self, mock_executor, mock_signal_manager):
        """Test iterative collaboration handles primary agent failure"""
        mock_executor.execute.side_effect = [
            # PM fails
            {"success": False, "error": "Failed to create PRD"}
        ]
        
        result = _run_iterative_collaboration(123, ["pm", "architect"], max_iterations=3)
        
        assert not result["success"]
        assert "pm failed" in result["error"]
        assert result["iterations"] == 0
    
    def test_iterative_collaboration_iteration_failure(self, mock_executor, mock_signal_manager):
        """Test iterative collaboration handles iteration failure"""
        mock_executor.execute.side_effect = [
            {"success": True, "output": "PRD v1", "file_path": "docs/prd/PRD-123.md"},
            {"success": True, "output": "Needs work"},
            {"success": False, "error": "Failed to iterate"}  # PM fails on iteration
        ]
        
        result = _run_iterative_collaboration(123, ["pm", "architect"], max_iterations=3)
        
        assert not result["success"]
        assert "iteration 1 failed" in result["error"]
        assert len(result["conversation"]) == 3


class TestFeedbackParsing:
    """Test feedback parsing logic"""
    
    def test_parse_feedback_approved(self):
        """Test parsing approved feedback"""
        result = {"output": "This looks good! APPROVED. Great work."}
        feedback = _parse_feedback(result)
        
        assert feedback["approved"]
        assert "great work" in feedback["comments"].lower()
        assert feedback["severity"] == "info"
    
    def test_parse_feedback_needs_work(self):
        """Test parsing feedback that needs work"""
        result = {"output": "This needs work. Fix the API design."}
        feedback = _parse_feedback(result)
        
        assert not feedback["approved"]
        assert "needs work" in feedback["comments"].lower()
    
    def test_parse_feedback_with_warning(self):
        """Test parsing feedback with warning severity"""
        result = {"output": "Concern: Security requirements are missing. Please revise."}
        feedback = _parse_feedback(result)
        
        assert not feedback["approved"]
        assert feedback["severity"] == "warning"
    
    def test_parse_feedback_critical(self):
        """Test parsing critical feedback"""
        result = {"output": "CRITICAL: This is a blocking issue. Cannot proceed."}
        feedback = _parse_feedback(result)
        
        assert not feedback["approved"]
        assert feedback["severity"] == "critical"
    
    def test_parse_feedback_empty_output(self):
        """Test parsing feedback with no output"""
        result = {"output": ""}
        feedback = _parse_feedback(result)
        
        assert "no feedback" in feedback["comments"].lower()
    
    def test_parse_feedback_lgtm(self):
        """Test parsing LGTM (Looks Good To Me) feedback"""
        result = {"output": "LGTM! Ready to proceed."}
        feedback = _parse_feedback(result)
        
        assert feedback["approved"]


class TestCollaborationIntegration:
    """Integration tests for collaboration flow"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_sequential_to_iterative_compatibility(self):
        """Test that sequential mode result format is compatible"""
        with patch('ai_squad.core.collaboration.AgentExecutor') as mock_exec_cls:
            executor = Mock()
            mock_exec_cls.return_value = executor
            executor.execute.return_value = {
                "success": True, 
                "output": "Done", 
                "file_path": "test.md"
            }
            
            seq_result = run_collaboration(123, ["pm"], mode=CollaborationMode.SEQUENTIAL)
            
            # Both modes should have success, mode, files
            assert "success" in seq_result
            assert "mode" in seq_result
            assert "files" in seq_result
    
    def test_iterative_signal_sending(self, temp_workspace):
        """Test that iterative mode sends signals for feedback"""
        with patch('ai_squad.core.collaboration.AgentExecutor') as mock_exec_cls, \
             patch('ai_squad.core.collaboration.SignalManager') as mock_signal_cls:
            
            executor = Mock()
            mock_exec_cls.return_value = executor
            
            signal_manager = Mock()
            mock_signal_cls.return_value = signal_manager
            
            executor.execute.side_effect = [
                {"success": True, "output": "PRD v1", "file_path": "prd.md"},
                {"success": True, "output": "APPROVED"}
            ]
            
            result = _run_iterative_collaboration(123, ["pm", "architect"], max_iterations=2)
            
            # Verify signal was sent
            assert signal_manager.send_message.called
            call_args = signal_manager.send_message.call_args
            assert call_args[1]["sender"] == "architect"
            assert call_args[1]["recipient"] == "pm"
            assert "thread_id" in call_args[1]


class TestBackwardCompatibility:
    """Test backward compatibility with legacy code"""
    
    def test_run_collaboration_without_mode_parameter(self):
        """Test that run_collaboration defaults to iterative when no mode specified"""
        with patch('ai_squad.core.collaboration._run_iterative_collaboration') as mock_iter:
            mock_iter.return_value = {"success": True, "mode": "iterative"}
            
            # Old API: run_collaboration(issue, agents)
            result = run_collaboration(123, ["pm", "architect"])
            
            assert result["success"]
            assert mock_iter.called
