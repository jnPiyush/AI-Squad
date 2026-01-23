"""
Base Agent Class

Foundation for all AI-Squad agents.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import os

try:
    from github_copilot_sdk import CopilotSDK, Agent
except ImportError:
    CopilotSDK = None
    Agent = None

from ai_squad.core.config import Config
from ai_squad.tools.github import GitHubTool
from ai_squad.tools.templates import TemplateEngine
from ai_squad.tools.codebase import CodebaseSearch


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, config: Config, sdk: Optional[Any] = None):
        """
        Initialize base agent
        
        Args:
            config: AI-Squad configuration
            sdk: GitHub Copilot SDK instance
        """
        self.config = config
        self.sdk = sdk
        self.github = GitHubTool(config)
        self.templates = TemplateEngine()
        self.codebase = CodebaseSearch()
        self.agent_type = self.__class__.__name__.replace("Agent", "").lower()
        
        # Execution mode: "manual" (CLI) or "automated" (watch mode)
        self.execution_mode = "manual"
        
        # Lazy load status manager and validator
        self._status_manager = None
        self._workflow_validator = None
    
    @property
    def status_manager(self):
        """Get status manager instance"""
        if self._status_manager is None:
            from ai_squad.core.status import StatusManager
            self._status_manager = StatusManager(self.github)
        return self._status_manager
    
    @property
    def workflow_validator(self):
        """Get workflow validator instance"""
        if self._workflow_validator is None:
            from ai_squad.core.status import WorkflowValidator
            self._workflow_validator = WorkflowValidator(self.config, self.github)
        return self._workflow_validator
        
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_output_path(self, issue_number: int) -> Path:
        """Get output file path for this agent"""
        pass
    
    def execute(self, issue_number: int) -> Dict[str, Any]:
        """
        Execute agent for given issue
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Dict with execution result
        """
        try:
            # Validate prerequisites
            missing = self.workflow_validator.get_missing_prerequisites(
                issue_number, self.agent_type
            )
            
            if missing:
                return {
                    "success": False,
                    "error": f"Missing prerequisites: {', '.join(missing)}",
                    "missing_prerequisites": missing
                }
            
            # Get issue details
            issue = self.github.get_issue(issue_number)
            if not issue:
                return {
                    "success": False,
                    "error": f"Issue #{issue_number} not found"
                }
            
            # Update status to agent's start status
            start_status = self.status_manager.get_agent_start_status(self.agent_type)
            try:
                self.status_manager.transition(
                    issue_number,
                    start_status,
                    self.agent_type,
                    f"{self.agent_type.title()} agent started"
                )
            except Exception as e:
                print(f"Warning: Could not update status: {e}")
            
            # Get codebase context
            context = self.codebase.get_context(issue)
            
            # Execute agent logic
            result = self._execute_agent(issue, context)
            
            # Update status to agent's complete status if successful
            if result.get("success"):
                complete_status = self.status_manager.get_agent_complete_status(self.agent_type)
                try:
                    self.status_manager.transition(
                        issue_number,
                        complete_status,
                        self.agent_type,
                        f"{self.agent_type.title()} agent completed successfully"
                    )
                except Exception as e:
                    print(f"Warning: Could not update status: {e}")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @abstractmethod
    def _execute_agent(self, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent-specific execution logic
        
        Args:
            issue: GitHub issue details
            context: Codebase context
            
        Returns:
            Dict with execution result
        """
        pass
    
    def _save_output(self, content: str, output_path: Path) -> Path:
        """
        Save agent output to file
        
        Args:
            content: Content to save
            output_path: Output file path
            
        Returns:
            Path to saved file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return output_path
    
    def _get_skills(self) -> str:
        """Get relevant skills for this agent"""
        skills_config = self.config.get("skills", ["all"])
        
        if "all" in skills_config:
            # Load all skills
            skills_dir = Path(__file__).parent.parent / "skills"
            if skills_dir.exists():
                skills = []
                for skill_file in skills_dir.glob("**/SKILL.md"):
                    skills.append(skill_file.read_text(encoding="utf-8"))
                return "\n\n".join(skills)
        else:
            # Load specific skills
            skills_dir = Path(__file__).parent.parent / "skills"
            skills = []
            for skill_name in skills_config:
                skill_file = skills_dir / skill_name / "SKILL.md"
                if skill_file.exists():
                    skills.append(skill_file.read_text(encoding="utf-8"))
            return "\n\n".join(skills)
        
        return ""
