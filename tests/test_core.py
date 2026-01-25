"""
Tests for core modules
"""
from pathlib import Path
import yaml

from ai_squad.core.config import Config
from ai_squad.core.init_project import initialize_project


class TestConfig:
    """Test configuration management"""
    
    def test_default_config(self):
        """Test default config"""
        config = Config.load()
        
        assert config.get("project.name") is not None
        assert config.get("agents.pm.enabled") == True
        assert config.get("agents.pm.model") == "claude-sonnet-4.5"
    
    def test_custom_config(self, tmp_path):
        """Test custom config loading"""
        config_path = tmp_path / "squad.yaml"
        
        custom_config = {
            "project": {
                "name": "Custom Project"
            },
            "agents": {
                "pm": {
                    "model": "gpt-3.5-turbo"
                }
            }
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(custom_config, f)
        
        config = Config.load(config_path)
        
        assert config.get("project.name") == "Custom Project"
        assert config.get("agents.pm.model") == "gpt-3.5-turbo"
        # Merged with defaults
        assert config.get("agents.pm.enabled") == True
    
    def test_config_save(self, tmp_path):
        """Test config saving"""
        config = Config(Config.DEFAULT_CONFIG.copy())
        config_path = tmp_path / "squad.yaml"
        
        config.save(config_path)
        
        assert config_path.exists()
        
        # Load and verify
        loaded = Config.load(config_path)
        assert loaded.get("project.name") == config.get("project.name")
    
    def test_config_properties(self):
        """Test config properties"""
        config = Config({
            "project": {
                "github_repo": "test-repo",
                "github_owner": "test-owner"
            },
            "output": {
                "prd_dir": "custom/prd"
            }
        })
        
        assert config.github_repo == "test-repo"
        assert config.github_owner == "test-owner"
        assert config.prd_dir == Path("custom/prd")


class TestInitProject:
    """Test project initialization"""
    
    def test_init_creates_structure(self, tmp_path, monkeypatch):
        """Test init creates all necessary files"""
        monkeypatch.chdir(tmp_path)
        
        result = initialize_project()
        
        assert result["success"] == True
        assert (tmp_path / "squad.yaml").exists()
        assert (tmp_path / "docs" / "prd").exists()
        assert (tmp_path / "docs" / "adr").exists()
    
    def test_init_without_force_fails(self, tmp_path, monkeypatch):
        """Test init without force fails if config exists"""
        monkeypatch.chdir(tmp_path)
        
        # First init
        result1 = initialize_project()
        assert result1["success"] == True
        
        # Second init without force
        result2 = initialize_project(force=False)
        assert result2["success"] == False
        assert "already initialized" in result2["error"].lower()
    
    def test_init_with_force_overwrites(self, tmp_path, monkeypatch):
        """Test init with force overwrites"""
        monkeypatch.chdir(tmp_path)
        
        # First init
        initialize_project()
        
        # Modify config
        config_path = tmp_path / "squad.yaml"
        with open(config_path, "a", encoding="utf-8") as f:
            f.write("\n# Modified")
        
        # Second init with force
        result = initialize_project(force=True)
        assert result["success"] == True
        
        # Config should be reset
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
            assert "# Modified" not in content
