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

logger = logging.getLogger(__name__)

# Detect GitHub Copilot SDK availability without importing unused symbols
SDK_AVAILABLE = importlib.util.find_spec("github_copilot_sdk") is not None

from ai_squad.core.config import Config
from ai_squad.tools.github import GitHubTool
from ai_squad.tools.templates import TemplateEngine
from ai_squad.tools.codebase import CodebaseSearch
from ai_squad.core.mailbox import MessagePriority
from ai_squad.core.handoff import HandoffReason
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
            sdk: GitHub Copilot SDK instance (preferred for AI generation)
            orchestration: Optional dict with shared orchestration managers:
                - 'workstate': WorkStateManager instance
                - 'mailbox': MailboxManager instance
                - 'handoff': HandoffManager instance
                - 'formula': FormulaManager instance
                - 'convoy': ConvoyManager instance
        """
        self.config = config
        self.sdk = sdk
        self.github = GitHubTool(config)
        self.templates = TemplateEngine()
        self.codebase = CodebaseSearch()
        self.agent_type = self.__class__.__name__.replace("Agent", "").lower()
        
        # Orchestration managers (shared instances via dependency injection)
        self.orchestration = orchestration or {}
        self.workstate = self.orchestration.get('workstate')
        self.mailbox = self.orchestration.get('mailbox')
        self.handoff = self.orchestration.get('handoff')
        self.formula = self.orchestration.get('formula')
        self.convoy = self.orchestration.get('convoy')
        
        # Track SDK availability for this agent
        self._using_sdk = self.sdk is not None
        if not self._using_sdk:
            warnings.warn(
                f"{self.__class__.__name__}: GitHub Copilot SDK not available. "
                "Using template-based fallback (reduced AI capabilities). "
                "Install with: pip install github-copilot-sdk",
                UserWarning,
                stacklevel=2
            )
        
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
    
    def _call_sdk(self, system_prompt: str, user_prompt: str, 
                  model: Optional[str] = None) -> Optional[str]:
        """
        Call GitHub Copilot SDK for AI generation
        
        Args:
            system_prompt: System prompt for the agent
            user_prompt: User prompt with specific request
            model: Model to use (defaults to config)
            
        Returns:
            Generated content or None if SDK not available/failed
        """
        if not self.sdk:
            return None
        
        model = model or self.config.get(f"agents.{self.agent_type}.model", "gpt-4")
        
        try:
            # Call SDK's chat completion
            response = self.sdk.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.get(f"agents.{self.agent_type}.temperature", 0.5),
                max_tokens=4096
            )
            
            if response and response.choices:
                return response.choices[0].message.content
            
        except AttributeError:
            # SDK might have different API - try alternative
            try:
                response = self.sdk.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model
                )
                return response.get("content") if isinstance(response, dict) else str(response)
            except (AttributeError, TypeError) as e:
                logger.warning("SDK API not compatible: %s", e)
                
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            logger.error("SDK call failed: %s", e)
            raise SDKExecutionError(f"SDK execution failed: {e}") from e
        
        return None

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
            
            # Execute agent logic
            result = self._execute_agent(issue, context)
            
            # Add SDK usage info
            result["using_sdk"] = self._using_sdk
            
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
                "error": f"SDK error: {e}",
                "using_sdk": self._using_sdk
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
            Message ID or None if mailbox not available
        """
        if not self.mailbox:
            logger.warning("MailboxManager not available, skipping message send")
            return None
        
        return self.mailbox.send_message(
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
            List of messages (empty if mailbox not available)
        """
        if not self.mailbox:
            return []
        
        return self.mailbox.get_inbox(
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

