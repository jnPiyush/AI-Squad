"""
Configuration management for AI-Squad
"""
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
            "pm": {"enabled": True, "model": "claude-sonnet-4.5"},
            "architect": {"enabled": True, "model": "claude-sonnet-4.5"},
            "engineer": {"enabled": True, "model": "claude-sonnet-4.5"},
            "ux": {"enabled": True, "model": "claude-sonnet-4.5"},
            "reviewer": {"enabled": True, "model": "claude-sonnet-4.5"},
        },
        "output": {
            "prd_dir": "docs/prd",
            "adr_dir": "docs/adr",
            "specs_dir": "docs/specs",
            "architecture_dir": "docs/architecture",
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
        "quality": {
            "test_coverage_threshold": 80,
            "test_pyramid": {
                "unit": 70,
                "integration": 20,
                "e2e": 10,
            },
        },
        "performance": {
            "response_time_p95_ms": 200,
            "throughput_req_per_sec": 1000,
            "concurrent_users": 100,
        },
        "accessibility": {
            "wcag_version": "2.1",
            "wcag_level": "AA",
            "contrast_ratio": 4.5,
        },
        "routing": {
            "allowed_capability_tags": [],
            "denied_capability_tags": [],
            "required_trust_levels": [],
            "max_data_sensitivity": "restricted",
            "trust_level": "high",
            "data_sensitivity": "internal",
            "priority": "normal",
            "warn_block_rate": 0.25,
            "critical_block_rate": 0.5,
            "circuit_breaker_block_rate": 0.7,
            "throttle_block_rate": 0.5,
            "min_events": 5,
            "window": 200,
            "enforce_cli_routing": False,
        },
        "design": {
            "breakpoints": {
                "mobile": "320px-767px",
                "tablet": "768px-1023px",
                "desktop": "1024px+",
            },
            "touch_target_min": "44px",
        },
        "runtime": {
            "provider": "copilot",
            "provider_order": ["copilot", "openai", "azure_openai"],
            "command": None,
            "args": [],
            "prompt_mode": "none",
            "base_dir": ".squad",
        },
        "hooks": {
            "enabled": True,
            "use_git_worktree": False,
            "hooks_dir": ".squad/hooks",
        },
        "theater": {
            "default": "default",
        },
        "patrol": {
            "stale_minutes": 120,
            "statuses": ["in_progress", "hooked", "blocked"],
        },
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
        
        with open(config_path, encoding="utf-8") as f:
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
        
        with open(path, "w", encoding="utf-8") as f:
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
    def architecture_dir(self) -> Path:
        """Get architecture output directory"""
        return Path(self.get("output.architecture_dir", "docs/architecture"))
    
    @property
    def ux_dir(self) -> Path:
        """Get UX output directory"""
        return Path(self.get("output.ux_dir", "docs/ux"))
    
    @property
    def reviews_dir(self) -> Path:
        """Get reviews output directory"""
        return Path(self.get("output.reviews_dir", "docs/reviews"))

    # Quality thresholds
    @property
    def test_coverage_threshold(self) -> int:
        """Get test coverage threshold (%)"""
        return self.get("quality.test_coverage_threshold", 80)
    
    @property
    def test_pyramid(self) -> Dict[str, int]:
        """Get test pyramid distribution"""
        return self.get("quality.test_pyramid", {"unit": 70, "integration": 20, "e2e": 10})
    
    # Performance requirements
    @property
    def response_time_p95_ms(self) -> int:
        """Get p95 response time target (ms)"""
        return self.get("performance.response_time_p95_ms", 200)
    
    @property
    def throughput_req_per_sec(self) -> int:
        """Get throughput target (req/s)"""
        return self.get("performance.throughput_req_per_sec", 1000)
    
    # Accessibility
    @property
    def wcag_version(self) -> str:
        """Get WCAG version"""
        return self.get("accessibility.wcag_version", "2.1")
    
    @property
    def wcag_level(self) -> str:
        """Get WCAG compliance level"""
        return self.get("accessibility.wcag_level", "AA")
    
    @property
    def contrast_ratio(self) -> float:
        """Get minimum contrast ratio"""
        return self.get("accessibility.contrast_ratio", 4.5)
    
    # Design breakpoints
    @property
    def breakpoints(self) -> Dict[str, str]:
        """Get responsive design breakpoints"""
        return self.get("design.breakpoints", {
            "mobile": "320px-767px",
            "tablet": "768px-1023px",
            "desktop": "1024px+"
        })
    
    @property
    def touch_target_min(self) -> str:
        """Get minimum touch target size"""
        return self.get("design.touch_target_min", "44px")
