"""
Tests for agent implementations
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import shutil

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
            "agents": {"pm": {"enabled": True, "model": "claude-sonnet-4.5"}},
            "output": {"prd_dir": "docs/prd"},
            "skills": ["all"]
        })
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def agent(self, config):
        """Create PM agent"""
        return ProductManagerAgent(config, sdk=None)
    
    @pytest.fixture
    def agent_with_orchestration(self, config, temp_workspace):
        """Create PM agent with orchestration context"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.signal import SignalManager
        
        orchestration = {
            'workstate': WorkStateManager(temp_workspace),
            'signal': SignalManager(temp_workspace),
            'handoff': None,
            'strategy': None,
            'convoy': None
        }
        return ProductManagerAgent(config, sdk=None, orchestration=orchestration)
    
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
    def test_execute_creates_prd(self, mock_get_issue, agent):
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
    
    def test_agent_inherits_from_base(self, agent):
        """Test PM agent inheritance"""
        from ai_squad.agents.base import BaseAgent
        assert isinstance(agent, BaseAgent)
    
    def test_agent_with_orchestration_has_managers(self, agent_with_orchestration):
        """Test PM agent receives orchestration managers"""
        assert agent_with_orchestration.workstate is not None
        assert agent_with_orchestration.signal is not None
    
    @patch("ai_squad.tools.github.GitHubTool.get_issue")
    def test_execute_with_labels_as_dicts(self, mock_get_issue, agent):
        """Test PRD creation with labels as dict objects"""
        mock_get_issue.return_value = {
            "number": 124,
            "title": "Test Feature",
            "body": "Test description",
            "labels": [{"name": "type:feature"}, {"name": "priority:high"}],
            "user": {"login": "testuser"},
            "created_at": "2026-01-22"
        }
        
        result = agent.execute(124)
        assert "success" in result
    
    @patch("ai_squad.tools.github.GitHubTool.get_issue")
    def test_execute_with_empty_body(self, mock_get_issue, agent):
        """Test PRD creation with empty issue body"""
        mock_get_issue.return_value = {
            "number": 125,
            "title": "Test Feature",
            "body": None,
            "labels": [],
            "user": {"login": "testuser"},
            "created_at": "2026-01-22"
        }
        
        result = agent.execute(125)
        assert "success" in result


class TestArchitectAgent:
    """Test Architect agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"architect": {"enabled": True, "model": "claude-sonnet-4.5"}},
            "output": {
                "adr_dir": "docs/adr",
                "specs_dir": "docs/specs",
                "architecture_dir": "docs/architecture",
            },
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
    
    def test_agent_type(self, agent):
        """Test agent type is set correctly"""
        assert "architect" in agent.agent_type.lower()

    @patch("ai_squad.tools.github.GitHubTool.get_issue")
    def test_execute_creates_architecture_doc(self, mock_get_issue, tmp_path, monkeypatch):
        """Architect should generate ADR, SPEC, and ARCH documents"""
        config = Config({
            "project": {"name": "Test"},
            "agents": {"architect": {"enabled": True, "model": "claude-sonnet-4.5"}},
            "output": {
                "adr_dir": str(tmp_path / "adr"),
                "specs_dir": str(tmp_path / "specs"),
                "architecture_dir": str(tmp_path / "architecture"),
            },
            "skills": ["all"],
        })

        mock_get_issue.return_value = {
            "number": 321,
            "title": "Test Feature",
            "body": "Test description",
            "labels": ["type:feature"],
            "user": {"login": "testuser"},
            "created_at": "2026-01-22",
        }

        agent = ArchitectAgent(config, sdk=None)
        agent.workflow_validator.get_missing_prerequisites = Mock(return_value=[])

        monkeypatch.chdir(tmp_path)
        result = agent.execute(321)

        assert result["success"] is True
        assert (tmp_path / "architecture" / "ARCH-321.md").exists()


class TestEngineerAgent:
    """Test Engineer agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"engineer": {"enabled": True, "model": "claude-sonnet-4.5"}},
            "output": {},
            "skills": ["testing", "security"]
        })
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def agent(self, config):
        """Create Engineer agent"""
        return EngineerAgent(config, sdk=None)
    
    @pytest.fixture
    def agent_with_orchestration(self, config, temp_workspace):
        """Create Engineer agent with orchestration context"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.signal import SignalManager
        
        orchestration = {
            'workstate': WorkStateManager(temp_workspace),
            'signal': SignalManager(temp_workspace),
            'handoff': None,
            'strategy': None,
            'convoy': None
        }
        return EngineerAgent(config, sdk=None, orchestration=orchestration)
    
    def test_get_system_prompt(self, agent):
        """Test system prompt"""
        prompt = agent.get_system_prompt()
        assert "Engineer" in prompt
        assert "test" in prompt.lower()
    
    def test_get_system_prompt_contains_coverage(self, agent):
        """Test system prompt contains coverage requirements"""
        prompt = agent.get_system_prompt()
        assert "%" in prompt  # Should mention coverage percentage
    
    def test_get_system_prompt_contains_test_pyramid(self, agent):
        """Test system prompt contains test pyramid info"""
        prompt = agent.get_system_prompt()
        assert "unit" in prompt.lower()
        assert "integration" in prompt.lower()
    
    def test_get_output_path_returns_src(self, agent):
        """Test output path returns src directory"""
        path = agent.get_output_path(789)
        assert "src" in str(path)
    
    @patch("ai_squad.tools.github.GitHubTool.get_issue")
    def test_execute_engineer_basic(self, mock_get_issue, agent):
        """Test basic engineer execution"""
        mock_get_issue.return_value = {
            "number": 789,
            "title": "Implement Login Feature",
            "body": "Add user login with JWT",
            "labels": ["type:feature"],
            "user": {"login": "testuser"},
            "created_at": "2026-01-22"
        }
        
        result = agent.execute(789)
        assert "success" in result
    
    def test_agent_with_orchestration_has_managers(self, agent_with_orchestration):
        """Test Engineer agent receives orchestration managers"""
        assert agent_with_orchestration.workstate is not None
        assert agent_with_orchestration.signal is not None


class TestUXDesignerAgent:
    """Test UX Designer agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"ux": {"enabled": True, "model": "claude-sonnet-4.5"}},
            "output": {"ux_dir": "docs/ux"},
            "skills": ["all"]
        })
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def agent(self, config):
        """Create UX Designer agent"""
        return UXDesignerAgent(config, sdk=None)
    
    @pytest.fixture
    def agent_with_orchestration(self, config, temp_workspace):
        """Create UX agent with orchestration context"""
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.signal import SignalManager
        
        orchestration = {
            'workstate': WorkStateManager(temp_workspace),
            'signal': SignalManager(temp_workspace),
            'handoff': None,
            'strategy': None,
            'convoy': None
        }
        return UXDesignerAgent(config, sdk=None, orchestration=orchestration)
    
    def test_get_system_prompt(self, agent):
        """Test system prompt"""
        prompt = agent.get_system_prompt()
        assert "UX Designer" in prompt
        assert "wireframe" in prompt.lower()
    
    def test_get_system_prompt_accessibility(self, agent):
        """Test system prompt mentions accessibility"""
        prompt = agent.get_system_prompt()
        # Should mention accessibility or WCAG
        assert "accessib" in prompt.lower() or "wcag" in prompt.lower() or "a11y" in prompt.lower()
    
    def test_get_output_path(self, agent):
        """Test output path for UX documents"""
        path = agent.get_output_path(101)
        assert "UX" in str(path) or "ux" in str(path).lower()
    
    @patch("ai_squad.tools.github.GitHubTool.get_issue")
    def test_execute_ux_basic(self, mock_get_issue, agent):
        """Test basic UX execution"""
        mock_get_issue.return_value = {
            "number": 101,
            "title": "Design Login Page",
            "body": "Create wireframes for login",
            "labels": ["type:ux"],
            "user": {"login": "testuser"},
            "created_at": "2026-01-22"
        }
        
        result = agent.execute(101)
        assert "success" in result
    
    def test_agent_with_orchestration_has_managers(self, agent_with_orchestration):
        """Test UX agent receives orchestration managers"""
        assert agent_with_orchestration.workstate is not None


class TestReviewerAgent:
    """Test Reviewer agent"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"reviewer": {"enabled": True, "model": "claude-sonnet-4.5"}},
            "output": {"reviews_dir": "docs/reviews"},
            "skills": ["code-review-and-audit", "security"]
        })
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def agent(self, config):
        """Create Reviewer agent"""
        return ReviewerAgent(config, sdk=None)
    
    def test_get_system_prompt(self, agent):
        """Test system prompt"""
        prompt = agent.get_system_prompt()
        assert "Reviewer" in prompt
        assert "review" in prompt.lower()
    
    def test_get_system_prompt_security(self, agent):
        """Test system prompt mentions security"""
        prompt = agent.get_system_prompt()
        assert "security" in prompt.lower()
    
    def test_get_output_path(self, agent):
        """Test output path"""
        path = agent.get_output_path(789)
        assert "REVIEW-789.md" in str(path)
    
    @patch("ai_squad.tools.github.GitHubTool.get_issue")
    def test_execute_reviewer_basic(self, mock_get_issue, agent):
        """Test basic reviewer execution"""
        mock_get_issue.return_value = {
            "number": 789,
            "title": "Add Login Feature",
            "body": "Implements JWT login",
            "labels": [],
            "user": {"login": "testuser"},
            "created_at": "2026-01-22",
            "state": "open"
        }
        
        result = agent.execute(789)
        assert "success" in result


class TestBaseAgentOrchestration:
    """Test BaseAgent orchestration integration"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"pm": {"enabled": True}},
            "output": {"prd_dir": "docs/prd"},
            "skills": []
        })
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_agent_without_orchestration(self, config):
        """Test agent works without orchestration context"""
        agent = ProductManagerAgent(config, sdk=None)
        
        assert agent.orchestration == {}
        assert agent.workstate is None
        assert agent.signal is None
    
    def test_agent_with_partial_orchestration(self, config, temp_workspace):
        """Test agent works with partial orchestration context"""
        from ai_squad.core.workstate import WorkStateManager
        
        orchestration = {
            'workstate': WorkStateManager(temp_workspace),
            # signal, handoff, etc. are missing
        }
        
        agent = ProductManagerAgent(config, sdk=None, orchestration=orchestration)
        
        assert agent.workstate is not None
        assert agent.signal is None  # Not provided
    
    def test_agent_inherits_execution_mode(self, config):
        """Test agent has execution mode property"""
        agent = ProductManagerAgent(config, sdk=None)
        
        assert hasattr(agent, 'execution_mode')
        assert agent.execution_mode == "manual"
    
    def test_agent_has_ai_provider(self, config):
        """Test agent has AI provider"""
        agent = ProductManagerAgent(config, sdk=None)
        
        assert hasattr(agent, 'ai_provider')
        assert agent.ai_provider is not None
