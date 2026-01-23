"""
Configuration management for AI-Squad
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class Config:
    """AI-Squad configuration"""
    
    DEFAULT_CONFIG = {
        "project": {
            "name": "My Project",
            "github_repo": None,
            "github_owner": None,
        },
        "agents": {
            "pm": {"enabled": True, "model": "gpt-4"},
            "architect": {"enabled": True, "model": "gpt-4"},
            "engineer": {"enabled": True, "model": "gpt-4"},
            "ux": {"enabled": True, "model": "gpt-4"},
            "reviewer": {"enabled": True, "model": "gpt-4"},
        },
        "output": {
            "prd_dir": "docs/prd",
            "adr_dir": "docs/adr",
            "specs_dir": "docs/specs",
            "ux_dir": "docs/ux",
            "reviews_dir": "docs/reviews",
        },
        "github": {
            "auto_create_issues": True,
            "auto_create_prs": False,
            "labels": {
                "epic": "type:epic",
                "feature": "type:feature",
                "story": "type:story",
                "bug": "type:bug",
            },
        },
        "skills": ["all"],  # or list specific skills
    }
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize configuration
        
        Args:
            data: Configuration dictionary
        """
        self.data = data
        
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from file
        
        Args:
            config_path: Path to squad.yaml (defaults to ./squad.yaml)
            
        Returns:
            Config instance
        """
        if config_path is None:
            config_path = Path.cwd() / "squad.yaml"
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            # Return default config
            return cls(cls.DEFAULT_CONFIG.copy())
        
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        # Merge with defaults
        merged = cls.DEFAULT_CONFIG.copy()
        cls._deep_merge(merged, data)
        
        return cls(merged)
    
    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> None:
        """Deep merge override into base"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save(self, path: Optional[Path] = None) -> None:
        """
        Save configuration to file
        
        Args:
            path: Path to save to (defaults to ./squad.yaml)
        """
        if path is None:
            path = Path.cwd() / "squad.yaml"
        
        with open(path, "w") as f:
            yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key
        
        Args:
            key: Key in dot notation (e.g., "agents.pm.model")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        parts = key.split(".")
        value = self.data
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    @property
    def github_repo(self) -> Optional[str]:
        """Get GitHub repository name"""
        return self.get("project.github_repo")
    
    @property
    def github_owner(self) -> Optional[str]:
        """Get GitHub repository owner"""
        return self.get("project.github_owner")
    
    @property
    def prd_dir(self) -> Path:
        """Get PRD output directory"""
        return Path(self.get("output.prd_dir", "docs/prd"))
    
    @property
    def adr_dir(self) -> Path:
        """Get ADR output directory"""
        return Path(self.get("output.adr_dir", "docs/adr"))
    
    @property
    def specs_dir(self) -> Path:
        """Get specs output directory"""
        return Path(self.get("output.specs_dir", "docs/specs"))
    
    @property
    def ux_dir(self) -> Path:
        """Get UX output directory"""
        return Path(self.get("output.ux_dir", "docs/ux"))
    
    @property
    def reviews_dir(self) -> Path:
        """Get reviews output directory"""
        return Path(self.get("output.reviews_dir", "docs/reviews"))
