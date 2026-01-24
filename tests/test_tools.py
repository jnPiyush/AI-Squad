"""
Tests for tools
"""
import pytest

from ai_squad.tools.github import GitHubTool
from ai_squad.tools.templates import TemplateEngine
from ai_squad.tools.codebase import CodebaseSearch


class TestGitHubTool:
    """Test GitHub integration"""
    
    @pytest.fixture
    def github_tool(self, mock_config, monkeypatch):
        """Create GitHub tool with no auth"""
        # Clear any env token
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        
        tool = GitHubTool(mock_config)
        tool.token = None  # Ensure no token
        tool.set_auth_cache(checked=True, authenticated=False)
        return tool
    
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

    def test_project_tier_wins_by_default(self, temp_project_dir):
        """Project-level templates should override bundled ones when present."""

        project_templates = temp_project_dir / ".squad" / "templates"
        project_templates.mkdir(parents=True)
        (project_templates / "prd.md").write_text("project-prd", encoding="utf-8")

        engine = TemplateEngine(workspace_root=temp_project_dir)
        content, trace = engine.get_template("prd", include_trace=True)

        assert content == "project-prd"
        assert trace.resolved["tier"] == "project"
        assert any(a["exists"] for a in trace.attempts)

    def test_force_tier_override_uses_system(self, temp_project_dir, monkeypatch):
        """Force-tier override should bypass project/org templates."""

        project_templates = temp_project_dir / ".squad" / "templates"
        project_templates.mkdir(parents=True)
        (project_templates / "prd.md").write_text("project-prd", encoding="utf-8")

        monkeypatch.setenv("AI_SQUAD_TEMPLATE_FORCE_TIER", "system")
        engine = TemplateEngine(workspace_root=temp_project_dir)
        content, trace = engine.get_template("prd", include_trace=True)

        assert "Product Requirements" in content or "PRD" in content
        assert trace.order == ["system"]
        assert trace.resolved and trace.resolved["tier"] == "system"


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
        keywords = search.extract_keywords(mock_issue)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
