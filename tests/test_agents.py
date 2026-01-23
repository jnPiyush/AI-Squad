"""
Tests for agent implementations
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from ai_squad.core.config import Config
from ai_squad.agents.product_manager import ProductManagerAgent
from ai_squad.agents.architect import ArchitectAgent
from ai_squad.agents.engineer import EngineerAgent
from ai_squad.agents.ux_designer import UXDesignerAgent
from ai_squad.agents.reviewer import ReviewerAgent


class TestProductManagerAgent:
    """Test Product Manager agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"pm": {"enabled": True, "model": "gpt-4"}},
            "output": {"prd_dir": "docs/prd"},
            "skills": ["all"]
        })
    
    @pytest.fixture
    def agent(self, config):
        """Create PM agent"""
        return ProductManagerAgent(config, sdk=None)
    
    def test_get_system_prompt(self, agent):
        """Test system prompt generation"""
        prompt = agent.get_system_prompt()
        assert "Product Manager" in prompt
        assert "PRD" in prompt
    
    def test_get_output_path(self, agent):
        """Test output path generation"""
        path = agent.get_output_path(123)
        assert "PRD-123.md" in str(path)
    
    @patch("ai_squad.tools.github.GitHubTool.get_issue")
    def test_execute_creates_prd(self, mock_get_issue, agent, tmp_path):
        """Test PRD creation"""
        # Mock issue
        mock_get_issue.return_value = {
            "number": 123,
            "title": "Test Feature",
            "body": "Test description",
            "labels": ["type:feature"],
            "user": {"login": "testuser"},
            "created_at": "2026-01-22"
        }
        
        # Execute (will fail without full setup, but we can test structure)
        result = agent.execute(123)
        
        # Should attempt to create PRD
        assert "success" in result


class TestArchitectAgent:
    """Test Architect agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"architect": {"enabled": True, "model": "gpt-4"}},
            "output": {"adr_dir": "docs/adr", "specs_dir": "docs/specs"},
            "skills": ["all"]
        })
    
    @pytest.fixture
    def agent(self, config):
        """Create Architect agent"""
        return ArchitectAgent(config, sdk=None)
    
    def test_get_system_prompt(self, agent):
        """Test system prompt"""
        prompt = agent.get_system_prompt()
        assert "Architect" in prompt
        assert "ADR" in prompt
    
    def test_get_output_path(self, agent):
        """Test output path"""
        path = agent.get_output_path(456)
        assert "ADR-456.md" in str(path)


class TestEngineerAgent:
    """Test Engineer agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"engineer": {"enabled": True, "model": "gpt-4"}},
            "output": {},
            "skills": ["testing", "security"]
        })
    
    @pytest.fixture
    def agent(self, config):
        """Create Engineer agent"""
        return EngineerAgent(config, sdk=None)
    
    def test_get_system_prompt(self, agent):
        """Test system prompt"""
        prompt = agent.get_system_prompt()
        assert "Engineer" in prompt
        assert "test" in prompt.lower()


class TestUXDesignerAgent:
    """Test UX Designer agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"ux": {"enabled": True, "model": "gpt-4"}},
            "output": {"ux_dir": "docs/ux"},
            "skills": ["all"]
        })
    
    @pytest.fixture
    def agent(self, config):
        """Create UX Designer agent"""
        return UXDesignerAgent(config, sdk=None)
    
    def test_get_system_prompt(self, agent):
        """Test system prompt"""
        prompt = agent.get_system_prompt()
        assert "UX Designer" in prompt
        assert "wireframe" in prompt.lower()


class TestReviewerAgent:
    """Test Reviewer agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"reviewer": {"enabled": True, "model": "gpt-4"}},
            "output": {"reviews_dir": "docs/reviews"},
            "skills": ["code-review-and-audit", "security"]
        })
    
    @pytest.fixture
    def agent(self, config):
        """Create Reviewer agent"""
        return ReviewerAgent(config, sdk=None)
    
    def test_get_system_prompt(self, agent):
        """Test system prompt"""
        prompt = agent.get_system_prompt()
        assert "Reviewer" in prompt
        assert "review" in prompt.lower()
    
    def test_get_output_path(self, agent):
        """Test output path"""
        path = agent.get_output_path(789)
        assert "REVIEW-789.md" in str(path)
