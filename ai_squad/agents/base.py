"""
Base Agent Class

Foundation for all AI-Squad agents.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
import warnings
import logging
import importlib.util
import subprocess

logger = logging.getLogger(__name__)

# Detect GitHub Copilot SDK availability without importing unused symbols
SDK_AVAILABLE = importlib.util.find_spec("copilot") is not None

from ai_squad.core.config import Config
from ai_squad.tools.github import GitHubTool
from ai_squad.tools.templates import TemplateEngine
from ai_squad.tools.codebase import CodebaseSearch
from ai_squad.core.signal import MessagePriority
from ai_squad.core.handoff import HandoffReason
from ai_squad.core.ai_provider import get_ai_provider


class InvalidIssueNumberError(ValueError):
    """Raised when an invalid issue number is provided"""


class SDKExecutionError(RuntimeError):
    """Raised when SDK execution fails"""


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(
        self, 
        config: Config, 
        sdk: Optional[Any] = None,
            orchestration: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base agent
        
        Args:
            config: AI-Squad configuration
            sdk: GitHub Copilot SDK instance (legacy, deprecated)
            orchestration: Optional dict with shared orchestration managers:
                - 'workstate': WorkStateManager instance
                - 'signal': SignalManager instance
                - 'handoff': HandoffManager instance
                - 'strategy': BattlePlanManager instance
                - 'convoy': ConvoyManager instance
        """
        self.config = config
        self.sdk = sdk  # Legacy - kept for compatibility
        self.github = GitHubTool(config)
        self.templates = TemplateEngine(config=self.config.data)
        self.codebase = CodebaseSearch()
        self.agent_type = self.__class__.__name__.replace("Agent", "").lower()
        
        # NEW: AI Provider chain (Copilot -> OpenAI -> Azure -> Template)
        self.ai_provider = get_ai_provider(self.config.data)
        
        # Orchestration managers (shared instances via dependency injection)
        self.orchestration = orchestration or {}
        self.workstate = self.orchestration.get('workstate')
        self.signal = self.orchestration.get('signal')
        self.handoff = self.orchestration.get('handoff')
        self.strategy = self.orchestration.get('strategy')
        self.convoy = self.orchestration.get('convoy')
        
        # Track AI availability
        self._using_ai = self.ai_provider.is_ai_available()
        if not self._using_ai:
            warnings.warn(
                f"{self.__class__.__name__}: No AI provider available. "
                "Using template-based fallback (reduced capabilities). "
                "Set GITHUB_TOKEN, OPENAI_API_KEY, or AZURE_OPENAI_* env vars.",
                UserWarning,
                stacklevel=2
            )
        else:
            provider_name = self.ai_provider.provider_type.value
            logger.info("%s: Using %s for AI generation", self.__class__.__name__, provider_name)
        
        
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
    
    @staticmethod
    def validate_issue_number(issue_number: Any) -> int:
        """
        Validate and normalize issue number
        
        Args:
            issue_number: Issue number to validate
            
        Returns:
            Validated issue number as int
            
        Raises:
            InvalidIssueNumberError: If issue number is invalid
        """
        if issue_number is None:
            raise InvalidIssueNumberError("Issue number cannot be None")
        
        try:
            num = int(issue_number)
        except (TypeError, ValueError) as e:
            raise InvalidIssueNumberError(
                f"Issue number must be a valid integer, got: {issue_number}"
            ) from e
        
        if num <= 0:
            raise InvalidIssueNumberError(
                f"Issue number must be positive, got: {num}"
            )
        
        return num
        
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent"""
        raise NotImplementedError
    
    @abstractmethod
    def get_output_path(self, issue_number: int) -> Path:
        """Get output file path for this agent"""
        raise NotImplementedError
    
    def _call_ai(self, system_prompt: str, user_prompt: str, 
                 model: Optional[str] = None) -> Optional[str]:
        """
        Call AI provider chain for generation.
        
        Tries providers in order: Copilot -> OpenAI -> Azure OpenAI
        Falls back to templates if all fail.
        
        Args:
            system_prompt: System prompt for the agent
            user_prompt: User prompt with specific request
            model: Model to use (defaults to config)
            
        Returns:
            Generated content or None if all providers failed
        """
        model = model or self.config.get(f"agents.{self.agent_type}.model", "gpt-4")
        temperature = self.config.get(f"agents.{self.agent_type}.temperature", 0.5)
        
        response = self.ai_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            max_tokens=4096
        )
        
        if response:
            logger.info("AI generation successful via %s", response.provider.value)
            return response.content
        
        return None
    
    # Legacy method - redirects to new _call_ai
    def _call_sdk(self, system_prompt: str, user_prompt: str, 
                  model: Optional[str] = None) -> Optional[str]:
        """
        Legacy method - use _call_ai instead.
        
        Kept for backward compatibility.
        """
        return self._call_ai(system_prompt, user_prompt, model)

    def execute(self, issue_number: int) -> Dict[str, Any]:
        """
        Execute agent for given issue
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Dict with execution result
        """
        # Validate issue number first
        try:
            issue_number = self.validate_issue_number(issue_number)
        except InvalidIssueNumberError as e:
            return {
                "success": False,
                "error": str(e)
            }
        
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

            identity_payload = None
            identity_path = None
            try:
                from ai_squad.core.identity import IdentityManager

                git_meta = self._get_git_metadata()
                author = None
                author_data = issue.get("author") or issue.get("user")
                if isinstance(author_data, dict):
                    author = author_data.get("login") or author_data.get("name")
                elif isinstance(author_data, str):
                    author = author_data

                identity_mgr = IdentityManager(config=self.config.data)
                dossier = identity_mgr.build(
                    workspace_name=str(self.config.get("project.name", "AI-Squad Project")),
                    agents=[self.agent_type],
                    author=author,
                    commit_sha=git_meta.get("commit_sha"),
                    extra={
                        "issue_number": str(issue_number),
                        "issue_title": str(issue.get("title", "")),
                    },
                )
                identity_path = identity_mgr.save(dossier)
                identity_payload = dossier.to_dict()
            except (ValueError, OSError, RuntimeError) as e:
                logger.warning("Identity dossier build failed: %s", e)
            
            # Update status to agent's start status
            start_status = self.status_manager.get_agent_start_status(self.agent_type)
            try:
                self.status_manager.transition(
                    issue_number,
                    start_status,
                    self.agent_type,
                    f"{self.agent_type.title()} agent started"
                )
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.warning("Could not update status: %s", e)
            
            # Get codebase context
            context = self.codebase.get_context(issue)
            if identity_payload:
                context["identity_dossier"] = identity_payload
            if identity_path:
                context["identity_path"] = str(identity_path)

            # Update operational graph for issue/agent linkage
            try:
                from ai_squad.core.operational_graph import OperationalGraph, NodeType, EdgeType

                graph = OperationalGraph(config=self.config.data)
                issue_node_id = f"issue-{issue_number}"
                graph.add_node(
                    issue_node_id,
                    NodeType.WORK_ITEM,
                    {"title": issue.get("title", ""), "issue_number": issue_number},
                )
                graph.add_node(self.agent_type, NodeType.AGENT, {"agent": self.agent_type})
                graph.add_edge(issue_node_id, self.agent_type, EdgeType.OWNS, {"source": "agent_execute"})
            except (ValueError, OSError, RuntimeError) as e:
                logger.warning("Operational graph update failed: %s", e)
            
            # Execute agent logic
            result = self._execute_agent(issue, context)
            
            # Add AI provider usage info
            result["using_ai"] = self._using_ai
            result["ai_provider"] = self.ai_provider.provider_type.value if self._using_ai else "template"
            if identity_payload:
                result["identity_dossier"] = identity_payload
            if identity_path:
                result["identity_path"] = str(identity_path)

            # Attach artifacts to work items when possible
            try:
                if self.workstate and issue_number:
                    work_item = self.workstate.get_work_item_by_issue(issue_number)
                    if work_item:
                        artifact_paths = []
                        if "file_path" in result:
                            artifact_paths.append(result["file_path"])
                        if "artifacts" in result and isinstance(result["artifacts"], list):
                            artifact_paths.extend(result["artifacts"])
                        for artifact in artifact_paths:
                            if artifact:
                                self.workstate.add_artifact(work_item.id, str(artifact))
            except (AttributeError, ValueError, OSError) as e:
                logger.warning("Failed to attach artifacts: %s", e)
            
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
                except (ConnectionError, TimeoutError, OSError) as e:
                    logger.warning("Could not update status: %s", e)
            
            return result
            
        except SDKExecutionError as e:
            return {
                "success": False,
                "error": f"AI provider error: {e}",
                "using_ai": self._using_ai
            }
        except (ValueError, KeyError, IOError) as e:
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
        raise NotImplementedError
    
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

    def _get_git_metadata(self) -> Dict[str, Optional[str]]:
        """Best-effort git metadata for provenance."""
        metadata = {"commit_sha": None, "author": None}
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                check=False,
            )
            if commit.returncode == 0:
                metadata["commit_sha"] = commit.stdout.strip()

            author = subprocess.run(
                ["git", "config", "user.name"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                check=False,
            )
            if author.returncode == 0:
                metadata["author"] = author.stdout.strip()
        except (OSError, ValueError) as e:
            logger.debug("Git metadata unavailable: %s", e)
        return metadata
    
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
    
    def _load_prompt_template(self, prompt_name: str) -> str:
        """
        Load prompt template from external file
        
        Args:
            prompt_name: Prompt name (pm, architect, engineer, ux, reviewer)
            
        Returns:
            Prompt template content or empty string if not found
        """
        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompts_dir / f"{prompt_name}.md"
        
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return ""
    
    def _render_prompt(self, template: str, **kwargs) -> str:
        """
        Render prompt template with config values
        
        Args:
            template: Prompt template with {placeholders}
            **kwargs: Additional variables to substitute
            
        Returns:
            Rendered prompt
        """
        # Get config values for common placeholders
        values = {
            "skills": kwargs.get("skills", ""),
            "test_coverage_threshold": self.config.test_coverage_threshold,
            "test_pyramid_unit": self.config.test_pyramid.get("unit", 70),
            "test_pyramid_integration": self.config.test_pyramid.get("integration", 20),
            "test_pyramid_e2e": self.config.test_pyramid.get("e2e", 10),
            "wcag_version": self.config.wcag_version,
            "wcag_level": self.config.wcag_level,
            "contrast_ratio": self.config.contrast_ratio,
            "breakpoint_mobile": self.config.breakpoints.get("mobile", "320px-767px"),
            "breakpoint_tablet": self.config.breakpoints.get("tablet", "768px-1023px"),
            "breakpoint_desktop": self.config.breakpoints.get("desktop", "1024px+"),
            "touch_target_min": self.config.touch_target_min,
            "response_time_p95_ms": self.config.response_time_p95_ms,
            "throughput_req_per_sec": self.config.throughput_req_per_sec,
        }
        values.update(kwargs)
        
        # Simple placeholder replacement
        result = template
        for key, value in values.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        return result
    
    # NEW: Orchestration Helper Methods
    
    def create_work_item(self, title: str, description: str, 
                         issue_number: Optional[int] = None, **kwargs) -> Optional[str]:
        """
        Create a work item in the orchestration system
        
        Args:
            title: Work item title
            description: Work item description
            issue_number: Associated GitHub issue number
            **kwargs: Additional work item fields
            
        Returns:
            Work item ID or None if orchestration not available
        """
        if not self.workstate:
            logger.warning("WorkStateManager not available, skipping work item creation")
            return None
        
        item = self.workstate.create_work_item(
            title=title,
            description=description,
            issue_number=issue_number,
            **kwargs
        )
        return item.id
    
    def send_message(self, recipient: str, subject: str, body: str,
                     priority: str = "normal", **kwargs) -> Optional[str]:
        """
        Send a message to another agent
        
        Args:
            recipient: Recipient agent type ("pm", "architect", etc.)
            subject: Message subject
            body: Message body
            priority: Message priority ("low", "normal", "high", "urgent")
            **kwargs: Additional message fields
            
        Returns:
            Message ID or None if signal not available
        """
        if not self.signal:
            logger.warning("SignalManager not available, skipping message send")
            return None
        
        return self.signal.send_message(
            sender=self.agent_type,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=MessagePriority(priority),
            **kwargs
        )
    
    def check_messages(self, unread_only: bool = True) -> List:
        """
        Check messages for this agent
        
        Args:
            unread_only: Only return unread messages
            
        Returns:
            List of messages (empty if signal not available)
        """
        if not self.signal:
            return []
        
        return self.signal.get_inbox(
            recipient=self.agent_type,
            unread_only=unread_only
        )
    
    def initiate_handoff(self, to_agent: str, work_item_id: str,
                          reason: str, summary: str, **kwargs) -> Optional[str]:
        """
        Initiate work handoff to another agent
        
        Args:
            to_agent: Target agent type
            work_item_id: Work item ID being handed off
            reason: Handoff reason ("workflow", "escalation", "specialization", etc.)
            summary: Summary of work done so far
            **kwargs: Additional handoff context
            
        Returns:
            Handoff ID or None if handoff manager not available
        """
        if not self.handoff:
            logger.warning("HandoffManager not available, skipping handoff")
            return None
        
        return self.handoff.initiate_handoff(
            from_agent=self.agent_type,
            to_agent=to_agent,
            work_item_id=work_item_id,
            reason=HandoffReason(reason),
            summary=summary,
            **kwargs
        )
    
    def accept_handoff(self, handoff_id: str, message: Optional[str] = None) -> None:
        """
        Accept a pending handoff
        
        Args:
            handoff_id: Handoff ID
            message: Optional acceptance message
        """
        if not self.handoff:
            logger.warning("HandoffManager not available, cannot accept handoff")
            return
        
        self.handoff.accept_handoff(handoff_id, message)
    
    def get_pending_handoffs(self) -> List:
        """
        Get pending handoffs for this agent
        
        Returns:
            List of pending handoffs (empty if handoff manager not available)
        """
        if not self.handoff:
            return []
        
        return self.handoff.get_pending_handoffs(to_agent=self.agent_type)

