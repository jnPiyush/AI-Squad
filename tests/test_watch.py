"""
Tests for watch mode functionality
"""
# pylint: disable=protected-access
import pytest
from unittest.mock import Mock, patch, MagicMock

from ai_squad.core.watch import WatchDaemon, WatchConfig
from ai_squad.core.config import Config


class TestWatchConfig:
    """Test watch configuration"""
    
    def test_default_interval(self):
        assert WatchConfig.DEFAULT_INTERVAL == 30
    
    def test_validate_interval_normal(self):
        assert WatchConfig.validate_interval(30) == 30
        assert WatchConfig.validate_interval(60) == 60
    
    def test_validate_interval_too_low(self):
        assert WatchConfig.validate_interval(5) == WatchConfig.MIN_INTERVAL
        assert WatchConfig.validate_interval(0) == WatchConfig.MIN_INTERVAL
    
    def test_validate_interval_too_high(self):
        assert WatchConfig.validate_interval(500) == WatchConfig.MAX_INTERVAL
        assert WatchConfig.validate_interval(1000) == WatchConfig.MAX_INTERVAL


class TestWatchDaemon:
    """Test watch daemon"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Mock(spec=Config)
        config.github_repo = "test-owner/test-repo"
        config.github_owner = "test-owner"
        config.prd_dir = "docs/prd"
        config.adr_dir = "docs/adr"
        return config
    
    @pytest.fixture
    def mock_daemon(self, mock_config):
        """Create watch daemon with mocked dependencies"""
        with patch('ai_squad.core.watch.GitHubTool'), \
             patch('ai_squad.core.watch.AgentExecutor'):
            daemon = WatchDaemon(mock_config, interval=10)
            return daemon
    
    def test_initialization(self, mock_config):
        """Test daemon initialization"""
        with patch('ai_squad.core.watch.GitHubTool'), \
             patch('ai_squad.core.watch.AgentExecutor'):
            daemon = WatchDaemon(mock_config, interval=30, repo="custom/repo")
            
            assert daemon.config == mock_config
            assert daemon.interval == 30
            assert daemon.repo == "custom/repo"
            assert daemon.stats["checks"] == 0
            assert daemon.stats["events"] == 0
    
    def test_agent_flow_mapping(self):
        """Test agent flow is correctly defined"""
        expected_flow = {
            "orch:pm-done": "architect",
            "orch:architect-done": "engineer",
            "orch:engineer-done": "reviewer",
        }
        assert WatchDaemon.AGENT_FLOW == expected_flow
    
    def test_get_next_step(self, mock_daemon):
        """Test next step messages"""
        assert "Architect" in mock_daemon._get_next_step("pm")
        assert "Engineer" in mock_daemon._get_next_step("architect")
        assert "Reviewer" in mock_daemon._get_next_step("engineer")
        assert "completed" in mock_daemon._get_next_step("reviewer")
    
    def test_create_completion_comment(self, mock_daemon):
        """Test completion comment generation"""
        result = {
            "success": True,
            "output_path": "docs/adr/ADR-123.md"
        }
        
        comment = mock_daemon._create_completion_comment("architect", result)
        
        assert "OK" in comment
        assert "architect" in comment.lower()
        assert "docs/adr/ADR-123.md" in comment
        assert "Engineer" in comment  # Next step
    
    def test_check_for_triggers_unconfigured(self, mock_daemon):
        """Test triggers check when GitHub not configured"""
        mock_daemon.github._is_configured = Mock(return_value=False)
        
        events = mock_daemon._check_for_triggers()
        
        assert events == []
    
    def test_check_for_triggers_with_issues(self, mock_daemon):
        """Test triggers check with matching issues"""
        mock_daemon.github._is_configured = Mock(return_value=True)
        mock_daemon.github.search_issues_by_labels = Mock(return_value=[
            {
                "number": 123,
                "title": "Test Issue",
                "labels": ["orch:pm-done"]
            }
        ])
        
        events = mock_daemon._check_for_triggers()
        
        assert len(events) >= 1
        assert events[0]["issue"]["number"] == 123
        assert events[0]["agent"] == "architect"
    
    def test_handle_event_success(self, mock_daemon):
        """Test successful event handling"""
        event = {
            "issue": {"number": 123, "title": "Test"},
            "agent": "architect",
            "trigger_label": "orch:pm-done"
        }
        
        mock_daemon.executor.execute = Mock(return_value={
            "success": True,
            "output_path": "docs/adr/ADR-123.md"
        })
        mock_daemon.github.add_labels = Mock(return_value=True)
        mock_daemon.github.add_comment = Mock(return_value=True)
        
        with patch('rich.live.Live'):
            live = MagicMock()
            result = mock_daemon._handle_event(event, live)
        
        assert result is True
        mock_daemon.executor.execute.assert_called_once_with("architect", 123)
        mock_daemon.github.add_labels.assert_called_once()
        mock_daemon.github.add_comment.assert_called_once()
    
    def test_handle_event_failure(self, mock_daemon):
        """Test failed event handling"""
        event = {
            "issue": {"number": 123, "title": "Test"},
            "agent": "engineer",
            "trigger_label": "orch:architect-done"
        }
        
        mock_daemon.executor.execute = Mock(return_value={
            "success": False,
            "error": "Test error"
        })
        mock_daemon.github.add_comment = Mock(return_value=True)
        
        with patch('rich.live.Live'):
            live = MagicMock()
            result = mock_daemon._handle_event(event, live)
        
        assert result is False
        mock_daemon.github.add_comment.assert_called_once()
    
    def test_processed_events_tracking(self, mock_daemon):
        """Test that events are tracked to avoid duplicates"""
        mock_daemon.github._is_configured = Mock(return_value=True)
        
        # Mock returns issue only when looking for orch:pm-done
        def mock_search(include_labels, exclude_labels=None):
            if "orch:pm-done" in include_labels:
                return [{"number": 123, "title": "Test", "labels": ["orch:pm-done"]}]
            return []
        
        mock_daemon.github.search_issues_by_labels = Mock(side_effect=mock_search)
        
        # First check should find event
        events1 = mock_daemon._check_for_triggers()
        assert len(events1) == 1
        
        # Second check should not return same event (already processed)
        events2 = mock_daemon._check_for_triggers()
        assert len(events2) == 0
    
    def test_create_status_table(self, mock_daemon):
        """Test status table creation"""
        mock_daemon.stats["checks"] = 5
        mock_daemon.stats["events"] = 3
        mock_daemon.stats["successes"] = 2
        mock_daemon.stats["failures"] = 1
        
        table = mock_daemon._create_status_table()
        
        assert table is not None
        assert "AI-Squad Watch Mode" in table.title
    
    def test_stats_initialization(self, mock_daemon):
        """Test statistics are properly initialized"""
        assert mock_daemon.stats["checks"] == 0
        assert mock_daemon.stats["events"] == 0
        assert mock_daemon.stats["successes"] == 0
        assert mock_daemon.stats["failures"] == 0


class TestWatchIntegration:
    """Integration tests for watch mode"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Mock(spec=Config)
        config.github_repo = "test-owner/test-repo"
        config.github_owner = "test-owner"
        return config
    
    def test_full_orchestration_flow(self, mock_config):
        """Test complete PM → Architect → Engineer → Reviewer flow"""
        with patch('ai_squad.core.watch.GitHubTool') as MockGitHub, \
             patch('ai_squad.core.watch.AgentExecutor') as MockExecutor:
            
            # Setup mocks
            github = MockGitHub.return_value
            github._is_configured.return_value = True
            
            executor = MockExecutor.return_value
            executor.execute.return_value = {"success": True, "output_path": "test.md"}
            
            daemon = WatchDaemon(mock_config, interval=10)
            
            # Simulate PM completion - only return when checking for pm-done
            def mock_search_pm(include_labels, exclude_labels=None):
                if "orch:pm-done" in include_labels and "orch:architect-done" in (exclude_labels or []):
                    return [{"number": 100, "title": "Epic", "labels": ["orch:pm-done"]}]
                return []
            
            github.search_issues_by_labels.side_effect = mock_search_pm
            
            events = daemon._check_for_triggers()
            assert len(events) == 1
            assert events[0]["agent"] == "architect"
            
            # Simulate Architect completion
            daemon.processed_events.clear()  # Reset for next check
            
            def mock_search_architect(include_labels, exclude_labels=None):
                if "orch:architect-done" in include_labels and "orch:engineer-done" in (exclude_labels or []):
                    return [{"number": 100, "title": "Epic", "labels": ["orch:architect-done"]}]
                return []
            
            github.search_issues_by_labels.side_effect = mock_search_architect
            
            events = daemon._check_for_triggers()
            assert len(events) == 1
            assert events[0]["agent"] == "engineer"
