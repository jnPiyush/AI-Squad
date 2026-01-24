"""
Agent Executor

Executes agents using GitHub Copilot SDK as the primary choice.
Falls back to template-based generation if SDK is not available.
"""
import os
import logging
import warnings
from typing import Dict, Any, Optional

from ai_squad.agents.base import InvalidIssueNumberError, SDKExecutionError

# GitHub Copilot SDK - Primary choice for AI-powered agent execution
try:
    from github_copilot_sdk import CopilotSDK, Agent
    SDK_AVAILABLE = True
except ImportError:
    CopilotSDK = None
    Agent = None
    SDK_AVAILABLE = False

from ai_squad.core.config import Config
from ai_squad.agents.product_manager import ProductManagerAgent
from ai_squad.agents.architect import ArchitectAgent
from ai_squad.agents.engineer import EngineerAgent
from ai_squad.agents.ux_designer import UXDesignerAgent
from ai_squad.agents.reviewer import ReviewerAgent
from ai_squad.core.captain import Captain  # NEW: Meta-agent coordinator (in core, not agents!)
from ai_squad.core.battle_plan import (
    BattlePlanExecutor,
    BattlePlanManager,
)
from ai_squad.core.convoy import ConvoyManager  # NEW: Parallel execution
from ai_squad.core.workstate import WorkStateManager  # NEW: Work tracking
from ai_squad.core.signal import SignalManager
from ai_squad.core.handoff import HandoffManager

logger = logging.getLogger(__name__)


class AgentExecutionError(RuntimeError):
    """Raised when agent execution fails"""


class AgentExecutor:
    """
    Execute AI agents using GitHub Copilot SDK.
    
    The executor prioritizes SDK-based AI generation for best results.
    Falls back to template-based generation with reduced capabilities
    when SDK is not available.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Config] = None,
        workstate_manager: Optional[Any] = None,
        strategy_manager: Optional[Any] = None,
        convoy_manager: Optional[Any] = None,
        signal_manager: Optional[Any] = None,
        handoff_manager: Optional[Any] = None
    ):
        """Initialize agent executor with optional injected managers."""
        self.config = config or Config.load(config_path)
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        if not self.github_token:
            warnings.warn(
                "GITHUB_TOKEN environment variable not set; using placeholder token for local/testing.",
                UserWarning
            )
            self.github_token = "ghp_mock_token"
        
        # Initialize SDK - this is our primary choice for AI generation
        self.sdk = None
        self._sdk_initialized = False
        
        if SDK_AVAILABLE:
            try:
                self.sdk = CopilotSDK(token=self.github_token)
                self._sdk_initialized = True
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                warnings.warn(
                    f"Failed to initialize GitHub Copilot SDK: {e}. "
                    "Falling back to template-based generation.",
                    UserWarning
                )
        else:
            warnings.warn(
                "GitHub Copilot SDK not installed. Using template-based fallback "
                "(reduced AI capabilities). Install with: pip install github-copilot-sdk",
                UserWarning
            )
        
        # NEW: Create shared orchestration managers FIRST (single source of truth)
        from pathlib import Path
        workspace_root = Path(getattr(self.config, "workspace_root", Path.cwd()))
        self.workstate_mgr = workstate_manager or WorkStateManager(workspace_root=workspace_root)
        self.signal_mgr = signal_manager or SignalManager(workspace_root=workspace_root)
        self.handoff_mgr = handoff_manager or HandoffManager(
            work_state_manager=self.workstate_mgr,
            signal_manager=self.signal_mgr,
            workspace_root=workspace_root
        )
        self.strategy_mgr = strategy_manager or BattlePlanManager(workspace_root=workspace_root)
        
        # Async agent executor for convoy with error handling
        async def _async_agent_executor(agent_type: str, work_item_id: str, 
                                         context: Optional[Dict[str, Any]] = None) -> str:
            """Async wrapper for agent execution in convoys with error handling"""
            try:
                work_item = self.workstate_mgr.get_work_item(work_item_id)
                if not work_item or not work_item.issue_number:
                    raise ValueError(f"Work item {work_item_id} has no issue number")
                
                result = self.execute(agent_type, work_item.issue_number)
                if not result.get("success"):
                    raise RuntimeError(result.get("error", "Unknown error"))
                
                return str(result.get("output", "Completed"))
            except Exception as e:
                logger.error(f"Convoy agent execution failed for {work_item_id}: {e}")
                raise
        
        self.convoy_mgr = convoy_manager or ConvoyManager(
            work_state_manager=self.workstate_mgr,
            agent_executor=_async_agent_executor
        )
        
        # Create orchestration context to inject into agents (DI pattern)
        self.orchestration = {
            'workstate': self.workstate_mgr,
            'signal': self.signal_mgr,
            'handoff': self.handoff_mgr,
            'strategy': self.strategy_mgr,
            'convoy': self.convoy_mgr
        }
        
        # Agent mapping - pass SDK AND shared orchestration managers
        self.agents = {
            "pm": ProductManagerAgent(self.config, self.sdk, self.orchestration),
            "architect": ArchitectAgent(self.config, self.sdk, self.orchestration),
            "engineer": EngineerAgent(self.config, self.sdk, self.orchestration),
            "ux": UXDesignerAgent(self.config, self.sdk, self.orchestration),
            "reviewer": ReviewerAgent(self.config, self.sdk, self.orchestration),
            "captain": Captain(self.config, self.sdk, self.orchestration),
        }
    
    @property
    def using_sdk(self) -> bool:
        """Check if SDK is being used for AI generation"""
        return self._sdk_initialized and self.sdk is not None
    
    def execute(self, agent_type: str, issue_number: int) -> Dict[str, Any]:
        """
        Execute an agent for a given issue
        
        Args:
            agent_type: Type of agent ("pm", "architect", "engineer", "ux", "reviewer")
            issue_number: GitHub issue number
            
        Returns:
            Dict with execution result including SDK usage status
        """
        if agent_type not in self.agents:
            return {
                "success": False,
                "error": f"Unknown agent type: {agent_type}. Available: {list(self.agents.keys())}"
            }
        
        agent = self.agents[agent_type]
        
        try:
            result = agent.execute(issue_number)
            # Add SDK usage info to result
            result["using_sdk"] = self.using_sdk
            if not self.using_sdk:
                result["notice"] = (
                    "Generated using template-based fallback. "
                    "Install github-copilot-sdk for AI-powered generation."
                )
            return result
            
        except InvalidIssueNumberError as e:
            logger.error("Invalid issue number: %s", e)
            return {
                "success": False,
                "error": f"Invalid issue number: {e}",
                "using_sdk": self.using_sdk
            }
        except SDKExecutionError as e:
            logger.error("SDK execution failed: %s", e)
            return {
                "success": False,
                "error": f"SDK error: {e}",
                "using_sdk": self.using_sdk
            }
        except (ValueError, KeyError, IOError, OSError) as e:
            logger.error("Agent execution failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "using_sdk": self.using_sdk
            }
    
    def list_agents(self) -> list:
        """Get list of available agents"""
        return list(self.agents.keys())
    
    def execute_strategy(
        self,
        strategy_name: str,
        issue_number: int,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a combat strategy workflow synchronously."""
        import asyncio

        async def _agent_callback(
            issue_number: int,
            agent_type: str,
            action: Optional[str] = None,
            step: Optional[Dict[str, Any]] = None,
            **_: Any,
        ) -> Dict[str, Any]:
            return self.execute(agent_type, issue_number)

        try:
            executor = BattlePlanExecutor(
                strategy_manager=self.strategy_mgr,
                work_state_manager=self.workstate_mgr,
                agent_executor=_agent_callback,
            )

            execution_id = asyncio.run(
                executor.execute_strategy(
                    strategy_name=strategy_name,
                    issue_number=issue_number,
                    variables=variables or {},
                )
            )

            execution = executor.get_execution(execution_id)

            return {
                "success": True,
                "execution_id": execution_id,
                "status": execution.status if execution else "unknown",
                "using_sdk": self.using_sdk,
            }

        except (ValueError, KeyError, IOError, OSError) as e:
            logger.error("Strategy execution failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "using_sdk": self.using_sdk,
            }
    
    def execute_convoy(self, convoy_id: str) -> Dict[str, Any]:
        """
        Execute a convoy (parallel work batch)
        
        Args:
            convoy_id: ID of the convoy to execute
            
        Returns:
            Dict with execution result
        """
        try:
            # Execute convoy using async runtime
            import asyncio
            convoy = asyncio.run(self.convoy_mgr.execute_convoy(convoy_id))
            
            return {
                "success": True,
                "convoy_id": convoy_id,
                "status": convoy.status.value,
                "completed": len([m for m in convoy.members if m.status == "completed"]),
                "failed": len([m for m in convoy.members if m.status == "failed"]),
                "using_sdk": self.using_sdk
            }
            
        except (ValueError, KeyError, IOError, OSError) as e:
            logger.error("Convoy execution failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "using_sdk": self.using_sdk
            }
    
    def coordinate_work(self, work_item_ids: list) -> Dict[str, Any]:
        """
        Use Captain to coordinate multiple work items
        
        Args:
            work_item_ids: List of work item IDs to coordinate
            
        Returns:
            Dict with coordination result
        """
        try:
            captain = self.agents["captain"]
            
            # Captain analyzes work items and creates execution plan
            result = captain.coordinate(
                work_items=work_item_ids,
                workstate_manager=self.workstate_mgr,
                plan_manager=None,
                convoy_manager=self.convoy_mgr
            )
            
            return {
                "success": True,
                "plan": result,
                "using_sdk": self.using_sdk
            }
            
        except (ValueError, KeyError, IOError, OSError) as e:
            logger.error("Coordination failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "using_sdk": self.using_sdk
            }



