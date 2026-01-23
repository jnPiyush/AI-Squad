"""
Tests for tools
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from ai_squad.tools.github import GitHubTool
from ai_squad.tools.templates import TemplateEngine
from ai_squad.tools.codebase import CodebaseSearch


class TestGitHubTool:
    """Test GitHub integration"""
    
    @pytest.fixture
    def github_tool(self, mock_config):
        """Create GitHub tool"""
        return GitHubTool(mock_config)
    
    def test_get_issue_mock(self, github_tool):
        """Test get_issue returns mock when not configured"""
        issue = github_tool.get_issue(123)
        
        assert issue is not None
        assert issue["number"] == 123
        assert "Mock Issue" in issue["title"]
    
    def test_get_pr_mock(self, github_tool):
        """Test get_pr returns mock when not configured"""
        pr = github_tool.get_pull_request(456)
        
        assert pr is not None
        assert pr["number"] == 456
        assert "Mock PR" in pr["title"]


class TestTemplateEngine:
    """Test template engine"""
    
    @pytest.fixture
    def engine(self):
        """Create template engine"""
        return TemplateEngine()
    
    def test_get_template(self, engine):
        """Test template loading"""
        template = engine.get_template("prd")
        
        assert template is not None
        assert "PRD" in template or "Product Requirements" in template
    
    def test_render_template(self, engine):
        """Test template rendering"""
        template = "# {{title}}\n\n{{description}}"
        variables = {
            "title": "Test Title",
            "description": "Test Description"
        }
        
        result = engine.render(template, variables)
        
        assert "Test Title" in result
        assert "Test Description" in result
    
    def test_render_handles_missing_variables(self, engine):
        """Test rendering with missing variables"""
        template = "# {{title}}\n\n{{description}}"
        variables = {
            "title": "Test Title"
            # description missing
        }
        
        result = engine.render(template, variables)
        
        assert "Test Title" in result
        assert "[TODO]" in result or "{{description}}" in result


class TestCodebaseSearch:
    """Test codebase search"""
    
    @pytest.fixture
    def search(self):
        """Create codebase search"""
        return CodebaseSearch()
    
    def test_get_context(self, search, mock_issue):
        """Test getting context"""
        context = search.get_context(mock_issue)
        
        assert "similar_files" in context
        assert "architecture_files" in context
        assert isinstance(context["similar_files"], list)
    
    def test_extract_keywords(self, search, mock_issue):
        """Test keyword extraction"""
        keywords = search._extract_keywords(mock_issue)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
